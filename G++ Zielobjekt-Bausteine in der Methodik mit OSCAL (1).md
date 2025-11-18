# Einleitung und Zielsetzung

* Zielsetzung  
  * Wir müssen die Menschen mitnehmen, um die Akzeptanz zu erhöhen und auch um die durch GS++ verursachten Bürokratiekosten (2-6 Mrd €) zu senken.  
  * Neue Namen sind notwendig, die die Brücke zwischen alt und neu bilden\! In den Köpfen sind die alten Namen, die es so nicht mehr gibt, oder die gleichen Wörter haben andere Bedeutungen (Profile Alt sind etwas ganz anderes als OSCAL Profiles)  
  * Zuordnung von Alten Anforderungen zu neuen Controls ist notwendig, um Anwendern den Weg zu G++ zu erleichtern  
* Wir brauchen eine Abbildung von unterschiedlichen Typen von Zielobjekten  
  * Um spezifische Sicherheitsanforderungen für diesen Typ als “Stand-Der-Technik” zu hinterlegen (gesetzliche Anforderung)  
  * Um sie in SSP zu nutzen, wenn es mehrere Gruppen des gleichen Zielobjekts gibt  
  * Technisch ist dies nur mit den OSCAL-Components möglich, da es für Zielobjekte die mehrfach in einem SSP vorkommen (z.B. mehrere Gruppen von Servern etc) ein Component pro Gruppe geben muss. Dieser technische Zwang ist in der Art begründet, mit der OSCAL die in SSP über Profiles hinzufügen Controls zusammenfasst. Wenn mehrere Profiles das gleiche Control enthalten, bleibt es als eine Instanz im SSP. Der Bezug zu mehren Gruppen von Zielobjekten ist nur über Components möglich\!  
* Deswegen Zielobjekt-Bausteine\!  
  * Der Name vereint die alte und die neue welt  
    * Menschen können es intuitiv verstehen  
  * Sie enthalten in der neuen OSCAL Struktur verweise auf die alten ED23 Bausteine  
    * Migration von existierenden Verbünden wird ermöglicht  
  * Zum Download bereitgestellt erleichtern sie die Anwendung durch  
    * Klare Vorgaben  
    * Für die Systeme der Anwender spezifische Umsezungshinweise

### Definition Zielobjekt-Baustein

Ein Zielobjekt-Baustein ist ein normatives, primär vom BSI bereitgestelltes Artefakt-Set, das einen spezifischen Zielobjekt-Typ kapselt. Er umfasst drei Kernelemente:

1. Anforderungsumfang (Das "Was"): Die exakte Menge der relevanten Anforderungen aus dem GS++ Kompendium für diesen Zielobjekt Typ, unter Berücksichtigung der vollständigen Vererbungshierarchie. Datenformat ist ein OSCAL-Profile.  
2. Umsetzungshinweise (Das "Wie"): Standardisierte Beschreibungen und Maßnahmen, wie diese Anforderungen für den Zielobjekt-Typ idealtypisch umgesetzt werden (Soll-Umsetzung). Datenformat ist ein OSCAL Component.

### Abgrenzung zu Blaupausen

Die Abgrenzung zu Blaupausen ist essenziell für das Gesamtmodell:

* Zielobjekt-Bausteine sind modulare, komponentenzentrierte Building Blocks. Sie definieren das Standard-Soll für einen einzelnen Asset-Typ (z.B. "Windows Server"). Sie sind weitgehend kontextunabhängig.  
* Blaupausen sind kontextspezifische Sicherheitsbaselines (umgesetzt als \<OSCAL Profile\>). Sie definieren das Soll für einen Anwendungsfall oder einen Informationsverbund. Blaupausen nutzen und kombinieren Anforderungen für verschiedene Asset-Typen und Praktiken und führen spezifisches Tailoring (z.B. Parametrisierung, Festlegung des Sicherheitsniveaus) durch.

### Technisches Modell: Das Zwei-Säulen-Modell

Die Realisierung der Zielobjekt-Bausteine in OSCAL erfolgt durch ein Zwei-Säulen-Modell, das auf der Grundlage des GS++ Katalogs aufbaut.

1. Die Katalog-Basis: Das GS++ Kompendium als \<OSCAL Catalog\> liefert alle Anforderungen (\<Controls\>).  
2. Säule 1: Zielobjekt-Profile (Anforderungsumfang): Für jeden Zielobjekt-Typ wird ein \<OSCAL Profile\> erstellt. Dieses selektiert präzise alle relevanten Anforderungen, ggf. differenziert nach Sicherheitsniveaus.  
3. Säule 2: Zielobjekt-Component-Definition (Identität und Umsetzung): Für jeden Zielobjekt-Typ wird eine \<OSCAL Component Definition\> erstellt. Diese definiert die Identität des Typs und enthält standardisierte Umsetzungshinweise.

Das Set aus der Component Definition (Säule 2\) und den zugehörigen Profilen (Säule 1\) bildet den Zielobjekt-Baustein.

# Kurzüberblick OSCAL

## Definition und Funktion des OSCAL Profile

Ein OSCAL Profile (Profil) ist ein **normatives Anweisungsdokument**, dessen Kernfunktion die Definition einer kontextspezifischen Sicherheitsbaseline ist. Es ist kein eigenständiger Anforderungskatalog. Stattdessen fungiert es als ein "Delta" oder "Overlay", das auf einen oder mehrere existierende OSCAL-Kataloge (z. B. NIST SP 800-53) angewendet wird.

Seine primäre Aufgabe ist es, von einer generischen Anforderungssammlung (dem "Was"-Universum eines Katalogs) zu einem verbindlichen, maßgeschneiderten Soll-Zustand (der "Baseline" für einen Anwendungsfall) zu gelangen.

---

### **Kernfunktion: Das Tailoring-Prinzip**

