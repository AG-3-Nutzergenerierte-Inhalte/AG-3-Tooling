#!/bin/bash

# Dieses Skript generiert eine Statistik-Tabelle durch das Kombinieren
# einer JSON-Datei (UUID -> Array) und einer CSV-Datei (UUID -> Name).
#
# Es verwendet 'jq' zur JSON-Verarbeitung und 'awk' zur CSV-Verarbeitung.
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

# 3. Prüfen, ob 'jq' und 'awk' installiert sind
if ! command -v jq &> /dev/null; then
  echo "Fehler: 'jq' ist nicht installiert. (z.B. sudo apt install jq)"
  exit 1
fi
if ! command -v awk &> /dev/null; then
  echo "Fehler: 'awk' ist nicht installiert. (Dies ist sehr ungewöhnlich)"
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
# 4. awk-Befehl
#    - Sucht in der CSV-Datei nach der $uuid
#    - -F, : Setzt das Trennzeichen auf Komma
#    - -v id="$uuid": Übergibt die Shell-Variable $uuid an awk
#    - NR > 1: Überspringt die Kopfzeile (Zeilennummer > 1)
#    - $7 == id: Prüft, ob die 7. Spalte (UUID) mit unserer ID übereinstimmt
#    - { print $1 }: Wenn ja, drucke die 1. Spalte (Zielobjekt/Name)

jq -r '.zielobjekt_controls_map | keys_unsorted[] as $uuid | "\($uuid) \(.[$uuid] | length)"' "$JSON_FILE" | while read -r uuid count; do
  
  # Suche den Namen in der CSV-Datei (ignoriere die Kopfzeile)
  # [NEU] Verwende 'sub' statt 'gensub' für bessere Kompatibilität.
  # 'sub' entfernt Leerzeichen/Wagenrückläufe (z.B. \r) am Ende von Spalte 7.
  name=$(awk -F, -v id="$uuid" 'NR > 1 { col7 = $7; sub(/[[:space:]]+$/, "", col7); if (col7 == id) print $1 }' "$CSV_FILE")
  
  # Fallback, falls die UUID in der CSV nicht gefunden wurde
  if [ -z "$name" ]; then
    name="<Nicht gefunden>"
  fi
  
  # Drucke die finale Tabellenzeile
  echo "| $name | $uuid | $count |"

done