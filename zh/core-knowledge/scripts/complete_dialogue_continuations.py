"""Trim vocabulary bleed and append continuation lines to dialogue turns.

The md extraction keeps reading order, but a spoken turn can be split across
physical lines, and vocabulary headings sometimes stick to the end of a turn.
This script uses the same extraction to clean and complete each turn.
Run with --dry-run to inspect proposals.
"""

import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "knowledge.json")
MD = os.path.join(DATA, "raw", "preschool.md")
EXPORT = os.path.join(BASE, "scripts", "export_tables.py")

STOP_RE = re.compile(r"^(Example:|Note:|NOTE:|Overview:|Core Knowledge Sequence)")
MARKERS = [
    "GRAD P", "GRAD ", "Teacher and Children", "Teacher Only",
    "LANGUAGE OF INSTRUCTION", "Reference Points in Space", "Maps ",
    "Geographic Concepts", "MISCELLANEOUS", "SPECIFIC WRITING STROKES",
    "Animals air alive", "Plants air alive", "Material World",
    "Tools/Construct", "Storybook Reading", "Scientific Reasoning",
    "Orientation in Space", "Nursery Rhymes, Poems", "Oral Language",
    "Autonomy and Social Skills", "Work Habits", "Movement and Coordination",
]


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def looks_like_vocab(text):
    words = text.split()
    if len(words) < 6:
        return False
    lower = sum(1 for w in words if w[:1].islower())
    if lower / len(words) < 0.7:
        return False
    return sum(text.count(c) for c in ".,;:!?…") <= 1


def trim_vocab(text):
    """Remove trailing vocabulary lists that were glued to a dialogue turn."""
    text = norm(text)
    positions = [text.find(m) for m in MARKERS if text.find(m) >= 0]
    if positions:
        text = text[:min(positions)].strip()
    matches = list(re.finditer(r"[.!?…]\s+(?=[a-z])", text))
    if matches:
        tail = text[matches[-1].end():]
        if looks_like_vocab(tail):
            text = text[:matches[-1].end()].strip()
    return text


def find_anchor(lines, turn):
    prefix = norm(turn)[:60]
    for idx, raw in enumerate(lines):
        if norm(raw).startswith(prefix):
            return idx
    return None


def collect_continuations(lines, anchor, max_lines=5):
    added = []
    idx = anchor + 1
    while idx < len(lines) and len(added) < max_lines:
        s = lines[idx].strip()
        idx += 1
        if not s:
            continue
        if (s.startswith("<!--") or s.startswith("#") or s.startswith("|")
                or STOP_RE.match(s) or s.startswith("Adult:")
                or s.startswith("Child:")):
            break
        trimmed = trim_vocab(s)
        if not trimmed or looks_like_vocab(trimmed):
            break
        added.append(trimmed)
        if trimmed != norm(s):
            break
    return added


def main():
    dry_run = "--dry-run" in sys.argv
    with open(SOURCE, encoding="utf-8") as f:
        data = json.load(f)
    with open(MD, encoding="utf-8") as f:
        lines = f.read().splitlines()

    changes = []
    for item in data["items"]:
        if item.get("type") != "dialogue":
            continue
        turns = item["en"].split("\n")
        new_turns = []
        for turn in turns:
            base_turn = trim_vocab(turn)
            anchor = find_anchor(lines, base_turn) if base_turn else None
            if anchor is None:
                new_turns.append(base_turn or norm(turn))
                if base_turn != turn:
                    changes.append((item["id"], turn, base_turn, []))
                continue
            base_line = trim_vocab(lines[anchor])
            extra = collect_continuations(lines, anchor)
            full = norm(" ".join([base_line] + extra))
            chosen = full if len(full) > len(base_turn) else base_turn
            new_turns.append(chosen)
            if chosen != turn:
                changes.append((item["id"], turn, chosen, extra))
        item["en"] = "\n".join(x for x in new_turns if x)

    print("turns completed:", len(changes))
    for item_id, old, new, extra in changes:
        print("---", item_id)
        print("OLD:", old[:160])
        print("NEW:", new[:320])
        print("ADDED:", extra)

    if dry_run:
        return

    with open(SOURCE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    subprocess.check_call([sys.executable, EXPORT])


if __name__ == "__main__":
    main()