Die Transformation eines generischen Katalogs in eine Baseline wird als **"Tailoring"** (Maßschneidern) bezeichnet, und das Profil ist das OSCAL-Modell, das diese Anweisungen kodifiziert. Es nutzt drei wesentliche Operationen, die als Anweisungen in der JSON-Struktur des Profils abgebildet werden:

1. **Selektion (Auswahl):** Das Profil deklariert, welche Anforderungen (controls) und Gruppen aus den Quell-Katalogen für den Anwendungsfall relevant sind und welche ignoriert werden.  
2. **Modifikation (Anpassung):** Das Profil kann bestehende Anforderungen verändern. Die häufigste Modifikation ist das verbindliche Setzen von anwendungsspezifischen Werten für Parameter (set-parameters), die im Katalog noch offen oder mit Standardwerten definiert waren.  
3. **Ergänzung (Erweiterung):** Das Profil kann gänzlich neue Anforderungen (add) definieren, die im Quell-Katalog nicht enthalten, aber für den spezifischen Kontext (z. B. organisationsinterne Richtlinien) notwendig sind.

---

### **Technisches Modell und JSON-Analyse**

Technisch gesehen ist ein Profil eine reine Instruktionsliste. Es wird erst wirksam, wenn ein OSCAL-Prozessor es "auflöst" (Resolution) und auf einen Katalog anwendet. Die folgenden JSON-Auszüge demonstrieren diesen Drei-Schritt-Prozess.

#### **1\. Der Katalog (Die Quelle)**

Dies ist ein Auszug aus einem Quell-Katalog. Er definiert die Anforderung cat-ac-1 (Session Lock) mit einem konfigurierbaren Parameter (Default: 30 Minuten).

```json
{  
  "catalog": {  
    "uuid": "uuid-katalog-quelle-01",  
    "controls": [  
      {  
        "id": "cat-ac-1",  
        "title": "Session Lock",  
        "params": [  
          {  
            "id": "cat-ac-1\_prm\_1",  
            "label": "Timeout-Dauer",  
            "props": [  
              { "name": "default-value", "value": "30" }  
            ]  
          }  
        ],  
        "parts": [  
          {  
            "name": "statement",  
            "prose": "Sperrt die Session nach {{ insert: param, cat-ac-1\_prm\_1 }} Minuten."  
          }  
        ]  
      }  
    ]  
  }  
}
```

#### **2\. Das Profil (Die Anweisung)**

Das Profil ist schlank. Es enthält keine Kontrolltexte, sondern nur Anweisungen. Es importiert den Katalog und gibt zwei Tailoring-Anweisungen: (A) Wähle cat-ac-1 aus und (B) Setze dessen Parameter auf '10'.

```json
{  
  "profile": {  
    "uuid": "uuid-profil-baseline-01",  
    "imports": [  
      {  
        "href": "#uuid-katalog-quelle-01"   
      }  
    ],  
    "merge": {  
      "include-controls": [  
        { "with-id": "cat-ac-1" }   
      ]  
    },  
    "modify": {  
      "set-parameters": [  
        {  
          "param-id": "cat-ac-1\_prm\_1",   
          "values": [ "10" ]   
        }  
      ]  
    }  
  }  
}
```

#### **3\. Das "Resolved Profile" (Das Ergebnis)**

Nach der Verarbeitung (Resolution) entsteht ein neuer, "aufgelöster" Katalog. Dieser enthält nur noch die ausgewählte Anforderung, wobei der Parameterwert verbindlich auf '10' gesetzt ist und der Text (Prosa) entsprechend aktualisiert wurde.

```json
{  
  "catalog": {  
    "uuid": "uuid-resolved-baseline-01",  
    "controls": [  
      {  
        "id": "cat-ac-1",  
        "title": "Session Lock",  
        "params": [  
          {  
            "id": "cat-ac-1\_prm\_1",  
            "label": "Timeout-Dauer",  
            "props": [  
              { "name": "default-value", "value": "30" }  
            ],  
            "values": [ "10" ]   
          }  
        ],  
        "parts": [  
          {  
            "name": "statement",  
            "prose": "Sperrt die Session nach 10 Minuten."   
          }  
        ]  
      }  
    ]  
  }  
}
```

---

### **Analyse der JSON-Schlüsselelemente**

Die zentralen JSON-Objekte in einem OSCAL Profile (wie im Beispiel oben) steuern den Tailoring-Prozess:

* **"profile"**: Dies ist das Wurzelelement, das deklariert, dass es sich bei dem Dokument um ein Profil handelt.  
* **"imports"**: Dieses Array ist entscheidend. Es deklariert, welche Quell-Kataloge (via "href"-Referenz auf deren UUID oder URL) als Basis für diese Baseline dienen.  
* **"merge"**: Dieses Objekt steuert die Selektion. **"include-controls"** (oder "include-all") definiert, welche spezifischen Anforderungen aus den importierten Katalogen ausgewählt und in die Baseline übernommen werden. Anforderungen, die nicht importiert und *nicht* inkludiert werden, sind nicht Teil des Ergebnisses.  
* **"modify"**: Dieses Objekt enthält die Anweisungen zur Modifikation. Das darin enthaltene Array **"set-parameters"** ist die häufigste Operation. Es identifiziert einen Parameter über seine "param-id" und weist ihm einen neuen, verbindlichen Wert (oder eine Werteliste) über das "values"-Array zu.  
* **"add"**: (In diesem Beispiel nicht gezeigt) Dieses Objekt würde verwendet, um gänzlich neue, im Profil selbst definierte "controls" hinzuzufügen, die in keinem der importierten Kataloge existierten.

## Was ist eine OSCAL Component Definition?

Eine OSCAL Component Definition ist ein standardisiertes, maschinenlesbares Dokument, das die Sicherheitsfunktionen und \-eigenschaften eines bestimmten IT-Assets beschreibt. Dieses Asset kann eine Hardware (z.B. ein Firewall-Modell), Software (z.B. ein Betriebssystem oder eine Anwendung), ein Service (z.B. ein Cloud-Speicher) oder sogar eine Richtlinie sein.

