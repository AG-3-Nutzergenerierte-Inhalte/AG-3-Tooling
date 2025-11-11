# **Automatisierte Erstellung hybrider OSCAL-Komponentendefinitionen mittels eingeschränkter 1:1 KI-Abbildung**

Dieses Dokument beschreibt ein überarbeitetes Konzeptrahmenwerk für die automatisierte Erstellung von OSCAL 1.1.3 Komponentendefinitionen, welches die Migration von BSI IT-Grundschutz Edition 2023 (Ed2023) zum modernisierten Grundschutz++ (G++) erleichtern soll. Die Überarbeitung spezifiziert eine Automatisierungsstrategie, die für die Ausführung auf der Google Cloud Platform (GCP) konzipiert ist und Künstliche Intelligenz (KI) für die semantische Abbildung unter einer strikt durchgesetzten Eins-zu-Eins (1:1) Entsprechung zwischen Altanforderungen und modernen Kontrollen nutzt.

## **1.0 Einleitung und strategischer Kontext**

Die Entwicklung vom modulbasierten IT-Grundschutz Edition 2023 hin zur datenzentrierten, vererbungsgesteuerten Grundschutz++ Methodik stellt einen bedeutenden Wandel dar. Organisationen benötigen Mechanismen zur Migration bestehender Informationssicherheits-Managementsysteme (ISMS), wobei die Nachvollziehbarkeit zu etablierten Implementierungen gewahrt bleiben muss.

Dieses Rahmenwerk skizziert einen automatisierten Ansatz zur Erstellung von „Transitional Component Definitions“ (Übergangs-Komponentendefinitionen). Das Ziel ist es, einen technischen Ed2023 **„Baustein“** auf das am nächsten entsprechende G++ **„Zielobjekt“** abzubilden und anschließend jede einzelne Ed2023 **„Anforderung“** auf genau eine G++ Kontrolle abzubilden. Dieser Ansatz operiert unter der strikten Einschränkung: **N:M (Viele-zu-Viele) Beziehungen sind untersagt**.

## **2.0 Methodik und Einschränkungen**

Die Methodik ist durch starre, zur Vereinfachung der Automatisierung entwickelte Einschränkungen definiert, die die semantische Genauigkeit der resultierenden Artefakte erheblich beeinflussen.

### **2.1 Die 1:1 Abbildungseinschränkung**

Das Rahmenwerk schreibt eine strikte 1:1 Abbildung an zwei kritischen Stellen vor:

*   **Baustein zu Zielobjekt:** Jeder technische Ed2023 Baustein (aus den Gruppen SYS, APP, INF, NET, IND) wird auf genau ein G++ Zielobjekt abgebildet.
*   **Anforderung zu Kontrolle:** Jede Ed2023 Anforderung innerhalb eines Bausteins wird auf genau eine G++ Kontrolle abgebildet.

### **2.2 Logik zur Abbildungspriorisierung**

Die Auswahl der entsprechenden G++ Kontrolle folgt einer definierten Optimierungslogik:

*   **Semantische Nähe:** Das primäre Kriterium ist die Identifizierung der „engsten Übereinstimmung“ basierend auf einer KI-gesteuerten semantischen Analyse.
*   **Vererbung als Präferenz:** Der G++ Mechanismus der **„Vererbung“** definiert eine Basislinie von Kontrollen für ein gegebenes Zielobjekt. Falls mehrere G++ Kontrollen eine vergleichbare semantische Nähe aufweisen, wird die Kontrolle priorisiert, die bereits in der vererbten Basislinie des Zielobjekts vorhanden ist.
*   **Globaler Geltungsbereich:** Die Abbildung ist nicht auf die vererbte Basislinie beschränkt. Wenn die engste semantische Übereinstimmung außerhalb der vererbten Menge existiert, wird diese ausgewählt.

### **2.3 Metadaten-Verarbeitung**

Die Nachvollziehbarkeit zu Ed2023 wird mittels OSCAL-Eigenschaften (*props*) implementiert. Gemäß den überarbeiteten Einschränkungen werden diese Metadaten als Freitext ohne definierenden Namensraum (*ns* Attribut weggelassen) aufgenommen.

`Case: `Request for a comprehensive code review, a new README.md file, and a to-do list of identified issues.
`---`
`Dixie: `I have conducted an in-depth review of the project. I've created a detailed README.md explaining the pipeline's architecture and purpose, as requested.

My analysis also uncovered several issues ranging from critical, execution-blocking bugs to deviations from our established best practices. I have compiled these findings into a prioritized to-do list. The most critical issues involve a typo in the main entry point, an incorrect JSON key lookup that will cause the matching logic to fail silently, and an incorrect function call to the AI client that will raise a `TypeError`. Addressing these is essential for the pipeline to function.


# Automated OSCAL Component Definition Generator

This project contains a Python-based, cloud-native pipeline designed to automate the creation of transitional OSCAL 1.1.3 component definitions. The primary goal is to facilitate the migration from the German BSI IT-Grundschutz Edition 2023 (Ed2023) framework to the modernized Grundschutz++ (G++) standard by mapping legacy requirements to modern controls using generative AI.

