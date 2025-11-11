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

## **3.0 Pipeline-Architektur und technische Implementierung**

Die Automatisierung ist in separate, ausführbare "Stages" unterteilt, die über Kommandozeilenargumente (`--stage`) gesteuert werden. Jede Stage hat eine klar definierte Aufgabe, von der Datenvorverarbeitung bis zur finalen Zuordnung.

### **3.1 Stage: `stage_strip` - Datenvorverarbeitung**

Diese vorgeschaltete Stage dient dazu, die umfangreichen JSON-Quelldateien von BSI und G++ in ein kompaktes, für Entwickler lesbares Markdown-Format zu überführen. Dies erleichtert die manuelle Analyse und das Debugging. Die Logik berücksichtigt dabei die spezifische Struktur der jeweiligen Quelldateien.

**Prozess:**

1.  **G++-Datenverarbeitung:** Das G++ Kompendium (`Grundschutz++-Kompendium.json`) wird rekursiv durchlaufen, um alle Kontrollen, auch die ineinander verschachtelten, zu erfassen. Die Kontrollen werden basierend auf dem Vorhandensein eines `target_objects`-Eintrags in zwei separate Dateien aufgeteilt:
    *   Kontrollen **mit** `target_objects`-Eintrag werden in `gpp_stripped.md` gespeichert. Dies sind in der Regel die primären, auf Zielobjekte anwendbaren Kontrollen.
    *   Kontrollen **ohne** `target_objects`-Eintrag, die oft prozessualen oder ISMS-Charakter haben, werden in `gpp_isms_stripped.md` gespeichert.
    Für jede Kontrolle werden `id`, `title`, `description` (gekürzt auf 150 Zeichen) und die `UUID` extrahiert.

2.  **BSI-Datenverarbeitung:** Die BSI 2023-Daten (`BSI_GS_OSCAL_current_2023_benutzerdefinierte.json`) werden eingelesen und Anforderungen basierend auf ihrer Gruppenzugehörigkeit gefiltert:
    *   Anforderungen aus den in `constants.ALLOWED_MAIN_GROUPS` definierten Hauptgruppen (z. B. `APP`, `SYS`) werden in `bsi_2023_stripped.md` gespeichert.
    *   Alle anderen Anforderungen (z. B. aus `ISMS`, `ORP`) werden in `bsi_2023_stripped_ISMS.md` gespeichert.

**Code-Beispiel: Rekursive G++-Verarbeitung (`stage_strip.py`)**
```python
def _process_controls_recursively(controls, target_objects_list, isms_list):
    """
    Recursively processes a list of controls, sorting them into two lists
    based on the presence of 'target_objects'.
    """
    for control in controls:
        # ... (Datenextraktion)

        # Sort the control into the appropriate list
        if _has_target_objects(control):
            target_objects_list.append(control_data)
        else:
            isms_list.append(control_data)

        # If there are nested controls, process them recursively
        if "controls" in control:
            _process_controls_recursively(control["controls"], target_objects_list, isms_list)
```

**Ausführung:**
```bash
./ai_tool/scripts/run_local.sh stage_strip
```

### **3.2 Stage: `stage_0` - KI-gestützte Zuordnung**

Dies ist die Kern-Stage der Pipeline. Sie orchestriert den gesamten Prozess der Zuordnung von BSI-Bausteinen und -Anforderungen zu ihren G++-Äquivalenten. Die Stage ist idempotent: Wenn die Ausgabedateien bereits existieren und `OVERWRITE_TEMP_FILES` auf `false` steht, wird die Ausführung übersprungen.

#### **3.2.1 Prozess-Flowchart**

