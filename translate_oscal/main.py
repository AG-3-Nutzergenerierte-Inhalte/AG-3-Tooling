"""
This script performs an automated, batch-based translation of a large JSON file
from German into multiple target languages using the Vertex AI Gemini API.

Version 4 Enhancements (Restartability):
- Detailed Gemini Error Parsing: Explicitly checks for and logs content generation
  failures (e.g., safety blocks) from the Gemini API.
- Deduplication: Identifies unique texts to avoid re-translating the same content,
  significantly reducing API calls and costs.
- Robust JSON Validation: Includes a retry loop that explicitly checks for valid
  JSON responses from the API before proceeding.
- Configurable Test Mode: Test mode now processes 5% of the data.
- **Restartability:** Saves translation progress to GCS, allowing the job to resume
  from where it left off if interrupted.

Workflow:
1.  Loads a source JSON file from a Google Cloud Storage (GCS) bucket.
2.  Recursively extracts all text values designated for translation.
3.  Deduplicates the extracted texts to create a minimal set for translation.
4.  **Loads existing translation progress from GCS to skip already translated texts.**
5.  Bundles the remaining unique texts into intelligent batches.
6.  Sends each batch to the Gemini model, requesting translations for all
    target languages, and retries if the response is not valid JSON or if content
    is blocked.
7.  **Saves translation progress to GCS after each successful batch.**
8.  Maps the translations of the unique texts back to all original occurrences.
9.  Saves a separate, fully translated JSON file for each target language back
    to the GCS bucket.

The script is optimized for deployment on Google Cloud Run.
"""

import json
import os
import sys
import asyncio
from datetime import datetime, timezone
import logging
import copy
import time # For time.time()

import vertexai
from vertexai.generative_models import GenerativeModel, Part, HarmCategory, HarmBlockThreshold, SafetySetting
# Specific exceptions for better error handling
from vertexai.generative_models._generative_models import ResponseValidationError
from google.cloud import storage
import google.api_core.exceptions

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# config for gemini

# Define the safety settings to BLOCK_NONE for all standard configurable categories
safety_settings = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    # While less common for direct configuration via BLOCK_NONE in the API,
    # some models might have internal handling for these or they might appear
    # in prompt feedback. It's best to stick to the explicitly documented ones.
    # HarmCategory.HARM_CATEGORY_UNSPECIFIED is a general placeholder
    # HarmCategory.HARM_CATEGORY_MEDICAL
    # HarmCategory.HARM_CATEGORY_DEROGATORY
    # HarmCategory.HARM_CATEGORY_VIOLENCE
    # HarmCategory.HARM_CATEGORY_TOXICITY
    # HarmCategory.HARM_CATEGORY_FLAMING
    # HarmCategory.HARM_CATEGORY_MISINFORMATION
    # HarmCategory.HARM_CATEGORY_PROMPT_UNSPECIFIED
]

generation_config={"response_mime_type": "application/json", "max_output_tokens": 65535}

# --- Configuration from Environment Variables ---
try:
    GCP_PROJECT_ID = os.environ["GCP_PROJECT_ID"]
    BUCKET_NAME = os.environ["BUCKET_NAME"]
    EXISTING_JSON_GCS_PATH = os.environ["EXISTING_JSON_GCS_PATH"]
    OUTPUT_PREFIX = os.environ.get("OUTPUT_PREFIX")
    TEST_MODE = os.environ.get("TEST", "false").lower() == 'true'

    logging.info("Successfully loaded all required environment variables.")

except KeyError as e:
    logging.critical(f"FATAL: A required environment variable is missing: {e}.")
    logging.critical("Please ensure GCP_PROJECT_ID, BUCKET_NAME, and EXISTING_JSON_GCS_PATH are all set.")
    sys.exit(1)


PROGRESS_FILE_PATH = "translation_progress/progress_data.json" # Path for the progress file
LANGUAGES = {
    "english": "en", "french": "fr", "dutch": "nl", "spanish": "es",
    "italian": "it", "czech": "cs", "hungarian": "hu", "pashtu": "ps",
    "farsi": "fa", "hindi": "hi", "chinese": "zh", "japanese": "ja",
    "russian": "ru", "korean": "ko"
}
TARGET_LANGUAGE_CODES = list(LANGUAGES.values())
TOKEN_LIMIT_PER_BATCH = 4000 # Increased for larger context window models
MAX_TRANSLATION_RETRIES = 5

