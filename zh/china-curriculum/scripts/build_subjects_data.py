#!/usr/bin/env python3
"""Build canonical data for the 2022 Chinese, Math and English standards.

Input is the locally OCR'd, gitignored MOE PDF text in source/extracted/ocr/.
Output is the public data layer only. No application/UI code is touched.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OCR = ROOT / "source" / "extracted" / "ocr"
DATA = ROOT / "data"

NOTICE_URL = "https://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"

SOURCES = {
    "chinese": {
        "id": "moe-cn-2022-chinese",
        "title": "义务教育语文课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/03-义务教育语文课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "math": {
        "id": "moe-cn-2022-math",
        "title": "义务教育数学课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/05-义务教育数学课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "english": {
        "id": "moe-cn-2022-english",
        "title": "义务教育英语课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/06-义务教育英语课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
}

SUBJECTS = OrderedDict([("chinese", "语文"), ("math", "数学"), ("english", "英语")])
STAGES = OrderedDict([
    ("x1", "小学低段（1-2年级）"),
    ("x2", "小学中段（3-4年级）"),
    ("x3", "小学高段（5-6年级）"),
    ("j1", "初中（7-9年级）"),
    ("all", "全学段"),
])
CN_STAGE_NUM = {"一": "x1", "二": "x2", "三": "x3", "四": "j1"}

TYPE_NAMES = {
    "stage_requirement": "学段要求",
    "content": "学习内容 / 内容要求",
    "academic": "学业要求",
    "tip": "教学提示",
    "theme": "主题与载体",
    "note": "阶段说明",
}

# OCR confusions seen in the scanned standards. Only unambiguous visual errors
# are corrected here; substantive wording is left as scanned.
TABLE_CELL_LABELS = {
    "范畴", "主题群", "子主题内容", "级别", "内容要求", "学习策略", "策略",
    "元认知", "认知", "交际", "情感管理", "听做", "说唱", "玩演", "视听", "续表",
    "生活与学习", "做人与做事", "社会服务与人际", "沟通", "文学、艺术与体育",
    "历史、社会与文化", "科学与技术", "自然生态", "环境保护", "灾害防范", "宇宙探索",
}

CORRECTIONS = {
    "自已": "自己",
    "票敬": "崇敬",
    "临拿": "临摹",
    "避选": "遴选",
    "自标": "目标",
    "莲续性": "连续性",
    "第四学段（79年级）": "第四学段（7～9年级）",
    "学会注明所援引资料的": "学会注明所援引资料的出处。",
    "符号<，三，>": "符号<，=，>",
    "总量=分量十分量": "总量=分量+分量",
    "体验19从数量到数的抽象过程": "体验1～9从数量到数的抽象过程",
}


def load_ocr(key: str) -> list[tuple[int, list[str]]]:
    path = OCR / f"{key}.txt"
    if not path.exists():
        raise SystemExit(f"missing OCR text: {path}; run scripts/ocr_pdfs.py first")
    pages: list[tuple[int, list[str]]] = []
    page_no = 0
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"<!-- PDF_PAGE (\d+) -->", raw)
        if m:
            if page_no:
                pages.append((page_no, [x for x in lines if x.strip()]))
            page_no = int(m.group(1))
            lines = []
            continue
        if page_no:
            lines.append(raw.strip())
    if page_no:
        pages.append((page_no, [x for x in lines if x.strip()]))
    return pages


def clean_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        for wrong, right in CORRECTIONS.items():
            line = line.replace(wrong, right)
        # Running headers and bare printed page numbers. OCR sometimes merges a
        # running header into a text line, so strip both whole-line and inline.
        line = re.sub(r"[IVX]?\s*义务教育(?:语文|数学|英语)课程标准（2022年版）", "", line)
        line = re.sub(
            r"[一二三四五六]、\s*(?:课程性质|课程理念|课程目标|课程内容|学业质量|课程实施)I?",
            "",
            line,
        )
        line = line.strip()
        if not line:
            continue
        if re.fullmatch(r"\d{1,3}", line):
            continue
        if line in TABLE_CELL_LABELS:
            continue
        if re.fullmatch(r"[—–\-\s]*PAGE\s*\d+[—–\-\s]*", line):
            continue
        out.append(line)
    return out


def tidy(parts: list[str]) -> str:
    text = "".join(x.strip() for x in parts if x.strip())
    text = re.sub(r"\s+([，。！？；：、）】])", r"\1", text)
    text = re.sub(r"\s{2,}", "", text)
    return text.strip()


def split_numbered(lines: list[str], style: str = "cn") -> list[str]:
    """Split numbered or bracketed items, joining wrapped continuation lines."""
    pat = re.compile(r"^（(\d+)）" if style == "cn" else r"^(\d+)[．.、]\s*")
    starts = [i for i, x in enumerate(lines) if pat.match(x)]
    if not starts:
        text = tidy(lines)
        return [text] if text else []
    items: list[str] = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        seg = [pat.sub("", lines[start], count=1)] + lines[start + 1 : end]
        text = tidy(seg)
        if text:
            items.append(text)
    return items


def make_item(
    counter: int,
    subject: str,
    source_id: str,
    stage: str,
    domain: str,
    topic: str,
    item_type: str,
    text: str,
    source_page: int | None,
    pdf_page: int | None,
) -> dict:
    digest = hashlib.sha1(
        f"{subject}|{stage}|{domain}|{topic}|{item_type}|{text}".encode("utf-8")
    ).hexdigest()[:8]
    return {
        "uid": f"{subject[:2]}-{stage}-{item_type[:3]}-{digest}",
        "seq": counter,
        "subject": SUBJECTS[subject],
        "subject_key": subject,
        "stage": STAGES.get(stage, stage),
        "stage_key": stage,
        "domain": domain,
        "topic": topic,
        "type": item_type,
        "text": text,
        "source_page": source_page,
        "source_pdf_page": pdf_page,
        "source_id": source_id,
    }


def parse_chinese() -> list[dict]:
    """Parse stage requirements and learning-task-group content."""
    source = SOURCES["chinese"]
    pages = load_ocr("chinese")
    items: list[dict] = []
    counter = 0

    stage_re = re.compile(r"^第([一二三四])学段[（(]([0-9～~\-]+)年级[）)]")
    bracket_re = re.compile(r"^【(.+?)】$")
    num_re = re.compile(r"^(\d+)[．.、]\s*")
    cn_num_re = re.compile(r"^（(\d+)）")
    task_groups = {
        "语言文字积累与梳理",
        "实用性阅读与交流",
        "文学阅读与创意表达",
        "思辨性阅读与表达",
        "整本书阅读",
        "跨学科学习",
    }

    def page_of(pdf_page: int) -> int:
        return pdf_page - source["pdf_offset"]

    def add(
        stage: str,
        domain: str,
        topic: str,
        item_type: str,
        text: str,
        pdf_page: int,
    ) -> None:
        nonlocal counter
        if not text:
            return
        counter += 1
        items.append(
            make_item(
                counter, "chinese", source["id"], stage, domain, topic,
                item_type, text, page_of(pdf_page), pdf_page,
            )
        )

    # 1. 学段要求 (PDF pages 14-24)
    stage = None
    category = None
    buffer: list[str] = []
    buf_page = 0

    def flush_stage() -> None:
        nonlocal buffer
        if buffer and stage and category:
            add(stage, category, "学段要求", "stage_requirement", tidy(buffer), buf_page)
        buffer = []

    for pdf_page, raw_lines in pages:
        if pdf_page < 14 or pdf_page > 24:
            continue
        lines = clean_lines(raw_lines)
        for line in lines:
            m = stage_re.match(line)
            if m:
                flush_stage()
                stage = CN_STAGE_NUM[m.group(1)]
                category = None
                continue
            if line.startswith("在落实以上要求过程中"):
                flush_stage()
                add(stage or "", "阶段说明", "学段要求", "note", line, pdf_page)
                continue
            m = bracket_re.match(line)
            if m:
                flush_stage()
                category = m.group(1)
                continue
            if num_re.match(line) or stage_re.match(line):
                flush_stage()
                buffer = [num_re.sub("", line, count=1)]
                buf_page = pdf_page
                continue
            if buffer:
                buffer.append(line)
    flush_stage()

    # 2. 主题与载体形式
    theme_re = re.compile(r"^(\d+)[．.、]\s*(中华优秀传统文化|革命文化|社会主义先进文化)$")
    theme = None
    theme_buf: list[str] = []
    theme_page = 0

    def flush_theme() -> None:
        nonlocal theme_buf
        if theme and theme_buf:
            add("all", "主题与载体形式", theme, "theme", tidy(theme_buf), theme_page)
        theme_buf = []

    for pdf_page, raw_lines in pages:
        if pdf_page < 25 or pdf_page > 26:
            continue
        for line in clean_lines(raw_lines):
            m = theme_re.match(line)
            if m:
                flush_theme()
                theme = m.group(2)
                theme_page = pdf_page
                continue
            if line.startswith("（二）内容组织与呈现方式"):
                flush_theme()
                theme = None
                continue
            if theme:
                theme_buf.append(line)
    flush_theme()

    # 3. 课程内容：学习任务群的学习内容与教学提示
    domain = None
    topic = None
    current_stage = None
    buffer = []
    buf_page = 0
    pending_group = False

    def flush_content() -> None:
        nonlocal buffer
        if buffer and domain:
            stage_key = current_stage if topic == "学习内容" else "all"
            item_type = "content" if topic == "学习内容" else "tip"
            add(stage_key, domain, topic or "学习内容", item_type, tidy(buffer), buf_page)
        buffer = []

    for pdf_page, raw_lines in pages:
        if pdf_page < 25 or pdf_page > 43:
            continue
        lines = clean_lines(raw_lines)
        for line in lines:
            if line in task_groups:
                flush_content()
                domain = line
                topic = None
                pending_group = False
                continue
            if num_re.match(line) and domain and not topic:
                # e.g. "1.基础型学习任务群" followed by the actual group name.
                pending_group = True
                continue
            if domain and not topic and line.startswith("本学习任务群旨在"):
                add("all", domain, "任务群说明", "note", line, pdf_page)
                continue
            m = bracket_re.match(line)
            if m:
                flush_content()
                topic = m.group(1)
                current_stage = None
                continue
            m = stage_re.match(line)
            if m:
                flush_content()
                current_stage = CN_STAGE_NUM[m.group(1)]
                continue
            if cn_num_re.match(line):
                flush_content()
                buffer = [cn_num_re.sub("", line, count=1)]
                buf_page = pdf_page
                continue
            if buffer:
                buffer.append(line)
    flush_content()
    return items


def parse_math() -> list[dict]:
    """Parse the four domains' content, academic and teaching requirements."""
    source = SOURCES["math"]
    pages = load_ocr("math")
    items: list[dict] = []
    counter = 0

    stage_re = re.compile(r"^第([一二三四])学段[（(]([0-9～~\-]+)年级[）)]")
    bracket_re = re.compile(r"^【(内容要求|学业要求|教学提示)】$")
    sub_re = re.compile(r"^(\d+)[．.、]\s*(.+)$")
    item_re = re.compile(r"^（(\d+)）")
    domain_re = re.compile(r"^（[一二三四]）(.+)$")
    domains = {"数与代数", "图形与几何", "统计与概率", "综合与实践"}
    topic_types = {"内容要求": "content", "学业要求": "academic", "教学提示": "tip"}

    def add(
        stage: str,
        domain: str,
        topic: str,
        item_type: str,
        text: str,
        pdf_page: int,
    ) -> None:
        nonlocal counter
        if not text:
            return
        counter += 1
        items.append(
            make_item(
                counter, "math", source["id"], stage, domain, topic,
                item_type, text, pdf_page - source["pdf_offset"], pdf_page,
            )
        )

    part = None
    domain = None
    stage = None
    topic_type = None
    subtopic = ""
    buffer: list[str] = []
    buf_page = 0

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        text = tidy(buffer)
        if text and stage and domain and topic_type:
            item_type = topic_types[topic_type]
            topic = "教学提示" if item_type == "tip" else (subtopic or topic_type)
            add(stage, domain, topic, item_type, text, buf_page)
        buffer = []

    for pdf_page, raw_lines in pages:
        if pdf_page < 24 or pdf_page > 86:
            continue
        lines = clean_lines(raw_lines)
        for line in lines:
            if line in ("小学部分", "初中部分"):
                flush()
                part = line
                domain = None
                stage = None
                topic_type = None
                subtopic = ""
                continue
            m = domain_re.match(line)
            if m and m.group(1) in domains:
                flush()
                domain = m.group(1)
                stage = None
                topic_type = None
                subtopic = ""
                continue
            m = stage_re.match(line)
            if m:
                flush()
                stage = CN_STAGE_NUM[m.group(1)]
                topic_type = None
                subtopic = ""
                continue
            m = bracket_re.match(line)
            if m:
                flush()
                topic_type = m.group(1)
                subtopic = ""
                continue
            m = sub_re.match(line)
            if m and topic_type:
                flush()
                # In 教学提示 the numbered lines are prose, not subtopics.
                if topic_type != "教学提示":
                    subtopic = m.group(2).strip()
                    buf_page = pdf_page
                    continue
                buffer.append(line)
                continue
            m = item_re.match(line)
            if m and topic_type == "内容要求":
                flush()
                buffer = [item_re.sub("", line, count=1)]
                buf_page = pdf_page
                continue
            if buffer:
                buffer.append(line)
            elif topic_type and stage and domain:
                buffer = [line]
                buf_page = pdf_page
        # Paragraphs can end at a page boundary; keep the buffer across pages.
    flush()
    return items


