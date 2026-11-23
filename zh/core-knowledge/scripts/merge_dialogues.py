"""Merge consecutive preschool dialogue lines into one dialogue item.

The PDF exporter emitted each Adult:/Child: line as a separate item. This
script collapses adjacent dialogue items from the same chapter and page into
a single item, keeping the first item's id and combining English and Chinese
with newlines. It then regenerates the CSV/XLSX and inline frontend data.
"""

import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "knowledge.json")
EXPORT = os.path.join(BASE, "scripts", "export_tables.py")


def dialogue_key(item):
    return (
        item.get("grade", ""),
        item.get("subject", ""),
        item.get("topic", ""),
        item.get("source", {}).get("page", ""),
    )


def main():
    with open(SOURCE, encoding="utf-8") as f:
        data = json.load(f)

    merged_items = []
    group = []

    def flush():
        if not group:
            return
        if len(group) == 1:
            merged_items.append(group[0])
        else:
            head = dict(group[0])
            head["en"] = "\n".join(x.get("en", "") for x in group)
            head["zh"] = "\n".join(x.get("zh", "") for x in group)
            merged_items.append(head)
        group.clear()

    last_key = None
    for item in data["items"]:
        if item.get("type") == "dialogue":
            key = dialogue_key(item)
            if group and key != last_key:
                flush()
            group.append(item)
            last_key = key
        else:
            flush()
            merged_items.append(item)
            last_key = None
    flush()

    removed = len(data["items"]) - len(merged_items)
    data["items"] = merged_items
    if isinstance(data.get("meta"), dict):
        data["meta"]["item_count"] = len(merged_items)

    with open(SOURCE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("merged %d dialogue items; %d items remain" % (removed, len(merged_items)))
    subprocess.check_call([sys.executable, EXPORT])


if __name__ == "__main__":
    main()
