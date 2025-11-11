# JSON Batch Translation Script for Google Cloud

This project contains a Python script (`main.py`) designed to translate large, structured JSON files from German into multiple other languages. It is optimized for cost and performance by using batch processing, text deduplication, and a single API call per batch for all target languages. It leverages Google's Vertex AI Gemini 1.5 Flash model and is built to run as a serverless Cloud Run Job on Google Cloud Platform (GCP).

The primary use case is the translation of OSCAL (Open Security Controls Assessment Language) catalogs, but it can be adapted for any JSON file where specific text fields (like `title` and `prose`) need translation.

## Target Languages

The script is configured to translate German text into the following languages:

-   English (`en`)
-   French (`fr`)
-   Dutch (`nl`)
-   Spanish (`es`)
-   Italian (`it`)
-   Czech (`cs`)
-   Hungarian (`hu`)
-   Pashtu (`ps`)
-   Farsi (`fa`)
-   Hindi (`hi`)
-   Chinese (`zh`)
-   Japanese (`ja`)
-   Russian (`ru`)
-   Korean (`ko`)

Absolutely\! Here's an updated `README.md` reflecting the enhancements to your batch translation script, including the restartability feature, improved error handling, deduplication, and the rate-limiting configuration.

```markdown
# Batch JSON Translation using Vertex AI Gemini

This project provides a robust and restartable Python script for automated, batch-based translation of large JSON files from German into multiple target languages. It leverages the Vertex AI Gemini API, optimized for deployment on Google Cloud Run Jobs.

---

## Key Features

* **Batch Processing:** Efficiently bundles unique texts into intelligent batches to optimize API calls.
* **Deduplication:** Identifies and translates unique text snippets only once, drastically reducing API calls and associated costs.
* **Restartability:** Saves translation progress to Google Cloud Storage (GCS) after each successful batch. If the job is interrupted or fails, it can resume from the last saved state, avoiding redundant work and saving costs.
* **Robust Error Handling & Retries:**
    * Explicitly checks for and logs content generation failures (e.g., safety blocks, `RECITATION` errors) from the Gemini API.
    * Includes a retry loop with exponential back-off for API calls, handling transient network issues, quota exhaustion, and invalid JSON responses.
* **Configurable Rate Limiting:** Implements client-side rate limiting to stay within Vertex AI Gemini API quotas, preventing `ResourceExhausted` errors.
* **Dynamic Language Support:** Supports translation into a broad array of target languages configurable via environment variables.
* **Seamless Integration with GCS:** Loads source JSON and saves translated outputs directly to GCS buckets.
* **Cloud Run Optimized:** Designed for efficient execution as a Cloud Run Job, leveraging its task-based execution model and resource allocation.

---

## Workflow

1.  **Load Source Data:** Reads a large JSON file from a specified GCS bucket.
2.  **Extract Translatable Texts:** Recursively traverses the JSON structure to identify and extract all text values marked for translation (e.g., "prose", "title" fields).
3.  **Deduplicate Texts:** Creates a minimal set of unique texts to be sent for translation.
4.  **Load Progress (Restartability):** Checks for and loads any existing `translation_progress.json` file from GCS to determine which unique texts have already been translated.
5.  **Batch Creation:** Groups the remaining (untranslated or partially translated) unique texts into optimized batches, respecting configured token limits.
6.  **Translate Batches:** Sends each batch asynchronously to the Vertex AI Gemini model. Each API call requests translations for all specified target languages. Includes internal retries for API-specific errors and JSON validation.
7.  **Save Progress:** After each successful batch translation, the updated translation progress is saved back to `translation_progress.json` in GCS.
8.  **Reintegrate Translations:** Maps the completed translations of unique texts back into a deep copy of the original JSON structure.
9.  **Save Translated Files:** Generates and saves a separate, fully translated JSON file for each target language back to GCS, maintaining a clear output structure.

---

## Setup and Deployment on Google Cloud Run Jobs

### 1. Requirements

Ensure you have the following in your `requirements.txt`:

```

google-cloud-aiplatform
google-cloud-storage

````

### 2. Environment Variables

The script relies on the following environment variables. These should be set in your Cloud Run Job configuration.

* `GCP_PROJECT_ID`: Your Google Cloud Project ID.
* `BUCKET_NAME`: The GCS bucket name where your input file resides and where outputs/progress will be stored.
* `INPUT_FILE`: The relative GCS path to your input JSON file (e.g., `input/my_document.json`).
* `TEST` (optional): Set to `true` to enable test mode (processes 5% of texts, logs full tracebacks, and translates only to English and Spanish). Default is `false`.

### 3. Model and Quota Configuration

* **Gemini Model:** The script is configured to use `gemini-2.5-pro`. You can change this to `gemini-1.5-pro` or `gemini-2.5-flash` in the script's `model = GenerativeModel(...)` line.
* **API Quota (`GEMINI_QPM_LIMIT`):** **Crucially**, adjust the `GEMINI_QPM_LIMIT` variable in the script to match your actual Query Per Minute (QPM) quota for the chosen Gemini model in your Google Cloud Project. You can find this in the Google Cloud Console under "IAM & Admin" > "Quotas" (search for "Generative Language API" or "Vertex AI API"). Setting this value too high will lead to `ResourceExhausted` errors, while setting it too low will unnecessarily slow down your job.

### 4. Deployment

Deploy your Cloud Run Job. The `--max-retries` parameter below configures Cloud Run's *task-level* retries if the container crashes or times out. This is separate from the script's internal API retries.

```bash
gcloud run jobs deploy translate-oscal \
  --source . \
  --tasks 1 \
  --max-retries 3 \  # Cloud Run will retry the task up to 3 times if it fails
  --region YOUR_REGION \
  --project=YOUR_PROJECT \
  --task-timeout 7200 \ # Task timeout in seconds (e.g., 2 hours)
  --memory 2Gi # Example: 2 GiB of memory per task
  # Add other resource flags like --cpu if needed
````

### 5\. Executing the Job

Once deployed, you can execute the job with your environment variables:

```bash
gcloud run jobs execute translate-oscal \
  --region YOUR_REGION \
  --project=YOUR_PROJECT \
  --update-env-vars="BUCKET_NAME=your_gcs_bucket_name,INPUT_FILE=path/to/your/input.json,GCP_PROJECT_ID=your_gcp_project_id"
```

**Note:** Do not include `--max-retries` or other job definition parameters in the `execute` command; they belong to the `deploy` or `update` command.

-----

## Restarting the Job

If the job is interrupted or completes partially, simply execute it again using the `gcloud run jobs execute` command. The script will automatically:

1.  Load the `translation_progress/progress_data.json` file from your GCS bucket.
2.  Identify which unique texts (and which target languages for those texts) still need translation.
3.  Process only the remaining work, ensuring efficient use of resources and API calls.

-----

## Considerations

  * **Large JSON Files:** Ensure your Cloud Run Job has sufficient memory (`--memory`) and CPU (`--cpu`) allocated to handle loading and processing very large JSON files.
  * **Token Limits:** The `TOKEN_LIMIT_PER_BATCH` is a heuristic. Monitor your API usage and adjust it for optimal performance without hitting model input limits.
  * **RECITATION Errors:** While safety settings are configured to `BLOCK_NONE` for standard categories, `RECITATION` errors (model reproducing training data) can still occur. If frequently encountered, consider rephrasing input text or adjusting prompt structure.
  * **Final Output Paths:** Translated files will be saved under the `translations/` prefix in your specified GCS bucket with a timestamp and language code (e.g., `gs://your_bucket/translations/translated_english_20240101_123456.json`).

<!-- end list -->

```
```