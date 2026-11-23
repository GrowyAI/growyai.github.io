"""Split untranslated items into small files for batch translation."""

import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
TRANS = os.path.join(BASE, "translations")
CHUNKS = os.path.join(TRANS, "chunks")
DONE = os.path.join(TRANS, "done")
SIZE = 320

os.makedirs(CHUNKS, exist_ok=True)
os.makedirs(DONE, exist_ok=True)

with open(os.path.join(DATA, "knowledge.json"), encoding="utf-8") as f:
    data = json.load(f)

pending = [i for i in data["items"] if not i.get("zh")]
for idx, start in enumerate(range(0, len(pending), SIZE), 1):
    part = pending[start:start + SIZE]
    payload = [
        {"id": i["id"], "en": i["en"], "subject": i["subject"], "topic": i["topic"], "type": i["type"]}
        for i in part
    ]
    path = os.path.join(CHUNKS, "part-%03d.json" % idx)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
print("created %d chunks of up to %d items (%d pending)" % (
    (len(pending) + SIZE - 1) // SIZE, SIZE, len(pending)))
