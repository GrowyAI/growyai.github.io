"""Remove the 'subheading' pseudo-type from the dataset.

K-8 PDF extraction produced standalone lines for:
  1. real section labels inside a topic (e.g. ELA skill groups), and
  2. physical line-wrap continuations of the previous bullet (e.g. "...North and South" + "Poles").

This script:
  - merges case (2) back into the preceding item;
  - turns case (1) into a `section` label carried by the following items;
  - converts any remaining stray lines into ordinary content items;
  - writes the English texts that need re-translation after the merge.
"""

import collections
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "knowledge.json")
CHUNK = os.path.join(BASE, "translations", "chunks", "subheading-merges.json")

HEADINGS = {
    "Grasping Specific Details and Key Ideas",
    "Observing Craft and Structure",
    "Integrating Information and Evaluating Evidence",
    "Writing to Reflect Audience, Purpose and Task",
    "Conducting Research",
    "II Reading",
}
HEADING_PREFIXES = (
    "Appendix A Why Listening and Learning are Critical to Reading",
    "Appendix C Teaching History and Geography in the Middle School",
    "Appendix E Core Knowledge Resources",
)
NEVER_CONTINUATION = {"Timeline"}
CONTINUATION_MAX = 100
TERMINAL_PUNCT = (".", "?", "!")
SOURCE_TYPES = {"objective", "question", "work", "note", "dialogue"}


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def item_key(item):
    return (item.get("grade", ""), item.get("subject", ""),
            item.get("topic", ""), item.get("subtopic", ""))


def is_heading(text):
    return text in HEADINGS or text.startswith(HEADING_PREFIXES)


def is_continuation(text, prev):
    if not prev or text in NEVER_CONTINUATION or is_heading(text):
        return False
    if len(text) > CONTINUATION_MAX:
        return False
    if prev.get("type") not in SOURCE_TYPES:
        return False
    return not prev.get("en", "").rstrip().endswith(TERMINAL_PUNCT)


def main():
    with open(SOURCE, encoding="utf-8") as f:
        data = json.load(f)

    kept = []
    section_by_key = {}
    pending = collections.OrderedDict()
    stats = collections.Counter()

    for n, item in enumerate(data["items"]):
        key = item_key(item)
        # Original ids are not globally unique across PDF sections; use a stable
        # positional uid for translation bookkeeping after the merge.
        item["uid"] = item.get("uid") or ("n%05d" % n)

        if item.get("type") == "subheading":
            text = clean(item.get("en", ""))

            if is_heading(text):
                section_by_key[key] = (text, clean(item.get("zh", "")))
                stats["heading"] += 1
                continue

            prev = kept[-1] if kept else None
            if is_continuation(text, prev) and item_key(prev) == key:
                prev["en"] = clean(prev.get("en", "") + " " + text)
                pending[prev["uid"]] = {
                    "uid": prev["uid"],
                    "id": prev["id"],
                    "en": prev["en"],
                    "subject": prev.get("subject", ""),
                    "topic": prev.get("topic", ""),
                    "type": prev.get("type", ""),
                }
                stats["continuation"] += 1
                continue

            # Stray standalone line: keep the content, drop the fake type.
            item["type"] = "note" if text.startswith("Appendix ") else "objective"
            stats["standalone"] += 1

        section = section_by_key.get(key, ("", ""))
        if section[0]:
            item["section"] = section[0]
            if section[1]:
                item["section_zh"] = section[1]
        else:
            item.pop("section", None)
            item.pop("section_zh", None)
        kept.append(item)

    data["items"] = kept
    data["meta"]["item_count"] = len(kept)
    types = data.get("taxonomy", {}).get("item_types", [])
    data["taxonomy"]["item_types"] = [t for t in types if t != "subheading"]

    with open(SOURCE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.makedirs(os.path.dirname(CHUNK), exist_ok=True)
    with open(CHUNK, "w", encoding="utf-8") as f:
        json.dump(list(pending.values()), f, ensure_ascii=False, indent=2)

    print("items:", len(kept), "stats:", dict(stats))
    print("merged English texts needing re-translation:", len(pending))


if __name__ == "__main__":
    main()
