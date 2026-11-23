"""Parse extracted Core Knowledge PDF text into a canonical knowledge.json.

Input:  data/raw/gk8.md and data/raw/preschool.md (text extracted from the PDFs)
Output: data/knowledge.json
"""

import json
import os
import re
import unicodedata
from collections import OrderedDict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
OUT = os.path.join(BASE, "data", "knowledge.json")

PAGE_RE = re.compile(r"^<!-- Page (\d+) -->$")
GRADE_SECTION_RE = re.compile(r"^#{1,3}\s*(Kindergarten|Grade\s+[1-8])\s*\|\s*(.+?)\s*$")
GRADE_ONLY_RE = re.compile(r"^#{1,3}\s*(Kindergarten|Grade\s+[1-8])\s*$")
TOPIC_RE = re.compile(r"^([IVXLCDM]+)\.\s+(.*)$")
SUBTOPIC_RE = re.compile(r"^([A-Z])\.\s+(.*)$")
BULLET_RE = re.compile(r"^[-*]\s+(.*)$")
SUBBULLET_RE = re.compile(r"^[Ź•]\s*(.*)$")
CODE_RE = re.compile(r"\b([IVX]-[A-Z]{1,4}\d+(?:\.\d+)?[a-z]?)\b")
QUESTION_RE = re.compile(r"\b(What|Why|How|Who|Where|When|Which|Can|Do|Does|Is|Are|Should|Could|Would)\b.*\?")

GRADE_LABELS = {
    "K": "Kindergarten", "1": "Grade 1", "2": "Grade 2", "3": "Grade 3",
    "4": "Grade 4", "5": "Grade 5", "6": "Grade 6", "7": "Grade 7", "8": "Grade 8",
    "Preschool": "Preschool",
}
SUBJECT_ORDER = [
    "English Language Arts", "History and Geography", "Visual Arts",
    "Music", "Mathematics", "Science",
]
PRESCHOOL_SUBJECTS = [
    "Movement and Coordination", "Social and Emotional Development",
    "Language and Literacy", "Mathematics", "History and Geography",
    "Science", "Music", "Visual Arts",
]
CODE_TOPIC = {
    "MC": ("Movement and Coordination", "Movement and Coordination"),
    "AS": ("Social and Emotional Development", "Autonomy and Social Skills"),
    "OL": ("Language and Literacy", "Oral Language"),
    "NR": ("Language and Literacy", "Nursery Rhymes, Poems, Fingerplays and Songs"),
    "SR": ("Language and Literacy", "Storybook Reading and Storytelling"),
    "EL": ("Language and Literacy", "Emerging Literacy Skills in Reading and Writing"),
    "MR": ("Mathematics", "Mathematical Reasoning and Number Sense"),
    "OT": ("History and Geography", "Orientation in Time"),
    "OS": ("History and Geography", "Orientation in Space"),
    "SC": ("Science", "Scientific Reasoning and the Physical World"),
    "MU": ("Music", "Music"),
    "VA": ("Visual Arts", "Visual Arts"),
}
CHAPTER_MARKERS = [
    "Movement and Coordination",
    "Social and Emotional Development: Autonomy and Social Skills",
    "Social and Emotional Development: Work Habits",
    "Language and Literacy",
    "Nursery Rhymes, Poems, Fingerplays and Songs",
    "Storybook Reading and Storytelling",
    "Emerging Literacy Skills in Reading and Writing",
    "Mathematical Reasoning and Number Sense",
    "History and Geography: Orientation in Time",
    "History and Geography: Orientation in Space",
    "Scientific Reasoning and the Physical World",
    "Music",
    "Visual Arts",
]
CHAPTER_SUBJECT = {
    "Movement and Coordination": "Movement and Coordination",
    "Social and Emotional Development: Autonomy and Social Skills": "Social and Emotional Development",
    "Social and Emotional Development: Work Habits": "Social and Emotional Development",
    "Language and Literacy": "Language and Literacy",
    "Nursery Rhymes, Poems, Fingerplays and Songs": "Language and Literacy",
    "Storybook Reading and Storytelling": "Language and Literacy",
    "Emerging Literacy Skills in Reading and Writing": "Language and Literacy",
    "Mathematical Reasoning and Number Sense": "Mathematics",
    "History and Geography: Orientation in Time": "History and Geography",
    "History and Geography: Orientation in Space": "History and Geography",
    "Scientific Reasoning and the Physical World": "Science",
    "Music": "Music",
    "Visual Arts": "Visual Arts",
}


