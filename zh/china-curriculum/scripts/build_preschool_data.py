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


# --- Concrete-content filter -------------------------------------------------
# Development goals are already observable milestones and are kept as-is.
# Education suggestions are displayed only when the suggestion itself or one
# of its examples gives something concrete to do; generic guidance is archived.

PRESCHOOL_FILTER_VERSION = "concrete-v1"
P_NUM = re.compile(r"\d|每天|每周|每年|经常|适时|定期|至少|不超过|左右|勤|早晚|饭后")
P_ACTION = re.compile(
    r"保证|睡|检查|体检|玩|提供|引导|指导|帮助|鼓励|提醒|组织|开展|进行|观察|"
    r"记录|讲述|朗读|阅读|书写|画|制作|尝试|练习|探索|感知|体验|比较|数|搭配|"
    r"分类|整理|收拾|清洗|扫地|洗手|刷牙|漱口|洗澡|换衣服|剪指甲|饮水|进食|"
    r"运动|游戏|表达|交流|倾听|观看|吃饭|进餐|连成|使用|交谈|参观|提问|布置"
)
P_OBJECT = re.compile(
    r"睡眠|午睡|小时|分钟|饮食|食物|蔬菜|水果|谷物|奶|蛋|水|身体|体态|姿势|"
    r"健康检查|体检|游戏|活动|玩具|图书|故事|儿歌|音乐|绘画|手工|情绪|安全|"
    r"规则|同伴|家人|父母|老师|自己|物品|书包|房间|玩具|自然|动植物|数字|多少|"
    r"文字|文字符号|话语|语言|句子|事情|安全教育|餐点|进餐|吃饭|图形|轮廓|"
    r"比赛|电视节目|指甲|衣服|阅读环境|图书|小学|任务"
)
P_META = re.compile(r"营造|注重|重视|关注|培养|促进|增强|形成安全感和信赖感|心理环境")


# Audited corrections where the extracted table lost leading unnumbered rows.
# Key: (domain, aspect, goal_no) -> (cell index, replacement cell).
GOAL_CELL_OVERRIDES: dict[tuple[str, str, int], tuple[int, str]] = {
    ("科学", "数学认知", 1): (
        1,
        "1．在指导下，感知和体会有些事物可以用形状来描述。\n"
        "2．在指导下，感知和体会有些事物可以用数来描述，对环境中各种数字的含义有进一步探究的兴趣。",
    ),
}