# --- Rate Limiting Configuration ---
# Max requests per minute (ADJUST THIS BASED ON YOUR ACTUAL GCP QUOTA)
# For Gemini 2.5 Pro, typical quotas are higher (e.g., 150-1000 QPM). Adjust this value
# to match your specific needs or a conservative estimate if you don't know your exact quota.
GEMINI_QPM_LIMIT = 10 # Example: If you need to limit to 10 requests per minute
REQUEST_DELAY_SECONDS = 60 / GEMINI_QPM_LIMIT

# --- Global variables for client and rate limiting ---
# These will be initialized in the try block below
model = None
gemini_semaphore = None
last_request_time = 0.0 # Using float for time in seconds
storage_client = None
bucket = None


# --- Adjustments for Test Mode ---
if TEST_MODE:
    logging.warning("############################################################")
    logging.warning("--- TEST MODE ENABLED ---")
    logging.warning("--- Processing only 5%% of texts and 2 languages (en, es).")
    logging.warning("--- Error messages will be logged with full tracebacks.")
    logging.warning("############################################################")
    TARGET_LANGUAGE_CODES = ["en", "es"]

# --- Initialization of Google Cloud Clients ---
try:
    vertexai.init(project=GCP_PROJECT_ID, location="global")
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    model = GenerativeModel("gemini-2.5-pro")

    # The semaphore should ideally reflect the *actual* concurrent request capacity,
    # which might be higher than the QPM limit, but the REQUEST_DELAY_SECONDS
    # will enforce the rate. Setting it equal to QPM_LIMIT is a safe starting point.
    gemini_semaphore = asyncio.Semaphore(GEMINI_QPM_LIMIT) # Max concurrent API calls
    logging.info(f"Vertex AI and GCS clients initialized for project '{GCP_PROJECT_ID}' and bucket '{BUCKET_NAME}'.")

except Exception as e:
    logging.critical(f"FATAL: Critical error during initialization of Google Cloud clients.")
    if TEST_MODE:
        logging.exception(e)
    else:
        logging.critical(f"Error details: {e}")
    sys.exit(1)


# ==============================================================================
# === HELPER FUNCTIONS FOR PROGRESS MANAGEMENT
# ==============================================================================

def load_progress():
    """Loads existing translation progress from GCS."""
    try:
        progress_blob = bucket.blob(PROGRESS_FILE_PATH)
        if progress_blob.exists():
            progress_content = progress_blob.download_as_string()
            logging.info(f"Loaded existing progress from gs://{BUCKET_NAME}/{PROGRESS_FILE_PATH}")
            return json.loads(progress_content)
        logging.info("No existing progress file found. Starting fresh.")
        return {}
    except Exception as e:
        logging.warning(f"Could not load progress file from GCS. Starting fresh. Error: {e}")
        if TEST_MODE:
            logging.exception(e)
        return {}

def save_progress(unique_texts_list_for_progress):
    """Saves current translation progress to GCS."""
    try:
        # Create a simplified dictionary for saving progress:
        # {original_text: {lang_code: translated_text, ...}, ...}
        # This includes only the information needed to resume.
        progress_data = {
            item['original_text']: item['translations']
            for item in unique_texts_list_for_progress
            if item.get('translations') # Only save if there are translations
        }
        
        progress_blob = bucket.blob(PROGRESS_FILE_PATH)
        progress_blob.upload_from_string(
            data=json.dumps(progress_data, indent=2, ensure_ascii=False),
            content_type="application/json"
        )
        logging.info(f"Progress saved to gs://{BUCKET_NAME}/{PROGRESS_FILE_PATH}")
    except Exception as e:
        logging.error(f"Failed to save progress to GCS. Error: {e}")
        if TEST_MODE:
            logging.exception(e)