Stellen Sie sich eine Component Definition als einen "digitalen Sicherheits-Beipackzettel" für eine IT-Komponente vor. Hersteller oder Systemintegratoren können solche Dokumente erstellen, um ihren Kunden oder internen Teams präzise Informationen über die implementierten Sicherheitsmerkmale zu liefern und deren Konfiguration zu beschreiben.

### Der detaillierte Aufbau einer Component Definition

Um die wahre Mächtigkeit der Component Definition zu verstehen, lohnt sich ein genauerer Blick auf ihren detaillierten Aufbau. Sie ist weit mehr als nur eine einfache Liste.

* **Metadaten:** Hier werden allgemeine Informationen wie der Titel des Dokuments, die OSCAL-Version, die Version der Component Definition selbst und das Veröffentlichungsdatum festgehalten.  
* **Import Profile:** Jede Component Definition muss den Sicherheitskatalog oder das Profil referenzieren, auf das sie sich bezieht. Dies stellt den Kontext her (z.B. `href` zu einem OSCAL-Katalog für den BSI IT-Grundschutz oder NIST SP 800-53).  
* **Komponentenbeschreibung (`component`):** Dies ist die Beschreibung des Assets selbst.  
  * `type`: Definiert die Art der Komponente (z.B. `software`, `hardware`, `service`).  
  * `title`: Der Name der Komponente (z.B. "Windows Server 2022 Hardened Template").  
  * `description`: Eine kurze Beschreibung des Zwecks der Komponente.  
  * `props` (Properties): Name-Wert-Paare für zusätzliche Metadaten, wie z.B. Hersteller, Version oder Lizenzinformationen.

### Das Herzstück: Control Implementations (`implemented-requirements`)

Dieser Abschnitt ist der entscheidende Teil der Component Definition. Er beschreibt detailliert, **wie** die Komponente die Anforderungen (Controls) aus dem referenzierten Katalog oder Profil erfüllt. Für jedes relevante Control wird Folgendes festgelegt:

* **`control-id`**: Die eindeutige Referenz auf die Anforderung im Katalog (z.B. die ID `APP.4.4.A3` aus dem BSI IT-Grundschutz oder `ac-2` aus NIST SP 800-53). Dies schafft eine direkte, maschinenlesbare Verknüpfung.  
    
* **`description` / `statement`**: Dies ist die zentrale Implementierungsaussage. Hier wird in Prosa beschrieben, **WIE** diese Komponente die Anforderung typischerweise erfüllt oder dazu beiträgt. Dies kann die Aussage des Herstellers sein ("Unsere Software verschlüsselt Daten im Ruhezustand mittels AES-256") oder eine Musterumsetzung für ein Template ("In diesem Template ist die Audit-Protokollierung standardmäßig aktiviert und konfiguriert.").  
    
* **`set-parameter`**: Dies ist eine der mächtigsten Funktionen. Viele Controls in Katalogen enthalten Platzhalter (Parameter), um flexibel zu bleiben. Die Component Definition kann diese Parameter mit konkreten Werten belegen.  
    
  * **Beispiel:** Ein Control fordert: "Passwörter müssen eine Mindestlänge von *[Mindestlänge der Organisation]* Zeichen haben."  
  * Die `set-parameter`\-Anweisung in der Component Definition für ein "High-Security-System-Template" könnte den Parameter `Mindestlänge der Organisation` auf den Wert `"14"` setzen. Damit wird eine abstrakte Anforderung zu einer konkreten, überprüfbaren Implementierung.


* **`responsible-roles`**: Hier kann definiert werden, wer für die Implementierung verantwortlich ist. Dies ist entscheidend für das Shared-Responsibility-Modell (z.B. in der Cloud). Mögliche Rollen sind `provider` (Anbieter), `customer` (Kunde) oder `shared`. So wird klar, welche Konfigurationsschritte der Nutzer noch selbst durchführen muss.  
    
* **`props` und `links`**: Innerhalb einer Implementierung können zusätzliche Eigenschaften (`props`) und Verweise (`links`) hinzugefügt werden.  
    
  * `props`: z.B. ein `implementation-status` mit dem Wert `complete` oder `partial`.  
  * `links`: z.B. ein Link zu einem externen Konfigurationshandbuch oder einer Wissensdatenbank-Seite, die die Implementierung im Detail beschreibt.

### Was kann eine Component Definition leisten?

* **Wiederverwendbarkeit und Modularität:** Statt Sicherheitsimplementierungen für jede Komponente in jedem System neu zu erfinden und zu dokumentieren, kann auf eine standardisierte, einmal erstellte Definition zurückgegriffen werden.  
* **Automatisierung ("Compliance as Code"):** Da Component Definitions maschinenlesbar sind (JSON, XML, YAML), ermöglichen sie eine weitreichende Automatisierung. System Security Plans (SSPs) können per Knopfdruck generiert werden, indem die Informationen aus den Component Definitions der Systembestandteile aggregiert werden.  
* **Kosten- und Zeitersparnis:** Der Aufwand für die Compliance-Dokumentation wird drastisch reduziert. Systemverantwortliche "erben" die Implementierungsaussagen der Hersteller und müssen nur noch die system-spezifischen Konfigurationen ergänzen.  
* **Verbesserte Genauigkeit und Konsistenz:** Die standardisierte Struktur sorgt für eine einheitliche Beschreibung von Sicherheitsimplementierungen. Manuelle Fehler und Inkonsistenzen werden minimiert.  
* **Transparenz und Nachvollziehbarkeit:** Component Definitions schaffen eine klare Kette von der abstrakten Anforderung (z.B. im BSI-Grundschutz) über die Konkretisierung (z.B. Setzen von Parametern) bis zur Implementierungsaussage für eine spezifische Komponente.

