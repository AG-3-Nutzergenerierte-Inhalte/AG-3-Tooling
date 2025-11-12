#!/bin/bash

# Dieses Skript generiert eine Statistik-Tabelle aus einer JSON-Datei.
# Es verwendet 'jq' zur JSON-Verarbeitung.
#
# Verwendung: ./stats.sh <json_datei>
# Beispiel:   ./stats.sh data.json

# --- Validierung ---

# 1. Prüfen, ob ein Dateiname als Argument übergeben wurde
if [ -z "$1" ]; then
  echo "Fehler: Bitte gib den Namen der JSON-Datei als Argument an."
  echo "Verwendung: $0 <json_datei>"
  exit 1
fi

JSON_FILE="$1"

# 2. Prüfen, ob die Datei existiert
if [ ! -f "$JSON_FILE" ]; then
  echo "Fehler: Die Datei '$JSON_FILE' wurde nicht gefunden."
  exit 1
fi

# 3. Prüfen, ob 'jq' installiert ist
if ! command -v jq &> /dev/null; then
  echo "Fehler: 'jq' ist nicht installiert. Bitte installiere 'jq', um dieses Skript auszuführen."
  echo "Installation (z.B. auf Debian/Ubuntu): sudo apt-get install jq"
  echo "Installation (z.B. auf macOS): brew install jq"
  exit 1
fi

# --- Verarbeitung ---

# 1. Header-Zeile drucken
echo "| Name | Baustein | Mapped | unmapped G++ | Summe G++ | Unmapped ED23 | UUID |"

# 2. jq-Befehl zur Verarbeitung der JSON-Daten
#    - keys_unsorted[] as $uuid: Iteriert über alle Top-Level-Schlüssel (die UUIDs)
#    - .[$uuid]: Greift auf das Objekt für die aktuelle UUID zu
#    - [...] | @tsv: Erstellt ein Array mit den gewünschten Werten und formatiert es als TSV (Tab-Separated Values)
#    - tr '\t' '|': Ersetzt die Tabs durch Pipes (|) für das Tabellenformat
jq -r '
  keys_unsorted[] as $uuid | .[$uuid] |
  [
    .zielobjekt_name,
    .baustein_id,
    (.mapping | length),
    (.unmapped_gpp | length),
    ((.mapping | length) + (.unmapped_gpp | length)),
    (.unmapped_ed2023 | length),
    $uuid
  ] | @tsv
' "$JSON_FILE" | tr '\t' '|' | sed 's/^/| /; s/$/ |/' # Fügt am Anfang und Ende Pipes hinzu