def parse_english() -> list[dict]:
    """Parse table-based content requirements and teaching tips."""
    source = SOURCES["english"]
    pages = load_ocr("english")
    items: list[dict] = []
    counter = 0

    element_re = re.compile(r"^\d+[．.、]\s*(主题|语篇|语言知识|文化知识|语言技能|学习策略)$")
    subelement_re = re.compile(r"^（\d+）(语音知识|词汇知识|语法知识|语篇知识|语用知识)$")
    tip_heading_re = re.compile(r"^\d+[．.、]\s*(预备级|一级|二级|三级).*年级")
    item_re = re.compile(r"^(\+?)(\d+)[．.、]\s*")
    paragraph_re = re.compile(r"^第[一二三四五六]，")

    def level_from(text: str) -> str | None:
        # 英语标准称 1-2 年级为“预备级”，统一并入小学低段。
        if "预备级" in text:
            return "x1"
        if "一级" in text:
            return "x2"
        if "二级" in text:
            return "x3"
        if "三级" in text:
            return "j1"
        return None

    def add(
        stage: str,
        domain: str,
        topic: str,
        item_type: str,
        text: str,
        pdf_page: int,
    ) -> None:
        nonlocal counter
        if not text:
            return
        counter += 1
        items.append(
            make_item(
                counter, "english", source["id"], stage, domain, topic,
                item_type, text, pdf_page - source["pdf_offset"], pdf_page,
            )
        )

    in_tips = False
    element = None
    subelement = None
    table_title = None
    table_level = None
    pending_table_num = False
    current_level = None
    buffer: list[str] = []
    buf_page = 0
    pending: list[dict] = []
    resolved: list[dict] = []

    def resolve_pending(default: str | None) -> None:
        for rec in pending:
            rec["stage"] = rec["stage"] or rec["table_level"] or default or "all"
            resolved.append(rec)
        pending.clear()

    def flush_item() -> None:
        nonlocal buffer
        if buffer:
            text = tidy(buffer)
            if text:
                pending.append({
                    "stage": current_level,
                    "table_level": table_level,
                    "domain": element or "课程内容",
                    "topic": subelement or table_title or "内容要求",
                    "type": "content",
                    "text": text,
                    "page": buf_page,
                })
        buffer = []

    def assign_level(level: str) -> None:
        nonlocal current_level
        resolve_pending(level)
        current_level = level

    tip_stage = None
    tip_buffer: list[str] = []
    tip_page = 0
    table21 = False

    def flush_tip() -> None:
        nonlocal tip_buffer
        if tip_buffer:
            add(tip_stage or "all", "教学提示", STAGES.get(tip_stage or "all", "教学提示"), "tip", tidy(tip_buffer), tip_page)
        tip_buffer = []

    for pdf_page, raw_lines in pages:
        if pdf_page < 20 or pdf_page > 48:
            continue
        lines = clean_lines(raw_lines)
        for line in lines:
            if line.startswith("（二）教学提示"):
                flush_item()
                resolve_pending(table_level or current_level)
                in_tips = True
                element = subelement = table_title = current_level = None
                pending_table_num = False
                continue

            if not in_tips:
                m = element_re.match(line)
                if m:
                    flush_item()
                    resolve_pending(table_level or current_level)
                    element = m.group(1)
                    subelement = None
                    table_title = None
                    current_level = None
                    pending_table_num = False
                    continue
                m = subelement_re.match(line)
                if m:
                    flush_item()
                    subelement = m.group(1)
                    continue
                if re.match(r"^表\d+", line):
                    flush_item()
                    resolve_pending(table_level or current_level)
                    rest = re.sub(r"^表\d+\s*", "", line).strip()
                    if rest and re.search(r"内容要求|学习活动", rest):
                        table_title = rest
                        table_level = level_from(rest)
                        current_level = None
                        pending_table_num = False
                    else:
                        pending_table_num = True
                    continue
                if pending_table_num and re.search(r"内容要求|学习活动", line):
                    table_title = line.strip()
                    table_level = level_from(table_title)
                    current_level = None
                    pending_table_num = False
                    continue
                if len(line) <= 16 and level_from(line):
                    flush_item()
                    assign_level(level_from(line))
                    continue
                m = item_re.match(line)
                if m:
                    flush_item()
                    buffer = [item_re.sub("", line, count=1)]
                    buf_page = pdf_page
                    continue
                if buffer:
                    buffer.append(line)
                continue

            # Teaching tips: grouped by level, with each 第一/第二... paragraph
            # kept as a separate item.
            if line.startswith("表21"):
                flush_tip()
                table21 = True
                continue
            m = tip_heading_re.match(line)
            if m:
                flush_tip()
                tip_stage = level_from(m.group(1))
                current_level = tip_stage
                table21 = False
                continue
            if table21 and item_re.match(line):
                flush_item()
                element = "小学低段学习活动"
                subelement = "学习要求"
                current_level = "x1"
                buffer = [item_re.sub("", line, count=1)]
                buf_page = pdf_page
                continue
            if paragraph_re.match(line):
                flush_tip()
                tip_buffer = [line]
                tip_page = pdf_page
                continue
            if tip_buffer:
                tip_buffer.append(line)

    flush_item()
    flush_tip()
    resolve_pending(table_level or current_level)
    for rec in resolved:
        add(rec["stage"], rec["domain"], rec["topic"], rec["type"], rec["text"], rec["page"])
    return items