Die Transformation des BSI IT‑Grundschutzes in das maschinenlesbare **Open Security Controls Assessment Language (OSCAL)**‑Format verlagert das Informationssicherheitsmanagement (ISMS) von einer dokumenten­zentrierten auf eine **daten­zentrierte** Arbeitsweise.  
Dieses Dokument beschreibt ein **praxis­taugliches 5‑Phasen‑Modell**, das jeden Schritt des IT‑Grundschutz‑Lebenszyklus – von den normativen Vorgaben des BSI bis zur Abarbeitung von Audit‑Feststellungen – vollständig in OSCAL abbildet.

## System Security Plan (SSP): Das Gesamtbild eines Systems 

Der System Security Plan (SSP) ist das zentrale Dokument, das die Sicherheitsmaßnahmen eines kompletten Informationssystems beschreibt. Er gibt einen Gesamtüberblick darüber, wie das System die geforderten Sicherheitskontrollen erfüllt. Im Gegensatz zur Komponentendefinition, die einen einzelnen Baustein betrachtet, beschreibt der SSP das gesamte System in seinem Betriebskontext.

**Struktur und Funktion eines SSPs:**

* **System-Charakteristika:** Der SSP beschreibt die Attribute des Systems, wie seinen Namen, seinen Zweck, die Art der verarbeiteten Informationen und die allgemeine Sensitivitätseinstufung.  
* **System-Implementierung:** Hier werden Details zur Systemarchitektur, den Benutzerrollen, den Netzwerkverbindungen und dem Software- und Hardware-Inventar festgehalten.  
* **Kontroll-Implementierung (Control Implementation):** Ähnlich wie bei der Komponentendefinition wird hier beschrieben, wie die Kontrollen umgesetzt werden. Der entscheidende Unterschied ist, dass dies auf Systemebene geschieht.  
* **Import eines Profils:** Ein SSP referenziert ein OSCAL-Profil, das die für das System geltende Baseline an Sicherheitskontrollen definiert.

### Das Zusammenspiel: Wie Komponentendefinitionen und SSPs zusammenarbeiten

Die Stärke von OSCAL liegt im intelligenten Zusammenspiel der verschiedenen Modelle. Ein SSP entsteht nicht im luftleeren Raum, sondern wird idealerweise aus einer oder mehreren Komponentendefinitionen "zusammengebaut".

Der Prozess sieht typischerweise so aus:

1. **Bereitstellung von Komponentendefinitionen:** Das BSI, Hersteller oder interne Teams erstellen detaillierte Komponentendefinitionen für die einzelnen Bausteine des Systems (z.B. Betriebssystem, Datenbank, Anwendungsserver).  
2. **Erstellung des SSPs:** Bei der Erstellung des SSPs für ein neues System werden die relevanten Komponentendefinitionen importiert oder referenziert.  
3. **Kontextualisierung im SSP:** Die allgemeinen Kontroll-Implementierungen aus den Komponentendefinitionen werden im SSP in den spezifischen Kontext des Gesamtsystems gesetzt. Der SSP ergänzt diese Informationen um systemweite Aspekte, die keine einzelne Komponente abdecken kann (z.B. physische Sicherheitsmaßnahmen im Rechenzentrum, organisationsweite Richtlinien oder die Interaktion der Komponenten untereinander).  
4. **Shared Responsibility Model:** Der SSP macht durch die Referenzierung der Komponenten klar, wer für welche Kontrollimplementierung verantwortlich ist. So kann eine Kontrolle teilweise durch einen Cloud-Anbieter (dessen Dienst als Komponente definiert ist), teilweise durch eine Software (andere Komponente) und teilweise durch eine organisationsinterne Richtlinie abgedeckt werden.

Durch diesen Ansatz wird die Erstellung von SSPs von einem manuellen, oft redundanten Schreibprozess zu einem effizienteren, bausteinbasierten und letztlich automatisierbaren Vorgang. Er ermöglicht es, Sicherheitsdokumentationen parallel zur Entwicklung zu pflegen ("Compliance-as-Code") und bei Änderungen an einer Komponente nur deren Definition aktualisieren zu müssen, anstatt zahlreiche SSPs manuell anzupassen.

### System Security Plan (SSP)  JSON

Ein System Security Plan (SSP) als JSON-Datei ist naturgemäß sehr strukturiert und für Maschinen optimiert. Anstatt eines narrativen Textes wie in einem Word-Dokument, finden Sie eine hierarchische Anordnung von Objekten und Schlüssel-Wert-Paaren.

Auf der obersten Ebene hat ein OSCAL-SSP-JSON eine Wurzel, typischerweise `"system-security-plan"`. Dieses Wurzelobjekt enthält die Hauptabschnitte des Plans.

Hier ist eine vereinfachte, aber repräsentative Darstellung der Struktur eines SSP in JSON, gefolgt von einer Erklärung der wichtigsten Abschnitte. Vollständige Beispiele finden Sie im OSCAL-GitHub-Repository.