# ==============================================================================
# === PHASE 1: EXTRACT TEXTS FROM THE JSON STRUCTURE
# ==============================================================================
def extract_translatable_texts(node, path, translation_map):
    """
    Recursively traverses the JSON structure to find and catalogue all texts
    that need to be translated.
    """
    try:
        if isinstance(node, dict):
            for key, value in node.items():
                current_path = f"{path}.{key}" if path else key
                if key in ["prose", "title"] and isinstance(value, str) and value.strip():
                    translation_map.append({
                        "path": current_path,
                        "original_text": value,
                        "translations": {} # Placeholder for future translations
                    })
                else:
                    extract_translatable_texts(value, current_path, translation_map)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                current_path = f"{path}[{index}]"
                extract_translatable_texts(item, current_path, translation_map)
    except Exception as e:
        logging.error(f"Error during extraction at path '{path}'.")
        if TEST_MODE:
            logging.exception(e)

# ==============================================================================
# === PHASE 2: CREATE BATCHES FOR THE API
# ==============================================================================
def create_batches(unique_texts_list_to_process):
    """
    Groups the unique texts into batches, ensuring each batch is under the token limit.
    """
    if not unique_texts_list_to_process:
        return []
        
    batches = []
    current_batch = []
    current_tokens = 0
    for item in unique_texts_list_to_process:
        try:
            # Estimate tokens - typically 1 word ~ 1.3-1.5 tokens, so char_count / 3 is a rough but common heuristic.
            item_tokens = len(item["original_text"]) // 3 
            
            # The prompt itself adds tokens, so we should consider that too.
            # A rough estimate for prompt overhead is 200-500 tokens, depending on complexity.
            # Let's add a small buffer for prompt overhead here.
            prompt_overhead_tokens = 200 # Roughly based on the prompt structure
            
            if (current_tokens + item_tokens + prompt_overhead_tokens) > TOKEN_LIMIT_PER_BATCH and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
                
            current_batch.append(item)
            current_tokens += item_tokens
        except Exception as e:
            logging.error(f"Error during batch creation for item ID {item.get('id', 'N/A')}.")
            if TEST_MODE:
                logging.exception(e)

    if current_batch:
        batches.append(current_batch)
        
    logging.info(f"Successfully created {len(batches)} batches.")
    return batches

# ==============================================================================
# === PHASE 3: TRANSLATE BATCHES (API COMMUNICATION)
# ==============================================================================
def build_translation_prompt(batch, lang_codes):
    """
    Constructs the detailed prompt for the Gemini API.
    """
    texts_to_translate = {str(item['id']): item['original_text'] for item in batch}
    
    prompt = f"""
    You are a professional translator and an expert in IT security terminology.
    Your task is to translate a list of German texts into multiple target languages.
    The German texts are provided as a JSON object where the key is a unique ID.

    Translate every single text into all of the following languages: {', '.join(lang_codes)}.

    RULES:
    1.  Maintain the professional tone and precise meaning of an IT security expert.
    2.  Return a single, valid JSON object and nothing else. No explanations, no comments, no markdown fences like ```json.
    3.  The top-level keys of the returned JSON object must be the original text IDs (as strings).
    4.  The value for each ID must be another JSON object, where the keys are the language codes ({', '.join(lang_codes)}) and the values are the corresponding translations.
    5.  DO NOT translate the text IDs or the language codes.
    6.  If a translation for a specific language is not possible or results in an empty string, return the string "TRANSLATION FAILED" instead.

    Here is the JSON object with the German texts to translate:
    {json.dumps(texts_to_translate, indent=2, ensure_ascii=False)}
    """
    return prompt

