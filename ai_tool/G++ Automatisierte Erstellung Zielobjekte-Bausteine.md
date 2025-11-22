# Automatisiertes Rahmenwerk zur Erstellung hybrider OSCAL-Komponentendefinitionen mittels sequenzieller 1:1 KI-Abbildung

Dieses Dokument beschreibt das technische Konzept und die Implementierungsdetails eines automatisierten Pipelinesystems zur Erstellung von OSCAL 1.1.3 Komponentendefinitionen. Das System soll die Migration von BSI IT-Grundschutz Edition 2023 (Ed2023) zum modernisierten Grundschutz++ (G++) unterstützen. Es nutzt eine sequenzielle Automatisierungsstrategie, die auf Python und Google Cloud Vertex AI (Gemini) basiert, um semantische Abbildungen unter einer strikt durchgesetzten Eins-zu-Eins (1:1) Entsprechung zwischen Altanforderungen und modernen Kontrollen durchzuführen.

## 1.0 Einleitung und strategischer Kontext

Die Weiterentwicklung vom modulbasierten IT-Grundschutz (Ed2023) zur datenzentrierten, vererbungsgesteuerten Grundschutz++ (G++) Methodik erfordert Mechanismen zur Migration bestehender Informationssicherheits-Managementsysteme (ISMS).

Dieses Rahmenwerk implementiert eine automatisierte Pipeline zur Erstellung von „Transitional Component Definitions“ (Übergangs-Komponentendefinitionen). Das Ziel ist es, einen technischen Ed2023 **„Baustein“** auf das am nächsten entsprechende G++ **„Zielobjekt“** abzubilden und anschließend jede einzelne Ed2023 **„Anforderung“** auf genau eine G++ **„Kontrolle“** innerhalb des Kontexts dieses Zielobjekts abzubilden.

## 2.0 Methodik und Einschränkungen

Die Methodik basiert auf einer Kombination aus deterministischer Datenanalyse (zur Bestimmung der Anwendbarkeit von Kontrollen) und KI-gestützter semantischer Analyse (zur Durchführung der Abbildung).

### 2.1 Die 1:1 Abbildungseinschränkung

Das Rahmenwerk erzwingt eine strikte 1:1 Abbildung an zwei kritischen Stellen der Pipeline:

1.  **Baustein zu Zielobjekt (Stage `match_bausteine`):** Jeder technische Ed2023 Baustein (definiert in `constants.ALLOWED_MAIN_GROUPS`, z.B. SYS, APP, INF, NET, IND) wird durch KI-Analyse auf genau ein G++ Zielobjekt abgebildet.
2.  **Anforderung zu Kontrolle (Stage `matching`):** Jede Ed2023 Anforderung innerhalb eines Bausteins wird durch KI-Analyse auf genau eine G++ Kontrolle abgebildet.

**N:M (Viele-zu-Viele) Beziehungen sind im automatisierten Prozess untersagt.**

### 2.2 Logik zur Abbildungspriorisierung und Kontextbegrenzung

Die Auswahl der entsprechenden G++ Kontrolle basiert auf einer definierten Logik, die den Kontext strikt eingrenzt:

1.  **Determinierung des Kontrollpools (Stage `gpp`):** Zuerst wird die Menge aller anwendbaren G++ Kontrollen für jedes Zielobjekt deterministisch ermittelt. Dies geschieht durch die Analyse der `target_objects`-Eigenschaften im G++ Kompendium und die rekursive Auflösung der Vererbungshierarchie gemäß `zielobjekte.csv`.
2.  **Semantische Nähe im Kontext (Stage `matching`):** Die KI-gesteuerte Abbildung einer BSI Anforderung erfolgt ausschließlich gegen den Pool von G++ Kontrollen, der für das zuvor ausgewählte Zielobjekt (aus Stage `match_bausteine`) ermittelt wurde. Eine globale Suche über alle G++ Kontrollen findet nicht statt. Das primäre Kriterium ist die Identifizierung der „engsten semantischen Übereinstimmung“ innerhalb dieses Pools.

### 2.3 Metadaten-Verarbeitung

