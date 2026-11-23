"""Export the updated preschool dialogues for a fresh translation pass."""

import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "knowledge.json")
OUT = os.path.join(BASE, "translations", "chunks", "dialogue-completion.json")

with open(SOURCE, encoding="utf-8") as f:
    data = json.load(f)

entries = []
for item in data["items"]:
    if item.get("type") == "dialogue":
        entries.append({
            "id": item["id"],
            "en": item["en"],
            "subject": item.get("subject", ""),
            "topic": item.get("topic", ""),
            "type": item["type"],
        })

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)

print("wrote %d dialogues to %s" % (len(entries), OUT))