async def translate_batch(batch, target_language_codes_for_batch, full_unique_texts_list):
    """
    Sends a single batch to the Gemini API for translation. Includes a robust retry
    loop that validates the JSON response and parses Gemini-specific errors.
    This function now takes target_language_codes_for_batch to allow
    dynamic selection based on what's missing for each item in the batch.
    """
    prompt = build_translation_prompt(batch, target_language_codes_for_batch)
    
    global last_request_time
    async with gemini_semaphore: # Acquire a semaphore lock before making the request
        # Proactive rate limiting: Ensure a minimum delay between requests
        current_time = time.time() # Use time.time() for wall-clock time
        time_since_last_request = current_time - last_request_time
        delay_needed = REQUEST_DELAY_SECONDS - time_since_last_request
        if delay_needed > 0:
            await asyncio.sleep(delay_needed)
        last_request_time = time.time() # Update last request time

        for attempt in range(MAX_TRANSLATION_RETRIES):
            try:
                response = await model.generate_content_async(
                    [Part.from_text(prompt)],
                    generation_config=generation_config, safety_settings=safety_settings
                )
                
                # === Detailed Gemini Response Validation ===
                if not response.candidates or response.candidates[0].finish_reason.name != "STOP":
                    finish_reason = "NO_CANDIDATES"
                    safety_ratings = "N/A"
                    if response.candidates:
                        finish_reason = response.candidates[0].finish_reason.name
                        if hasattr(response.candidates[0], 'safety_ratings') and response.candidates[0].safety_ratings:
                            safety_ratings = [str(rating) for rating in response.candidates[0].safety_ratings]
                        else:
                            safety_ratings = "No safety ratings provided" # Handle case where it's not present
                    
                    # Check for "RECITATION" specifically if it's a finish_reason
                    if finish_reason == "RECITATION":
                        logging.error(f"Attempt {attempt + 1}/{MAX_TRANSLATION_RETRIES}: Gemini content generation failed due to RECITATION for batch. This is often due to reproducing copyrighted training data. Consider rephrasing input text or prompt structure.")
                    else:
                        logging.error(f"Attempt {attempt + 1}/{MAX_TRANSLATION_RETRIES}: Gemini content generation failed for batch.")
                    logging.error(f"--> Finish Reason: {finish_reason}")
                    logging.error(f"--> Safety Ratings: {safety_ratings}")
                    await asyncio.sleep(2**attempt)
                    continue # Go to the next attempt

                # If generation was successful, validate the JSON format.
                try:
                    translated_data = json.loads(response.text)
                    
                    # If parsing is successful, update the items in the batch
                    # This is where we update `item['translations']` directly
                    # and signal success for this batch.
                    for item in batch:
                        item_id_str = str(item['id'])
                        if item_id_str in translated_data:
                            # Update the item with new translations for its missing languages
                            new_translations = translated_data[item_id_str]
                            for lang_code in target_language_codes_for_batch:
                                if lang_code in new_translations and new_translations[lang_code] not in ["", "TRANSLATION FAILED"]:
                                    item['translations'][lang_code] = new_translations[lang_code]
                                else:
                                    # Mark as failed if the translation was explicitly empty or "TRANSLATION FAILED"
                                    item['translations'][lang_code] = "TRANSLATION FAILED (Gemini)" 
                        else:
                            if TEST_MODE:
                                logging.warning(f"No translation found for ID {item_id_str} in API response for batch. Marking all as failed for missing languages.")
                            for lang_code in target_language_codes_for_batch:
                                if lang_code not in item['translations']: # Only mark if not already translated
                                    item['translations'][lang_code] = "TRANSLATION FAILED (Gemini)"

                    logging.info(f"Successfully translated and validated batch of {len(batch)} items (Attempt {attempt + 1}).")
                    save_progress(full_unique_texts_list) # Save progress after this batch is successful
                    return True # Success, exit the function.

                except json.JSONDecodeError as json_e:
                    logging.error(f"Attempt {attempt + 1}/{MAX_TRANSLATION_RETRIES}: API response was not valid JSON. Retrying...")
                    if TEST_MODE:
                        logging.error(f"Invalid JSON content: {response.text[:500]}...")
                        logging.exception(json_e)
                    await asyncio.sleep(1) # Short delay before retry
                    continue # Retry

            except google.api_core.exceptions.ResourceExhausted as e:
                wait_time = max(REQUEST_DELAY_SECONDS * 2, 2**attempt) # Wait at least the min delay, or back-off
                logging.warning(f"Attempt {attempt + 1}/{MAX_TRANSLATION_RETRIES}: API quota exhausted. Retrying in {wait_time:.2f}s. Error: {e}")
                await asyncio.sleep(wait_time)
            except Exception as e:
                wait_time = max(REQUEST_DELAY_SECONDS * 2, 2**attempt) # Wait at least the min delay, or back-off
                logging.error(f"Attempt {attempt + 1}/{MAX_TRANSLATION_RETRIES}: An unexpected error occurred during translation. Retrying in {wait_time:.2f}s.")
                if TEST_MODE:
                    logging.exception(e)
                await asyncio.sleep(wait_time)
                
    logging.critical(f"Failed to translate batch after {MAX_TRANSLATION_RETRIES} attempts. Giving up on this batch.")
    return False # Final failure.