## Core Concept: 1:1 Constrained Mapping

The fundamental principle of this pipeline is a strictly enforced **1:1 mapping constraint** at two levels:

1.  **Baustein to Zielobjekt:** Each technical Ed2023 "Baustein" is mapped to exactly one G++ "Zielobjekt".
2.  **Anforderung to Kontrolle:** Each Ed2023 "Anforderung" within a Baustein is mapped to exactly one G++ "Kontrolle".

This constraint simplifies automation but introduces known semantic trade-offs, which are documented in the project's conceptual framework. The pipeline uses a "Schema-Stub" architecture, where all communication with the generative AI is done via structured JSON, validated against predefined schemas to ensure reliability and quality.

## Pipeline Architecture

The pipeline is divided into distinct, executable stages, controlled via the `--stage` command-line argument.

### Stage: `stage_strip`
-   **Purpose:** A pre-processing step that converts the large, complex source JSON files from BSI (Ed2023) and G++ into compact, developer-friendly Markdown tables.
-   **Output:** Creates four `.md` files in the `Stand-der-Technik-Bibliothek/Bausteine-Zielobjekte/hilfsdateien/` directory, separating technical controls from ISMS/process-oriented controls. This simplifies the context provided to the AI in later stages.

### Stage: `stage_0`
-   **Purpose:** Performs the initial high-level mapping.
-   **Process:**
    1.  Loads all BSI Bausteine and G++ Zielobjekte.
    2.  For each BSI Baustein, it calls the AI model to find the single best-matching G++ Zielobjekt based on semantic similarity.
    3.  Once a match is found, it traverses the G++ Zielobjekt hierarchy to determine the complete set of all inherited G++ controls.
-   **Output:**
    -   `bausteine_zielobjekt.json`: A map of BSI Baustein IDs to their matched G++ Zielobjekt UUIDs.
    -   `zielobjekt_controls.json`: A map of G++ Zielobjekt UUIDs to a list of all their inherited G++ control IDs.

### Stage: `stage_matching`
-   **Purpose:** The core AI-driven task that performs the detailed, 1:1 mapping of requirements to controls.
-   **Process:**
    1.  Uses the outputs from `stage_0` to identify which BSI Baustein maps to which G++ Zielobjekt and its corresponding controls.
    2.  For each Baustein-Zielobjekt pair, it creates a tailored context for the AI, consisting of two filtered Markdown tables: one with all Anforderungen for the BSI Baustein, and one with all inherited Kontrollen for the G++ Zielobjekt.
    3.  It sends this context to the AI with a prompt instructing it to perform an exhaustive 1:1 mapping.
-   **Output:**
    -   `controls_anforderungen.json`: The final, detailed mapping file containing the 1:1 relationships, as well as lists of any unmatched elements from both standards.

## Project Structure

-   `/src`: Contains the main Python application source code.
    -   `/assets`: Stores static assets like JSON schemas and prompt configurations.
    -   `/clients`: Contains clients for interacting with external services (GCP, Vertex AI).
    -   `/pipeline`: Holds the logic for each distinct pipeline stage.
    -   `/utils`: Provides helper functions for common tasks like logging, data loading, and parsing.
-   `/scripts`: Houses automation scripts for local execution, deployment, and datastore management.
-   `/tests`: Contains unit and integration tests for the application.

## Setup and Usage

### Local Development
To run a pipeline stage locally, use the `run_local.sh` script. This script sets up the necessary environment variables for development mode (`TEST="true"`).

```bash
# Example: Run the stripping stage
./scripts/run_local.sh stage_strip

# Example: Run the initial mapping stage
./scripts/run_local.sh stage_0
```

### Cloud Deployment & Execution
The application is designed to run as a Google Cloud Run Job.

1.  **Deploy the Job:**
    The `deploy.sh` script builds the Docker container, pushes it to Google Container Registry, and deploys it as a Cloud Run Job.
    ```bash
    ./scripts/deploy.sh <GCP_PROJECT_ID> <GCP_REGION>
    ```

2.  **Execute the Job:**
    The `run_cloud.sh` script triggers an execution of the deployed job, passing in production configuration via environment variables.
    ```bash
    ./scripts/run_cloud.sh <GCP_PROJECT_ID> <GCP_REGION> <BUCKET_NAME> <SOURCE_PREFIX> <OUTPUT_PREFIX> <AI_ENDPOINT_ID>
    ```

## Configuration
The application is configured via environment variables, which are parsed in `src/config.py`. Key variables include:
-   `GCP_PROJECT_ID`: The Google Cloud project ID.
-   `BUCKET_NAME`: The GCS bucket for input and output data.
-   `TEST`: Set to `"true"` for local development to limit data processing and increase log verbosity.
-   `OVERWRITE_TEMP_FILES`: Set to `"true"` to force regeneration of intermediate files (e.g., the outputs of `stage_0`).