```mermaid
flowchart TD
    A[Start: run_phase_0] --> B{Idempotency Check};
    B -- Files exist --> C[End];
    B -- Files missing --> D[Initialize AiClient];

    D --> E[Load Data];
    subgraph "Daten laden"
        E[Load Zielobjekte, BSI JSON, G++ JSON];
    end

    E --> F[Parse Data];
    subgraph "Daten parsen"
        F[Parse Zielobjekte, BSI Bausteine, G++ Controls];
    end

    F --> G[Loop through BSI Bausteine];
    G --> H{Match Baustein to Zielobjekt};
    H -- KI Call --> I[Matched Zielobjekt UUID];

    I --> J[Get All Inherited Controls];
    subgraph "G++ Vererbung"
        J[Recursively traverse Zielobjekt hierarchy];
        J --> K[Return Dict of {Control-ID: Title}];
    end

    K --> L[Batch BSI Controls];
    L -- Loop over batches --> M{Match BSI Controls to G++ Controls};
    M -- KI Call --> N[Batch Results Map];
    N --> O[Aggregate Batch Results];
    O --> P[Determine Unmatched Controls];

    P --> G;
    G -- End Loop --> Q[Format & Save Outputs];

    subgraph "JSON-Ausgaben"
        Q --> Q1[bausteine_zielobjekt.json];
        Q --> Q2[zielobjekt_controls.json];
        Q --> Q3[controls_anforderungen.json];
    end

    Q --> C;
```

#### **3.2.2 Detaillierter Prozessablauf**

1.  **Daten laden und parsen:**
    *   `Zielobjekte.csv` wird eingelesen, um eine hierarchische Karte (`zielobjekte_map`) zu erstellen, die `ChildOfUUID`-Beziehungen abbildet.
    *   `BSI_GS_OSCAL_current_2023.json` wird geparst, um `bausteine`-Objekte zu extrahieren.
    *   `gpp_kompendium.json` wird geparst, um eine Zuordnung von `Zielobjekt`-Namen zu G++-Kontrollen sowie ein Dictionary aller G++-Kontroll-Titel zu erstellen.

2.  **Hauptverarbeitungsschleife (pro Baustein):**
    *   **Baustein-zu-Zielobjekt-Mapping:** Für jeden BSI-Baustein wird ein KI-Aufruf (`matching.match_baustein_to_zielobjekt`) gestartet, um das semantisch beste G++-Zielobjekt zu finden.
    *   **Vererbungslogik:** `inheritance.get_all_inherited_controls` traversiert rekursiv die `ChildOfUUID`-Hierarchie und sammelt alle vererbten G++-Kontrollen.

        **Code-Beispiel: Rekursive Vererbung (`inheritance.py`)**
        ```python
        def get_all_inherited_controls(...) -> Dict[str, str]:
            # ... (Memoization check)

            # Get controls directly associated with the current Zielobjekt
            inherited_control_ids = set(...)

            # Recursively get controls from the parent
            parent_uuid = current_zielobjekt.get("ChildOfUUID")
            if parent_uuid:
                parent_controls_dict = get_all_inherited_controls(...)
                inherited_control_ids.update(parent_controls_dict.keys())

            # ... (Store in memo and return)
        ```
    *   **Batch-Verarbeitung:** BSI-Anforderungen werden in Batches (Größe: 50) aufgeteilt.
    *   **Anforderung-zu-Kontrolle-Mapping:** Für jeden Batch wird `matching.match_bsi_controls_to_gpp_controls_batch` aufgerufen, um BSI-Anforderungen den am besten passenden G++-Kontrollen zuzuordnen.
    *   **Ermittlung ungenutzter Kontrollen:** Die Differenz zwischen allen vererbten G++-Kontrollen und den tatsächlich zugeordneten wird als `unmatched_controls` für die Baustein-Zielobjekt-Kombination erfasst.

3.  **Speichern der Ergebnisse:** Die gesammelten Daten werden in drei JSON-Dateien geschrieben: `bausteine_zielobjekt.json`, `zielobjekt_controls.json` und `controls_anforderungen.json`.

#### **3.2.3 Fehlerbehandlung und Logging**

Die Pipeline ist robust gegenüber transienten Fehlern bei externen API-Aufrufen und Validierungsfehlern konzipiert.

*   **Retry-Mechanismus:** Alle Aufrufe an das KI-Modell sind in eine Retry-Logik mit exponentiellem Backoff und Jitter gekapselt. Dies stellt sicher, dass vorübergehende Netzwerkprobleme oder kurzzeitige Überlastungen der API nicht zum Abbruch der gesamten Pipeline führen.
*   **Schema-Validierung:** Die `AiClient`-Klasse validiert jede Antwort des KI-Modells strikt gegen ein vordefiniertes JSON-Schema. Schlägt die Validierung fehl (z. B. wegen eines falschen Datentyps oder einer unerwarteten Struktur), wird der Fehler protokolliert (`logging.error`), und die Verarbeitung für das betreffende Element wird übersprungen, ohne den gesamten Prozess zu beenden.
*   **Logging:** Die Anwendung verwendet das Standard-`logging`-Modul von Python.
    *   Im **Testmodus** (`TEST="true"`) werden detaillierte `DEBUG`-Meldungen ausgegeben, um den Kontrollfluss nachzuvollziehen.
    *   Im **Produktionsmodus** werden `DEBUG`-Meldungen unterdrückt, und nur `INFO`-Meldungen und höhere Stufen werden angezeigt, um die Log-Ausgabe übersichtlich zu halten.