# ==============================================================================
# === PHASE 4: REINTEGRATE TRANSLATIONS AND SAVE
# ==============================================================================
def reintegrate_translations(original_data, translation_map, target_lang_code):
    """
    Creates a new, complete JSON structure by inserting the translations from the
    'translation_map' into a deep copy of the original data.
    """
    translated_data = copy.deepcopy(original_data)
    
    for item in translation_map:
        try:
            path_keys = item['path'].replace(']', '').replace('[', '.').split('.')
            current_level = translated_data
            
            for key in path_keys[:-1]:
                current_level = current_level[int(key)] if key.isdigit() else current_level[key]

            last_key = path_keys[-1]
            # Use the already translated text, or the original if no translation exists
            translation = item['translations'].get(target_lang_code, item['original_text'])
            
            if last_key.isdigit():
                current_level[int(last_key)] = translation
            else:
                current_level[last_key] = translation
        except (KeyError, IndexError, TypeError) as e:
            logging.warning(f"Could not reintegrate translation for path '{item['path']}' in language '{target_lang_code}'.")
            if TEST_MODE:
                logging.exception(e)

    return translated_data

def save_to_gcs(data, language_code):
    """Saves the final, translated data as a new JSON file in GCS."""
    try:
        lang_name = next((name for name, code in LANGUAGES.items() if code == language_code), "unknown")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_filename = f"{OUTPUT_PREFIX}translated_{lang_name}_{timestamp}.json"
        
        output_blob = bucket.blob(output_filename)
        output_blob.upload_from_string(
            data=json.dumps(data, indent=2, ensure_ascii=False),
            content_type="application/json"
        )
        logging.info(f"Successfully saved: gs://{BUCKET_NAME}/{output_filename}")
    except Exception as e:
        logging.error(f"Failed to save file for language {language_code} to GCS.")
        if TEST_MODE:
            logging.exception(e)