def norm_grade(raw):
    raw = raw.strip()
    if raw.lower().startswith("kindergarten"):
        return "K"
    m = re.search(r"[1-8]", raw)
    return m.group(0) if m else raw


def clean(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ").replace("\u00ad", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_footer(line):
    if line.startswith("Core Knowledge Sequence |"):
        return True
    if re.fullmatch(r"\d{1,3}", line):
        return True
    if re.fullmatch(r"[K1-8]", line):
        return True
    if re.fullmatch(r"Grade\s*[K1-8]?", line):
        return True
    if re.fullmatch(r"[ivxlcdm]{1,4}", line):
        return True
    if line in ("GRAD P", "K", "P"):
        return True
    return False


def collapse_headings(lines):
    """Merge consecutive # heading lines (with blank lines between) into one."""
    out = []
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("#"):
            parts = []
            while i < len(lines) and (lines[i].lstrip().startswith("#") or lines[i].strip() == ""):
                stripped = lines[i].strip()
                if stripped.startswith("#"):
                    parts.append(re.sub(r"^#+\s*", "", stripped).strip())
                i += 1
            if parts:
                out.append("# " + " ".join(parts))
        else:
            out.append(lines[i])
            i += 1
    return out


def split_teacher(text):
    m = re.search(r"\bTeachers?:\s*", text)
    if not m:
        return text, ""
    return text[:m.start()].strip(), text[m.end():].strip()


def questions_from(text):
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z“])", text)
    found = []
    for part in parts:
        part = clean(part)
        unquoted = re.sub(r"“[^”]*”", "", part)
        if "?" in unquoted and QUESTION_RE.search(unquoted) and len(unquoted) >= 18:
            found.append(part)
    return found


def works_from(text):
    parts = re.findall(r"“([^”]{2,140})”", text)
    return [clean(p) for p in parts if len(clean(p)) >= 5 and not clean(p).endswith(",")]