# Full education-suggestion lists for goals whose first numbered marker was
# lost in extraction. Entries are (head, examples).
SUGGESTION_OVERRIDES: dict[tuple[str, str, int], list[tuple[str, list[str]]]] = {
    ("健康", "生活习惯与生活能力", 1): [
        ("让幼儿保持有规律的生活，养成良好的作息习惯。如：早睡早起、每天午睡、按时进餐、吃好早餐等。", []),
        ("帮助幼儿养成良好的饮食习惯。如：", [
            "合理安排餐点，帮助幼儿养成定点、定时、定量进餐的习惯。",
            "帮助幼儿了解食物的营养价值，引导他们不偏食不挑食、少吃或不吃不利于健康的食品；多喝白开水，少喝饮料。",
            "吃饭时不过分催促，提醒幼儿细嚼慢咽，不要边吃边玩。",
        ]),
        ("帮助幼儿养成良好的个人卫生习惯。如：", [
            "早晚刷牙、饭后漱口。",
            "勤为幼儿洗澡、换衣服、剪指甲。",
            "提醒幼儿保护五官，如不乱挖耳朵、鼻孔，看电视时保持3米左右的距离等。",
        ]),
        ("激发幼儿参加体育活动的兴趣，养成锻炼的习惯。如：", [
            "为幼儿准备多种体育活动材料，鼓励他选择自己喜欢的材料开展活动。",
            "经常和幼儿一起在户外运动和游戏，鼓励幼儿和同伴一起开展体育活动。",
            "和幼儿一起观看体育比赛或有关体育赛事的电视节目，培养他对体育活动的兴趣。",
        ]),
    ],
    ("语言", "倾听与表达", 1): [
        ("多给幼儿提供倾听和交谈的机会。如：经常和幼儿一起谈论他感兴趣的话题，或一起看图书、讲故事。", []),
        ("引导幼儿学会认真倾听。如：", [
            "成人要耐心倾听别人（包括幼儿）的讲话，等别人讲完再表达自己的观点。",
            "与幼儿交谈时，要用幼儿能听得懂的语言。",
            "对幼儿提要求和布置任务时要求他注意听，鼓励他主动提问。",
        ]),
        ("对幼儿讲话时，注意结合情境使用丰富的语言，以便于幼儿理解。如：", [
            "说话时注意语气、语调，让幼儿感受语气、语调的作用。如对幼儿的不合理要求以比较坚定的语气表示不同意；讲故事时，尽量把故事人物高兴、悲伤的心情用不同的语气、语调表现出来。",
            "根据幼儿的理解水平有意识地使用一些反映因果、假设、条件等关系的句子。",
        ]),
    ],
    ("语言", "阅读与书写准备", 3): [
        ("让幼儿在写写画画的过程中体验文字符号的功能，培养书写兴趣。如：", [
            "准备供幼儿随时取放的纸、笔等材料，也可利用沙地、树枝等自然材料，满足幼儿自由涂画的需要。",
            "鼓励幼儿将自己感兴趣的事情或故事画下来并讲给别人听，让幼儿体会写写画画的方式可以表达自己的想法和情感。",
            "把幼儿讲过的事情用文字记录下来，并念给他听，使幼儿知道说的话可以用文字记录下来，从中体会文字的用途。",
        ]),
        ("在绘画和游戏中做必要的书写准备，如：", [
            "通过把虚线画出的图形轮廓连成实线等游戏，促进手眼协调，同时帮助幼儿学习由上至下、由左至右的运笔技能。",
            "鼓励幼儿学习书写自己的名字。",
            "提醒幼儿写画时保持正确姿势。",
        ]),
    ],
    ("社会", "人际交往", 4): [
        ("成人以身作则，以尊重、关心的态度对待自己的父母、长辈和其他人。如：", [
            "经常问候父母，主动做家务。",
            "礼貌地对待老年人，如坐车时主动为老人让座。",
            "看到别人有困难能主动关心并给予一定的帮助。",
        ]),
        ("引导幼儿尊重、关心长辈和身边的人，尊重他人劳动及成果。如：", [
            "提醒幼儿关心身边的人，如妈妈累了，知道让她安静休息一会儿。",
            "借助故事、图书等给幼儿讲讲父母抚育孩子成长的经历，让幼儿理解和体会父爱与母爱。",
            "结合实际情境，提醒幼儿注意别人的情绪，了解他们的需要，给予适当的关心和帮助。",
            "利用生活机会和角色游戏，帮助幼儿了解与自己关系密切的社会服务机构及其工作，如商场、邮局、医院等，体会这些机构给大家提供的便利和服务，懂得尊重工作人员的劳动，珍惜劳动成果。",
        ]),
        ("引导幼儿学习用平等、接纳和尊重的态度对待差异。如：", [
            "了解每个人都有自己的兴趣、爱好和特长，可以相互学习。",
            "利用民间游戏、传统节日等，适当向幼儿介绍我国主要民族和世界其它国家和民族的文化，帮助幼儿感知文化的多样性和差异性，理解人们之间是平等的，应该互相尊重，友好相处。",
        ]),
    ],
    ("社会", "社会适应", 2): [
        ("成人要遵守社会行为规则，为幼儿树立良好的榜样。如：答应幼儿的事一定要做到、尊老爱幼、爱护公共环境，节约水电等。", []),
        ("结合社会生活实际，帮助幼儿了解基本行为规则或其它游戏规则，体会规则的重要性，学习自觉遵守规则。如：", [
            "经常和幼儿玩带有规则的游戏，遵守共同约定的游戏规则。",
            "利用实际生活情境和图书故事，向幼儿介绍一些必要的社会行为规则，以及为什么要遵守这些规则。",
            "在幼儿园的区域活动中，创设情境，让幼儿体会没有规则的不方便，鼓励他们讨论制定规则并自觉遵守。",
            "对幼儿表现出的遵守规则的行为要及时肯定，对违规行为给予纠正。如：幼儿主动为老人让座时要表扬；幼儿损害别人的物品或公共物品时要及时制止并主动赔偿。",
        ]),
        ("教育幼儿要诚实守信。如：", [
            "对幼儿诚实守信的行为要及时肯定。",
            "允许幼儿犯错误，告诉他改了就好。不要打骂幼儿，以免他因害怕惩罚而说谎。",
            "小年龄幼儿经常分不清想象和现实，成人不要误认为他是在说谎。",
            "发现幼儿说谎时，要反思是否是因自己对幼儿的要求过高过严造成的。如果是，要及时调整自己的行为，同时要严肃地告诉幼儿说谎是不对的。",
            "经常给幼儿分配一些力所能及的任务，要求他完成并及时给予表扬，培养他的责任感和认真负责的态度。",
        ]),
    ],
    ("社会", "社会适应", 3): [
        ("亲切地对待幼儿，关心幼儿，让他感到长辈是可亲、可近、可信赖的，家庭和幼儿园是温暖的。如：", [
            "多和孩子一起游戏、谈笑，尽量在家庭和班级中营造温馨的氛围。",
            "通过和幼儿一起翻阅照片、讲幼儿成长的故事等，让幼儿感受到家庭和幼儿园的温暖，老师的和蔼可亲，对养育自己的人产生感激之情。",
        ]),
        ("吸引和鼓励幼儿参加集体活动，萌发集体意识。如：", [
            "幼儿园和班级里的重大事情和计划，请幼儿集体讨论决定。",
            "幼儿园应经常组织多种形式的集体活动，萌发幼儿的集体荣誉感。",
        ]),
        ("运用幼儿喜闻乐见和能够理解的方式激发幼儿爱家乡、爱祖国的情感。如：", [
            "和幼儿说一说或在地图上找一找自己家所在的省、市、县（区）名称。",
            "和幼儿一起外出游玩，一起看有关的电视节目或画报等；和他们一起收集有关家乡、祖国各地的风景名胜、著名的建筑、独特物产的图片等，在观看和欣赏的过程中激发幼儿的自豪感和热爱之情。",
            "利用电视节目或参加升旗等活动，向幼儿介绍国旗、国歌以及观看升旗、奏国歌的礼仪。",
        ]),
    ],
}

