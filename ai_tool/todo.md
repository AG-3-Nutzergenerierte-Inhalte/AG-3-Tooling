# Prioritized Technical Debt and To-Do List

This list is prioritized based on the impact on application stability, adherence to mandatory project requirements, and overall maintainability.

## 1.0 CRITICAL: Immediate Bug Fixes

These issues cause data corruption or application instability and must be addressed first.

- [ ] **[BUG] Fix Mutation of Cached Objects (1.2):**
  - **Impact:** The use of shallow copies when modifying the cached JSON schema in `src/pipeline/stage_0_tasks/matching.py` leads to data corruption and incorrect results during asynchronous execution.
  - **Action:** Use `copy.deepcopy(schema)` instead of `schema.copy()` to ensure cached objects are not mutated.

## 2.0 HIGH: Architecture and Mandatory Requirements

These tasks address fundamental design issues that prevent the application from meeting its objectives or violate mandatory standards.

- [ ] **[Arch] Refactor for Cloud-Native Execution (1.1):**
  - **Impact:** The reliance on local file paths outside the application directory prevents the application from running in containers (Cloud Run), failing the primary objective (Requirement 2.0).
  - **Action:** Refactor data loading to read all input files from Google Cloud Storage (GCS) based on environment variables (`BUCKET_NAME`, `SOURCE_PREFIX`). Update `constants.py` and `data_loader.py` accordingly.

- [ ] **Implement Robust, Compliant Retry Mechanism (1.3 / 2.1):**
  - **Impact:** The current manual retry logic violates Requirement 5.3.1 (lacks jitter) and inefficiently retries on schema validation errors (AI Slop).
  - **Action:** Refactor `src/clients/ai_client.py` to use the `tenacity` library.
  - **Action:** Configure `tenacity` for asynchronous retries with exponential backoff AND jitter.
  - **Action (Efficiency Improvement):** Configure retries for transient errors (network/API issues) and `JSONDecodeError` (syntactically invalid JSON). Do **NOT** retry on `ValidationError` (schema mismatch).

## 3.0 HIGH: Robustness and Maintainability

These tasks address critical flaws in data integrity and significant maintenance burdens.

- [ ] **Sanitize Markdown Generation (2.2):**
  - **Impact:** Failure to escape pipe characters (`|`) in source data can corrupt the markdown tables used as AI context, leading to incorrect mappings. Violates Requirement 2.0 (Robust/Automated).
  - **Action:** In `src/pipeline/stage_strip.py`, programmatically escape or remove pipe characters from titles and descriptions before generating the markdown tables.

- [ ] **Centralize and Refactor Duplicated Parsing Logic (3.1):**
  - **Impact:** The complex logic for traversing BSI/G++ JSON structures is duplicated in `stage_strip.py` and `data_parser.py`, leading to high maintenance overhead and brittleness.
  - **Action:** Create a centralized utility module for all OSCAL parsing logic. Refactor both files to use these common functions.

## 4.0 MEDIUM: Configuration, Standards, and Efficiency

- [ ] **Fix Hardcoded Concurrency (3.3):**
  - **Action:** In `src/pipeline/stage_0.py`, update the `asyncio.Semaphore` initialization to use `app_config.max_concurrent_ai_requests` instead of the hardcoded value `10`.

- [ ] **Fix Broken Idempotency (3.4):**
  - **Action:** Update `src/pipeline/stage_strip.py` to exit the function early if output files exist and `OVERWRITE_TEMP_FILES` is false, rather than just deleting and regenerating them (Requirement 5.2.7).

- [ ] **Improve Configuration Validation (3.3):**
  - **Action:** Modify `src/config.py` to ensure essential variables required for initialization (like `GCP_PROJECT_ID` for the `AiClient`) are validated even in test mode.

- [ ] **Update Local Script Defaults (3.3):**
  - **Action:** In `scripts/run_local.sh`, change the default `TEST` environment variable to `"true"` for safety and verbose logging (Requirement 9.2).

- [ ] **Standardize Project Structure (3.5):**
  - **Action:** Move `Dockerfile` and the `assets` directory from `src/` to the project root. Update `constants.py` to use `pathlib.Path` for cleaner, more robust path resolution instead of relative `../..` paths.

## 5.0 LOW: Cleanup and Minor Fixes

- [ ] **Remove Unused Code and Assets (4.1):**
  - **Action:** Remove unused constants (`API_RETRY_BACKOFF_FACTOR`, `API_RETRY_JITTER`). Remove the dead code (duplicate `return None`) in `src/pipeline/stage_0_tasks/matching.py`. Verify if `ANFORDERUNG_TO_KONTROLLE_SCHEMA_PATH` is truly unused and remove it if so.

- [ ] **Correct Prompt Engineering Error (2.4):**
  - **Action:** In `src/assets/json/prompt_config.json`, correct the JSON example within the `anforderung_to_kontrolle_1_1_prompt` to use arrays (`[]`) instead of objects (`{}`) for the `unmapped_gpp` and `unmapped_ed2023` lists.

- [ ] **Code Style and Efficiency Fixes (4.2):**
  - **Action:** Move the `_parse_baustein_details` function definition outside the loop in `src/utils/data_parser.py`. Correct misplaced imports in `data_loader.py` and `data_parser.py`.

## Deferred (Per User Request)

- [ ] **[1.4/3.2] Migrate Bash data scripts (`zielobjekte_stats.sh`, etc.) to Python.** (Acknowledged violation of Req 8.1, accepted inefficiency for manual tooling).
- [ ] **[2.3] Replace Markdown with a structured intermediate data format.** (Acknowledged brittleness, justified by token optimization).