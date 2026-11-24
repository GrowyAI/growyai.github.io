"""Targeted data-quality repairs for the K-8 portion of knowledge.json.

Scope is limited to grade != "Preschool".  The repairs are reproducible:
  1. remove PDF page-footer noise that was appended to item text;
  2. normalize the stray PDF bullet glyph "Ź" to "•";
  3. restore Chinese translations that were overwritten because the original
     translation files were keyed by non-unique per-section ids;
  4. split a few objective lines that the PDF exporter merged.

Run from anywhere:
    python scripts/repair_k8_data.py
"""

import copy
import glob
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "knowledge.json")
FIX_DIR = os.path.join(BASE, "scripts", "k8_zh_fixes")
EXPORT = os.path.join(BASE, "scripts", "export_tables.py")

EN_FOOTER = re.compile(
    r"\s*\b\d{1,3}\s+Core Knowledge Sequence\s*\|\s*"
    r"(?:Kindergarten|Grade\s*[1-8]|[K1-8])\b"
)
EN_FOOTER_BARE = re.compile(
    r"\s*Core Knowledge Sequence\s*\|\s*"
    r"(?:Kindergarten|Grade\s*[1-8]|[K1-8])\b"
)
ZH_PAREN_FOOTER = re.compile(r"（[^）]*核心知识序列[^）]*）")
ZH_ORIGINAL_FOOTER = re.compile(r"（原文附：[^）]*）")
ZH_FOOTER = re.compile(
    r"\s*\d*\s*《?核心知识序列》?\s*[|｜]?\s*"
    r"(?:幼儿园|[一二三四五六七八]年级|Grade\s*[1-8])\s*"
    r"(?:第\s*\d+\s*页)?"
)
ZH_PAGE_FOOTER = re.compile(r"《核心知识序列》第\s*\d+\s*页\s*[|｜]?\s*(?:幼儿园|[一二三四五六七八]年级)?")
ZH_EN_FOOTER = re.compile(
    r"\s*\b\d{1,3}\s+Core Knowledge Sequence\s*\|\s*"
    r"(?:Kindergarten|Grade\s*[1-8]|[K1-8]|幼儿园|[一二三四五六七八]年级)"
)


def squash(text):
    return re.sub(r"\s+", " ", text or "").strip()


def clean_en(text):
    had_footer = bool(EN_FOOTER.search(text or "") or EN_FOOTER_BARE.search(text or ""))
    text = EN_FOOTER.sub("", text or "")
    text = EN_FOOTER_BARE.sub("", text)
    text = text.replace("Ź", "•")
    text = squash(text)
    if had_footer:
        text = re.sub(r"\s+\d{1,3}$", "", text)
    return text


def clean_zh(text):
    had_footer = bool(
        ZH_PAREN_FOOTER.search(text or "")
        or ZH_ORIGINAL_FOOTER.search(text or "")
        or ZH_FOOTER.search(text or "")
        or ZH_PAGE_FOOTER.search(text or "")
        or ZH_EN_FOOTER.search(text or "")
    )
    text = ZH_ORIGINAL_FOOTER.sub("", text or "")
    text = ZH_PAREN_FOOTER.sub("", text)
    text = ZH_PAGE_FOOTER.sub("", text)
    text = ZH_FOOTER.sub("", text)
    text = ZH_EN_FOOTER.sub("", text)
    text = text.replace("Ź", "•")
    text = squash(text)
    if had_footer:
        text = re.sub(r"[；;，,]\s*$", "", text)
        text = re.sub(r"\s+\d{1,3}$", "", text)
    return text


def load_zh_fixes():
    fixes = {}
    for path in sorted(glob.glob(os.path.join(FIX_DIR, "batch-*.json"))):
        with open(path, encoding="utf-8") as f:
            fixes.update(json.load(f))
    return fixes


def make_split_item(source, uid, item_id, en, zh, typ="objective"):
    new_item = copy.deepcopy(source)
    new_item.update({
        "uid": uid,
        "id": item_id,
        "type": typ,
        "en": clean_en(en),
        "zh": clean_zh(zh),
    })
    return new_item


def main():
    with open(SOURCE, encoding="utf-8") as f:
        data = json.load(f)

    zh_fixes = load_zh_fixes()
    stats = {"footer_en": 0, "footer_zh": 0, "bullet": 0, "zh_fixed": 0}
    new_items = []
    existing_uids = {item["uid"] for item in data["items"]}
    splits = [
        ("n01065", "n07225", "k8-1-mathematics-0022b",
         "Using objects and drawings.", "使用实物和画图。", "objective"),
        ("n01087", "n07226", "k8-1-mathematics-0044b",
         "Example questions: how many in each category, or how many more or less are in one category than in another.",
         "示例问题：每一类有多少，或某一类比另一类多多少、少多少。", "question"),
        ("n04332", "n07227", "k8-6-mathematics-0049b",
         "Pack the right rectangular prism with unit cubes of the appropriate unit fraction edge lengths.",
         "用棱长为适当单位分数的小立方体填充直长方体。", "objective"),
    ]

    for item in data["items"]:
        if item.get("grade") == "Preschool":
            continue

        original_en, original_zh = item.get("en", ""), item.get("zh", "")
        item["en"] = clean_en(original_en)
        item["zh"] = clean_zh(original_zh)
        if item["en"] != original_en:
            stats["footer_en"] += 1
        if item["zh"] != original_zh:
            stats["footer_zh"] += 1
        if "Ź" in original_en or "Ź" in original_zh:
            stats["bullet"] += 1

        if item["uid"] in zh_fixes:
            item["zh"] = squash(zh_fixes[item["uid"]])
            stats["zh_fixed"] += 1

        uid = item["uid"]
        for source_uid, new_uid, item_id, en, zh, typ in splits:
            if uid != source_uid or new_uid in existing_uids:
                continue
            if uid == "n01065":
                item["en"] = "Compare two two-digit numbers based on meanings of the tens and ones digits."
                item["zh"] = "根据十位和个位的含义比较两个两位数。"
            elif uid == "n01087":
                item["en"] = "Partition circles and rectangles into two and four equal shares."
                item["zh"] = "把圆形和长方形分成二等份和四等份。"
            elif uid == "n04332":
                item["en"] = "Summarize numerical data sets in relation to their context, such as by:"
                item["zh"] = "结合背景概括数值数据集，例如："
            new_items.append(make_split_item(item, new_uid, item_id, en, zh, typ))
            existing_uids.add(new_uid)

    # Keep new split items adjacent to their source item.
    if new_items:
        source_by_new_uid = {new_uid: source_uid for source_uid, new_uid, *_ in splits}
        ordered = []
        for item in data["items"]:
            ordered.append(item)
            for new_item in new_items:
                if source_by_new_uid.get(new_item["uid"]) == item["uid"]:
                    ordered.append(new_item)
        data["items"] = ordered

    data["meta"]["item_count"] = len(data["items"])

    with open(SOURCE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    subprocess.check_call([sys.executable, EXPORT])
    print("K-8 repairs:", stats)
    print("new split items:", len(new_items))
    print("total items:", len(data["items"]))


if __name__ == "__main__":
    main()
