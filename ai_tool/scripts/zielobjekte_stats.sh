#!/bin/bash

# Dieses Skript generiert eine Statistik-Tabelle durch das Kombinieren
# einer JSON-Datei (UUID -> Array) und einer CSV-Datei (UUID -> Name).
#
# Es verwendet 'jq' zur JSON-Verarbeitung, 'grep' zur Suche und 'awk' zur Extraktion.
#
# Verwendung: ./stats_v2.sh <json_datei> <csv_datei>
# Beispiel:   ./stats_v2.sh controls_map.json zielobjekte.csv

# --- Validierung ---

# 1. Prüfen, ob zwei Dateinamen als Argumente übergeben wurden
if [ $# -ne 2 ]; then
  echo "Fehler: Bitte gib die JSON-Datei und die CSV-Datei als Argumente an."
  echo "Verwendung: $0 <json_datei> <csv_datei>"
  exit 1
fi

JSON_FILE="$1"
CSV_FILE="$2"

# 2. Prüfen, ob die Dateien existieren
if [ ! -f "$JSON_FILE" ]; then
  echo "Fehler: Die JSON-Datei '$JSON_FILE' wurde nicht gefunden."
  exit 1
fi
if [ ! -f "$CSV_FILE" ]; then
  echo "Fehler: Die CSV-Datei '$CSV_FILE' wurde nicht gefunden."
  exit 1
fi

# 3. Prüfen, ob 'jq', 'awk' und 'grep' installiert sind
if ! command -v jq &> /dev/null; then
  echo "Fehler: 'jq' ist nicht installiert. (z.B. sudo apt install jq)"
  exit 1
fi
if ! command -v awk &> /dev/null; then
  echo "Fehler: 'awk' ist nicht installiert."
  exit 1
fi
if ! command -v grep &> /dev/null; then
  echo "Fehler: 'grep' ist nicht installiert."
  exit 1
fi

# --- Verarbeitung ---

# 1. Header-Zeile drucken
echo "| Name | UUID | Anzahl |"
echo "| --- | --- | --- |" # Markdown Tabellen-Trennlinie

# 2. jq-Befehl zur Verarbeitung der JSON-Datei
#    - Extrahiert die UUID (key) und die LÄNGE (length) des Arrays
#    - Gibt beides getrennt durch ein Leerzeichen aus (z.B. "uuid-string 12")
# 3. while read loop
#    - Liest jede Zeile von jq in die Variablen $uuid und $count
# 4. [NEUE LOGIK] grep + awk
#    - 'grep -F -m 1 "$uuid" "$CSV_FILE"': Sucht nach der exakten UUID (-F)
#      in der CSV-Datei und stoppt nach dem ersten Treffer (-m 1).
#    - 'awk -F, '{ print $1 }'': Extrahiert das erste Feld (Name) aus der
#      gefundenen Zeile.

jq -r '.zielobjekt_controls_map | keys_unsorted[] as $uuid | "\($uuid) \(.[$uuid] | length)"' "$JSON_FILE" | while read -r uuid count; do
  
  # Suche die Zeile in der CSV-Datei (ignoriere die Kopfzeile)
  line=$(grep -F -m 1 "$uuid" "$CSV_FILE")
  
  if [ -n "$line" ]; then
    # Wenn grep eine Zeile gefunden hat, extrahiere den Namen (Feld 1)
    name=$(echo "$line" | awk -F, '{ print $1 }')
  else
    # Fallback, falls die UUID in der CSV nicht gefunden wurde
    name="<Nicht gefunden>"
  fi
  
  # Drucke die finale Tabellenzeile
  echo "| $name | $uuid | $count |"

done