# Concrete suggestion that the generic filter rejected even though it names a
# checkable arts task.
PRESCHOOL_KEEP_UIDS = {
    "ps-a-a2-g2-s-04",
    "ps-s-a2-g2-s-01",
}


def concrete_preschool_text(text: str) -> bool:
    number = bool(P_NUM.search(text))
    actions = len(P_ACTION.findall(text))
    objects = len(P_OBJECT.findall(text))
    return (number and actions >= 1) or (actions >= 1 and objects >= 1)


def filter_preschool(items: list[dict]) -> tuple[list[dict], list[dict]]:
    kept: list[dict] = []
    excluded: list[dict] = []
    for item in items:
        if item.get("uid") in PRESCHOOL_KEEP_UIDS:
            kept.append(item)
            continue
        if item.get("type") != "suggestion":
            kept.append(item)
            continue
        examples = item.get("examples") or []
        text = item.get("text", "")
        if examples:
            kept.append(item)
            continue
        if concrete_preschool_text(text):
            kept.append(item)
            continue
        archived = dict(item)
        archived["filter_reason"] = "suggestion-no-concrete-example"
        excluded.append(archived)
    return kept, excluded


def build() -> tuple[dict, list[dict]]:
    lines, toc = read_source()
    goals = parse_goals(lines)
    for g in goals:
        key = (g["domain"], g["aspect"], g["goal_no"])
        if key in GOAL_CELL_OVERRIDES:
            cell_index, cell = GOAL_CELL_OVERRIDES[key]
            if cell_index < len(g["cells"]):
                g["cells"][cell_index] = cell
        if key in SUGGESTION_OVERRIDES:
            g["suggestions"] = [list(entry) for entry in SUGGESTION_OVERRIDES[key]]
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

    kept, excluded = filter_preschool(items)
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
            "filter": {
                "version": PRESCHOOL_FILTER_VERSION,
                "rule": "发展目标全部保留；教育建议带具体举例，或建议本身给出具体行动时展示。",
                "kept": len(kept),
                "excluded": len(excluded),
            },
        },
        "items": kept,
    }, excluded


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


def write_excluded(excluded: list[dict]) -> None:
    archive = {
        "meta": {
            "title": "幼儿园未展示教育建议（暂存）",
            "filter_version": PRESCHOOL_FILTER_VERSION,
            "filter_rule": "发展目标全部保留；教育建议带具体举例，或建议本身给出具体行动时展示。",
            "count": len(excluded),
            "notice": "这些建议没有删除，只是不符合当前「只展示干货」的筛选标准。",
        },
        "items": excluded,
    }
    (DATA / "preschool-excluded.json").write_text(
        json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    fields = [
        "uid", "stage", "age", "domain", "aspect", "goal_no", "goal", "type",
        "text", "examples", "reference", "source_page", "source_id", "filter_reason",
    ]
    with (DATA / "preschool-excluded.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in excluded:
            row = {k: "" for k in fields}
            row.update(item)
            row["examples"] = "\n".join(item.get("examples", []))
            writer.writerow(row)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    data, excluded = build()
    (DATA / "preschool.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_inline(data)
    write_csv(data)
    write_xlsx(data)
    write_preview(data)
    write_excluded(excluded)
    count = Counter(x["type"] for x in data["items"])
    stages = Counter(x.get("stage") for x in data["items"] if x["type"] == "goal")
    print(f"items={len(data['items'])} goals={count['goal']} suggestions={count['suggestion']}")
    print("excluded suggestions:", len(excluded))
    print("goal items by stage:", dict(stages))
    print("domains:", dict(Counter(x["domain"] for x in data["items"] if x["type"] == "goal")))
    print("missing source_page:", sum(not x.get("source_page") for x in data["items"]))


if __name__ == "__main__":
    main()