Die Nachvollziehbarkeit zu Ed2023 wird in den resultierenden OSCAL-Komponentendefinitionen (Stage `component`) implementiert. Dabei werden Details der ursprünglichen BSI Anforderung (wie Titel und Beschreibungen der verschiedenen Maturitätsstufen) in die `props` und `statements` der implementierten G++ Kontrolle integriert.

## 3.0 Pipeline-Architektur und technische Implementierung

Die Architektur ist als modulare, mehrstufige Pipeline implementiert, die in Python geschrieben ist. Die Orchestrierung erfolgt über `src/main.py` und `src/pipeline/processing.py`. Die Pipeline kann vollständig oder in einzelnen Stages ausgeführt werden (z.B. `python src/main.py --stage stage_matching`).

### 3.1 Unterstützende Infrastruktur

#### 3.1.1 KI-Client (`src/clients/ai_client.py`)

Der `AiClient` ist die zentrale Komponente für alle Interaktionen mit Google Vertex AI (Gemini).

*   **Modell-Konfiguration:** Verwendet standardmäßig `gemini-1.5-flash`, erlaubt jedoch Overrides (z.B. `gemini-1.5-pro` für komplexere Aufgaben in `stage_matching`).
*   **Strukturierte Ausgabe:** Nutzt `GenerationConfig` mit `response_mime_type="application/json"` und `response_schema`, um die KI zu zwingen, gültiges JSON gemäß einem definierten Schema zurückzugeben.
*   **Asynchrone Verarbeitung:** Implementiert `generate_content_async` für parallele Anfragen.
*   **Robuste Fehlerbehandlung:** Implementiert einen asynchronen Retry-Mechanismus mit exponentiellem Backoff (konfigurierbar über `API_MAX_RETRIES`). Es werden sowohl API-Fehler (z.B. Quota-Überschreitungen) als auch Validierungsfehler (wenn die KI kein gültiges JSON oder kein Schema-konformes JSON liefert) abgefangen und wiederholt.
*   **Validierung:** Jede Antwort wird nach dem Empfang mittels `jsonschema.validate` gegen das erwartete Schema validiert.

```python
# src/clients/ai_client.py (Auszug aus generate_validated_json_response)
for attempt in range(retries):
    try:
        # ... (API Aufruf) ...
        response_json = self._process_response(response)
        validate(instance=response_json, schema=json_schema)
        return response_json
    except (api_core_exceptions.GoogleAPICallError, ValueError, TypeError, ValidationError) as e:
        wait_time = 2 ** attempt
        # ... (Logging und Wartezeit) ...
        await asyncio.sleep(wait_time)
```

#### 3.1.2 Konfiguration und Logging

*   **Konfiguration (`src/config.py`, `src/constants.py`):** Die Anwendung wird über Umgebungsvariablen konfiguriert (z.B. `GCP_PROJECT_ID`, `MAX_CONCURRENT_AI_REQUESTS`). Konstanten definieren Dateipfade, Modellnamen und Schwellenwerte.
*   **Testmodus (`TEST="true"`):** Wenn aktiviert, wird der Logging-Level auf `DEBUG` gesetzt (`src/utils/logger.py`) und die Datenverarbeitung in den Stages auf eine kleine Teilmenge (z.B. die ersten 3 Elemente) reduziert, um schnelle Iterationen zu ermöglichen.
*   **Idempotenz (`OVERWRITE_TEMP_FILES`):** Stages prüfen, ob ihre Ausgabedateien bereits existieren. Wenn `OVERWRITE_TEMP_FILES="false"`, wird die Stage übersprungen (implementiert in z.B. `stage_match_bausteine.py`).

### 3.2 Stage: `stage_strip` - Datenvorverarbeitung und Reduktion

Diese Stage reduziert die umfangreichen JSON-Quelldateien in kompakte Markdown-Tabellen. Dieses Format dient später als effizienter Kontext für die KI-Modelle.

*   **Inputs:**
    *   `BSI_GS_OSCAL_current_2023_benutzerdefinierte.json` (BSI Ed2023)
    *   `Grundschutz++-Kompendium.json` (G++)
