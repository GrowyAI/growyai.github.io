"""Merge batch translations back into knowledge.json and regenerate exports."""

import glob
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
TRANS_DONE = os.path.join(BASE, "translations", "done")
SOURCE = os.path.join(DATA, "knowledge.json")

with open(SOURCE, encoding="utf-8") as f:
    data = json.load(f)

valid_ids = {item["id"] for item in data["items"]}
translations = {}
for path in sorted(glob.glob(os.path.join(TRANS_DONE, "*.json"))):
    with open(path, encoding="utf-8") as f:
        batch = json.load(f)
    fresh = {k: v for k, v in batch.items() if k in valid_ids}
    translations.update(fresh)
    print("merged", os.path.basename(path), len(fresh), "of", len(batch))

count = 0
for item in data["items"]:
    zh = translations.get(item["id"])
    if zh and str(zh).strip():
        item["zh"] = str(zh).strip()
        count += 1

with open(SOURCE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("translated items:", count, "of", len(data["items"]))
subprocess.check_call([sys.executable, os.path.join(BASE, "scripts", "export_tables.py")])
