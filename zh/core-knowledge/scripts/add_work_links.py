"""Add Google search links for concrete work titles.

Quoted short titles in English text are detected conservatively, with section
names and common classroom phrases excluded. Items already typed as `work`
also get a link built directly from their English title, since those bullets
are titles by definition. Each matching item gets one `work` title and one
`link` (a Google search URL) field.
"""

import json
import os
import re
import shutil
from urllib.parse import quote_plus

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "knowledge.json")
BACKUP = os.path.join(DATA, "knowledge-before-work-links.json")

QUOTE_RE = re.compile(r'["“]([^"”]{3,70})["”]')

STOP = {
    "language of instruction", "using the preschool sequence",
    "using the core knowledge sequence", "critical skill", "core knowledge",
    "core knowledge sequence", "sequence", "overview", "note", "retell", "read",
    "and", "why", "warm", "cool", "please", "excuse me", "do re mi",
    "higher-order problem-solving skills", "higher order", "higher-order",
    "american", "the people", "which one is true", "which one is true?",
    "go together", "more than", "putting together", "taking away",
    "little stories", "what if", "what will happen if", "the lucky",
    "father of the constitution", "land of opportunity", "melting pot",
    "mosaic", "wild west", "the common man", "captains of industry",
    "robber barons", "free enterprise", "natural rights", "unalienable rights",
    "rebirth", "dark ages", "decline and fall", "new france", "hellenistic",
    "final solution", "great recession", "seven cities of cibola",
    "what does it mean to be free", "mr. (name)", "ms. (name)", "mrs. (name)",
    "boss", "emperor", "okie", "quakers", "great leader", "myplate",
    "little image", "de-perónize",
}

# Lowercase phrases that are still meaningful things a parent may want to look up.
PHRASES = {
    "one if by land, two if by sea",
    "no taxation without representation",
    "give me liberty or give me death",
    "a house divided against itself cannot stand",
    "with malice toward none, with charity for all",
    "shot heard 'round the world",
    "yankee doodle",
}

HINTS = {
    "Music": "music composer kids listen",
    "Visual Arts": "painting artwork museum kids",
    "English Language Arts": "poem story read aloud kids",
    "Language and Literacy": "nursery rhyme song kids",
    "History and Geography": "history kids explain",
    "Mathematics": "math kids explain",
    "Science": "science kids explain",
    "Social and Emotional Development": "kids activity",
    "Movement and Coordination": "kids activity",
}


def build_headings(items):
    headings = set()
    for item in items:
        for key in ("topic", "subtopic", "section"):
            value = (item.get(key) or "").strip()
            if value:
                headings.add(value.lower())
    return headings


def looks_like_work(candidate, headings):
    title = candidate.strip(" .,;:!?")
    if not (4 <= len(title) <= 70):
        return False
    low = title.lower()
    if low in headings or low in STOP:
        return False
    if "[" in title or "]" in title or "\\" in title:
        return False
    if "“" in title or "”" in title or "(name)" in low:
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'’\-]*", title)
    if not words:
        return False
    if len(words) <= 2 and all(word.isupper() for word in words):
        return False
    if title == title.lower() and low not in PHRASES:
        return False
    return True


def search_url(work, subject):
    query = '"%s" %s' % (work, HINTS.get(subject, "kids learn"))
    return "https://www.google.com/search?q=" + quote_plus(query)


def main():
    with open(SOURCE, encoding="utf-8") as f:
        data = json.load(f)

    if not os.path.exists(BACKUP):
        shutil.copyfile(SOURCE, BACKUP)
    headings = build_headings(data["items"])
    count = 0
    examples = []

    for item in data["items"]:
        item["work"] = ""
        item["link"] = ""
        for match in QUOTE_RE.finditer(item.get("en", "")):
            if not looks_like_work(match.group(1), headings):
                continue
            work = match.group(1).strip(" .,;:!?")
            item["work"] = work
            item["link"] = search_url(work, item.get("subject", ""))
            count += 1
            if len(examples) < 20:
                examples.append((work, item.get("subject", ""), item["en"][:90].replace("\n", " ")))
            break

        if item.get("type") == "work" and not item["link"]:
            title = re.sub(r"\s+", " ", (item.get("en") or "").strip()).strip(" .,;:!?")
            if 3 <= len(title) <= 90:
                item["work"] = title
                item["link"] = search_url(title, item.get("subject", ""))
                count += 1
                if len(examples) < 20:
                    examples.append((title, item.get("subject", ""), "type=work"))

    with open(SOURCE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("items with work links:", count, "of", len(data["items"]))
    for work, subject, text in examples:
        print("-", subject, "|", work, "|", text)


if __name__ == "__main__":
    main()