*   **Prozess (G++):**
    1.  Das G++ Kompendium wird rekursiv durchlaufen (`_process_controls_recursively`), um alle Kontrollen (auch verschachtelte) zu extrahieren.
    2.  Für jede Kontrolle werden ID, Titel, UUID (`alt-identifier`) und eine auf 150 Zeichen gekürzte Beschreibung (`statement prose`) extrahiert.
    3.  Die Kontrollen werden basierend auf dem Vorhandensein einer `target_objects`-Eigenschaft (`_has_target_objects`) aufgeteilt.
*   **Prozess (BSI):**
    1.  Das BSI Kompendium wird durchlaufen, um alle Anforderungen (Controls) zu extrahieren.
    2.  Es werden ID, Titel und eine gekürzte Beschreibung extrahiert.
    3.  Die Anforderungen werden basierend auf ihrer Zugehörigkeit zu den `ALLOWED_MAIN_GROUPS` (SYS, APP, NET, IND, INF) aufgeteilt.
*   **Outputs (in `hilfsdateien/`):**
    *   `gpp_stripped.md`: G++ Kontrollen mit `target_objects`.
    *   `gpp_isms_stripped.md`: G++ Kontrollen ohne `target_objects` (ISMS/Prozess-bezogen).
    *   `bsi_2023_stripped.md`: BSI Anforderungen aus den erlaubten technischen Gruppen.
    *   `bsi_2023_stripped_ISMS.md`: BSI Anforderungen aus anderen Gruppen (z.B. ORP, ISMS).

### 3.3 Stage: `stage_gpp` - Deterministische G++ Analyse und Vererbung

Diese Stage führt eine deterministische Analyse durch, um für jedes G++ Zielobjekt die exakte Menge der anwendbaren Kontrollen zu bestimmen, unter Berücksichtigung der Vererbungshierarchie.

*   **Inputs:**
    *   `Grundschutz++-Kompendium.json`
    *   `zielobjekte.csv` (Definiert die Hierarchie mittels `UUID` und `ChildOfUUID`)
*   **Prozess:**
    1.  **Extraktion der Kontrollen (`_create_target_controls_map`):** Das G++ Kompendium wird rekursiv durchlaufen (`_traverse_and_extract_controls`). Kontrollen werden extrahiert und in zwei Maps aufgeteilt: `target_controls` (keyed by Zielobjekt Name) und `isms_controls`.
    2.  **Erstellung der Zielobjekt-Map (`_create_zielobjekt_map`):** Die `zielobjekte.csv` wird geladen.
    3.  **Auflösung der Vererbung:** Für jedes Zielobjekt wird die Funktion `_get_parent_names_recursive` aufgerufen. Diese traversiert die `ChildOfUUID`-Beziehungen nach oben und sammelt die Namen aller übergeordneten Zielobjekte.
    4.  **Zusammenführung:** Für jedes Zielobjekt (keyed by UUID) werden alle Kontrollen gesammelt, die seinem eigenen Namen oder einem seiner übergeordneten Namen in der `target_controls_map` zugeordnet sind.
*   **Outputs:**
    *   `zielobjekt_controls.json`: Eine Map, die für jede Zielobjekt-UUID die Liste der IDs aller anwendbaren (direkten und vererbten) G++ Kontrollen enthält. Enthält auch einen speziellen "ISMS"-Eintrag.

### 3.4 Stage: `stage_match_bausteine` - KI-gestützte Baustein-zu-Zielobjekt-Abbildung

Diese Stage führt die erste KI-gestützte Abbildung durch: die Zuordnung jedes technischen BSI Bausteins zu genau einem G++ Zielobjekt.

*   **Inputs:**
    *   BSI Ed2023 JSON
    *   `zielobjekte.csv`
    *   `prompt_config.json`, `baustein_to_zielobjekt_schema.json`
