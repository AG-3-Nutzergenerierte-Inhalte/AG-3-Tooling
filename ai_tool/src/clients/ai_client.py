# src/clients/ai_client.py
import logging
import json
import asyncio
import datetime
from typing import List, Dict, Any, Optional

from google.cloud import aiplatform
from google.api_core import exceptions as api_core_exceptions
from google.auth import exceptions
from jsonschema import validate, ValidationError
from vertexai.generative_models import GenerativeModel, GenerationConfig, Part

from config import app_config
from constants import *

logger = logging.getLogger(__name__)

class AiClient:
    """A client for all Vertex AI model interactions, using the aiplatform SDK."""

    def __init__(self, config):
        """
        Initializes the AiClient.

        Args:
            config: The application configuration object.
        """
        self.config = config
        
        with open(PROMPT_CONFIG_PATH, 'r', encoding='utf-8') as f:
            prompt_config = json.load(f)
        
        base_system_message = prompt_config.get("system_message", "")
        if not base_system_message:
            logger.warning("System message is empty. AI calls will not have a predefined persona.")

        # Append the current date to the system prompt
        current_date = datetime.date.today().strftime("%Y-%m-%d")
        self.system_message = f"{base_system_message}\n\nImportant: Today's date is {current_date}."

        # Initialize aiplatform with the configured region, as Vertex AI services are regionalized.
        aiplatform.init(project=config.gcp_project_id, location=config.region)

        # Default model instance
        self.generative_model = GenerativeModel(
            GROUND_TRUTH_MODEL, system_instruction=self.system_message
        )
        
        # Cache for alternative model instances
        self._model_cache = {GROUND_TRUTH_MODEL: self.generative_model}
        
        self.semaphore = asyncio.Semaphore(config.max_concurrent_ai_requests)

        logger.info(f"Vertex AI Client instantiated for project '{config.gcp_project_id}' in region '{config.region}'.")
        logger.info(f"System Message Context includes today's date: {current_date}")

    def _get_model_instance(self, model_name: str) -> GenerativeModel:
        """
        Get or create a GenerativeModel instance for the specified model.
        
        Args:
            model_name: The model name (e.g., 'gemini-1.5-pro', 'gemini-1.5-flash')
            
        Returns:
            GenerativeModel instance for the specified model
        """
        if model_name not in self._model_cache:
            logger.info(f"Creating new model instance for '{model_name}'")
            self._model_cache[model_name] = GenerativeModel(
                model_name, system_instruction=self.system_message
            )
        return self._model_cache[model_name]

    def _prepare_generation_config(self, json_schema: Dict[str, Any]) -> GenerationConfig:
        """Prepares and converts the JSON schema for the GenerationConfig."""
        try:
            schema_for_api = json.loads(json.dumps(json_schema))
            schema_for_api.pop("$schema", None)
        except Exception as e:
            logger.error(f"Failed to process JSON schema before API call: {e}")
            raise ValueError("Invalid JSON schema provided.") from e

        # Initialization validates the schema compatibility. If the conversion failed or the schema is otherwise invalid, 
        # this might raise exceptions (including the AttributeError we aim to fix).
        try:
            return GenerationConfig(
                response_mime_type="application/json",
                response_schema=schema_for_api,
                max_output_tokens=API_MAX_OUTPUT_TOKEN,
                temperature=API_TEMPERATURE,
            )
        except Exception as e:
            logger.error(f"Failed to initialize GenerationConfig. Schema might still be incompatible: {e}", exc_info=True)
            raise ValueError(f"Invalid or incompatible GenerationConfig: {e}") from e

    def _process_response(self, response) -> Dict[str, Any]:
        """Processes the model response, handling finish reasons and JSON parsing."""
        if not response.candidates:
            raise ValueError("The model response contained no candidates.")

        # --- Robust Finish Reason Check ---
        # We check the integer value of the finish reason enum because accessing .name 
        # can sometimes cause 'AttributeError' in certain environments (Protobuf conflicts).
        # Expected values (from GAPIC definition): 1 = STOP, 2 = MAX_TOKENS.

        finish_reason_obj = response.candidates[0].finish_reason
        try:
            # Attempt to cast to int (standard behavior for proto.Enum)
            finish_reason_int = int(finish_reason_obj)
        except TypeError:
            logger.error(
                f"Could not cast finish reason to integer. Type: {type(finish_reason_obj)}. Value: {finish_reason_obj}."
            )
            # Raise TypeError to distinguish this specific issue from generic ValueErrors.
            raise TypeError(f"Could not determine finish reason integer value.")

        if finish_reason_int not in [1, 2]:
            # Try to get the name for logging, fallback to int.
            reason_display = f"Code {finish_reason_int}"
            try:
                # We attempt to access .name here only for logging purposes, inside a safe block.
                if hasattr(finish_reason_obj, 'name') and finish_reason_obj.name:
                    reason_display = f"{finish_reason_obj.name} (Code {finish_reason_int})"
            except Exception:
                pass # Ignore errors during logging fallback
            
            raise ValueError(f"Model finished with non-OK reason: {reason_display}")
        # --- End Robust Finish Reason Check ---

        try:
            response_json = json.loads(response.text)
        except json.JSONDecodeError as e:
            # Clean JSON error without the full traceback
            raise ValueError(f"Failed to parse model response as JSON: {str(e).split(':')[0]}")
        
        return response_json

    async def generate_json_response(
        self, 
        prompt: str, 
        json_schema: Dict[str, Any], 
        gcs_uris: List[str] = None, 
        request_context_log: str = "Generic AI Request",
        model_override: Optional[str] = None,
        max_retries: int = None
    ) -> Dict[str, Any]:
        """
        Generates a JSON response from the AI model, enforcing a specific schema and
        optionally providing GCS files as context. Implements an async retry loop
        with exponential backoff and connection limiting.

        Args:
            prompt: The text prompt for the model.
            json_schema: The JSON schema to enforce on the model's output.
            gcs_uris: A list of 'gs://...' URIs pointing to PDF files for context.
            request_context_log: A string to identify the request source in logs.
            model_override: Optional model name to use instead of the default.
            max_retries: Optional override for the number of retries (defaults to MAX_RETRIES).

        Returns:
            The parsed JSON response from the model.
        """
        retries = max_retries if max_retries is not None else API_MAX_RETRIES
        
        # --- Configuration phase (fails fast if invalid) ---
        # This will raise ValueError if the configuration/schema is bad, preventing entry into the retry loop.
        # This handles the original AttributeError caused by the schema incompatibility.
        try:
            gen_config = self._prepare_generation_config(json_schema)
        except ValueError as e:
            logger.error(f"[{request_context_log}] Configuration failed. Cannot proceed with AI request: {e}")
            raise

        # Select the appropriate model
        model_to_use = model_override if model_override else GROUND_TRUTH_MODEL
        generative_model = self._get_model_instance(model_to_use)

        # Build the content list.
        contents = [prompt]
        if gcs_uris:
            for uri in gcs_uris:
                contents.append(Part.from_uri(uri, mime_type="application/pdf"))
            if self.config.is_test_mode:
                logger.debug(f"Attaching {len(gcs_uris)} GCS files to the prompt.")

        # --- Execution phase (retries on specific errors) ---
        async with self.semaphore:
            for attempt in range(retries):
                try:
                    logger.info(f"[{request_context_log}] Attempt {attempt + 1}/{retries}: Calling Gemini model '{model_to_use}'...")
                    response = await generative_model.generate_content_async(
                        contents=contents,
                        generation_config=gen_config,
                    )

                    # logger.debug(f"[{request_context_log}] Raw model response: {response.text}")

                    response_json = self._process_response(response)
                    
                    logger.info(f"[{request_context_log}] Successfully generated and parsed JSON response on attempt {attempt + 1}.")
                    return response_json

                # Catch only exceptions we specifically want to retry on (Rule 5.3.3).
                # We retry on transient API errors and ValueErrors/TypeErrors (which we raise for bad responses/JSON/finish reasons).
                except (api_core_exceptions.GoogleAPICallError, ValueError, TypeError) as e:
                    wait_time = 2 ** attempt
                    if attempt == retries - 1:
                        logger.critical(f"[{request_context_log}] AI generation failed after all {retries} retries.", exc_info=True)
                        raise

                    if isinstance(e, api_core_exceptions.GoogleAPICallError):
                        logger.warning(f"[{request_context_log}] Generation attempt {attempt + 1} failed with Google API Error (Code: {e.code}): {e.message}. Retrying in {wait_time}s...")
                    else: # ValueError or TypeError (processing errors)
                        error_msg = str(e)
                        if "Failed to parse model response as JSON" in error_msg:
                            logger.warning(f"[{request_context_log}] Attempt {attempt + 1} failed: JSON parsing error. Retrying in {wait_time}s...")
                        else:
                            logger.warning(f"[{request_context_log}] Attempt {attempt + 1} failed with processing error: {error_msg}. Retrying in {wait_time}s...")

                    await asyncio.sleep(wait_time)
                
                # Catch any other unexpected errors (like SDK bugs or programming errors) that should not be retried.
                except Exception as e:
                    logger.error(f"[{request_context_log}] Unexpected, non-retryable error during AI generation on attempt {attempt + 1}: {type(e).__name__}: {e}", exc_info=True)
                    raise

    async def generate_validated_json_response(
        self, 
        prompt: str, 
        json_schema: Dict[str, Any], 
        gcs_uris: List[str] = None, 
        request_context_log: str = "Generic AI Request",
        model_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates and validates a JSON response from the AI model.
        
        Raises:
            ValidationError: If the response doesn't match the provided schema
            
        Returns:
            The validated JSON response from the model
        """
        try:
            result = await self.generate_json_response(prompt, json_schema, gcs_uris, request_context_log, model_override)
            # Validation is done against the original JSON schema, not the OpenAPI converted one
            validate(instance=result, schema=json_schema)
            return result
        except ValidationError as e:
            # Clean validation error message
            clean_msg = e.message.split('\n')[0] if '\n' in e.message else e.message
            logger.error(f"[{request_context_log}] Schema validation failed: {clean_msg}")
            raise ValidationError(f"Response validation failed: {clean_msg}")