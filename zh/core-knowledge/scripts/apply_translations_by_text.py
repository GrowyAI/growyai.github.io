"""Restore Chinese translations after a reparse changes item ids.

The batch translation files are keyed by ids from the original parse. When the
parser changes (for example, merging dialogue lines), ids shift. This script
reconnects translations using the original English text plus context.
"""

import glob
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
TRANS = os.path.join(BASE, "translations")
SOURCE = os.path.join(DATA, "knowledge.json")
EXPORT = os.path.join(BASE, "scripts", "export_tables.py")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    old_entries = []
    for path in sorted(glob.glob(os.path.join(TRANS, "chunks", "part-*.json"))):
        old_entries.extend(load_json(path))

    zh_by_id = {}
    # Stale batch first; newer files override it.
    for pattern in ("stale/part-*.json", "done/new-part-*.json"):
        for path in sorted(glob.glob(os.path.join(TRANS, pattern))):
            zh_by_id.update(load_json(path))

    by_key = {}
    by_en = {}
    for entry in old_entries:
        zh = zh_by_id.get(entry.get("id", ""))
        if not zh:
            continue
        key = (entry.get("en", ""), entry.get("subject", ""),
               entry.get("topic", ""), entry.get("type", ""))
        by_key.setdefault(key, zh)
        by_en.setdefault(entry.get("en", ""), zh)

    data = load_json(SOURCE)

    def lookup(en, subject, topic, typ):
        return (by_key.get((en, subject, topic, typ))
                or by_en.get(en)
                or "")

    filled = 0
    for item in data["items"]:
        subject = item.get("subject", "")
        topic = item.get("topic", "")
        typ = item.get("type", "")
        if typ == "dialogue" and "\n" in item.get("en", ""):
            parts = item["en"].split("\n")
            zh_parts = [lookup(p, subject, topic, typ) for p in parts]
        else:
            zh_parts = [lookup(item.get("en", ""), subject, topic, typ)]
        item["zh"] = "\n".join(zh_parts)
        if item["zh"].strip():
            filled += 1

    with open(SOURCE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("restored Chinese for %d of %d items" % (filled, len(data["items"])))
    subprocess.check_call([sys.executable, EXPORT])


if __name__ == "__main__":
    main()
