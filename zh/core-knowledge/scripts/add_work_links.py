"""Add Google search links for concrete work titles.

Quoted short titles in English text are detected conservatively, with section
names and common classroom phrases excluded. Items already typed as `work`
also get a link built directly from their English title. As a final fallback,
any item still without a link gets a Google search built from the first
Chinese book-title mark 《...》 in its translation. Each matching item gets a
`work` title, an optional `work_en` anchor when an English title can be paired,
and a `link` (a Google search URL).
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
BOOK_RE = re.compile(r"《([^》]{1,80})》")
BOOK_EN_RE = re.compile(r"《[^》]{1,80}》\s*[（(]([^）)]{2,80})[）)]")
YEAR_ONLY_RE = re.compile(r"^[\d\s\-–—/]+$")
YEAR_GROUP_RE = re.compile(
    r"\s*[\[(]\s*(?:c\.\s*)?\d{3,4}[a-z]?(?:\s*[-–—/]\s*\d{2,4})?\s*[\])]"
    r"|\s*,\s*(?:c\.\s*)?\d{3,4}[a-z]?\s*$"
)

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


def english_title_from_en(item):
    """Recover an English work title when 《中文》（…） held only a year.

    The Chinese translation often has a date in parentheses, e.g.
    《星夜》（1889）, which used to be stored as work_en. The English line
    usually has the title too; take the text just before the last date,
    dropping an artist prefix, a descriptive clause, or a "by Author" tail.
    """
    text = re.sub(r"\s+", " ", (item.get("en") or "")).strip()
    text = text.replace("\\[", "[").replace("\\]", "]")
    matches = list(YEAR_GROUP_RE.finditer(text))
    before = text[:matches[-1].start()] if matches else text

    # A semicolon usually separates background from the actual work title.
    if ";" in before:
        before = before.rsplit(";", 1)[1].strip()

    # Assigned readings are often written "Title by Author (year)".
    if item.get("subject") == "English Language Arts":
        by = re.match(r"^(.{3,80}?)\s+by\s+", before, flags=re.I)
        if by:
            before = by.group(1)

    # Most Visual Arts entries are "Artist, Title" or "Title, artist context".
    if "," in before:
        candidate = before.split(",", 1)[1].strip()
        if len(candidate) >= 3 and re.search(r"[A-Za-z]", candidate):
            before = candidate

    # Drop a lowercase explanatory tail after a colon.
    if ":" in before:
        head, tail = before.split(":", 1)
        if tail.strip() and tail.strip()[0].islower():
            before = head

    before = before.strip(" .,;:!?")
    if not (3 <= len(before) <= 110) or not re.search(r"[A-Za-z]", before):
        return ""
    if YEAR_ONLY_RE.fullmatch(before):
        return ""
    return before


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
        item["work_en"] = ""
        item["link"] = ""
        for match in QUOTE_RE.finditer(item.get("en", "")):
            if not looks_like_work(match.group(1), headings):
                continue
            work = match.group(1).strip(" .,;:!?")
            item["work"] = work
            item["work_en"] = work
            item["link"] = search_url(work, item.get("subject", ""))
            count += 1
            if len(examples) < 20:
                examples.append((work, item.get("subject", ""), item["en"][:90].replace("\n", " ")))
            break

        if item.get("type") == "work" and not item["link"]:
            title = re.sub(r"\s+", " ", (item.get("en") or "").strip()).strip(" .,;:!?")
            if 3 <= len(title) <= 90:
                item["work"] = title
                item["work_en"] = title
                item["link"] = search_url(title, item.get("subject", ""))
                count += 1
                if len(examples) < 20:
                    examples.append((title, item.get("subject", ""), "type=work"))

        if not item["link"]:
            match = BOOK_RE.search(item.get("zh", ""))
            if match:
                title = match.group(1).strip()
                if title:
                    item["work"] = title
                    en_match = BOOK_EN_RE.search(item.get("zh", ""))
                    if en_match:
                        en_title = en_match.group(1).strip()
                        en_title = re.sub(r"^(?:英语|英文|English)\s*[:：]\s*", "", en_title, flags=re.I)
                        if YEAR_ONLY_RE.fullmatch(en_title):
                            # 《作品》（1940）: the parenthetical is a date, not a
                            # title. Recover the real English title from `en`.
                            item["work_en"] = english_title_from_en(item)
                        elif en_title and en_title in item.get("en", ""):
                            item["work_en"] = en_title
                    item["link"] = search_url(title, item.get("subject", ""))
                    count += 1

    # Older runs stored a bare year as work_en when 《作品》（1940） was seen.
    # Recover the English title from the English line before inheriting.
    for item in data["items"]:
        if item.get("work_en") and YEAR_ONLY_RE.fullmatch(item["work_en"].strip()):
            item["work_en"] = english_title_from_en(item)

    by_work = {}
    by_en = {}
    for item in data["items"]:
        if item.get("work") and item.get("work_en"):
            by_work.setdefault(item["work"], set()).add(item["work_en"])
        if item.get("en") and item.get("work_en"):
            by_en.setdefault(item["en"], set()).add(item["work_en"])
    for item in data["items"]:
        if not item["link"] or item.get("work_en"):
            continue
        candidates = set()
        if item.get("work") in by_work:
            candidates |= by_work[item["work"]]
        if item.get("en") in by_en:
            candidates |= by_en[item["en"]]
        if len(candidates) == 1:
            item["work_en"] = next(iter(candidates))

    # Case differences (e.g. "untitled" vs "Untitled") break the viewer's
    # exact-match anchor; use the spelling that actually appears in `en`.
    for item in data["items"]:
        anchor = item.get("work_en")
        if not anchor or anchor in (item.get("en") or ""):
            continue
        found = re.search(re.escape(anchor), item.get("en") or "", flags=re.I)
        if found:
            item["work_en"] = found.group(0)

    with open(SOURCE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("items with work links:", count, "of", len(data["items"]))
    for work, subject, text in examples:
        print("-", subject, "|", work, "|", text)


if __name__ == "__main__":
    main()