*   **Prozess:**
    1.  **Datenvorbereitung:** BSI Bausteine aus den `ALLOWED_MAIN_GROUPS`, die eine Beschreibung (`usage prose`) haben, werden extrahiert (`utils.data_parser.find_bausteine_with_prose`). Die Zielobjekte und ihre Definitionen werden aus der CSV geladen.
    2.  **Asynchrone Verarbeitung:** Der `AiClient` wird initialisiert. Ein `asyncio.Semaphore` wird verwendet, um die Parallelität zu begrenzen (`MAX_CONCURRENT_AI_REQUESTS`).
    3.  **KI-Abbildung (`match_baustein_to_zielobjekt`):** Für jeden Baustein wird ein Prompt erstellt, der die Bausteinbeschreibung und eine Liste aller verfügbaren Zielobjekte enthält.
    4.  Die KI (Gemini Flash) wird aufgefordert, das am besten passende Zielobjekt auszuwählen und die Antwort als validiertes JSON zurückzugeben.
    5.  Die Ergebnisse werden gesammelt.
*   **Outputs:**
    *   `bausteine_zielobjekt.json`: Eine Map von BSI Baustein ID zu der UUID des am besten passenden G++ Zielobjekts.

### 3.5 Stage: `stage_matching` - KI-gestützte Anforderung-zu-Kontrolle-Abbildung

Dies ist die komplexeste Stage der Pipeline. Sie führt die detaillierte 1:1 Abbildung zwischen BSI Anforderungen und G++ Kontrollen durch, strikt begrenzt auf den Kontext der zuvor ermittelten Baustein-Zielobjekt-Paare.

*   **Inputs:**
    *   Die 4 gestrippten Markdown-Dateien (aus `stage_strip`).
    *   `bausteine_zielobjekt.json` und `zielobjekt_controls.json`.
    *   BSI Ed2023 JSON (zur Ermittlung der Anforderungen pro Baustein).
    *   `prompt_config.json`, `matching_schema.json`.
*   **Prozess (`_process_mapping`):**
    1.  Die Pipeline iteriert über jedes Paar (BSI Baustein ID, Zielobjekt UUID) aus `bausteine_zielobjekt.json`.
    2.  **Kontext-Filterung (Entscheidender Schritt):**
        *   Die Liste der relevanten BSI Anforderungen für den Baustein wird ermittelt.
        *   Die Liste der anwendbaren G++ Kontrollen für das Zielobjekt wird ermittelt (aus `stage_gpp` Ergebnissen).
        *   Die Markdown-Dateien werden gefiltert (`_filter_markdown`), sodass sie nur die relevanten BSI Anforderungen und G++ Kontrollen enthalten. Dies reduziert den Kontext für die KI erheblich.
    3.  **KI-Abbildung:** Ein Prompt wird erstellt, der die gefilterten Markdown-Tabellen enthält und die KI anweist, eine 1:1 Abbildung durchzuführen.
    4.  Der `AiClient` wird verwendet, wobei explizit das leistungsfähigere Modell `gemini-1.5-pro` angefordert wird (`model_override`).
    5.  **Validierung:** Die KI-Antwort (die das Mapping sowie Listen von nicht zugeordneten Elementen enthält) wird validiert. Zusätzlich wird geprüft, ob die IDs im Mapping dem erwarteten Format entsprechen (`_validate_mapping_keys`).
    6.  Die Ergebnisse werden asynchron gesammelt und zusammengeführt.
*   **Outputs:**
    *   `controls_anforderungen.json`: Eine umfassende Datei, die für jede Zielobjekt-UUID die zugehörige Baustein-ID, den Zielobjekt-Namen, das detaillierte 1:1 Mapping (`Anforderung-ID`: `Kontrolle-ID`) und Listen der nicht zugeordneten Elemente enthält.

### 3.6 Stage: `stage_profiles` - Generierung von OSCAL-Profilen

Diese Stage generiert OSCAL-Profile für jedes Zielobjekt. Ein Profil definiert eine Auswahl von Kontrollen aus einem Katalog (hier: G++ Kompendium).

*   **Inputs:**
    *   `zielobjekt_controls.json` (aus `stage_gpp`).
    *   `zielobjekte.csv`.