# ==============================================================================
# === MAIN FUNCTION (ORCHESTRATES THE ENTIRE PROCESS)
# ==============================================================================
async def main():
    """Orchestrates the entire translation workflow from start to finish."""
    logging.info("--- Starting Translation Workflow ---")
    
    try:
        logging.info(f"Loading source file: gs://{BUCKET_NAME}/{EXISTING_JSON_GCS_PATH}")
        blob = bucket.blob(EXISTING_JSON_GCS_PATH)
        if not blob.exists():
            raise FileNotFoundError(f"Source file not found at gs://{BUCKET_NAME}/{EXISTING_JSON_GCS_PATH}")
        json_content_string = blob.download_as_string()
        original_data = json.loads(json_content_string)
        logging.info("Source file successfully loaded and parsed as JSON.")
    except Exception as e:
        logging.critical(f"FATAL: Could not load or parse source file gs://{BUCKET_NAME}/{EXISTING_JSON_GCS_PATH}")
        if TEST_MODE: logging.exception(e)
        sys.exit(1)

    # 1. Extract all text occurrences
    full_translation_map = []
    extract_translatable_texts(original_data, "", full_translation_map)
    
    if not full_translation_map:
        logging.warning("No translatable text found ('prose' or 'title' fields). Exiting.")
        return
        
    # --- Deduplication Logic ---
    # Create a dictionary where each key is a unique German text,
    # now also storing the index of its first occurrence to reuse its 'id'.
    unique_texts_dict = {}
    for i, item in enumerate(full_translation_map):
        if item['original_text'] not in unique_texts_dict:
            unique_texts_dict[item['original_text']] = {
                "id": i, # Use the index as a unique ID for the original text
                "original_text": item['original_text'],
                "translations": {}
            }
    
    # Convert back to a list, maintaining a stable order for processing
    unique_texts_list = list(unique_texts_dict.values())
    logging.info(f"Found {len(full_translation_map)} total text items, with {len(unique_texts_list)} unique texts to translate.")

    # --- Load Progress ---
    # Load previously completed translations
    completed_translations = load_progress()
    logging.info(f"Loaded {len(completed_translations)} previously translated unique texts.")

    # Populate `translations` for unique_texts_list from loaded progress
    # and identify which texts still need translation
    texts_to_translate_in_this_run = []
    for item in unique_texts_list:
        original_text = item['original_text']
        item_needs_translation = False
        
        # If this text was previously translated, populate its translations
        if original_text in completed_translations:
            item['translations'] = completed_translations[original_text]
        
        # Determine which languages are still missing for this specific unique text
        missing_languages = [
            lang_code for lang_code in TARGET_LANGUAGE_CODES
            if lang_code not in item['translations'] or item['translations'].get(lang_code) == "TRANSLATION FAILED (Gemini)"
        ]
        
        if missing_languages:
            item['missing_languages'] = missing_languages
            texts_to_translate_in_this_run.append(item)
            item_needs_translation = True
        else:
            item['missing_languages'] = [] # All translations complete for this text

    if not texts_to_translate_in_this_run:
        logging.info("All unique texts already translated in all target languages based on progress file. Exiting.")
        # Proceed to final JSON saving, as all unique texts are done.
        pass # Will continue to the final save loop below
    else:
        logging.info(f"Identified {len(texts_to_translate_in_this_run)} unique texts that still require translation.")
        if TEST_MODE:
            num_test_items = max(1, int(len(texts_to_translate_in_this_run) * 0.05))
            texts_to_translate_in_this_run = texts_to_translate_in_this_run[:num_test_items]
            logging.info(f"TEST MODE: Reduced texts to translate in this run to {len(texts_to_translate_in_this_run)} items (~5%).")

        # 2. Create batches from the *remaining* unique texts
        batches = create_batches(texts_to_translate_in_this_run)
        if not batches:
            logging.warning("No batches were created from remaining unique texts. This might be fine if all translations were already done.")
        else:
            # 3. Translate batches of unique texts
            logging.info(f"Starting translation of {len(batches)} batches (saving progress after each)...")
            
            translation_tasks = []

            for batch in batches:
                # For each batch, collect all *missing* languages across its items
                # This ensures we only ask for translations we don't have yet.
                # If an item has translations for some languages but not others,
                # the prompt will only request the missing ones.
                # However, Gemini currently translates *all* requested languages per prompt.
                # So we simply pass all TARGET_LANGUAGE_CODES to the prompt,
                # and rely on the internal `item['translations']` to fill what's missing.
                translation_tasks.append(translate_batch(batch, TARGET_LANGUAGE_CODES, unique_texts_list))
                
            results = await asyncio.gather(*translation_tasks)

            if not all(results):
                logging.warning("Some batches failed translation. Partial results will be saved. Review logs for details.")


    # --- Rehydration Step ---
    # Create a simple lookup dictionary (cache) from the translated unique texts.
    # This now reflects all translations, including newly completed ones.
    logging.info("Rehydrating full translation map with unique translations...")
    translation_cache = {item['original_text']: item['translations'] for item in unique_texts_list}

    # Populate the original full map with the results from the cache.
    for item in full_translation_map:
        if item['original_text'] in translation_cache:
            item['translations'] = translation_cache[item['original_text']]
    logging.info("Rehydration complete.")


    # 4. For each language, create the final JSON and save it.
    logging.info("--- Saving final translated files to GCS ---")
    for lang_code in TARGET_LANGUAGE_CODES:
        lang_name = next((name for name, code in LANGUAGES.items() if code == lang_code), "unknown")
        logging.info(f"Reintegrating translations for {lang_name} ({lang_code})...")
        final_json = reintegrate_translations(original_data, full_translation_map, lang_code)
        save_to_gcs(final_json, lang_code)

    logging.info("--- Translation Workflow Completed Successfully ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical("An unhandled exception occurred at the top level.")
        if TEST_MODE:
            logging.exception(e)