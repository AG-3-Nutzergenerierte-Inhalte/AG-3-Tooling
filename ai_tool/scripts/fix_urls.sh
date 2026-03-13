#!/bin/bash

# Finde alle regulären Dateien ab dem aktuellen Verzeichnis.
# Schließe den .git Ordner aus, um das Repository nicht zu korrumpieren.
find . -type d -name ".git" -prune -o -type f -exec sed -i \
    -e 's|https://raw.githubusercontent.com/AG-3-Nutzergenerierte-Inhalte/Stand-der-Technik-Bibliothek/refs/heads/main/Kompendien/Grundschutz%2B%2B-Kompendium/profile/|https://raw.githubusercontent.com/AG-3-Nutzergenerierte-Inhalte/Stand-der-Technik-Bibliothek/refs/heads/main/Nutzergenerierte-Inhalte/Zielobjektkategorien/profile/|g' \
    -e 's|https://raw.githubusercontent.com/AG-3-Nutzergenerierte-Inhalte/Stand-der-Technik-Bibliothek/refs/heads/main/Kompendien/Grundschutz%2B%2B-Kompendium/komponenten/|https://raw.githubusercontent.com/AG-3-Nutzergenerierte-Inhalte/Stand-der-Technik-Bibliothek/refs/heads/main/Nutzergenerierte-Inhalte/Zielobjektkategorien/komponenten/|g' \
    -e 's|https://raw.githubusercontent.com/BSI-Bund/Stand-der-Technik-Bibliothek/refs/heads/main/Kompendien/Grundschutz%2B%2B-Kompendium/Grundschutz%2B%2B-Kompendium.json|https://raw.githubusercontent.com/AG-3-Nutzergenerierte-Inhalte/Stand-der-Technik-Bibliothek/refs/heads/main/Anwenderkataloge/Grundschutz%2B%2B/Grundschutz%2B%2B-catalog.json|g' {} +

echo "Ersetzungen erfolgreich abgeschlossen."