```json
{
  "system-security-plan": {
    "uuid": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "metadata": {
      "title": "System Security Plan für die Unternehmens-Cloud-Anwendung",
      "last-modified": "2025-06-19T12:00:00Z",
      "version": "1.0.0",
      "oscal-version": "1.1.2",
      "roles": [
        { "id": "system-owner", "title": "Systemeigentümer" }
      ],
      "parties": [
        { "uuid": "f1e2d3c4-b5a6-4f7e-8c9d-0a1b2c3d4e5f", "type": "organization", "name": "Beispiel GmbH" }
      ],
      "responsible-parties": [
        { "role-id": "system-owner", "party-uuids": ["f1e2d3c4-b5a6-4f7e-8c9d-0a1b2c3d4e5f"] }
      ]
    },
    "import-profile": {
      "href": "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST\_SP-800-53\_rev5\_MODERATE-baseline\_profile.json"
    },
    "system-characteristics": {
      "system-ids": [
        { "identifier-type": "https://example.com/ids", "id": "ECA-01" }
      ],
      "system-name": "Unternehmens-Cloud-Anwendung",
      "description": "Diese Anwendung dient der Verwaltung von Kundendaten in der Cloud.",
      "security-sensitivity-level": "moderate",
      "information-types": [
        { "title": "Personally Identifiable Information (PII)", "description": "Enthält Namen und Adressen von Kunden." }
      ],
      "authorization-boundary": {
        "description": "Die Autorisierungsgrenze umfasst die Webserver, die Datenbank und das zugehörige virtuelle Netzwerk."
      }
    },
    "system-implementation": {
      "users": [
        { "role-ids": ["admin"], "title": "Administratoren", "description": "Verwalten das System." }
      ],
      "components": [
        {
          "uuid": "c1b2a3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
          "type": "software",
          "title": "Apache Web Server",
          "description": "Der Webserver, der die Anwendung ausliefert.",
          "status": { "state": "operational" }
        }
      ]
    },
    "control-implementation": {
      "description": "Implementierung der Kontrollen gemäß NIST SP 800-53 Rev. 5.",
      "implemented-requirements": [
        {
          "uuid": "d1c2b3a4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
          "control-id": "ac-1",
          "description": "Die Zugriffssteuerungsrichtlinien und -verfahren sind definiert und werden durchgesetzt.",
          "statements": [
            {
              "statement-id": "ac-1\_smt.a",
              "by-components": [
                {
                  "component-uuid": "c1b2a3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                  "description": "Die Zugriffskontrolle wird auf dem Apache Web Server über .htaccess-Dateien und Mod\_authz-Module konfiguriert und durchgesetzt."
                }
              ]
            }
          ]
        }
      ]
    },
    "back-matter": {
      "resources": [
        {
          "uuid": "e1f2a3b4-c5d6-7a8b-9c0d-1e2f3a4b5c6d",
          "description": "Netzwerkdiagramm der Systemarchitektur.",
          "rlinks": [
            { "href": "network-diagram.png", "media-type": "image/png" }
          ]
        }
      ]
    }
  }
}
```

### Erklärung der Schlüsselabschnitte

* **`uuid` und `metadata`**: Jedes OSCAL-Dokument beginnt mit Metadaten. Dies umfasst eine eindeutige ID (`uuid`) für den SSP, den Titel, das Datum der letzten Änderung, die OSCAL-Version sowie die Definition von Rollen (z. B. "Systemeigentümer") und verantwortlichen Parteien (Personen oder Organisationen).  
* **`import-profile`**: Dies ist ein entscheidender Link. Anstatt alle Kontrolldefinitionen zu kopieren, verweist der SSP hier auf ein externes OSCAL-Profil (z. B. ein JSON-Dokument, das die "Moderate"-Baseline von NIST SP 800-53 definiert). Dies macht den SSP schlank und stellt sicher, dass er auf einem standardisierten Set von Anforderungen basiert.  
* **`system-characteristics`**: Hier werden die grundlegenden Eigenschaften des Systems beschrieben. Dazu gehören ein eindeutiger Systemname (`system-name`), eine Beschreibung, der Vertraulichkeitsgrad (`security-sensitivity-level`) und die Definition der Systemgrenzen (`authorization-boundary`).  
* **`system-implementation`**: Dieser Abschnitt beschreibt, wie das System aufgebaut ist. Er enthält eine Liste der Systemkomponenten (`components`) – also der Bausteine wie Server, Datenbanken oder Anwendungen. Hier werden auch Benutzerrollen und Netzwerkverbindungen definiert. Jede Komponente hat ihre eigene `uuid`, um sie eindeutig zu identifizieren.  
* **`control-implementation`**: Dies ist das Herzstück, in dem die eigentliche Arbeit dokumentiert wird. Das Array `implemented-requirements` enthält für jede geforderte Kontrolle (referenziert über die `control-id` wie "ac-1") eine Beschreibung, wie sie umgesetzt wird.  
  * Der entscheidende Punkt ist die Verknüpfung zur Komponentenebene: Innerhalb einer Kontrolle wird unter `by-components` mittels der `component-uuid` genau angegeben, welcher Baustein aus `system-implementation` für die Umsetzung dieser spezifischen Anforderung verantwortlich ist.  
  * Dies zeigt die Stärke von OSCAL: Man kann präzise nachvollziehen, dass die Anforderung "ac-1.a" durch den "Apache Web Server" erfüllt wird, und wie dies geschieht.  
* **`back-matter`**: Dieser Bereich dient als Ablage für zusätzliche Ressourcen wie Anhänge. Man kann hier zum Beispiel auf ein Netzwerkdiagramm verweisen, das dann an anderer Stelle im Dokument referenziert wird.

Zusammenfassend lässt sich sagen, dass das JSON-Format eines SSPs darauf ausgelegt ist, Beziehungen zwischen Kontrollanforderungen, Systemkomponenten und Verantwortlichkeiten explizit und maschinenlesbar zu machen. Anstelle von Prosa werden eindeutige IDs und Verknüpfungen (`href`, `uuid`) verwendet, um ein präzises und automatisierbares Modell der Systemsicherheit zu erstellen.

### **Definition OSCAL Assessment Plan (Prüfplan)**

Ein OSCAL Assessment Plan (AP) ist ein **planerisches Dokument**, das den Umfang, die Methodik und die Logistik einer Sicherheitsüberprüfung (Assessment) formal definiert. Es ist die maßgebliche Blaupause für die Durchführung einer Prüfung und dient als verbindliche Vereinbarung zwischen dem Prüfer (Assessor) und dem Systemeigner.

Seine Kernfunktion ist die **Operationalisierung eines Anforderungsprofils**. Es übersetzt die abstrakte "Soll-Baseline" (typischerweise ein aufgelöstes OSCAL Profile) in eine konkrete, durchführbare Abfolge von Testaktivitäten.