*   **Prozess:**
    1.  Die Pipeline iteriert über die Ergebnisse von `stage_gpp`.
    2.  Für jede Zielobjekt-UUID (und den speziellen ISMS-Eintrag) wird ein OSCAL-Profil erstellt (`create_oscal_profile`).
    3.  Das Profil importiert das G++ Kompendium (über eine GitHub-URL) und inkludiert die Liste der anwendbaren Kontroll-IDs (`include-controls` -> `with-ids`).
    4.  Der Dateiname wird aus dem Zielobjekt-Namen abgeleitet und sanitisiert (`utils.text_utils.sanitize_filename`).
*   **Outputs:**
    *   `profiles/*.json`: Eine OSCAL-Profildatei für jedes Zielobjekt.

### 3.7 Stage: `stage_component` - Generierung von OSCAL-Komponentendefinitionen

Diese Stage generiert die finalen OSCAL-Komponentendefinitionen. Eine Komponente beschreibt die Implementierung der Kontrollen, die in einem Profil definiert sind, und integriert die Migrationsmetadaten.

*   **Inputs:**
    *   Alle intermediären Mapping-Dateien und generierten Profile.
    *   BSI Ed2023 JSON und G++ JSON (für Detailinformationen).
    *   `oscal_component_schema.json`.
*   **Prozess:**
    1.  Die Pipeline iteriert über die Baustein-Zielobjekt-Zuordnungen.
    2.  Für jeden Baustein wird das entsprechende Profil geladen.
    3.  **Generierung Detaillierter Komponenten (`generate_detailed_component`):**
        *   Es wird eine Komponente erstellt, die den Baustein repräsentiert. Der Typ (z.B. software, hardware) wird basierend auf dem Baustein-Präfix bestimmt (`get_component_type`).
        *   Die Komponente referenziert das Profil als Quelle (`control-implementations` -> `source`).
        *   **KI-Anreicherung:** Die Prose- und Guidance-Texte aller im Profil referenzierten G++ Kontrollen werden mittels rekursiver Suche (`extract_all_gpp_controls`) aus dem G++ Kompendium extrahiert. Diese Texte dienen zusammen mit den BSI Baustein-Teilen (Parts) als Kontext für eine KI-Anfrage.
        *   **KI-Generierung:** Die KI generiert für jede Kontrolle erweiterte Inhalte (Maturitätsstufen 1-5, Klassifizierungen).
        *   Für jede implementierte G++ Kontrolle (`implemented-requirements`):
            *   Die Beschreibung wird aus dem G++ Prose/Guidance Text zusammengesetzt, angereichert mit einem Hinweis auf den BSI Baustein-Kontext.
            *   Die von der KI generierten Inhalte (Statements für Maturity Levels, Props für Klassifizierungen) werden eingefügt.
            *   **Wichtig:** Es werden keine Inhalte aus den originalen BSI *Anforderungen* (Controls) verwendet, sondern ausschließlich KI-generierte Inhalte basierend auf den G++ Kontrollen und dem BSI Baustein-Kontext.
    4.  **Generierung Minimaler Komponenten (`generate_minimal_component`):** Eine vereinfachte Version, die nur die G++ Kontroll-IDs auflistet, ohne die erweiterten KI-Inhalte.
    5.  **Validierung:** Jede generierte Komponentendefinition wird gegen das offizielle OSCAL-Schema validiert (`utils.oscal_utils.validate_oscal`).
*   **Outputs:**
    *   `components/DE/*-benutzerdefiniert-component.json`: Detaillierte Komponentendefinitionen.
    *   `components/DE/*-component.json`: Minimale Komponentendefinitionen.

## 4.0 OSCAL Implementierung und Struktur

Die resultierenden Artefakte entsprechen dem OSCAL 1.1.3 Schema und nutzen spezifische Strukturen, um die Migration abzubilden.

### 4.1 Struktur der Komponentendefinition

Die `component-definition` kapselt die migrierten Bausteine als `components`.

```json
"component-definition": {
    "uuid": "[Generierte UUID]",
    "metadata": { ... },
    "components": [{
        "uuid": "[Component UUID]",
        "type": "software", // Bestimmt durch get_component_type()
        "title": "[Baustein ID] [Baustein Title]",
        "description": "...",
        "control-implementations": [{
            "uuid": "[Impl UUID]",
            // Referenz auf das generierte Profil (relative GitHub URL)
            "source": "https://raw.githubusercontent.com/AG-3-Nutzergenerierte-Inhalte/...",
            "description": "Implementation for all controls in Baustein [Baustein ID]",
            "implemented-requirements": [ /* Siehe 4.2 */ ]
        }]
    }]
}
```

