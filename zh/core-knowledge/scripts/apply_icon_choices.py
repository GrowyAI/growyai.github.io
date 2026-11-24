"""Apply the user-approved icon choices to knowledge.json.

Only grades listed in scripts/icon-choices.json are touched. Items in those
grades without an explicit choice get an empty emoji list; an explicit empty
list means the item was reviewed and deliberately left without an icon.

After writing the JSON, this script regenerates the CSV/XLSX/inline JS via
export_tables.py so every derived file carries the same icons.
"""

import json
import os
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "knowledge.json")
CHOICES = os.path.join(BASE, "scripts", "icon-choices.json")
BACKUP = os.path.join(DATA, "knowledge-before-icon-curation.json")
EXPORT = os.path.join(BASE, "scripts", "export_tables.py")


def main():
    with open(CHOICES, encoding="utf-8") as f:
        choices = json.load(f)
    with open(SOURCE, encoding="utf-8") as f:
        data = json.load(f)

    if not os.path.exists(BACKUP):
        shutil.copyfile(SOURCE, BACKUP)

    by_uid = {item["uid"]: item for item in data["items"]}
    for grade, mapping in choices.items():
        unknown = sorted(set(mapping) - set(by_uid))
        if unknown:
            raise SystemExit("Unknown uids in icon choices for %s: %s" % (grade, unknown))
        selected = 0
        for item in data["items"]:
            if item.get("grade") != grade:
                continue
            icons = mapping.get(item["uid"], [])
            item["emojis"] = list(icons)
            selected += 1 if icons else 0
        present = sum(1 for item in data["items"] if item.get("grade") == grade)
        print("grade %s: %d/%d items have icons" % (grade, selected, present))

    with open(SOURCE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    subprocess.check_call([sys.executable, EXPORT])
    print("applied icon choices and regenerated derived files")


if __name__ == "__main__":
    main()
