"""Export the curated PD/CC0 image sample to a browser-ready inline JS file.

`data/image-pilot.json` is the canonical list of hand-checked items: each entry
has a Wikimedia Commons file, a thumbnail URL, a larger full-size URL, and the
license metadata. This script writes `data/image-pilot-inline.js` with a
`window.IMAGE_PILOT` map keyed by uid, so the static viewer works from file://
without needing fetch().
"""

import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "image-pilot.json")
OUT = os.path.join(DATA, "image-pilot-inline.js")


def main():
    with open(SOURCE, encoding="utf-8") as f:
        entries = json.load(f)
    by_uid = {}
    for entry in entries:
        uid = entry["uid"]
        by_uid[uid] = {
            "thumb": entry.get("thumb", ""),
            "full": entry.get("full") or entry.get("thumb", ""),
            "license": entry.get("license", ""),
            "artist": entry.get("artist", ""),
            "page": entry.get("page", ""),
            "en": entry.get("en", ""),
            "zh": entry.get("zh", ""),
        }
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.IMAGE_PILOT = ")
        json.dump(by_uid, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print("wrote", OUT, len(by_uid), "items")


if __name__ == "__main__":
    main()
