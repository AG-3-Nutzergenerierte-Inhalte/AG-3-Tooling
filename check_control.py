import json
import os

path = "Stand-der-Technik-Bibliothek/Kompendien/Grundschutz++-Kompendium/Grundschutz++-Kompendium.json"

if not os.path.exists(path):
    print(f"File not found: {path}")
    exit(1)

with open(path, 'r') as f:
    data = json.load(f)

def find_control(data, target_id):
    if isinstance(data, dict):
        if data.get("id") == target_id:
            return True
        for key, value in data.items():
            if find_control(value, target_id):
                return True
    elif isinstance(data, list):
        for item in data:
            if find_control(item, target_id):
                return True
    return False

target = "KONF.14.5"
found = find_control(data, target)
print(f"Control {target} found: {found}")

target2 = "KONF.6.13"
print(f"Control {target2} found: {find_control(data, target2)}")
