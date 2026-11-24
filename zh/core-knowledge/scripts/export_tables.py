"""Export knowledge.json to flat CSV / XLSX views."""

import csv
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "knowledge.json")
CSV_OUT = os.path.join(DATA, "knowledge.csv")
QUESTIONS_CSV = os.path.join(DATA, "questions.csv")
XLSX_OUT = os.path.join(DATA, "knowledge.xlsx")
INLINE_OUT = os.path.join(DATA, "knowledge-inline.js")

GRADE_LABELS = {
    "K": "Kindergarten", "1": "Grade 1", "2": "Grade 2", "3": "Grade 3",
    "4": "Grade 4", "5": "Grade 5", "6": "Grade 6", "7": "Grade 7",
    "8": "Grade 8", "Preschool": "Preschool",
}
COLUMNS = [
    "id", "uid", "grade", "grade_label", "subject", "topic", "subtopic",
    "section", "section_zh", "type", "level", "en", "zh", "emojis",
    "work", "work_en", "link", "details", "source_doc", "source_page", "tags",
]


def row_for(item):
    return [
        item.get("id", ""),
        item.get("uid", ""),
        item.get("grade", ""),
        GRADE_LABELS.get(item.get("grade", ""), item.get("grade", "")),
        item.get("subject", ""),
        item.get("topic", ""),
        item.get("subtopic", ""),
        item.get("section", ""),
        item.get("section_zh", ""),
        item.get("type", ""),
        item.get("level", ""),
        item.get("en", ""),
        item.get("zh", ""),
        " ".join(item.get("emojis", [])),
        item.get("work", ""),
        item.get("work_en", ""),
        item.get("link", ""),
        " | ".join(item.get("details", [])),
        item.get("source", {}).get("doc", ""),
        item.get("source", {}).get("page", ""),
        " | ".join(item.get("tags", [])),
    ]


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)


def write_xlsx(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "knowledge"
    ws.append(COLUMNS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DCE6F1")
    for row in rows:
        ws.append(row)
    widths = {
        "id": 20, "uid": 10, "grade": 10, "grade_label": 14, "subject": 26,
        "topic": 32, "subtopic": 20, "section": 28, "section_zh": 22,
        "type": 12, "level": 10, "en": 70, "zh": 40, "emojis": 10,
        "work": 28, "work_en": 28, "link": 60, "details": 50, "source_doc": 12,
        "source_page": 12, "tags": 20,
    }
    for idx, col in enumerate(COLUMNS, 1):
        ws.column_dimensions[get_column_letter(idx)].width = widths.get(col, 20)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)


def main():
    with open(SOURCE, encoding="utf-8") as f:
        data = json.load(f)
    rows = [row_for(item) for item in data["items"]]
    write_csv(CSV_OUT, rows)
    write_xlsx(XLSX_OUT, rows)
    qrows = [row_for(item) for item in data["items"]
             if item.get("type") in ("question", "dialogue")]
    write_csv(QUESTIONS_CSV, qrows)
    with open(INLINE_OUT, "w", encoding="utf-8") as f:
        f.write("window.KNOWLEDGE = ")
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print("wrote %d rows to CSV and XLSX; %d question/dialogue rows" % (len(rows), len(qrows)))


if __name__ == "__main__":
    main()