### 4.2 Struktur der implementierten Anforderung (Detailliert)

Das `implemented-requirement`-Objekt in der detaillierten Komponente zeigt die Integration der G++ Kontrolle und der BSI Altdaten.

```json
"implemented-requirements": [{
    "uuid": "[Req UUID]",
    "control-id": "[G++ Control ID]", // z.B. ARCH.2.1
    "description": "[G++ Control Prose und Guidance]",
    // Eigenschaften der ursprünglichen BSI Anforderung
    "props": [
        // z.B. BSI alt-identifier
    ],
    // Details der BSI Maturitätsstufen
    "statements": [{
        "statement-id": "[BSI Statement ID]",
        "uuid": "[Generierte UUID]",
        "description": "[BSI Maturitätsstufen Titel]", // z.B. Basis-Anforderungen
        "props": [
            {
                "name": "[BSI Sub-Part Name]", // z.B. statement
                "value": "[BSI Sub-Part Prose]" // Die eigentliche Anforderung
            }
        ]
    }]
}]
```

## 5.0 Kritische Analyse und methodische Einschränkungen

Die dem Rahmenwerk auferlegten Einschränkungen, insbesondere die strikte 1:1 Abbildung und die Kontextbegrenzung, bergen signifikante methodische Risiken.

### 5.1 Inhärente semantische Verluste (Die 1:1 Einschränkung)

Das Verbot von N:M Beziehungen ist die schwerwiegendste Einschränkung.

*   **Verlust durch Zerlegung (*Decomposition Loss*):** Wenn eine Ed2023 Anforderung mehrere Aspekte abdeckt, die in separate G++ Kontrollen zerlegt werden, erzwingt die 1:1 Abbildung die Auswahl nur einer Kontrolle, was zu Lücken in der Abdeckung führt.
*   **Verzerrung durch Konsolidierung (*Consolidation Distortion*):** Wenn mehrere Ed2023 Anforderungen in einer G++ Kontrolle konsolidiert werden, wird die G++ Kontrolle künstlich für jede Altanforderung repliziert, was die Struktur des G++ Ansatzes verzerrt.

### 5.2 Kontextbegrenzung durch Baustein-Zuordnung

Die Entscheidung, eine BSI Anforderung nur gegen den Pool von Kontrollen des *einen* ausgewählten Zielobjekts abzubilden, kann zu suboptimalen Ergebnissen führen. Wenn ein Baustein Aspekte mehrerer Zielobjekte abdeckt, wird die KI gezwungen, das "am wenigsten schlechte" Zielobjekt auszuwählen, und ignoriert potenziell besser passende Kontrollen, die anderen Zielobjekten zugeordnet sind.

### 5.3 KI-Abhängigkeit und Validierungsaufwand

Die Qualität der Ergebnisse ist vollständig von der Fähigkeit des KI-Modells (insbesondere Gemini Pro in Stage `matching`) abhängig, die "beste" 1:1 Übereinstimmung korrekt zu identifizieren. Die Subjektivität dieser Aufgabe macht eine umfassende Validierung durch Fachexperten erforderlich, um die Zuverlässigkeit der generierten Artefakte sicherzustellen.

## 6.0 Kritische Annahmen

*   **Datenquellen-Integrität:** Es wird angenommen, dass das G++ Kompendium, die Zielobjekt-Definitionen (CSV) und das Ed2023 JSON-Repository zugänglich, strukturell stabil und inhaltlich korrekt sind.
*   **Stabilität der KI-Modelle:** Es wird angenommen, dass die Vertex AI Services verfügbar sind und konsistente Ergebnisse liefern.
*   **Übergangs-Nutzen:** Es ist verstanden, dass die generierten Artefakte Übergangshilfen darstellen und keine definitive, langfristige Implementierung der G++ Methodik repräsentieren.