#### **Kernfunktion: Definition von Umfang und Methodik**

Ein Assessment Plan beantwortet die zentralen Fragen *vor* einer Prüfung:

1. **Was wird geprüft?** Es definiert den genauen Prüfgegenstand (z.B. ein spezifisches System, referenziert als OSCAL System Security Plan \- SSP) und die anzuwendende Baseline (das OSCAL Profile).  
2. **Welche Anforderungen werden geprüft?** Es listet präzise auf, welche Anforderungen (controls) aus der Baseline im Scope der Prüfung sind (reviewed-controls).  
3. **Wie wird geprüft?** Es legt die spezifischen Prüfmethoden (z. B. "Examine", "Interview", "Test") und die konkreten Prüfschritte (assessment-actions) fest, die zur Validierung jeder Anforderung erforderlich sind.  
4. **Wer und Womit wird geprüft?** Es identifiziert die beteiligten Rollen, Verantwortlichkeiten und die zu prüfenden Systemkomponenten (assessment-subjects).

#### **JSON-Beispiel (Stark vereinfacht)**

Dieses Beispiel zeigt einen AP, der plant, eine einzelne Anforderung (cat-ac-1) durch eine spezifische Testaktion (Untersuchung der Konfiguration) zu prüfen.

```json
{  
  "assessment-plan": {  
    "uuid": "uuid-ap-01",  
    "metadata": {  
      "title": "Prüfplan für System-X"  
    },  
    "import-ssp": {  
      "href": "#uuid-ssp-system-x"  
    },  
    "reviewed-controls": {  
      "control-selections": [  
        { "include-controls": [ { "with-id": "cat-ac-1" } ] }  
      ]  
    },  
    "assessment-actions": [  
      {  
        "uuid": "uuid-action-01",  
        "title": "Prüfung Session Lock",  
        "description": "Prüfen, ob der Timeout-Wert korrekt gesetzt ist.",  
        "steps": [  
          {  
            "step-id": "step-1",  
            "description": "Konfigurationsdatei 'settings.conf' untersuchen."  
          }  
        ],  
        "related-controls": [  
          { "control-id": "cat-ac-1" }  
        ]  
      }  
    ]  
  }  
}
```

#### **Analyse der JSON-Schlüsselelemente**

* **"import-ssp"**: Referenziert den Prüfgegenstand (das System Security Plan-Dokument), das den "Ist-Zustand" des Systems beschreibt.  
* **"reviewed-controls"**: Definiert den genauen Scope. In diesem Fall wird explizit nur die Anforderung cat-ac-1 in die Prüfung einbezogen.  
* **"assessment-actions"**: Dies ist das Herzstück des Plans. Es definiert die konkreten Testfälle. Jede Aktion ist idealerweise mit einer oder mehreren Anforderungen über **"related-controls"** verknüpft.

---

## Definition OSCAL Assessment Results (Prüfbericht)

Ein OSCAL Assessment Results (AR) ist ein **evidentiary record** (Nachweisdokument), das die Ergebnisse und Beobachtungen einer durchgeführten Sicherheitsüberprüfung dokumentiert. Es ist die formale Antwort auf den OSCAL Assessment Plan und stellt den "Ist-Zustand" der Konformität zum Zeitpunkt der Prüfung fest.

Seine Kernfunktion ist die **Dokumentation von Konformität und Abweichungen (Findings)**. Es hält fest, welche Prüfschritte (aus dem AP) wie durchgeführt wurden, welche Beweise gesammelt wurden und – am wichtigsten – ob die geprüften Anforderungen als erfüllt ("satisfied") oder nicht erfüllt ("not-satisfied") bewertet wurden.

### Kernfunktion: Feststellung von Ergebnissen und Mängeln

Ein Assessment Results-Dokument enthält:

1. **Referenz auf den Plan:** Es importiert den zugrundeliegenden Assessment Plan (import-ap), um den Kontext der Prüfung herzustellen.  
2. **Beobachtungen (Observations):** Dies sind die rohen Beweismittel, die während der Prüfung gesammelt wurden (z.B. Konfigurationsauszüge, Screenshots, Interviewnotizen).  
3. **Ergebnisse (Results):** Für jede geprüfte Anforderung wird eine Konformitätsaussage getroffen.  
4. **Mängel (Findings):** Dies ist das wichtigste Element. Ein "Finding" ist eine formalisierte Feststellung einer Abweichung (eines Mangels) von einer Anforderung.

### JSON-Beispiel (Stark vereinfacht)

Dieses Beispiel dokumentiert das Ergebnis für cat-ac-1. Es wurde eine Beobachtung gemacht (der Wert war '30' statt '10') und ein Mangel (Finding) erstellt.

```json
{  
  "assessment-results": {  
    "uuid": "uuid-ar-01",  
    "metadata": {  
      "title": "Prüfbericht für System-X"  
    },  
    "import-ap": {  
      "href": "#uuid-ap-01"  
    },  
    "results": [  
      {  
        "uuid": "uuid-result-01",  
        "title": "Prüfung von cat-ac-1",  
        "status": "not-satisfied",  
        "observations": [  
          {  
            "uuid": "uuid-obs-01",  
            "description": "Wert in 'settings.conf' war auf '30' gesetzt."  
          }  
        ],  
        "findings": [  
          {  
            "uuid": "uuid-finding-01",  
            "title": "Session Timeout ist falsch konfiguriert",  
            "description": "Der erforderliche Timeout von 10 Minuten (gemäß Profil) wurde nicht umgesetzt. Der Wert ist auf 30 Minuten eingestellt."  
          }  
        ]  
      }  
    ]  
  }  
}
```

### Analyse der JSON-Schlüsselelemente

