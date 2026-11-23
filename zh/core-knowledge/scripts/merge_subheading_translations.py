"""Apply re-translations for bullet points completed by fix_subheadings.py."""

import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "knowledge.json")
DONE = os.path.join(BASE, "translations", "done", "subheading-merges.json")

with open(DONE, encoding="utf-8") as f:
    translations = json.load(f)

with open(SOURCE, encoding="utf-8") as f:
    data = json.load(f)

count = 0
for item in data["items"]:
    zh = translations.get(item.get("uid", ""))
    if zh and str(zh).strip():
        item["zh"] = str(zh).strip()
        count += 1

with open(SOURCE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("re-translated merged bullets:", count, "of", len(translations))
subprocess.check_call([sys.executable, os.path.join(BASE, "scripts", "export_tables.py")])