def build() -> dict:
    all_items: list[dict] = []
    all_items.extend(parse_chinese())
    all_items.extend(parse_math())
    all_items.extend(parse_english())
    return {
        "meta": {
            "title": "中国小学初中课程标准知识点（语文 / 数学 / 英语）",
            "scope": "义务教育阶段 1-9 年级，2022 年版课程标准",
            "sources": [SOURCES[k] for k in SUBJECTS],
            "notice": "非官方整理；条目从行政指导文件抽取并结构化，若与原文有出入，以教育部发布的原文为准。官方 PDF 不复制到本站。",
            "type_names": TYPE_NAMES,
            "item_types": {
                "stage_requirement": "各学段应达到的学习要求",
                "content": "学习内容或内容要求",
                "academic": "学业要求",
                "tip": "教学提示",
                "theme": "主题与载体",
                "note": "阶段说明",
            },
        },
        "items": all_items,
    }


def write_inline(data: dict) -> None:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c")
    (DATA / "primary-secondary-inline.js").write_text(
        "window.PRIMARY_SECONDARY_DATA = " + payload + ";\n", encoding="utf-8"
    )


def write_csv(data: dict) -> None:
    fields = [
        "uid", "seq", "subject", "subject_key", "stage", "stage_key",
        "domain", "topic", "type", "text", "source_page", "source_pdf_page", "source_id",
    ]
    with (DATA / "primary-secondary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in data["items"]:
            writer.writerow({k: item.get(k, "") for k in fields})


def write_xlsx(data: dict) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    fields = [
        "uid", "seq", "subject", "subject_key", "stage", "stage_key",
        "domain", "topic", "type", "text", "source_page", "source_pdf_page", "source_id",
    ]
    wb = Workbook()
    ws = wb.active
    ws.title = "primary-secondary"
    ws.append(fields)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for item in data["items"]:
        ws.append([item.get(k, "") for k in fields])
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    widths = [26, 7, 8, 10, 20, 10, 22, 18, 16, 80, 11, 13, 22]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = width
    ws.freeze_panes = "A2"
    wb.save(DATA / "primary-secondary.xlsx")


def write_preview(data: dict) -> None:
    lines = [
        f"# {data['meta']['title']} · 数据预览",
        "",
        "> 这是数据层预览，不是应用界面。非官方整理，若有出入以原文为准。",
        "",
    ]
    grouped: OrderedDict = OrderedDict()
    for item in data["items"]:
        key = (item["subject"], item["stage"], item["domain"], item["topic"], item["type"])
        grouped.setdefault(key, []).append(item)
    for (subject, stage, domain, topic, item_type), group in grouped.items():
        lines += [f"## {subject} / {stage} / {domain} / {topic} · {TYPE_NAMES.get(item_type, item_type)}", ""]
        for item in group:
            page = item.get("source_page")
            suffix = f"（印刷版第 {page} 页）" if page else ""
            lines.append(f"- {item['text']}{suffix}")
        lines.append("")
    (DATA / "primary-secondary-preview.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    data = build()
    (DATA / "primary-secondary.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for key, label in SUBJECTS.items():
        subset = {
            "meta": {**data["meta"], "title": f"{label}课程标准知识点（2022年版）", "sources": [SOURCES[key]]},
            "items": [x for x in data["items"] if x["subject_key"] == key],
        }
        (DATA / f"{key}.json").write_text(
            json.dumps(subset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    write_inline(data)
    write_csv(data)
    write_xlsx(data)
    write_preview(data)
    print("items", len(data["items"]))
    print("by subject", dict(Counter(x["subject"] for x in data["items"])))
    print("by type", dict(Counter(x["type"] for x in data["items"])))


if __name__ == "__main__":
    main()