* **"import-ap"**: Verknüpft den Bericht direkt mit dem Plan, der seine Grundlage war.  
* **"results"**: Ein Array, das die Ergebnisse für die geprüften Anforderungen bündelt.  
* **"status"**: Eine kritische Aussage ("satisfied", "not-satisfied"), die das Ergebnis der Anforderungsprüfung zusammenfasst.  
* **"observations"**: Enthält die Beweismittel, die zu dem Ergebnis geführt haben.  
* **"findings"**: Das Objekt, das einen Mangel formal beschreibt. Es ist die direkte Eingabe für den POA\&M-Prozess.

## Definition OSCAL POA\&M (Plan of Action & Milestones)

Ein OSCAL POA\&M (Plan of Action & Milestones) ist ein **Maßnahmenverfolgungs- und Risikomanagement-Dokument**. Es ist ein "lebendes" Artefakt, das dazu dient, die Behebung von identifizierten Sicherheitsmängeln (den "Findings" aus einem Assessment Results-Dokument) systematisch zu planen, zu verfolgen und zu verwalten.

Seine Kernfunktion ist das **Management von Abweichungen (Remediation Tracking)**. Es stellt sicher, dass für jeden identifizierten Mangel ein klar definierter Behebungsplan, ein Verantwortlicher und eine Zeitachse (Meilensteine) existieren.

#### **Kernfunktion: Management des Mängelbehebungsprozesses**

Ein POA\&M-Dokument ist im Wesentlichen eine Liste von Aufgaben (poam-items), die sich direkt aus den findings eines oder mehrerer Prüfberichte (AR) speist. Für jeden Mangel beantwortet es:

1. **Was ist das Problem?** (Referenz auf das Finding).  
2. **Was ist der Lösungsplan?** (Die "Action").  
3. **Wer ist verantwortlich?** (Rollen oder Personen).  
4. **Wann wird es behoben?** (Die "Milestones").  
5. **Wie ist der aktuelle Stand?** (z.B. "on-going", "completed", "risk-accepted").

#### **JSON-Beispiel (Stark vereinfacht)**

Dieses Beispiel zeigt einen POA\&M-Eintrag, der sich um den zuvor im AR identifizierten Mangel (uuid-finding-01) kümmert.

```json
{  
  "poam": {  
    "uuid": "uuid-poam-system-x-01",  
    "metadata": {  
      "title": "POA\&M für System-X"  
    },  
    "poam-items": [  
      {  
        "uuid": "uuid-poam-item-01",  
        "description": "Session Timeout-Wert in 'settings.conf' auf '10' korrigieren.",  
        "related-findings": [  
          { "finding-uuid": "uuid-finding-01" }  
        ],  
        "milestones": [  
          {  
            "uuid": "uuid-milestone-01",  
            "title": "Korrektur implementiert",  
            "start": "2025-11-12T08:00:00Z",  
            "end": "2025-11-20T17:00:00Z"  
          }  
        ],  
        "status": "on-going"  
      }  
    ]  
  }  
}
```

#### **Analyse der JSON-Schlüsselelemente**

* **"poam-items"**: Das Array, das alle offenen oder verwalteten Mängelbehebungsmaßnahmen enthält.  
* **"related-findings"**: Der kritische Link. Dieses Array verknüpft den POA\&M-Eintrag direkt mit dem spezifischen Mangel (finding-uuid) aus dem Assessment Results-Dokument.  
* **"description"**: Beschreibt die geplante Maßnahme zur Behebung des Mangels.  
* **"milestones"**: Definiert den Zeitplan für die Umsetzung der Maßnahme.  
* **"status"V**: Verfolgt den Fortschritt des Behebungsplans (z.B. "on-going", "completed").

# Der 5‑Phasen‑Lebenszyklus des IT‑Grundschutzes in OSCAL

\+-------------------------------------------------------------------------+

| Phase 1: BSI – Bereitstellung der normativen Grundlagen                 |  
| Akteur: BSI                                                             |  
| Artefakte: OSCAL Katalog, Zielobjekt-Bausteine |  
\+----------------------------------+--------------------------------------+  
                                   |  
                                   V  
\+-------------------------------------------------------------------------+  
| Phase 2: BSI & Branchen – Definition der verbindlichen Soll‑Vorgaben     |  
| Akteur: BSI (primär), Branchenverbände (sekundär)                       |  
| Artefakte: Offizielle BSI‑Profile (Blaupausen), B3S‑Profile|  
\+----------------------------------+--------------------------------------+  
                                   |  
                                   V  
\+-------------------------------------------------------------------------+  
| Phase 3: Organisation – Erstellung des Sicherheitskonzepts              |  
| Akteur: Organisation                                                    |  
| Artefakte: Risikoanalyse-Profil, OSCAL System Security Plan (SSP)       |  
\+----------------------------------+--------------------------------------+  
                                   |  
                                   V  
\+-------------------------------------------------------------------------+  
| Phase 4: Auditor – Prüfung des Sicherheitskonzepts                      |  
| Akteur: Auditor / Prüfer                                                |  
| Artefakte: OSCAL Assessment Plan (AP), OSCAL Assessment Results (AR)    |  
\+----------------------------------+--------------------------------------+  
                                   |  
                                   V  
\+-------------------------------------------------------------------------+

| Phase 5: Organisation – Abarbeitung der Feststellungen                  |  
| Akteur: Organisation                                                   |  
| Artefakt: OSCAL Plan of Action & Milestones (POA\&M)                     |  
\+-------------------------------------------------------------------------+

## Phase 1 – Bereitstellung der Grundlagen durch das BSI

**Akteur:** BSI

| OSCAL‑Artefakt | Zweck |
| :---- | :---- |
| **Katalog** | Vollständiges IT‑Grundschutz‑Kompendium, „Single Source of Truth” für Bausteine & Anforderungen. Das Artefakt existiert. |

Das BSI erstellt diese Artefakte, die für jede Zielgruppe (Privatwirtschaft und Bundesministerien und andere) die klaren und verbindlichen Mindeststandards nach Stand-der-Technik gemäß des gesetzlichen Auftrags definieren.

