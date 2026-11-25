#!/usr/bin/env python3
"""Build canonical data for the 2012 MOE preschool learning-and-development guide.

Input is the locally extracted (gitignored) DOC text; output is the public,
tracked data layer only. No application/UI code is generated here.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "source" / "extracted" / "3-6岁儿童学习与发展指南.txt"
DATA = ROOT / "data"

DOMAIN_CODES = {"健康": "h", "语言": "l", "社会": "s", "科学": "c", "艺术": "a"}
DOMAIN_NUMS = dict(zip(DOMAIN_CODES, "一二三四五"))
LEVELS = OrderedDict([("小班", "3-4岁"), ("中班", "4-5岁"), ("大班", "5-6岁")])
LEVEL_CODES = {"小班": "x", "中班": "z", "大班": "d"}

SOURCE = {
    "id": "moe-preschool-2012",
    "title": "3-6岁儿童学习与发展指南",
    "document_no": "教基二〔2012〕4号",
    "issuer": "中华人民共和国教育部",
    "published": "2012-10-09",
    "guide_date": "2012年9月",
    "url": "http://www.moe.gov.cn/srcsite/A06/s3327/201210/t20121009_143254.html",
    "local_file": "source/幼儿园-3-6岁儿童学习与发展指南.doc",
    "note": "行政指导文件；本站为非官方整理，若与原文有出入，以教育部发布的原文为准。",
}


def read_source() -> tuple[list[str], dict[str, int]]:
    raw = RAW.read_text(encoding="utf-8").splitlines()
    toc: dict[str, int] = {}
    for line in raw:
        m = re.search(
            r"\x01\x14([^\t\x13\x14\x15]+)\t\x13\s*PAGEREF[^\x01\x15]*\x01\x14(\d+)",
            line,
        )
        if m:
            toc[m.group(1).strip()] = int(m.group(2))

    lines = []
    for line in raw:
        line = "".join(ch for ch in line if ord(ch) >= 32 or ch == "\t")
        # Leading tabs are table cell boundaries in the DOC; keep them.
        line = line.rstrip()
        if not line:
            continue
        if line.lstrip().startswith("TOC ") or "HYPERLINK" in line or "PAGEREF" in line:
            continue
        if re.fullmatch(r"[—–\-\s]*PAGE\s*\d+[—–\-\s]*", line):
            continue
        lines.append(line)
    start = next(i for i, line in enumerate(lines) if re.fullmatch(r"说\s*明", line.strip()))
    lines = lines[start:]
    while len(lines) >= 2 and not lines[-1] and not lines[-2]:
        lines.pop()
    return lines, toc


def tidy(text: str) -> str:
    text = re.sub(r"\s+([，。！？；：、）])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def split_reference(cell: str) -> tuple[str, list[str]]:
    """Separate the height/weight reference table from the goal statement."""
    keep: list[str] = []
    ref: list[str] = []
    in_ref = False
    for line in (x.strip() for x in cell.splitlines()):
        if not line:
            continue
        if line.startswith("身高和体重适宜"):
            keep.append("身高和体重适宜。")
            in_ref = True
            continue
        if in_ref:
            both = re.match(r"^身高：(.+?)体重：(.+)$", line)
            if both:
                ref.extend([f"身高：{both.group(1)}", f"体重：{both.group(2)}"])
                continue
            if line.startswith(("男孩：", "女孩：", "身高：", "体重：")):
                ref.append(line)
                continue
        in_ref = False
        keep.append(line)
    return "\n".join(keep), ref


def split_items(cell: str) -> tuple[list[str], list[str]]:
    """Return short goal items and optional height/weight reference rows."""
    cell = re.sub(r"\n\s*注：.*$", "", cell.strip(), flags=re.S).strip()
    if not cell:
        return [], []
    reference: list[str] = []
    if "参考标准" in cell:
        cell, reference = split_reference(cell)

    lines = [re.sub(r"\s+", " ", x).strip() for x in cell.splitlines() if x.strip()]
    numbered = [i for i, x in enumerate(lines) if re.match(r"^\d+[．.、]\s*", x)]
    if numbered:
        items = []
        for idx, start in enumerate(numbered):
            end = numbered[idx + 1] if idx + 1 < len(numbered) else len(lines)
            seg = [re.sub(r"^\d+[．.、]\s*", "", lines[start])] + lines[start + 1 : end]
            text = tidy("".join(seg))
            if text:
                items.append(text)
        return items, reference

    # Unnumbered columns put one item per paragraph; narrow cells sometimes wrap
    # a single sentence across lines, so only close an item at sentence punctuation.
    items: list[str] = []
    buf = ""
    for line in lines:
        buf += line
        if re.search(r"[。！？；）)]$", buf):
            items.append(tidy(buf))
            buf = ""
    if buf.strip():
        items.append(tidy(buf))
    return items, reference


def split_suggestions(block: str) -> list[tuple[str, list[str]]]:
    lines = [re.sub(r"\s+", " ", x).strip() for x in block.splitlines() if x.strip()]
    numbered = [i for i, x in enumerate(lines) if re.match(r"^\d+[．.、]\s*", x)]
    if not numbered:
        return [(tidy(x), []) for x in lines]
    out = []
    for idx, start in enumerate(numbered):
        end = numbered[idx + 1] if idx + 1 < len(numbered) else len(lines)
        head = tidy(re.sub(r"^\d+[．.、]\s*", "", lines[start]))
        out.append((head, [tidy(x) for x in lines[start + 1 : end]]))
    return out


def parse_goals(lines: list[str]) -> list[dict]:
    goals: list[dict] = []
    domain = aspect = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r"^([一二三四五])、(.+)$", line)
        if m and m.group(2) in DOMAIN_CODES:
            domain, aspect = m.group(2), None
            i += 1
            continue
        m = re.match(r"^（([一二三四五])）(.+)$", line)
        if m:
            aspect = m.group(2)
            i += 1
            continue
        m = re.match(r"^目标\s*(\d+)\s+(.+)$", line)
        if m:
            goal_no, goal = int(m.group(1)), m.group(2).strip()
            j = i + 1
            block: list[str] = []
            while j < len(lines):
                nxt = lines[j].strip()
                if (
                    re.match(r"^目标\s*\d+", nxt)
                    or re.match(r"^[一二三四五]、", nxt)
                    or re.match(r"^（[一二三四五]）", nxt)
                ):
                    break
                block.append(lines[j])
                j += 1
            joined = "\n".join(block)
            pos = joined.find("教育建议：")
            table, suggestion_block = (
                (joined[:pos], joined[pos + len("教育建议：") :]) if pos >= 0 else (joined, "")
            )
            table = re.sub(
                r"^3\s*[~～-]\s*4岁\s*\t\s*4\s*[~～-]\s*5岁\s*\t\s*5\s*[~～-]\s*6岁\s*\t+",
                "",
                table.strip(),
            )
            cells = [x.strip() for x in table.split("\t")[:3]]
            goals.append(
                {
                    "domain": domain,
                    "aspect": aspect,
                    "goal_no": goal_no,
                    "goal": goal,
                    "cells": cells,
                    "suggestions": split_suggestions(suggestion_block),
                }
            )
            i = j
            continue
        i += 1
    return goals


def build() -> dict:
    lines, toc = read_source()
    goals = parse_goals(lines)
    items: list[dict] = []
    aspect_order: dict[str, list[str]] = {}

    for g in goals:
        aspects = aspect_order.setdefault(g["domain"], [])
        if g["aspect"] not in aspects:
            aspects.append(g["aspect"])
        aspect_index = aspects.index(g["aspect"]) + 1
        num = DOMAIN_NUMS[g["domain"]]
        prefix = f"ps-{DOMAIN_CODES[g['domain']]}-a{aspect_index}-g{g['goal_no']}"
        page = toc.get(f"（{'一二三四五'[aspect_index - 1]}）{g['aspect']}") or toc.get(
            f"{num}、{g['domain']}"
        )
        common = {
            "domain": g["domain"],
            "aspect": g["aspect"],
            "goal_no": g["goal_no"],
            "goal": g["goal"],
            "source_id": SOURCE["id"],
            "source_page": page,
        }
        for level, cell in zip(LEVELS, g["cells"]):
            texts, ref = split_items(cell)
            for index, text in enumerate(texts, 1):
                item = dict(common)
                item.update(
                    {
                        "uid": f"{prefix}-{LEVEL_CODES[level]}-{index:02d}",
                        "type": "goal",
                        "stage": level,
                        "age": LEVELS[level],
                        "text": text,
                    }
                )
                if ref and index == 1:
                    item["reference"] = ref
                items.append(item)
        for index, (text, examples) in enumerate(g["suggestions"], 1):
            item = dict(common)
            item.update(
                {
                    "uid": f"{prefix}-s-{index:02d}",
                    "type": "suggestion",
                    "text": text,
                    "examples": examples,
                }
            )
            items.append(item)

    return {
        "schema_version": 1,
        "meta": {
            "id": SOURCE["id"],
            "title": SOURCE["title"],
            "stage": "幼儿园",
            "levels": [{"stage": k, "age": v} for k, v in LEVELS.items()],
            "source": SOURCE,
            "source_page_note": "source_page 是所属“方面”在指南印刷版中的起始页，由目录提取。",
            "item_types": {
                "goal": "小班/中班/大班在各目标下的发展水平条目",
                "suggestion": "对应目标的教育建议；举例放在 examples 字段",
            },
        },
        "items": items,
    }


def write_inline(data: dict) -> None:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c")
    (DATA / "preschool-inline.js").write_text(
        "window.PRESCHOOL_DATA = " + payload + ";\n", encoding="utf-8"
    )


def write_csv(data: dict) -> None:
    fields = [
        "uid", "stage", "age", "domain", "aspect", "goal_no", "goal", "type",
        "text", "examples", "reference", "source_page", "source_id",
    ]
    with (DATA / "preschool.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in data["items"]:
            row = {k: "" for k in fields}
            row.update(item)
            row["examples"] = "\n".join(item.get("examples", []))
            row["reference"] = "\n".join(item.get("reference", []))
            writer.writerow(row)


def write_xlsx(data: dict) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    fields = [
        "uid", "stage", "age", "domain", "aspect", "goal_no", "goal", "type",
        "text", "examples", "reference", "source_page", "source_id",
    ]
    wb = Workbook()
    ws = wb.active
    ws.title = "preschool"
    ws.append(fields)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for item in data["items"]:
        row = {k: "" for k in fields}
        row.update(item)
        row["examples"] = "\n".join(item.get("examples", []))
        row["reference"] = "\n".join(item.get("reference", []))
        ws.append([row[k] for k in fields])
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    widths = [22, 8, 9, 9, 16, 9, 28, 12, 60, 60, 30, 11, 20]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = width
    ws.freeze_panes = "A2"
    wb.save(DATA / "preschool.xlsx")


def write_preview(data: dict) -> None:
    meta = data["meta"]
    lines = [
        f"# {meta['title']} · 幼儿园阶段数据预览",
        "",
        f"来源：{meta['source']['issuer']}，{meta['source']['document_no']}，{meta['source']['published']}。",
        f"官方页面：{meta['source']['url']}",
        "",
        "> 这是数据层预览，不是应用界面。非官方整理，若有出入以原文为准。",
        "",
    ]
    grouped: OrderedDict = OrderedDict()
    for item in data["items"]:
        grouped.setdefault((item["domain"], item["aspect"], item["goal_no"], item["goal"]), []).append(item)
    for (domain, aspect, no, goal), group in grouped.items():
        lines += [f"## {domain} / {aspect} / 目标{no} {goal}", ""]
        for level in LEVELS:
            texts = [x for x in group if x["type"] == "goal" and x["stage"] == level]
            if not texts:
                continue
            lines.append(f"**{level}（{LEVELS[level]}）**")
            for item in texts:
                lines.append(f"- {item['text']}")
                if item.get("reference"):
                    lines.append("  - 参考标准：" + "；".join(item["reference"]))
            lines.append("")
        suggestions = [x for x in group if x["type"] == "suggestion"]
        if suggestions:
            lines.append("**教育建议**")
            for item in suggestions:
                lines.append(f"- {item['text']}")
                for example in item.get("examples", []):
                    lines.append(f"  - {example}")
            lines.append("")
    (DATA / "preschool-preview.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    data = build()
    (DATA / "preschool.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_inline(data)
    write_csv(data)
    write_xlsx(data)
    write_preview(data)
    count = Counter(x["type"] for x in data["items"])
    stages = Counter(x.get("stage") for x in data["items"] if x["type"] == "goal")
    print(f"items={len(data['items'])} goals={count['goal']} suggestions={count['suggestion']}")
    print("goal items by stage:", dict(stages))
    print("domains:", dict(Counter(x["domain"] for x in data["items"] if x["type"] == "goal")))
    print("missing source_page:", sum(not x.get("source_page") for x in data["items"]))


if __name__ == "__main__":
    main()
