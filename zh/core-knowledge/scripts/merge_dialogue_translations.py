"""Merge the freshly translated preschool dialogues into knowledge.json."""

import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "knowledge.json")
TRANS = os.path.join(BASE, "translations", "done", "dialogue-completion.json")
EXPORT = os.path.join(BASE, "scripts", "export_tables.py")

with open(SOURCE, encoding="utf-8") as f:
    data = json.load(f)
with open(TRANS, encoding="utf-8") as f:
    translations = json.load(f)

count = 0
for item in data["items"]:
    if item.get("type") == "dialogue" and item["id"] in translations:
        item["zh"] = translations[item["id"]]
        count += 1

with open(SOURCE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("updated %d dialogue translations" % count)
subprocess.check_call([sys.executable, EXPORT])