## Phase 2 – Definition der verbindlichen Soll‑Vorgaben 

**Akteure:** BSI (primär), Branchenverbände („B3S“) (sekundär)

| Name | OSCAL‑Artefakt | Zweck |
| :---- | :---- | :---- |
| **Zielobjekte** | **OSCAL Profiles**  | Die Liste aller Anforderungen, die für ein Zielobjekt gelten. Die OSCAL Profiles sind als zielobjekte.csv bereits vorhanden, den das JSON für die Profile kann über die Vererbung aus dem Katalog erstellt werden. |
| **Zielobjekt-Bausteine** | **Component Definitions** | Wiederverwendbare Vorlagen für die vom Anwender oder Hersteller eines Systems zu erstellenden OSCAL-Components. Die AG 3 Nutzergenerierte Inhalte bietet hier an, eine für alle in der Edition 2023 existierenden Bausteine und eine Liste von aktuell benötigten Bausteinen diese Artefakte automatisiert und qualitätsgesichert zu erstellen. |
| **Blaupausen** | **OSCAL Profiles** | TBD AG Blaupausen Vorschlag wäre das die AG Blaupausen für typischen Organisationen erstellt wie z.B. Bundesministerien, Landesverwaltungen, Kommunale Verwaltungen und AöR. |

## Branchenspezifische Sicherheitsstandards (B3S)

Branchenverbände können wie bei den B3S schon gelebt weiterhin eigene Blaupausen als B3S erstellen, die nach den bereits etablierten Verfahren freigegeben werden.  
B3S‑Profile importieren ein offizielles BSI‑Profil und passen es via `alter` an.  
Beispiel: Ein Krankenhaus‑Profil verschärft einzelne Parameter oder fügt zusätzliche Controls hinzu.

**Wichtig :** Ein B3S‑Profil **muss** dabei stets den offiziellen, versionierten **BSI‑Katalog** sowie die durch das BSI veröffentlichten **Component Definitions** referenzieren. Sollten in der Branche Zielobjekt-Typen im einsatz sein, die nicht vom BSI bereits als Component bereit gestellt werden, so **müssen** diese hinzugefügt werden. Branchenspezifische Erweiterungen erfolgen ausschließlich über `alter` oder zusätzliche `include-controls`; die BSI‑Artefakte selbst werden nicht kopiert oder verändert.

# Phase 3 – Erstellung des Sicherheitskonzepts (SSP) und Risikoanalyse für hohen Schutzbedarf

**Akteur:** Organisation

1. **Sofern vorhanden: Import der Blaupause**  
2. **Import des Zielobjekt-Bausteins “ISMS” Profils:** Alle Anforderungen an das ISMS und seine Prozesse und Dokumente.  
3. **Import aller Zielobjekt-Baustein Zielgruppen-Typ spezifischen Profile** Abdeckung der Zielobjekte im Informationsverbund.  
4. **Durchführung Risikoanalyse** Die zusätzlichen Anforderungen gemäß Risikoanalyse werden in einem RA-Profil eingetragen und in den SSP importiert.  
5. **Instanziierung der Komponenten** – jede reale Ressource im Informationsverbund erhält eine eigene `component`‑Instanz mit eindeutiger `uuid`.  
6. **Dokumentation des Umsetzungs­status** pro Control *und* Komponente via `by-component` im SSP.

## Beispiel – Vier Komponenten & differenzierte Umsetzung

```yaml
# mein-verbund-ssp.yaml
system-security-plan:
  import-profile: profil-ISMS-standardabsicherung.json
  import-profile: profil-windows-server-standardabsicherung.json
  import-profile: risikoanalyse\_verbund.json
  system-characteristics:
    system-id: Mein-Windows-Server-Verbund
    components:
      - uuid: uuid-isms
        type: process
        title: ISMS-Prozesslandschaft
      - uuid: uuid-server-A
        type: hardware
        title: Windows Server A
        description: Produktivserver Finanzbuchhaltung.
      - uuid: uuid-server-B
        type: hardware
        title: Windows Server B
        description: Legacy‑Anwendungsserver.
      - uuid: uuid-server-C
        type: hardware
        title: Windows Server C
        description: Testserver, identisch zu A.
  control-implementation:
    - implemented-requirement:
        control-id: SYS.1.1.A16
        description: Umsetzung der Härtung
        by-component:
          - component-uuid: uuid-server-A
            description: Vollständig umgesetzt via GPO "PROD-Server-Hardening-v2".
          - component-uuid: uuid-server-B
            description: Teilweise umgesetzt – Ausnahme für Port XYZ (Ticket T‑12345).
          - component-uuid: uuid-server-C
            description: Vollständig umgesetzt (gleiches GPO wie A).
```

*Nur ein Control‑Eintrag – drei unterschiedliche Umsetzungs­beschreibungen.*

---

# Phase 4 – Prüfung durch den Auditor

| Schritt | OSCAL‑Artefakt | Inhalt |
| :---- | :---- | :---- |
| **4.1 Assessment Plan** | AP | Prüfumfang, Methodik, Referenz auf SSP. |
| **4.2 Assessment Results** | AR | Strukturierte `observations` und `findings`, jeweils verknüpft mit Control‑ID und Component‑UUID. |

Digital erfasste Nachweise und Feststellungen erlauben eine **voll­automatische Ableitung** von Korrektur­maßnahmen.

# Phase 5 – Abarbeitung der Feststellungen

1. **Generierung des POA\&M**  
   Tools können aus den `findings` des AR automatisch einen **Plan of Action & Milestones (POA\&M)** erzeugen.  
2. **Nachverfolgung**  
   Verantwortliche, Fristen, Fortschritts­tracking – alles in einem maschinenlesbaren Artefakt.

Der POA\&M schließt den Kreis und führt zurück zur laufenden Pflege des SSP.