def slug(text):
    text = clean(text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "item"


def make_item(items, grade, subject, topic, subtopic, typ, en, page, level=None, tags=None):
    item = {
        "id": "",
        "grade": grade,
        "subject": subject,
        "topic": clean(topic) if topic else "",
        "subtopic": clean(subtopic) if subtopic else "",
        "type": typ,
        "en": clean(en),
        "zh": "",
        "source": {"doc": "preschool" if grade == "Preschool" else "k8", "page": page},
        "tags": tags or [],
    }
    if level:
        item["level"] = level
    items.append(item)
    return item


def parse_k8(lines):
    items = []
    structure = []
    page = 0
    grade = None
    subject = None
    in_overview = False
    cur_topic = ""
    cur_sub = ""
    cur_item = None
    section_items = []

    def flush():
        nonlocal section_items, cur_item, cur_topic, cur_sub
        if subject and grade:
            for idx, item in enumerate(section_items, 1):
                item["id"] = "k8-%s-%s-%04d" % (grade, slug(subject)[:18], idx)
            topics = OrderedDict()
            for item in section_items:
                t = item["topic"] or "(General)"
                if t not in topics:
                    topics[t] = []
                if item["subtopic"] and item["subtopic"] not in topics[t]:
                    topics[t].append(item["subtopic"])
            structure.append({
                "grade": grade,
                "label": GRADE_LABELS[grade],
                "subject": subject,
                "topics": [{"title": t, "subtopics": s} for t, s in topics.items()],
            })
            items.extend(section_items)
        section_items = []
        cur_item = None
        cur_topic = ""
        cur_sub = ""

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        m = PAGE_RE.match(line)
        if m:
            page = int(m.group(1))
            continue
        if line.startswith("<!--") or is_footer(line):
            continue

        ms = GRADE_SECTION_RE.match(line)
        if ms:
            flush()
            grade = norm_grade(ms.group(1))
            subject = clean(ms.group(2))
            in_overview = False
            continue
        if GRADE_ONLY_RE.match(line):
            grade = norm_grade(line.lstrip("#").strip())
            in_overview = True
            continue
        if line.startswith("#"):
            flush()
            if "Overview of Topics" in line:
                in_overview = True
            continue
        if in_overview or not grade or not subject:
            continue

        mt = TOPIC_RE.match(line)
        if mt:
            cur_item = None
            title, teacher = split_teacher(mt.group(2))
            cur_topic = clean(title)
            cur_sub = ""
            if teacher:
                make_item(section_items, grade, subject, cur_topic, "", "note", teacher, page)
                for q in questions_from(teacher):
                    make_item(section_items, grade, subject, cur_topic, "", "question", q, page)
            continue

        msu = SUBTOPIC_RE.match(line)
        if msu and len(line) < 220:
            cur_item = None
            title, teacher = split_teacher(msu.group(2))
            cur_sub = clean(title)
            if teacher:
                make_item(section_items, grade, subject, cur_topic, cur_sub, "note", teacher, page)
                for q in questions_from(teacher):
                    make_item(section_items, grade, subject, cur_topic, cur_sub, "question", q, page)
            continue

        mb = BULLET_RE.match(line)
        if mb:
            cur_item = None
            text = clean(mb.group(1))
            works = works_from(text) if text.count("“") >= 3 else []
            typ = "question" if "?" in text and QUESTION_RE.search(text) else "objective"
            cur_item = make_item(section_items, grade, subject, cur_topic, cur_sub, typ, text, page)
            if works and typ != "question":
                for w in works:
                    make_item(section_items, grade, subject, cur_topic, cur_sub, "work", w, page)
            continue

        msb = SUBBULLET_RE.match(line)
        if msb:
            detail = clean(msb.group(1))
            if detail and cur_item:
                extra = cur_item.get("details", [])
                for part in re.split(r"[Ź•]\s*", detail):
                    part = clean(part)
                    if part:
                        extra.append(part)
                cur_item["details"] = extra
            continue

        # Remaining paragraphs: notes, subheadings, works, or wrapped bullet text.
        if re.match(r"^(Teachers?:|Note:|NOTE:|Overview:)", line):
            cur_item = None
            make_item(section_items, grade, subject, cur_topic, cur_sub, "note", line, page)
            for q in questions_from(line):
                make_item(section_items, grade, subject, cur_topic, cur_sub, "question", q, page)
            continue
        if re.fullmatch(r"[A-Z][A-Za-z ’'\-–,]{3,79}", line) and not line.endswith("."):
            cur_item = None
            make_item(section_items, grade, subject, cur_topic, cur_sub, "subheading", line, page)
            continue
        if line.count("“") >= 3:
            cur_item = None
            for w in works_from(line):
                make_item(section_items, grade, subject, cur_topic, cur_sub, "work", w, page)
            continue
        if cur_item:
            cur_item["en"] = clean(cur_item["en"] + " " + line)
            if "?" in line and QUESTION_RE.search(line):
                cur_item["type"] = "question"

    flush()
    return items, structure


def parse_preschool(lines):
    items = []
    structure = []
    page = 0
    chapter = ""
    chapter_items = []
    dialogue_buf = []
    dialogue_page = 0

    def flush():
        nonlocal chapter_items
        flush_dialogue()
        if chapter:
            for idx, item in enumerate(chapter_items, 1):
                item["id"] = "ps-%s-%04d" % (slug(chapter)[:18], idx)
            topics = OrderedDict()
            for item in chapter_items:
                topics.setdefault(item["topic"] or "(General)", [])
            structure.append({
                "grade": "Preschool",
                "label": "Preschool",
                "subject": CHAPTER_SUBJECT.get(chapter, chapter),
                "topics": [{"title": t, "subtopics": []} for t in topics],
            })
            items.extend(chapter_items)
        chapter_items = []

    def chapter_subject():
        return CHAPTER_SUBJECT.get(chapter, chapter)

    def flush_dialogue():
        nonlocal dialogue_buf, dialogue_page
        if dialogue_buf:
            text = "\n".join(clean(x) for x in dialogue_buf)
            item = make_item(chapter_items, "Preschool", chapter_subject(), chapter, "",
                             "dialogue", text, dialogue_page)
            item["en"] = text
            dialogue_buf = []
            dialogue_page = 0

    for raw_line in lines:
        line = raw_line.strip()
        m = PAGE_RE.match(line)
        if m:
            page = int(m.group(1))
            continue
        if not line or line.startswith("<!--"):
            continue
        if line.startswith("#"):
            title = clean(line.lstrip("#"))
            matched = None
            for marker in CHAPTER_MARKERS:
                if title.lower().startswith(marker.lower()) or marker.lower().startswith(title.lower()):
                    matched = marker
                    break
            if matched:
                flush()
                chapter = matched
            continue
        if not chapter:
            continue
        if is_footer(line):
            continue

        is_dialogue_line = line.startswith("Adult:") or line.startswith("Child:")
        if not is_dialogue_line:
            flush_dialogue()

        if re.match(r"^(Overview:|Note:|NOTE:)", line):
            make_item(chapter_items, "Preschool", chapter_subject(), chapter, "", "note", line, page)
            for q in questions_from(line):
                make_item(chapter_items, "Preschool", chapter_subject(), chapter, "", "question", q, page)
            continue

        if is_dialogue_line:
            if not dialogue_buf:
                dialogue_page = page
            dialogue_buf.append(line)
            continue

        if "LANGUAGE OF INSTRUCTION" in line.upper():
            continue

        tokens = line.split()
        if (len(tokens) >= 8 and not re.search(r"[.!?]", line)
                and sum(1 for t in tokens if t.islower()) >= 0.8 * len(tokens)):
            words = [t for t in tokens if t.islower() and len(t) >= 2]
            make_item(chapter_items, "Preschool", chapter_subject(), chapter, "", "vocabulary", " ".join(words), page)
            continue

        codes = list(CODE_RE.finditer(line))
        for idx, cm in enumerate(codes):
            code = cm.group(1)
            rest = line[cm.end():]
            nxt = codes[idx + 1].start() if idx + 1 < len(codes) else len(line)
            if idx + 1 < len(codes):
                rest = line[cm.end():nxt]
            rest = re.split(r"\bGOAL:|Level [IVX]\b", rest)[0]
            text = clean(rest)
            if not text:
                continue
            prefix = code.split("-")[1]
            prefix = re.match(r"[A-Z]+", prefix).group(0)
            subject, topic = CODE_TOPIC.get(prefix, (chapter, chapter))
            level = "Level I" if code.startswith("I-") else "Level II"
            make_item(chapter_items, "Preschool", subject, topic, code, "skill", "%s %s" % (code, text), page, level=level)
            for q in questions_from(text):
                make_item(chapter_items, "Preschool", subject, topic, code, "question", q, page, level=level)

    flush_dialogue()
    flush()
    return items, structure


def main():
    with open(os.path.join(RAW, "gk8.md"), encoding="utf-8") as f:
        k8_lines = collapse_headings(f.read().splitlines())
    with open(os.path.join(RAW, "preschool.md"), encoding="utf-8") as f:
        ps_lines = collapse_headings(f.read().splitlines())

    k8_items, k8_struct = parse_k8(k8_lines)
    ps_items, ps_struct = parse_preschool(ps_lines)

    all_items = ps_items + k8_items
    seen = set()
    unique = []
    for item in all_items:
        key = (item["grade"], item["subject"], item["topic"], item["subtopic"], item["type"], item["en"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    data = {
        "meta": {
            "title": "Core Knowledge Sequence knowledge points",
            "edition": "2023",
            "sources": [
                {"doc": "preschool", "file": "CK_Sequence2023_PreSchool_W2.pdf", "pages": 62},
                {"doc": "k8", "file": "CK_Sequence2023_GK8_W3.pdf", "pages": 355},
            ],
            "generated_by": "scripts/parse_pdfs.py",
            "item_count": len(unique),
        },
        "taxonomy": {
            "grades": list(GRADE_LABELS.values()),
            "preschool_subjects": PRESCHOOL_SUBJECTS,
            "k8_subjects": SUBJECT_ORDER,
            "item_types": ["skill", "objective", "detail", "question", "note", "work", "vocabulary", "dialogue", "subheading"],
        },
        "items": unique,
        "structure": ps_struct + k8_struct,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("wrote %s with %d items" % (OUT, len(unique)))
    print("K8 items: %d, Preschool items: %d" % (len(k8_items), len(ps_items)))


if __name__ == "__main__":
    main()