## **4.0 OSCAL Implementierung und Struktur**

Die resultierenden Artefakte entsprechen dem OSCAL 1.1.3 Schema.

### **4.1 Struktur der Komponentendefinition**

Die *component-definition* enthält die Metadaten und die *components*, welche die migrierten Entitäten darstellen.

***JSON Beispiel (Auszug)***:
```json
"component-definition" : {
  "uuid" :  "[Generierte UUID]",
  "metadata" : { ... },
  "components" : [
    {
      "uuid" :  "[Component UUID]",
      "type" :  "software",
      "title" :  "Transitional Component: Server (Abgebildet von SYS.1.1)",
      "description" :  "Eine OSCAL-Komponente, die ein Server Zielobjekt darstellt...",
      "control-implementations" : [ ... ]
    }
  ]
}
```

### **4.2 Struktur der implementierten Anforderung**

Das *implemented-requirement* Objekt demonstriert die Integration der G++ Autorität und der Ed2023 Metadaten.

***JSON Beispiel (Auszug)***:
```json
"implemented-requirements" : [
  {
    "uuid" :  "[Generierte UUID]",
    "control-id" :  "ARCH.2.1",
    "props" : [
      {
        "name" :  "ed2023_legacy_id",
        "value" :  "NET.1.1.A5"
      },
      {
        "name" :  "ed2023_legacy_title",
        "value" :  "Aufteilung des Netzes in Segmente"
      }
    ],
    "remarks" :  "Diese G++ Kontrolle ist der designierte 1:1 Nachfolger..."
  }
]
```

## **5.0 Kritische Analyse und methodische Einschränkungen**

Die dem Rahmenwerk auferlegten Einschränkungen bergen signifikante methodische Risiken.

### **5.1 Inhärente semantische Verluste (Die 1:1 Einschränkung)**

Das Verbot von N:M Beziehungen ist die schwerwiegendste Einschränkung.

*   **Verlust durch Zerlegung (*Decomposition Loss*):** Wenn eine Ed2023 Anforderung mehrere Aspekte abdeckt, die in separate G++ Kontrollen zerlegt werden, erzwingt die 1:1 Abbildung die Auswahl nur einer Kontrolle, was zu Informationsverlust führt.
*   **Verzerrung durch Konsolidierung (*Consolidation Distortion*):** Wenn mehrere Ed2023 Anforderungen in einer G++ Kontrolle konsolidiert werden, wird die G++ Kontrolle künstlich für jede Altanforderung repliziert.

### **5.2 Kuratierungs-Aufwand und KI-Abhängigkeit**

Die operative Pipeline ist vollständig von der Qualität des kuratierten Crosswalks abhängig. Die Subjektivität bei der Bestimmung der „einzig besten Übereinstimmung“ macht einen erheblichen Expertenbeitrag zur Validierung erforderlich.

### **5.3 Interoperabilitätsrisiken (Metadaten ohne Namensraum)**

Die Entscheidung, formale Namensräume für Alt-Metadaten wegzulassen, reduziert die Robustheit und Interoperabilität der OSCAL-Artefakte, da automatisierte Tools den Ursprung der Metadaten nicht eindeutig bestimmen können.

## **6.0 Kritische Annahmen**

*   **Kuratierbarkeit:** Es wird angenommen, dass Fachexperten die KI-generierten 1:1 Abbildungen erfolgreich zu einem validierten, statischen Crosswalk kuratieren können.
*   **Datenquellen-Integrität:** Es wird angenommen, dass das G++ Kompendium, die Zielobjekt-Definitionen und das Ed2023 JSON-Repository zugänglich, strukturell stabil und vollständig sind.
*   **Übergangs-Nutzen:** Es ist verstanden, dass die generierten Artefakte Übergangshilfen darstellen und keine definitive, langfristige Implementierungsstrategie repräsentieren.
