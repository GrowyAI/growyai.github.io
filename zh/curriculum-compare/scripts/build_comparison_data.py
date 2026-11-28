#!/usr/bin/env python3
"""Build a grade-labeled concept-cluster comparison dataset for US/CN curricula.

Only data files are produced; no web pages are generated.
Chinese displayed items and items hidden by the app's concrete-content filter
are both included, with their status preserved.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "zh" / "curriculum-compare" / "data"

US_PATH = ROOT / "zh" / "core-knowledge" / "data" / "knowledge.json"
CN_PS = ROOT / "zh" / "china-curriculum" / "data" / "preschool.json"
CN_PS_EXCLUDED = ROOT / "zh" / "china-curriculum" / "data" / "preschool-excluded.json"
CN_SS = ROOT / "zh" / "china-curriculum" / "data" / "primary-secondary.json"
CN_SS_EXCLUDED = ROOT / "zh" / "china-curriculum" / "data" / "primary-secondary-excluded.json"


US_GRADE_LABELS = {
    "Preschool": "美国幼儿园前班（对应中国小班、中班）",
    "K": "美国幼儿园大班（K）",
    "1": "美国小学1年级",
    "2": "美国小学2年级",
    "3": "美国小学3年级",
    "4": "美国小学4年级",
    "5": "美国小学5年级",
    "6": "美国小学6年级",
    "7": "美国初中7年级",
    "8": "美国初中8年级",
}

US_INTERVALS = {
    "Preschool": (0, 1),
    "K": (2, 2),
    "1": (3, 3),
    "2": (4, 4),
    "3": (5, 5),
    "4": (6, 6),
    "5": (7, 7),
    "6": (8, 8),
    "7": (9, 9),
    "8": (10, 10),
}

CN_STAGE_LABELS = {
    "小班": "幼儿园小班（3-4岁）",
    "中班": "幼儿园中班（4-5岁）",
    "大班": "幼儿园大班（5-6岁）",
    "幼儿园小班/中班/大班（通用）": "幼儿园小班/中班/大班（通用）",
    "小学1-2年级": "小学1-2年级",
    "小学3-4年级": "小学3-4年级",
    "小学5-6年级": "小学5-6年级",
    "小学1-6年级": "小学1-6年级",
    "初中7-9年级": "初中7-9年级",
    "各年级通用（未细分）": "各年级通用（未细分）",
}

CN_INTERVALS = {
    "幼儿园小班（3-4岁）": (0, 0),
    "幼儿园中班（4-5岁）": (1, 1),
    "幼儿园大班（5-6岁）": (2, 2),
    "幼儿园小班/中班/大班（通用）": (0, 2),
    "小学1-2年级": (3, 4),
    "小学3-4年级": (5, 6),
    "小学5-6年级": (7, 8),
    "小学1-6年级": (3, 8),
    "初中7-9年级": (9, 11),
    "各年级通用（未细分）": (0, 11),
}

CN_STAGE_KEY_LABELS = {
    "x1": "小学1-2年级",
    "x2": "小学3-4年级",
    "x3": "小学5-6年级",
    "j1": "初中7-9年级",
    "p": "小学1-6年级",
    "all": "各年级通用（未细分）",
}

CN_SOURCE_LABELS = {
    "moe-cn-2022-math": "教育部《义务教育数学课程标准（2022年版）》",
    "moe-cn-2022-science": "教育部《义务教育科学课程标准（2022年版）》",
    "moe-cn-2022-physics": "教育部《义务教育物理课程标准（2022年版）》",
    "moe-cn-2022-chemistry": "教育部《义务教育化学课程标准（2022年版）》",
    "moe-cn-2022-biology": "教育部《义务教育生物学课程标准（2022年版）》",
    "moe-cn-2022-geography": "教育部《义务教育地理课程标准（2022年版）》",
    "moe-preschool-2012": "教育部《3-6岁儿童学习与发展指南》（2012）",
}


CLUSTERS: list[dict[str, Any]] = [
    {
        "id": "math-number-place",
        "domain": "数学",
        "concept": "数、位值与十进制",
        "us": {
            "subjects": ["Mathematics"],
            "topic_regex": r"Counting and Cardinality|Number and Operations in Base Ten|Number Sense|The Number System|Place Value",
            "text_regex": r"place value|ones?|tens?|hundreds?|thousands?|cardinality|counting|number names|decimal system|compare numbers|order numbers",
        },
        "cn": {
            "subjects": ["数学"],
            "text_regex": r"数位|计数单位|十进制|万以内|有理数|实数|数轴|数感|认、读、写|数数|比较.*大小",
            "exclude_regex": r"函数的概念|函数值|四分位数|百分位数|线段的和|线段的长短",
        },
        "relation_note": "两边都从低年级建立数感；美国从幼儿园前班的分类与计数开始，中国在小学1-2年级明确提出万以内数和数位。",
        "emphasis": "两边相当，起点略有不同",
    },
    {
        "id": "math-four-operations",
        "domain": "数学",
        "concept": "加、减、乘、除四则运算",
        "us": {
            "subjects": ["Mathematics"],
            "topic_regex": r"Operations and Algebraic Thinking|Number and Operations in Base Ten|The Number System|Mathematical Reasoning and Number Sense",
            "text_regex": r"\baddition\b|\bsubtraction\b|\bmultiplication\b|\bdivision\b|\badd(?:ing)?\b|\bsubtract(?:ing)?\b|\bmultiply\b|\bdivide\b|\bproduct\b|\bquotient\b",
        },
        "cn": {
            "subjects": ["数学"],
            "text_regex": r"加法|减法|乘法|除法|四则运算|运算之间的关系|口算",
        },
        "relation_note": "两边都把四则运算放在小学低段；中国课标对算理、算法和熟练程度写得更集中。",
        "emphasis": "两边相当",
    },
    {
        "id": "math-fractions-decimals",
        "domain": "数学",
        "concept": "分数与小数",
        "us": {
            "subjects": ["Mathematics"],
            "topic_regex": r"Number and Operations—Fractions|Fractions|Number and Operations in Base Ten|The Number System",
            "text_regex": r"\bfraction\b|\bfractions\b|\bnumerator\b|\bdenominator\b|\bdecimal\b|\btenths\b|\bhundredths\b",
        },
        "cn": {
            "subjects": ["数学"],
            "text_regex": r"分数|分数单位|分子|分母|小数|十分位|百分位(?!数)",
            "exclude_regex": r"四分位数|百分位数|加权平均数|方差",
        },
        "relation_note": "美国3年级开始把分数作为数系统学习；中国在小学3-4年级提出初步认识，5-6年级做四则运算。",
        "emphasis": "两边都有，中国分段更明确",
    },
    {
        "id": "math-ratio-percent",
        "domain": "数学",
        "concept": "比、比例、比例尺与百分数",
        "us": {
            "subjects": ["Mathematics"],
            "topic_regex": r"Ratios and Proportional Relationships|Number and Operations—Fractions|Statistics and Probability",
            "text_regex": r"\bratio\b|\bproportion\b|\bpercent\b|scale drawing|\bfor every\b|per 100",
        },
        "cn": {
            "subjects": ["数学"],
            "text_regex": r"比例尺|按比例|百分数|百分率|比的意义|比和比例|比例关系",
            "exclude_regex": r"函数的概念|图形的相似|相似三角",
        },
        "relation_note": "两边都在小学高段到初中前后出现；中国把比例尺、按比分配和百分数列得更集中。",
        "emphasis": "中国更集中",
    },
    {
        "id": "math-negative-rational",
        "domain": "数学",
        "concept": "负数、整数与有理数",
        "us": {
            "subjects": ["Mathematics"],
            "topic_regex": r"The Number System|Expressions and Equations",
            "text_regex": r"\bnegative numbers?\b|positive and negative|opposite numbers|\bintegers?\b|\brational numbers?\b",
            "exclude_ids": {"n07046"},
        },
        "cn": {
            "subjects": ["数学"],
            "text_regex": r"负数|有理数|相反数",
        },
        "manual_relation": "两边都有，首次阶段接近；中国5-6年级暂存档已出现负数，初中系统学习",
        "relation_note": "美国6年级用正负数描述相反意义的量；中国5-6年级主题活动中已出现负数（暂存档），初中把有理数作为代数内容系统学习。",
        "emphasis": "起步阶段接近，中国更系统",
    },
    {
        "id": "math-equations-algebra",
        "domain": "数学",
        "concept": "等式、方程与代数表达",
        "us": {
            "subjects": ["Mathematics"],
            "topic_regex": r"Expressions and Equations|Operations and Algebraic Thinking|Algebra",
            "text_regex": r"\bequation\b|\bvariable\b|solve for|algebraic|expressions and equations|write an equation",
        },
        "cn": {
            "subjects": ["数学"],
            "text_regex": r"方程|等式|字母表示数|代数式|不等式",
        },
        "relation_note": "美国从K年级的运算关系开始铺垫，6-8年级有独立表达式与方程单元；中国在5-6年级出现等式性质，初中集中学习方程与不等式。",
        "emphasis": "美国更早铺垫",
    },
    {
        "id": "math-functions",
        "domain": "数学",
        "concept": "函数与变化关系",
        "us": {
            "subjects": ["Mathematics"],
            "topic_regex": r"Functions",
            "text_regex": r"\bfunction\b|\binput\b|\boutput\b|\blinear\b|\bslope\b|rate of change",
        },
        "cn": {
            "subjects": ["数学"],
            "text_regex": r"函数|自变量|因变量|常量、变量",
            "exclude_regex": r"数与运算的教学|教学要引导学生",
            "exclude_ids": {"ma-j1-aca-9018a320"},
        },
        "relation_note": "两边都在初中阶段系统出现；美国8年级有独立函数主题，中国在初中7-9年级统一安排函数内容。",
        "emphasis": "阶段接近，组织方式不同",
    },
    {
        "id": "math-geometry",
        "domain": "数学",
        "concept": "图形、角与几何关系",
        "us": {
            "subjects": ["Mathematics"],
            "topic_regex": r"Geometry|Mathematical Reasoning and Number Sense",
            "text_regex": r"\bangle\b|\btriangle\b|\bquadrilateral\b|\bcircle\b|\bshape\b|\bgeometry\b|\bsymmetry\b|\bcongruent\b|\bsimilar\b|\bpolygon\b|solid figure",
        },
        "cn": {
            "subjects": ["数学"],
            "text_regex": r"三角形|四边形|圆|角|图形|对称|全等|相似|长方体|正方体|圆柱|球",
        },
        "relation_note": "两边从低年级辨认图形开始；中国按1-2、3-4、5-6、初中分段推进得更清楚，美国K-8连续覆盖。",
        "emphasis": "两边相当",
    },
    {
        "id": "math-measurement",
        "domain": "数学",
        "concept": "测量、面积、周长与体积",
        "us": {
            "subjects": ["Mathematics"],
            "topic_regex": r"Measurement and Data|Geometry|Mathematical Reasoning and Number Sense",
            "text_regex": r"\barea\b|\bperimeter\b|\bvolume\b|\bmeasur|\blength\b|\bweight\b|\bcapacity\b|\bunit\b",
        },
        "cn": {
            "subjects": ["数学"],
            "text_regex": r"面积|周长|体积|测量|长度单位|质量单位|容积",
            "exclude_regex": r"图形的相似|面积比等于相似比的平方",
        },
        "relation_note": "两边都从幼儿园/低年级的可测量属性起步，再进入面积、周长和体积。",
        "emphasis": "两边相当",
    },
    {
        "id": "math-statistics",
        "domain": "数学",
        "concept": "数据、统计与概率",
        "us": {
            "subjects": ["Mathematics"],
            "topic_regex": r"Measurement and Data|Statistics and Probability",
            "text_regex": r"\bprobability\b|\bdata\b|\bgraph\b|\bchart\b|\bmean\b|\bmedian\b|\bmode\b|\bstatistics\b|bar graph|line plot|pie chart",
        },
        "cn": {
            "subjects": ["数学"],
            "text_regex": r"统计|数据|平均数|中位数|众数|可能性|概率|条形统计图|折线统计图|扇形统计图",
        },
        "relation_note": "美国从K年级的生活化数据活动开始，6、8年级有统计与概率单元；中国从1-2年级数据分类到初中抽样与概率逐步体系化。",
        "emphasis": "美国更前置，中国更体系化",
    },
    {
        "id": "science-matter",
        "domain": "科学",
        "concept": "物质性质与物理、化学变化",
        "us": {
            "subjects": ["Science"],
            "topic_regex": r"Matter|Physical Changes|Chemical Reactions|Chemical Bonds|Properties of Matter|Investigating Matter|Building with Matter|Heating and Cooling",
            "text_regex": r"\bmatter\b|physical change|chemical reaction|\bproperty\b|\bsolid\b|\bliquid\b|\bgas\b|\batom\b|\bmolecule\b",
        },
        "cn": {
            "subjects": ["科学", "物理", "化学"],
            "text_regex": r"物质|物理变化|化学变化|化学反应|固体|液体|气体|分子|原子|溶解|传热|导热",
        },
        "manual_relation": "两边都有，中国幼儿园已有生活现象感知，美国2年级起系统分类",
        "relation_note": "中国幼儿园已感知溶解、传热等现象；美国2-5年级系统描述物质属性与变化，初中由物理、化学分科深化。",
        "emphasis": "中国起步更早，美国分类更系统",
    },
    {
        "id": "science-atoms-bonds",
        "domain": "科学",
        "concept": "原子、分子、元素与化学基础",
        "us": {
            "subjects": ["Science"],
            "topic_regex": r"Chemical Bonds|Chemical Reactions|Atoms|Matter",
            "text_regex": r"\batom\b|\bmolecule\b|\belement\b|\bcompound\b|chemical bond|periodic table",
        },
        "cn": {
            "subjects": ["科学", "化学"],
            "text_regex": r"原子|分子|元素|化合物|化学式|元素周期表",
        },
        "relation_note": "美国7年级在化学反应单元引入键与物质构成；中国主要由初中化学承担，概念链条更集中。",
        "emphasis": "中国化学更系统",
    },
    {
        "id": "science-force-motion",
        "domain": "科学",
        "concept": "力、运动、磁与简单机械",
        "us": {
            "subjects": ["Science"],
            "topic_regex": r"Forces|Force|Motion|Pushes|Collisions|Gravity|Simple Machines|Magnetism|Predicting Motion",
            "text_regex": r"\bforce\b|\bmotion\b|\bpush\b|\bpull\b|\bmagnet\b|\bgravity\b|\bfriction\b|simple machine|\bcollision\b|\bspeed\b",
        },
        "cn": {
            "subjects": ["科学", "物理"],
            "text_regex": r"用力|力量|推力|拉力|磁力|重力|摩擦力|简单机械|运动快慢|速度|碰撞|磁铁|推拉",
        },
        "relation_note": "美国从K年级推拉、1年级简单机械、3-8年级反复深化；中国在小学科学有现象铺垫，初中物理系统讲运动和力。",
        "emphasis": "美国更螺旋，中国更系统",
    },
    {
        "id": "science-energy-electricity",
        "domain": "科学",
        "concept": "能量、热、光、声、电与磁",
        "us": {
            "subjects": ["Science"],
            "topic_regex": r"Energy|Thermal|Electricity|Magnetism|Light|Sound|Waves|Renewable Resources",
            "text_regex": r"\benergy\b|\bheat\b|\bthermal\b|\blight\b|\bsound\b|\belectric\b|\bcurrent\b|\bmagnet\b|\bwave\b",
        },
        "cn": {
            "subjects": ["科学", "物理"],
            "text_regex": r"能量|热量|传热|导热|发光|光线|声音|电流|电压|磁力|磁场|波|太阳光|热胀冷缩",
        },
        "manual_relation": "两边都有，中国幼儿园已有传热感知，美国1年级起系统讲声光",
        "relation_note": "中国幼儿园已有传热等生活感知，小学高段做热胀冷缩实验；美国1年级起系统讲光与声，1-8年级持续铺开，中国初中物理再做归纳。",
        "emphasis": "中国起步更早，美国覆盖更连续",
    },
    {
        "id": "science-life-genetics",
        "domain": "科学",
        "concept": "生命体、细胞、遗传与进化",
        "us": {
            "subjects": ["Science"],
            "topic_regex": r"Cells|Genetics|Natural Selection|Evolution|Structures and Functions of Living Things|Animal Diversity|Metabolic|Reproduction|Growth and Development",
            "text_regex": r"\bcell\b|\bhered|\bgene\b|\bgenetic\b|\borganism\b|living thing|\bplant\b|\banimal\b|\bevolution\b|natural selection|\breproduction\b",
        },
        "cn": {
            "subjects": ["科学", "生物学"],
            "text_regex": r"细胞|遗传|基因|生物|植物|动物|进化|自然选择|繁殖",
        },
        "manual_relation": "两边都有，中国幼儿园已有动植物认知，美国1年级起系统讲繁殖",
        "relation_note": "中国幼儿园已认识常见动植物及其生长变化；美国1年级起讲繁殖与照顾后代，6-8年级进入细胞、遗传和自然选择，中国初中生物学按体系展开。",
        "emphasis": "中国起步更早，美国初中内容更深",
    },
    {
        "id": "science-ecology-environment",
        "domain": "科学",
        "concept": "生态系统、食物链与环境保护",
        "us": {
            "subjects": ["Science"],
            "topic_regex": r"Ecosystem|Habitats|Protecting|Natural Resources|Environment|Matter Cycles|Plants and Animals|Human Changes",
            "text_regex": r"\becosystem\b|\bhabitat\b|food chain|\benvironment\b|\bresource\b|\bprotecting\b|\bplant\b|\banimal\b|\brenewable\b",
        },
        "cn": {
            "subjects": ["科学", "生物学"],
            "text_regex": r"生态系统|食物链|栖息地|环境保护|保护环境|生态平衡|可再生资源|自然资源|生态",
        },
        "relation_note": "两边都重视生态与环境；美国在K-5非常密集，中国在小学科学与初中生物学中都有明确内容。",
        "emphasis": "两边都有，美国更前置",
    },
    {
        "id": "science-human-body",
        "domain": "科学",
        "concept": "人体、感官与健康",
        "us": {
            "subjects": ["Science"],
            "topic_regex": r"Human Body|Senses|Vision|Nervous System|Taking Care of|Stimulus",
            "text_regex": r"human body|\bsenses\b|\bsight\b|\bhearing\b|\bsmell\b|\btaste\b|\btouch\b|\beye\b|nervous system|body system|\bhealth\b",
        },
        "cn": {
            "subjects": ["科学", "生物学"],
            "text_regex": r"人体|感官|眼睛|听觉|触觉|味觉|嗅觉|神经系统|身体器官|健康",
        },
        "manual_relation": "两边都有，中国从幼儿园感官体验起步，美国K年级起系统讲身体",
        "relation_note": "中国幼儿园已用多种感官探索物体；美国K年级系统讲视觉、听觉和身体系统，3-5年级深化，中国初中生物学再系统学习。",
        "emphasis": "中国起步更早，美国概念更系统",
    },
    {
        "id": "science-earth-space",
        "domain": "科学",
        "concept": "地球、宇宙与地质现象",
        "us": {
            "subjects": ["Science"],
            "topic_regex": r"Astronomy|Space|Earth|Stars|Sun|Moon|Plate Tectonics|Earthquakes|Volcanoes|Land",
            "text_regex": r"\bearth\b|\bspace\b|\bastronomy\b|\bplanet\b|\bmoon\b|\bsun\b|\bstar\b|\bsolar\b|\borbit\b|plate tectonic|\bearthquake\b|\bvolcano\b",
        },
        "cn": {
            "subjects": ["科学", "地理"],
            "text_regex": r"地球|宇宙|太阳|月球|行星|恒星|板块|地震|火山",
        },
        "relation_note": "美国1、5、6、8年级都有天体与地球现象；中国在小学科学观察现象，初中地理讲原理。",
        "emphasis": "美国现象先行，中国原理更系统",
    },
    {
        "id": "science-weather-water",
        "domain": "科学",
        "concept": "天气、气候与水循环",
        "us": {
            "subjects": ["Science"],
            "topic_regex": r"Weather|Climate|Water Cycle|Water Cycling|Severe Weather|Natural Hazards",
            "text_regex": r"\bweather\b|\bclimate\b|water cycle|\bcloud\b|\brain\b|\bprecipitation\b|\bseason\b|\bhazard\b",
        },
        "cn": {
            "subjects": ["科学", "地理"],
            "text_regex": r"天气|气候|水循环|云|雨|降水|季节",
        },
        "manual_relation": "两边都有，中国从幼儿园天气体验起步，美国K年级起记录天气数据",
        "relation_note": "中国小班已感知天气影响，中班认识季节；美国K年级开始定义天气并记录温度、降水、风速，6年级系统讲水循环。",
        "emphasis": "中国起步更早，美国数据化更早",
    },
    {
        "id": "science-inquiry-experiment",
        "domain": "科学",
        "concept": "观察、实验、探究与工程设计",
        "us": {
            "subjects": ["Science"],
            "topic_regex": r"Scientific|Investigating|Investigation|Designing and Engineering|Scientific Reasoning",
            "text_regex": r"\bobserv|\bexperiment|\binvestigat|\bdesign|\bengineer|\bmeasure|\bhypothes|scientific reasoning",
        },
        "cn": {
            "subjects": ["科学", "物理", "化学", "生物学"],
            "text_regex": r"观察|实验|探究|调查|测量|制作|工程设计",
        },
        "relation_note": "两边都把探究作为学习方式；中国课标把“学生必做实验与跨学科实践活动”写得更实，美国则突出工程设计活动。",
        "emphasis": "中国实验清单更突出，美国工程设计更突出",
    },
    {
        "id": "geo-map-skills",
        "domain": "地理",
        "concept": "地图、方向与位置",
        "us": {
            "subjects": ["History and Geography"],
            "topic_regex": r"Geography|Map",
            "text_regex": r"\bmap\b|\bglobe\b|direction|legend|compass rose|\bnorth\b|\bsouth\b|\beast\b|\bwest\b|latitude|longitude",
        },
        "cn": {
            "subjects": ["地理", "科学", "社会"],
            "text_regex": r"地图|图例|方向|方位|指南针|经纬网|东西南北|东、西|南、北|位置与方向",
            "exclude_regex": r"轮流|分享|不许|借别人",
        },
        "manual_relation": "两边都有，中国从幼儿园方位词起步，美国1年级起正式地图技能",
        "relation_note": "中国小班已理解上下、前后、里外等方位；美国K年级要求定位北美与美国的州，1年级开始地图图例和东西南北，中国系统地图技能主要在初中地理。",
        "emphasis": "中国方位更早，美国地图技能更早",
    },
    {
        "id": "geo-continents-oceans",
        "domain": "地理",
        "concept": "大洲、大洋与国家定位",
        "us": {
            "subjects": ["History and Geography"],
            "topic_regex": r"Geography|World Geography|Geography of the Americas|Early World Civilizations",
            "text_regex": r"\bcontinent\b|\bocean\b|\bcountry\b|\bcapital\b|seven continents|four oceans|locate.*world",
        },
        "cn": {
            "subjects": ["地理", "科学", "社会"],
            "text_regex": r"七大洲|四大洋|大洲|大洋|亚洲|欧洲|非洲|美洲|南极洲|首都|国家的位置|国土面积",
        },
        "relation_note": "美国低年级偏世界地名与常识记忆；中国初中地理偏区域定位与分析。",
        "emphasis": "美国更前置，侧重不同",
    },
    {
        "id": "geo-coordinates-earth-motion",
        "domain": "地理",
        "concept": "经纬度、半球与地球运动",
        "us": {
            "subjects": ["History and Geography"],
            "topic_regex": r"Geography|Astronomy|Space|Earth in Space|Stars|Sun|Moon",
            "text_regex": r"latitude|longitude|equator|hemisphere|rotat|revolv|orbit|time zone|prime meridian",
        },
        "cn": {
            "subjects": ["地理", "科学"],
            "text_regex": r"经度|纬度|赤道|半球|自转|公转|时区|本初子午线",
        },
        "relation_note": "美国1年级已定位赤道和南北半球；中国5-6年级用地球仪模拟自转公转，初中地理对经纬网和地球运动的表述更成体系。",
        "emphasis": "中国更系统",
    },
    {
        "id": "geo-physical",
        "domain": "地理",
        "concept": "地形、气候、河流与自然资源",
        "us": {
            "subjects": ["History and Geography"],
            "topic_regex": r"Geography|World Geography|Processes That Shape Earth|Land|Water|River|Resources|Climate|Weather|Plate",
            "text_regex": r"\bmountain\b|\briver\b|\bclimate\b|\blandform\b|natural resource|\bsoil\b|\bvegetation\b|\bearthquake\b|\bvolcano\b|\bweather\b|ocean current",
        },
        "cn": {
            "subjects": ["地理", "科学"],
            "text_regex": r"地形|地势|山脉|河流|气候|自然资源|土地|植被|盆地|高原|平原|等高线|分层设色|水资源|矿产资源",
            "exclude_regex": r"社会资源|历史文化",
        },
        "relation_note": "美国常把自然地理嵌在世界历史与地区单元中；中国在小学科学有现象铺垫，初中地理形成自然地理体系。",
        "emphasis": "中国更系统，美国更嵌入式",
    },
    {
        "id": "geo-human",
        "domain": "地理",
        "concept": "人口、城市、文化与区域差异",
        "us": {
            "subjects": ["History and Geography"],
            "topic_regex": r"Geography|World Geography|Immigration|Urbanization|Migrating|Population|Culture|Religion",
            "text_regex": r"\bpopulation\b|\bmigration\b|\bimmigration\b|\bcity\b|\burban\b|\bculture\b|\breligion\b|\blanguage\b|\beconomic\b|\btrade\b|\bindustry\b",
        },
        "cn": {
            "subjects": ["地理"],
            "text_regex": r"人口|城市|聚落|文化|宗教|语言|经济|产业|交通|迁移",
        },
        "relation_note": "美国大量人文地理内容嵌在历史单元里；中国初中地理把人口、聚落、区域发展单独组织。",
        "emphasis": "中国更独立，美国更嵌入式",
    },
    {
        "id": "geo-admin-divisions",
        "domain": "地理",
        "concept": "州与省：行政区划与行政中心",
        "us": {
            "subjects": ["History and Geography"],
            "topic_regex": r"Geography",
            "text_regex": r"Name and locate the town, city, or community, as well as the state where you live|Name your continent, country, state, and community|Fifty states(?: and capitals)?",
        },
        "cn": {
            "subjects": ["地理"],
            "text_regex": r"省级行政区|行政区划图|简称和行政中心",
        },
        "manual_relation": "两边都有，起步美国早，中国后段集中完成",
        "relation_note": "州和省都是一级行政区，可以直接横向对照：美国从学前认识所在州，3-4年级知道50州，5-6年级记州府；中国在7-9年级识别34个省级行政区并记住简称和行政中心。",
        "emphasis": "内容可对标，阶段安排不同",
    },
    # ---- 语言与读写：按母语功能对标，美国 ELA/Language and Literacy 对 中国语文/学前语言 ----
    {
        "id": "lang-listen-speak",
        "domain": "语言与读写",
        "concept": "倾听、理解与口语表达",
        "us": {
            "subjects": ["Language and Literacy", "English Language Arts"],
            "text_only": True,
            "topic_regex": r".*",
            "text_regex": r"\blisten|listening|\bspeak|speaking|conversation|dialogue|discussion|discuss|oral presentation|\bdebate|retell|recount|respond|talk about",
        },
        "cn": {
            "subjects": ["语言", "语文"],
            "text_only": True,
            "text_regex": r"注意听|听懂|倾听|交谈|对话|讲述|口语|回应|说话|普通话|大声说|礼貌用语|交流|讨论|复述|转述|演讲|发言|有自己的看法",
        },
        "manual_relation": "两边都有，起步接近，中国后段口语表达要求更集中",
        "relation_note": "美国从学前口语互动到K-8课堂讨论逐年级推进；中国学前语言领域先抓倾听与日常对话，小学语文再把复述、讨论、即席讲话与主题演讲写成学段目标。",
        "emphasis": "两边都有，功能对标",
    },
    {
        "id": "lang-emergent-literacy",
        "domain": "语言与读写",
        "concept": "文字、图书与读写准备",
        "us": {
            "subjects": ["Language and Literacy", "English Language Arts"],
            "text_only": True,
            "topic_regex": r".*",
            "text_regex": r"print awareness|identify.*print|letter|phoneme|phonics|blend|book.*cover|turn.*page|rhyming|decod|sight word|fluen",
        },
        "cn": {
            "subjects": ["语言", "语文"],
            "text_only": True,
            "text_regex": r"图书|画册|标记|符号|笔画|汉字|拼音|认读|写字|翻书|涂涂|画画|识字|部首|查字典",
        },
        "manual_relation": "两边都有，具体文字系统不同但功能对标",
        "relation_note": "美国从学前辨识生活中的印刷品、图书结构，到K-2年级系统学拼读解码；中国学前先建立图书与符号兴趣，小学低段集中识字、写字、拼音，两套文字系统不同但都是读写准备。",
        "emphasis": "功能对标，文字系统不同",
    },
    {
        "id": "lang-reading",
        "domain": "语言与读写",
        "concept": "阅读理解与文本分析",
        "us": {
            "subjects": ["English Language Arts", "Language and Literacy"],
            "text_only": True,
            "topic_regex": r".*",
            "text_regex": r"\bretell|read aloud|comprehension|describe characters|understand.*text|infer|summariz|main idea|text evidence|analyz|interpret|evaluate|author.*purpose|point of view",
        },
        "cn": {
            "subjects": ["语言", "语文"],
            "text_only": True,
            "text_regex": r"朗读|默读|课文|词句|阅读|理解.*内容|复述|概括|分析|体会|评价|揣摩|品味|梳理|思想感情|表达效果",
        },
        "manual_relation": "两边都有，起步接近，深度持续推进",
        "relation_note": "美国K年级起朗读、复述故事，3-8年级逐步加入推断、概括、文本证据与作者意图；中国小学低段先朗读理解词句，中高段到初中转入概括、分析与评价。",
        "emphasis": "两边都有，功能对标",
    },
    {
        "id": "lang-writing",
        "domain": "语言与读写",
        "concept": "写作与书面表达",
        "us": {
            "subjects": ["Language and Literacy", "English Language Arts"],
            "text_only": True,
            "topic_regex": r".*",
            "text_regex": r"dictate|caption|draw.*represent|write.*letter|label.*picture|copy.*letter|narrative|essay|draft|revise|paragraph|composition|write.*story|persuasive|expository",
        },
        "cn": {
            "subjects": ["语言", "语文"],
            "text_only": True,
            "text_regex": r"写自己的|愿意写|写话|涂涂|画画|口述|画.*表示|写写画画|习作|作文|记实|想象作文|读书笔记|应用文|修改.*习作|分段表述",
        },
        "manual_relation": "两边都有，中国低段写话更早明确",
        "relation_note": "美国学前先口述、画图、听写，再到K-8的叙事、说明与议论文写作；中国学前以涂画表达起步，小学低段明确“写话”，中高段到初中完成记实、想象作文与应用文。",
        "emphasis": "两边都有，功能对标",
    },
    {
        "id": "lang-literature",
        "domain": "语言与读写",
        "concept": "文学体裁、诗歌与故事",
        "us": {
            "subjects": ["Language and Literacy", "English Language Arts"],
            "text_only": True,
            "topic_regex": r".*",
            "text_regex": r"nursery rhyme|fairy tale|poem|rhyming|storybook|\bpoetry|fiction|myth|legend|literary|drama|novel|fable",
        },
        "cn": {
            "subjects": ["语言", "语文"],
            "text_only": True,
            "text_regex": r"儿歌|童谣|古诗|童话|故事|寓言|复述|诗文|神话|小说|散文|背诵|文学|叙事性作品",
        },
        "manual_relation": "两边都有，起步接近，体裁逐步扩展",
        "relation_note": "美国学前以儿歌、韵诗、童话故事入门，K-8扩展到诗歌、神话、戏剧与小说；中国学前从儿歌童谣、听故事起步，小学到初中加入古诗文诵读、寓言神话、小说散文等体裁。",
        "emphasis": "两边都有，功能对标",
    },
    # ---- 文化：功能对标，不硬套同一人物或节日 ----
    {
        "id": "culture-symbols",
        "domain": "文化",
        "concept": "国家符号与共同记忆",
        "us": {
            "subjects": ["History and Geography", "English Language Arts", "Visual Arts", "Music"],
            "text_only": True,
            "exclude_regex": r"Teachers:|Note:|Sayings and Phrases|Discuss with students:|𝆏|\bpiano\b|\bforte\b|capital letters|proper nouns",
            "topic_regex": r".*",
            "text_regex": r"American flag|Statue of Liberty|national anthem|national symbol|Stars and Stripes|bald eagle|Pledge of Allegiance",
        },
        "cn": {
            "subjects": ["社会", "语文", "道德与法治", "历史", "英语"],
            "text_only": True,
            "text_regex": r"国旗|国歌|国徽|国家象征|红领巾|升旗|中国.*象征",
        },
        "manual_relation": "两边都有，具体符号不同，功能对标",
        "relation_note": "美国低年级认识国旗、自由女神像、国歌等国家符号；中国学前与小学低段认识国旗、国歌、国徽并在升旗仪式中实践。具体符号不同，但都是国家认同的共同记忆教育。",
        "emphasis": "功能对标，符号不同",
    },
    {
        "id": "culture-holiday-heritage",
        "domain": "文化",
        "concept": "节日、风俗与文化传承",
        "us": {
            "subjects": ["History and Geography", "English Language Arts", "Visual Arts", "Music"],
            "text_only": True,
            "exclude_regex": r"Teachers:|Note:|Sayings and Phrases|Discuss with students:|𝆏|\bpiano\b|\bforte\b|capital letters|proper nouns",
            "topic_regex": r".*",
            "text_regex": r"Thanksgiving|Independence Day|Columbus Day|holiday|celebrat|festival|heritage|tradition",
        },
        "cn": {
            "subjects": ["社会", "语文", "道德与法治", "历史", "英语"],
            "text_only": True,
            "text_regex": r"传统节日|节日|风俗|文化体验|风土人情|中华优秀传统文化|习俗",
        },
        "manual_relation": "两边都有，具体节日不同，功能对标",
        "relation_note": "美国在感恩节、独立日等节日与庆典中建立文化记忆；中国从身边的传统节日、风俗体验到“中华优秀传统文化”的系统传承。节日不同，但都是文化传承的载体。",
        "emphasis": "功能对标，内容不同",
    },
    {
        "id": "culture-heritage-stories",
        "domain": "文化",
        "concept": "神话、传说与传统故事",
        "us": {
            "subjects": ["History and Geography", "English Language Arts", "Visual Arts", "Music"],
            "text_only": True,
            "exclude_regex": r"Teachers:|Note:|Sayings and Phrases|Discuss with students:|𝆏|\bpiano\b|\bforte\b|capital letters|proper nouns",
            "topic_regex": r".*",
            "text_regex": r"folktale|fairy tale|\bfable|legend|myth|Paul Bunyan|John Henry|\bhero",
        },
        "cn": {
            "subjects": ["社会", "语文", "道德与法治", "历史", "英语"],
            "text_only": True,
            "text_regex": r"神话|传说|成语故事|民间故事|寓言|传统美德|历史故事|智慧",
        },
        "manual_relation": "两边都有，具体故事不同，功能对标",
        "relation_note": "美国用民间故事、传说、神话与英雄人物传递文化价值；中国用神话传说、成语故事、寓言与历史故事传递传统美德与思维方法。故事不同，功能相近。",
        "emphasis": "功能对标，内容不同",
    },
    {
        "id": "culture-diversity",
        "domain": "文化",
        "concept": "多元文化与世界理解",
        "us": {
            "subjects": ["History and Geography", "English Language Arts", "Visual Arts", "Music"],
            "text_only": True,
            "exclude_regex": r"Teachers:|Note:|Sayings and Phrases|Discuss with students:|𝆏|\bpiano\b|\bforte\b|capital letters|proper nouns",
            "topic_regex": r".*",
            "text_regex": r"Native American|ways of life|culture|diversity|multicultural|world culture|immigrant|heritage|other countries|different cultures",
        },
        "cn": {
            "subjects": ["社会", "语文", "道德与法治", "历史", "英语"],
            "text_only": True,
            "text_regex": r"自己的民族|多民族|各民族|互相尊重|不同.*民族|世界主要国家|文化多样|中外文化|文化习俗|国际理解|各国",
        },
        "manual_relation": "两边都有，起步接近，中国后段更集中表述",
        "relation_note": "美国从认识本土部落与多元文化人群，到高年级的世界文化与移民内容；中国学前先建立多民族大家庭意识，英语与文化课在小学高段到初中明确世界主要国家与文化多样性。",
        "emphasis": "两边都有，功能对标",
    },
]

# 人工复核的“后续覆盖 + 内容深度”判断。仅使用面向读者的年级/学段措辞。
DEPTH_REVIEW: dict[str, dict[str, str]] = {
    "math-number-place": {
        "美国": "初中7年级把数扩展到有理数，并要求用运算律完成乘除与混合运算。",
        "中国": "幼儿园小班已有点数、数词和比较多少，小学1-2、3-4、5-6年级连续推进，初中7-9年级系统学习有理数、实数、数轴与运算律。",
        "终局关系": "起步都在学前，终局中国更系统；美国跨年级覆盖更广。",
        "说明": "两边都从学前数数起步；美国从幼儿园前班一直铺到初中，中国把认识、运算与一致性按学段分段写得更集中。",
    },
    "math-four-operations": {
        "美国": "从幼儿园前班分物开始，小学各年级反复回返，初中7年级进入有理数四则运算。",
        "中国": "幼儿园中班已有“2和3合在一起是5”，大班做10以内加减；小学低、中、高段各有明确要求，初中7-9年级把运算律和有理数混合运算集中系统化。",
        "终局关系": "起步接近，终局相当；美国覆盖更连续。",
        "说明": "双方学前已有数量分合；中国把算理、算法和熟练程度写得更集中，美国把接触面铺得更长。",
    },
    "math-fractions-decimals": {
        "美国": "小学3年级起以分数为数学习，4-5年级大量分数运算，初中7年级延伸到有理数。",
        "中国": "小学3-4年级初步认识，5-6年级集中做分数、小数运算与运算一致性，未在独立初中主题中继续展开。",
        "终局关系": "阶段接近，中国分段更清楚；美国后续跨度更长。",
        "说明": "首次时间差不大；中国主要在小学两个学段内完成认识与运算，美国则从3年级一路铺到初中有理数。",
    },
    "math-ratio-percent": {
        "美国": "小学6年级集中学习比与百分数，初中7年级用比例关系解决多步问题。",
        "中国": "集中在小学5-6年级，把比例尺、按比分配、百分数并列，更晚学段没有独立回返。",
        "终局关系": "起步接近，中国内容更集中但后续跨度更短。",
        "说明": "两边都不是长跨度概念；美国初中7年级还有一步比例应用，中国则集中在小学高段一次讲清。",
    },
    "math-negative-rational": {
        "美国": "小学6年级引入正负数，初中7-8年级扩展到有理数方程、根式与运算。",
        "中国": "小学5-6年级暂存档已有负数情境，初中7-9年级系统讲有理数、实数、数轴和运算律。",
        "终局关系": "起步阶段接近，终局中国更系统。",
        "说明": "首次年级应按区间理解：美国6年级对应中国5-6年级，且中国该条为暂存；初中阶段中国把有理数作为代数基础集中展开，系统性差异出现在后段。",
    },
    "math-equations-algebra": {
        "美国": "从幼儿园大班起用运算关系铺垫，小学各年级持续出现，初中8年级解含小数与科学记数法的一元一次方程。",
        "中国": "小学5-6年级出现等式性质，初中7-9年级集中学习方程、方程组和不等式。",
        "终局关系": "美国铺垫更长，终局中国更系统。",
        "说明": "美国“早”主要是长线铺垫；中国的系统性集中在初中，因此不能把首次差距直接理解为终局差距。",
    },
    "math-functions": {
        "美国": "初中8年级有独立函数主题，强调输入输出、函数规则和图像关系。",
        "中国": "初中7-9年级集中安排函数概念、自变量、函数值、一次函数和图像分析。",
        "终局关系": "阶段接近，中国内容更系统。",
        "说明": "双方都在初中才系统出现；中国在同一学段内展开的概念链更长，美国则以独立主题呈现。",
    },
    "math-geometry": {
        "美国": "从幼儿园前班辨认形状一路到初中8年级变换、相似与勾股定理。",
        "中国": "幼儿园小班已感知多种形状，中班能识别常见几何图形并分类；小学低、中、高段分学段推进，初中7-9年级进入性质、变化、坐标与几何证明体系。",
        "终局关系": "起步接近，美国覆盖更广，中国终局更系统。",
        "说明": "两边都呈螺旋；中国初中把定义、基本事实和证明串成体系，是后续深度上的关键差异。",
    },
    "math-measurement": {
        "美国": "从幼儿园大班可测量属性到小学长度、面积、体积，初中8年级解决柱体、锥体、球体体积问题。",
        "中国": "幼儿园已感知大小、多少、高矮长短、粗细厚薄和轻重，小学各学段推进面积、周长、体积，初中转向相似图形中的面积比等几何度量。",
        "终局关系": "起步接近，终局各有侧重；美国覆盖更连续。",
        "说明": "共同基础部分大体相当；美国后段继续做立体度量应用，中国后段更多与几何推理结合。",
    },
    "math-statistics": {
        "美国": "从低年级图表活动到初中8年级双向表、散点图和线性关联。",
        "中国": "幼儿园大班已用记录表、统计图表示简单数量关系，小学低年级做数据分类，初中7-9年级集中讲抽样、数据分析、统计图和概率。",
        "终局关系": "起步接近，终局中国更体系化。",
        "说明": "双方在学前和小学低段都有生活化数据活动；中国把抽样、数字特征和随机事件组织成完整初中主题。",
    },
    "science-matter": {
        "美国": "小学2年级观察分类，5年级系统性质与守恒，初中7年级进入化学反应中的物质守恒。",
        "中国": "幼儿园中班已有溶解、传热等生活感知，小学各段观察实验，初中物理、化学分科深化。",
        "终局关系": "起步中国早，终局双方分科深化，中国覆盖更广。",
        "说明": "中国从生活现象出发更早，但美国初中仍有明确的物质守恒要求；两边后段都进入分科体系。",
    },
    "science-atoms-bonds": {
        "美国": "初中7年级出现元素与原子层次的定义。",
        "中国": "初中7-9年级把纯净物、混合物、单质、化合物、元素等放到同一分类框架中。",
        "终局关系": "阶段接近，中国更系统。",
        "说明": "美国命中较少且集中在初中；中国虽也集中在初中，但概念层级和分类链更完整。",
    },
    "science-force-motion": {
        "美国": "从幼儿园大班推拉、简单机械到小学各年级，初中8年级进入力的定量表达。",
        "中国": "小学有生活经验和简单实验，初中7-9年级集中做摩擦力、浮力、电磁等必做实验。",
        "终局关系": "美国螺旋更早，中国终局实验化更系统。",
        "说明": "美国的长期回返明显；中国的后发集中体现在实验清单和定量探究要求上。",
    },
    "science-energy-electricity": {
        "美国": "小学1年级起持续出现，4-6年级高密度展开，初中8年级延伸到波与声的概念。",
        "中国": "幼儿园已有感知，小学高段开始实验，初中7-9年级集中讲能量转化、守恒和实验探究。",
        "终局关系": "中国起步早，美国覆盖更连续，中国终局更系统。",
        "说明": "双方后段都不弱；差别在美国的跨年级连续性与中国初中阶段的原理化和探究化。",
    },
    "science-life-genetics": {
        "美国": "小学阶段观察生物，初中7-8年级进入细胞、遗传、共同祖先与进化证据。",
        "中国": "幼儿园小班已有生命感知，小学连续回返，初中7-9年级集中做显微观察、细胞与生物分类。",
        "终局关系": "中国起步早，终局双方均深，侧重点不同。",
        "说明": "美国后段偏进化与遗传证据链，中国后段偏显微观察与实验操作；首次领先需拆成两条不同路径。",
    },
    "science-ecology-environment": {
        "美国": "从低年级生态认知到小学5年级食物网、物质循环，初中7年级讨论生态系统破坏。",
        "中国": "幼儿园大班有环境保护意识，小学高段做项目研究，初中7-9年级调查生态系统并制作生态瓶。",
        "终局关系": "美国起步早，终局中国项目化更突出。",
        "说明": "美国覆盖更连续；中国后段把调查、设计和制作结合起来，深度表现方式不同。",
    },
    "science-human-body": {
        "美国": "低年级从感官和健康起步，小学3-5年级进入腺体、激素等人体结构知识。",
        "中国": "幼儿园小班已有生活健康要求，初中7-9年级聚焦食品安全与健康行为。",
        "终局关系": "起步中国早，终局美国更具体。",
        "说明": "中国早期生活化健康要求更早，但美国小学中段的人体结构内容更细；中国初中后段偏行为与安全。",
    },
    "science-earth-space": {
        "美国": "从幼儿园大班天体现象到小学5年级高密度展开，初中8年级讨论日食月食与观测证据。",
        "中国": "小学各学段持续观察，初中7-9年级用板块构造解释火山、地震等现象。",
        "终局关系": "美国覆盖更连续，中国终局偏原理解释。",
        "说明": "美国是现象与观测的长线铺开；中国后段更强调用理论解释现象。",
    },
    "science-weather-water": {
        "美国": "低年级天气现象，小学3年级系统天气因素，6年级进入气候分类。",
        "中国": "幼儿园已有天气感知，小学各段持续，初中7-9年级用气温降水数据描述气候规律。",
        "终局关系": "起步中国早，终局中国覆盖更连续且更数据化。",
        "说明": "中国几乎全学段都有回返，初中以图表和数据归纳规律；美国集中在小学若干节点。",
    },
    "science-inquiry-experiment": {
        "美国": "幼儿园前班起有观察与探究，小学2-5年级持续做调查和工程设计。",
        "中国": "幼儿园起贯穿全学段，小学各学段扩展，初中7-9年级集中实验探究、器材与项目制作。",
        "终局关系": "起步接近，中国后段明显更强。",
        "说明": "这是中国后段覆盖最突出的概念之一：必做实验、器材建议和项目制作把探究落到可操作层面。",
    },
    "geo-map-skills": {
        "美国": "从低年级地图方向到初中8年级继续在历史、区域单元中使用地图信息。",
        "中国": "幼儿园有方位感知，小学低、中、高段都有要求，初中7-9年级系统使用比例尺、图例、方向和经纬度。",
        "终局关系": "起步美国早，终局中国系统地图技能更突出。",
        "说明": "美国很多后段命中嵌在历史内容里；中国把地图作为独立技能链逐步推进。",
    },
    "geo-continents-oceans": {
        "美国": "小学1-3年级认识大洲大洋，初中8年级仍用于区域与历史背景定位。",
        "中国": "初中7-9年级用地图分析大洲位置、热量带、降水、地形与人口经济特征。",
        "终局关系": "起步美国早，终局中国深度明显更高。",
        "说明": "美国后段多是地理常识调用，中国后段进入区域分析；这是首次优势被后续深度反转的典型。",
    },
    "geo-coordinates-earth-motion": {
        "美国": "小学1-6年级逐步认识赤道、半球、时区与国际日期变更线。",
        "中国": "小学5-6年级初步接触，初中7-9年级系统学习经纬线、经纬度定位和分布规律。",
        "终局关系": "起步美国早，终局中国更系统。",
        "说明": "美国的表述更生活化、节点更早；中国把经纬网做成完整定位工具。",
    },
    "geo-physical": {
        "美国": "从小学低年级地形资源常识到初中8年级在区域单元中继续出现。",
        "中国": "小学有零散感知，初中7-9年级集中学习等高线地形图、地形识别和气候影响因素。",
        "终局关系": "阶段接近，中国终局更系统。",
        "说明": "美国多为嵌入历史与地区单元的背景知识；中国后段有明确的地图与原理任务。",
    },
    "geo-human": {
        "美国": "从低年级文化、城市内容到初中8年级全球化、贸易与文化传播，跨度很长。",
        "中国": "初中7-9年级把人口、聚落、区域差异和家乡调查组织成独立主题。",
        "终局关系": "起步美国早且覆盖广，终局中国综合实践更强。",
        "说明": "美国首次优势没有被后续深度抵消，但中国的初中主题更独立、更综合；两边组织形式差异大于阶段差异。",
    },
    "geo-admin-divisions": {
        "美国": "幼儿园大班到小学2年级要求说出所在州，小学2年级知道50州，5年级要求记住50州及州府。",
        "中国": "初中7-9年级要求识别34个省级行政区，并记住简称和行政中心。",
        "终局关系": "起步美国早，终局都是一级行政区的记识，中国更集中。",
        "说明": "这一组可以直接对标：州和省都是一级行政区；美国从学前铺垫到5年级记州府，中国在7-9年级一次完成省级行政区、简称和行政中心。",
    },
    "lang-listen-speak": {
        "美国": "从学前口语互动、课堂讨论到幼儿园大班到初中的讨论规则、口头报告，逐年级连续覆盖。",
        "中国": "学前先抓倾听与日常对话，小学各学段把复述、转述、讨论、即席讲话与主题演讲写成明确目标。",
        "终局关系": "起步接近，双方后段都深但中国表达目标更成文。",
        "说明": "听说两边都贯穿全学段；美国的推进更依赖课堂实践，中国把口语交际写成学段目标，终局可对照。",
    },
    "lang-emergent-literacy": {
        "美国": "从学前印刷品与图书结构意识到K-2年级拼读、解码与朗读流利度，形成系统读写准备。",
        "中国": "学前建立图书与符号兴趣，1-2年级集中识字、写字、拼音与查字典，后段转向独立识字。",
        "终局关系": "功能对标，各自文字系统不同，后段都走向独立读写。",
        "说明": "美国学的是字母拼读，中国学的是汉字与拼音；不能按字面比对，但都是读写入门的核心能力。",
    },
    "lang-reading": {
        "美国": "K年级起朗读复述，3-5年级进入推断、概括与文本证据，6-8年级分析作者意图与观点。",
        "中国": "小学低段朗读理解词句，中段到高段概括、分析、体会表达效果，初中评价与梳理成体系。",
        "终局关系": "起步接近，双方后段都走向文本分析，深度相当。",
        "说明": "阅读理解是两边最可比的能力链：低段都是朗读与复述，高段都是推断、概括与分析评价。",
    },
    "lang-writing": {
        "美国": "学前口述、画图、听写起步，小学到初中完成叙事、说明、议论文与修订。",
        "中国": "学前涂画表达，1-2年级明确写话，中高段到初中完成记实、想象作文、应用文与修改。",
        "终局关系": "中国低段写话更早明确，双方后段都形成完整写作体系。",
        "说明": "写作是功能对标最好的一块：两边都从非文字表达过渡到篇章写作，并在后段加入体裁与修订。",
    },
    "lang-literature": {
        "美国": "从儿歌、韵诗、童话入门，K-8逐步加入诗歌、神话、戏剧、小说与文学术语。",
        "中国": "学前儿歌童谣与听故事，小学到初中加入古诗文背诵、寓言神话、小说散文等体裁。",
        "终局关系": "起步接近，后段体裁都扩展，中国古诗文背诵更突出。",
        "说明": "文学体裁两边都逐学段扩展；中国尤其强调古诗文积累，美国更强调诗歌与小说的读析。",
    },
    "culture-symbols": {
        "美国": "低年级认识国旗、自由女神像与国歌等国家符号，并在历史与音乐单元反复出现。",
        "中国": "学前认识国旗国歌，小学低段在升旗、少先队活动中实践国家象征认知。",
        "终局关系": "功能对标，具体符号不同，起步都早。",
        "说明": "国家符号不宜按具体对象比对，应按“国家认同的共同记忆”功能对照；两边都从低龄开始。",
    },
    "culture-holiday-heritage": {
        "美国": "感恩节、独立日等节日贯穿K-8的历史与文化单元。",
        "中国": "从身边传统节日与风俗体验，到小学“中华优秀传统文化”与初中的文化传承要求。",
        "终局关系": "功能对标，中国后段文化传承更成体系。",
        "说明": "节日内容两边差异很大，应看“借节日做文化传承”这个功能；中国在后段把它写成明确主题。",
    },
    "culture-heritage-stories": {
        "美国": "民间故事、传说、神话与英雄人物在低中段密集出现，作为文化价值载体。",
        "中国": "神话传说、成语故事、寓言与历史故事贯穿小学到初中，传递传统美德与思维方法。",
        "终局关系": "功能对标，中国更强调传统美德与价值观传递。",
        "说明": "故事人物不可直接对照，但“用传统故事传递文化价值”的功能高度可比。",
    },
    "culture-diversity": {
        "美国": "从认识本土部落与多元文化人群，到高年级世界文化与移民、不同信仰的内容。",
        "中国": "学前建立多民族大家庭意识，小学高段到初中由英语与文化课明确世界主要国家与文化多样性。",
        "终局关系": "起步接近，中国后段表述更集中，双方功能可比。",
        "说明": "多元文化理解两边都从低龄起步；美国偏社会文化实景，中国偏文化知识与多民族意识。",
    },
}

# 面向展示的阅读顺序、分组与一句话结论。
# 顺序是人工校对后的叙事顺序，不直接按计算出的首次年级排序。
# 展示轨道全部为实心点，不携带展示/暂存状态。
STORY_META: dict[str, dict[str, Any]] = {
    "math-number-place": {
        "order": 1,
        "group": "数与运算",
        "short": "美国起步早，中国后段更系统；美国跨年级铺得更长。",
    },
    "math-four-operations": {
        "order": 2,
        "group": "数与运算",
        "short": "双方小学低段起步；美国回返更久，中国讲得更集中。",
    },
    "math-geometry": {
        "order": 3,
        "group": "图形与测量",
        "short": "两边都螺旋推进；美国覆盖广，中国初中进入证明体系。",
    },
    "math-measurement": {
        "order": 4,
        "group": "图形与测量",
        "short": "起步接近；美国立体度量更连续，中国后段偏几何推理。",
    },
    "math-fractions-decimals": {
        "order": 5,
        "group": "数的扩展",
        "short": "阶段接近；中国分段清楚，美国从3年级延伸到初中。",
    },
    "math-ratio-percent": {
        "order": 6,
        "group": "数的扩展",
        "short": "起步接近；中国集中在小学高段，美国初中再回返一步。",
    },
    "math-negative-rational": {
        "order": 7,
        "group": "数的扩展",
        "short": "起步接近；中国初中把有理数讲得更系统。",
    },
    "math-equations-algebra": {
        "order": 8,
        "group": "代数与统计",
        "short": "美国铺垫更长；中国初中集中学方程，终局更系统。",
    },
    "math-functions": {
        "order": 9,
        "group": "代数与统计",
        "short": "双方都在初中系统学；中国概念链更完整。",
    },
    "math-statistics": {
        "order": 10,
        "group": "代数与统计",
        "short": "美国从低年级做起；中国初中把抽样、统计和概率组织完整。",
    },
    "science-inquiry-experiment": {
        "order": 1,
        "group": "探究与工程",
        "short": "起步接近；中国后段实验清单更实，美国工程设计更突出。",
    },
    "science-life-genetics": {
        "order": 2,
        "group": "生命科学",
        "short": "中国幼儿园起步早；美国偏进化证据，中国偏显微实验。",
    },
    "science-human-body": {
        "order": 3,
        "group": "生命科学",
        "short": "中国生活健康更早；美国小学人体结构更细。",
    },
    "science-matter": {
        "order": 4,
        "group": "物质与化学",
        "short": "中国生活感知更早；双方初中分科深化。",
    },
    "science-force-motion": {
        "order": 5,
        "group": "运动与能量",
        "short": "美国螺旋更早；中国初中实验化更系统。",
    },
    "science-energy-electricity": {
        "order": 6,
        "group": "运动与能量",
        "short": "中国起步早，美国覆盖连续，中国初中更原理化。",
    },
    "science-ecology-environment": {
        "order": 7,
        "group": "生态与地球",
        "short": "美国起步早；中国后段项目化更突出。",
    },
    "science-earth-space": {
        "order": 8,
        "group": "生态与地球",
        "short": "美国现象铺得长；中国后段偏原理解释。",
    },
    "science-weather-water": {
        "order": 9,
        "group": "生态与地球",
        "short": "中国全学段回返更连续，初中数据化更强。",
    },
    "science-atoms-bonds": {
        "order": 10,
        "group": "物质与化学",
        "short": "阶段接近；中国初中分类框架更完整。",
    },
    "geo-map-skills": {
        "order": 1,
        "group": "地图与定位",
        "short": "美国地图技能更早；中国从方位到初中地图技能成链。",
    },
    "geo-coordinates-earth-motion": {
        "order": 2,
        "group": "地图与定位",
        "short": "美国节点更早；中国初中把经纬网讲成完整工具。",
    },
    "geo-continents-oceans": {
        "order": 3,
        "group": "世界地理",
        "short": "美国常识记忆早；中国初中进入区域分析，深度反超。",
    },
    "geo-physical": {
        "order": 4,
        "group": "自然地理",
        "short": "阶段接近；美国背景式，中国初中成自然地理体系。",
    },
    "geo-human": {
        "order": 5,
        "group": "人文地理",
        "short": "美国起步早且跨度长；中国初中主题更独立综合。",
    },
    "geo-admin-divisions": {
        "order": 6,
        "group": "区域对照",
        "short": "州与省都是一级行政区：美国从学前认识州，中国7-9年级集中学省级行政区与行政中心。",
    },
    "lang-listen-speak": {
        "order": 1,
        "group": "听说与口语",
        "short": "两边都从学前听说起步；美国靠课堂讨论推进，中国把口语交际写成学段目标。",
    },
    "lang-emergent-literacy": {
        "order": 2,
        "group": "识字与读写准备",
        "short": "美国学字母拼读，中国学汉字拼音；文字不同，读写准备的功能一致。",
    },
    "lang-reading": {
        "order": 3,
        "group": "阅读理解",
        "short": "低段都朗读复述，高段都走向推断、概括与分析评价，最容易对标。",
    },
    "lang-writing": {
        "order": 4,
        "group": "写作与表达",
        "short": "都从非文字表达起步；中国低段写话更早明确，后段都形成完整写作体系。",
    },
    "lang-literature": {
        "order": 5,
        "group": "文学与诗歌",
        "short": "体裁都逐学段扩展；中国突出古诗文背诵，美国侧重诗歌小说读析。",
    },
    "culture-symbols": {
        "order": 1,
        "group": "国家认同",
        "short": "国旗国歌功能相同、对象不同；两边都从低龄建立国家共同记忆。",
    },
    "culture-holiday-heritage": {
        "order": 2,
        "group": "文化传承",
        "short": "节日内容不同，但都借节日做文化传承；中国后段更成体系。",
    },
    "culture-heritage-stories": {
        "order": 3,
        "group": "文化传承",
        "short": "传统故事人物不同，都在传递文化价值；中国更强调传统美德。",
    },
    "culture-diversity": {
        "order": 4,
        "group": "多元理解",
        "short": "都从低龄起步；美国偏社会实景，中国偏文化知识与多民族意识。",
    },
}

DEPTH_TERMS = re.compile(
    r"系统|独立|单元|分析|应用|探究|实验|设计|项目|解决|综合|推理|证明|解释|调查|规划|制作|评价"
    r"|investigat|experiment|design|analy|appl|system|solve|model|reason|evaluate",
    re.I,
)
GENERIC_CN_LABELS = {
    "各年级通用（未细分）",
    "小学1-6年级",
    "幼儿园小班/中班/大班（通用）",
}

# Audit exclusions: these source items were repeatedly used as evidence for
# unrelated concepts, or are teaching-method notes rather than content.
AUDIT_GLOBAL_US_EXCLUDE_IDS = {
    "n05047",  # suburban lifestyle in a Cold War unit, not a holiday item
    "n05601",  # French vocabulary list, not speech/debate
    "n02209", "n02210", "n02211", "n02212",  # time measurement in a geometry row
    "n07046",  # square/cube roots in a negative-number row
}
AUDIT_GLOBAL_CN_EXCLUDE_IDS = {
    "hi-j1-tip-c894baac", "hi-j1-tip-b07c731d",  # interdisciplinary pedagogy tips reused in culture rows
    "sc-x2-con-a6f351ee",  # tool use/engineering reused in map, motion and energy rows
    "sc-x3-con-b59a3b7c",  # solar/earth model reused in map and energy rows
    "sc-j1-con-4beb6dd5",  # microscopy reused in geography and body rows
}
AUDIT_US_META_RE = re.compile(
    r"in greater depth and detail in Grade 5|Second grade teachers should examine",
    re.I,
)
US_SHORT_LABELS = {
    "美国幼儿园前班（对应中国小班、中班）": "幼儿园前班",
    "美国幼儿园大班（K）": "幼儿园大班K",
    "美国小学1年级": "小学1年级",
    "美国小学2年级": "小学2年级",
    "美国小学3年级": "小学3年级",
    "美国小学4年级": "小学4年级",
    "美国小学5年级": "小学5年级",
    "美国小学6年级": "小学6年级",
    "美国初中7年级": "初中7年级",
    "美国初中8年级": "初中8年级",
}
CN_SHORT_LABELS = {
    "幼儿园小班（3-4岁）": "小班（3-4岁）",
    "幼儿园中班（4-5岁）": "中班（4-5岁）",
    "幼儿园大班（5-6岁）": "大班（5-6岁）",
    "幼儿园小班/中班/大班（通用）": "幼儿园通用",
    "小学1-2年级": "小学1-2年级",
    "小学3-4年级": "小学3-4年级",
    "小学5-6年级": "小学5-6年级",
    "小学1-6年级": "小学1-6年级",
    "初中7-9年级": "初中7-9年级",
    "各年级通用（未细分）": "全学段通用",
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def clean_text(text: Any, limit: int | None = None) -> str:
    value = " ".join(str(text or "").split())
    if limit is None or len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def cn_grade_label(item: dict[str, Any]) -> str:
    if item.get("stage_key"):
        raw = CN_STAGE_KEY_LABELS.get(item["stage_key"], "各年级通用（未细分）")
    elif item.get("stage"):
        raw = str(item["stage"])
    elif item.get("grade"):
        raw = str(item["grade"])
    else:
        raw = "幼儿园小班/中班/大班（通用）"
    return CN_STAGE_LABELS.get(raw, raw)


def cn_interval(label: str) -> tuple[int, int]:
    return CN_INTERVALS.get(label, (0, 11))


def cn_sort_key(item: dict[str, Any]) -> tuple[int, int, int]:
    label = cn_grade_label(item)
    start, end = cn_interval(label)
    # Grade-unspecified items should never be treated as "earliest".
    unspecified = 1 if label == "各年级通用（未细分）" else 0
    return (unspecified, start, end)


def us_sort_key(item: dict[str, Any]) -> tuple[int, int]:
    return US_INTERVALS.get(item["grade"], (99, 99))


def us_label_interval(label: str) -> tuple[int, int]:
    for key, full_label in US_GRADE_LABELS.items():
        if full_label == label:
            return US_INTERVALS[key]
    return US_INTERVALS.get(label, (99, 99))


def us_short(label: str) -> str:
    if label in US_SHORT_LABELS:
        return US_SHORT_LABELS[label]
    if label in US_GRADE_LABELS:
        return US_SHORT_LABELS.get(US_GRADE_LABELS[label], label)
    return label


def cn_short(label: str) -> str:
    return CN_SHORT_LABELS.get(label, label)


def label_interval(label: str, side: str) -> tuple[int, int]:
    return us_label_interval(label) if side == "美国" else cn_interval(label)


def stage_distribution(items: list[dict[str, Any]], side: str) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for item in items:
        label = (
            US_GRADE_LABELS.get(item["grade"], item["grade"])
            if side == "美国"
            else cn_grade_label(item)
        )
        group = groups.setdefault(label, {"年级": label, "命中": 0, "展示": 0, "暂存": 0})
        group["命中"] += 1
        group[item["status"]] += 1
    return sorted(groups.values(), key=lambda g: label_interval(g["年级"], side))


def format_distribution(distribution: list[dict[str, Any]], side: str) -> str:
    parts: list[str] = []
    for group in distribution:
        label = us_short(group["年级"]) if side == "美国" else cn_short(group["年级"])
        if side == "中国" and group["暂存"]:
            parts.append(
                f"{label} {group['命中']}（展示{group['展示']}/暂存{group['暂存']}）"
            )
        else:
            parts.append(f"{label} {group['命中']}")
    return "；".join(parts) if parts else "无"


US_BAND_BY_GRADE = {
    "Preschool": 0, "K": 0,
    "1": 1, "2": 1,
    "3": 2, "4": 2,
    "5": 3, "6": 3,
    "7": 4, "8": 4,
}
CN_BAND_BY_LABEL = {
    "幼儿园小班（3-4岁）": 0,
    "幼儿园中班（4-5岁）": 0,
    "幼儿园大班（5-6岁）": 0,
    "小学1-2年级": 1,
    "小学3-4年级": 2,
    "小学5-6年级": 3,
    "初中7-9年级": 4,
}
GENERIC_CN_LABELS_FOR_TRACK = {
    "幼儿园小班/中班/大班（通用）",
    "小学1-6年级",
    "各年级通用（未细分）",
}


def us_band(item: dict[str, Any]) -> int | None:
    return US_BAND_BY_GRADE.get(item["grade"])


def cn_band(item: dict[str, Any]) -> int | None:
    label = cn_grade_label(item)
    if label in GENERIC_CN_LABELS_FOR_TRACK:
        return None
    return CN_BAND_BY_LABEL.get(label)


def display_track(distribution: list[dict[str, Any]], side: str) -> list[str]:
    """展示轨道：所有点实心；跨学段通用项不进轨道，避免虚增点数。"""
    result: list[str] = []
    for group in distribution:
        label = group["年级"]
        if side == "中国" and label in GENERIC_CN_LABELS_FOR_TRACK:
            continue
        result.append(us_short(label) if side == "美国" else cn_short(label))
    return result


def later_items(
    hits: list[dict[str, Any]], side: str
) -> list[dict[str, Any]]:
    if not hits:
        return []
    if side == "美国":
        first_start = us_sort_key(hits[0])[0]
        return [item for item in hits if us_sort_key(item)[0] > first_start]
    first_label = cn_grade_label(hits[0])
    if first_label in GENERIC_CN_LABELS:
        return []
    first_start = cn_interval(first_label)[0]
    return [
        item
        for item in hits
        if cn_grade_label(item) not in GENERIC_CN_LABELS
        and cn_interval(cn_grade_label(item))[0] > first_start
    ]


def format_stage_list(items: list[dict[str, Any]], side: str) -> str:
    if not items:
        return "无（止于首次）"
    labels: dict[str, str] = {}
    for item in items:
        label = (
            US_GRADE_LABELS.get(item["grade"], item["grade"])
            if side == "美国"
            else cn_grade_label(item)
        )
        labels.setdefault(label, us_short(label) if side == "美国" else cn_short(label))
    ordered = sorted(labels.items(), key=lambda pair: label_interval(pair[0], side))
    return "、".join(short for _, short in ordered)


def representative_evidence(
    hits: list[dict[str, Any]], side: str, cfg: dict[str, Any]
) -> dict[str, Any] | None:
    pool = later_items(hits, side)
    if not pool:
        return None
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in pool:
        label = (
            US_GRADE_LABELS.get(item["grade"], item["grade"])
            if side == "美国"
            else cn_grade_label(item)
        )
        groups.setdefault(label, []).append(item)
    candidates_labels = [
        label
        for label in groups
        if side == "美国" or label not in GENERIC_CN_LABELS
    ] or list(groups)
    chosen = max(candidates_labels, key=lambda label: label_interval(label, side))
    pattern_text = cfg.get("core_regex") or cfg.get("text_regex")
    pattern = re.compile(pattern_text, re.I) if pattern_text else None

    def score(item: dict[str, Any]) -> tuple[int, int, int]:
        text = str(item.get("text") or "")
        direct = len(pattern.findall(text)) if pattern else 0
        return (direct, len(DEPTH_TERMS.findall(text)), len(text))

    return evidence(max(groups[chosen], key=score), side)


def us_haystack(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key, ""))
        for key in ("topic", "subtopic", "en", "zh")
    )


def cn_haystack(item: dict[str, Any]) -> str:
    parts = [str(item.get(key, "")) for key in ("text", "topic", "domain", "goal", "aspect")]
    ref = item.get("reference") or []
    if isinstance(ref, list):
        parts.extend(str(x) for x in ref)
    return " ".join(parts)


def load_corpus() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    us_raw = load_json(US_PATH)
    us_items: list[dict[str, Any]] = []
    for item in us_raw.get("items", []):
        source = item.get("source") or {}
        us_items.append(
            {
                "id": item.get("uid") or item.get("id"),
                "grade": item.get("grade", ""),
                "subject": item.get("subject", ""),
                "topic": item.get("topic", ""),
                "subtopic": item.get("subtopic", ""),
                "text": item.get("en") or item.get("zh") or "",
                "status": "展示",
                "source": clean_text(f"Core Knowledge Sequence 2023 · {source.get('doc', '')}", 120),
                "source_page": source.get("page"),
                "haystack": us_haystack(item),
            }
        )

    cn_items: list[dict[str, Any]] = []
    source_groups = [
        (CN_PS, "展示"),
        (CN_PS_EXCLUDED, "暂存"),
        (CN_SS, "展示"),
        (CN_SS_EXCLUDED, "暂存"),
    ]
    for path, status in source_groups:
        data = load_json(path)
        rows = data.get("items", data) if isinstance(data, dict) else data
        for item in rows:
            sid = item.get("source_id", "")
            cn_items.append(
                {
                    "id": item.get("uid"),
                    "status": status,
                    "filter_reason": item.get("filter_reason"),
                    "grade": cn_grade_label(item),
                    "subject": item.get("subject") or item.get("domain") or "",
                    "topic": item.get("topic") or item.get("aspect") or "",
                    "text": item.get("text") or item.get("goal") or "",
                    "source": CN_SOURCE_LABELS.get(sid, sid),
                    "source_page": item.get("source_page"),
                    "haystack": cn_haystack(item),
                }
            )
    return us_items, cn_items


def us_matches(item: dict[str, Any], cfg: dict[str, Any]) -> bool:
    if item["subject"] not in cfg["subjects"]:
        return False
    if item["id"] in AUDIT_GLOBAL_US_EXCLUDE_IDS or item["id"] in cfg.get("exclude_ids", ()):
        return False
    if AUDIT_US_META_RE.search(str(item.get("text", ""))):
        return False
    # 语言/文化类簇用 text_only，只匹配条目正文，避免 topic/subtopic 的主题词污染。
    haystack = str(item["text"]) if cfg.get("text_only") else item["haystack"]
    if re.match(r"^(Overview|Teachers):", str(item["text"]).strip(), re.I):
        return False
    if cfg.get("exclude_regex") and re.search(cfg["exclude_regex"], haystack, re.I):
        return False
    if "bands" in cfg and us_band(item) not in cfg["bands"]:
        return False
    if cfg.get("text_only"):
        return bool(re.search(cfg["text_regex"], haystack, re.I))
    topic_ok = bool(re.search(cfg["topic_regex"], item["topic"] + " " + item["subtopic"], re.I))
    text_ok = bool(re.search(cfg["text_regex"], haystack, re.I))
    return topic_ok and text_ok


def cn_matches(item: dict[str, Any], cfg: dict[str, Any]) -> bool:
    if item["id"] in AUDIT_GLOBAL_CN_EXCLUDE_IDS or item["id"] in cfg.get("exclude_ids", ()):
        return False
    # 中国幼儿园“数学认知”在《3-6 岁指南》中归在“科学”领域；
    # 早期数学簇需要用专门规则把它接进来，避免漏掉数数、分合等学前证据。
    preschool_pattern = cfg.get("preschool_regex")
    preschool_math = bool(
        preschool_pattern
        and str(item.get("grade", "")).startswith("幼儿园")
        and item.get("topic") == "数学认知"
    )
    subjects = cfg["subjects"]
    if subjects and item["subject"] not in subjects and not preschool_math:
        return False
    # 语言/文化类簇用 text_only，只匹配条目正文，避免 topic/aspect/domain 的主题词污染。
    haystack = str(item.get("text", "")) if cfg.get("text_only") else item["haystack"]
    if cfg.get("exclude_regex") and re.search(cfg["exclude_regex"], haystack):
        return False
    if "bands" in cfg and cn_band(item) not in cfg["bands"]:
        return False
    if preschool_math:
        # 只看条目标题本身，避免“数量关系”等主题词把所有数学认知条目误命中。
        return bool(re.search(preschool_pattern, str(item.get("text", ""))))
    pattern = cfg.get("text_regex")
    return bool(pattern and re.search(pattern, haystack))


def relation_between(us_first: dict[str, Any] | None, cn_first: dict[str, Any] | None) -> str:
    if not us_first and not cn_first:
        return "两边都未找到证据"
    if not us_first:
        return "本数据中仅中国有"
    if not cn_first:
        return "本数据中仅美国有"
    us_start, us_end = us_sort_key(us_first)
    _, cn_start, cn_end = cn_sort_key(cn_first)
    if us_end >= cn_start and cn_end >= us_start:
        return "两边都有，阶段接近"
    gap = max(cn_start - us_end, us_start - cn_end)
    if gap <= 1:
        return "两边都有，阶段接近"
    if us_end < cn_start:
        return "两边都有，美国更早"
    return "两边都有，中国更早"


def evidence(item: dict[str, Any], side: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "年级": (
            US_GRADE_LABELS.get(item["grade"], item["grade"])
            if side == "美国"
            else item["grade"]
        ),
        "状态": item["status"],
        "来源": item["source"],
        "文本": clean_text(item["text"]),
        "来源条目": item["id"],
    }
    if item.get("source_page") is not None:
        result["来源页"] = item["source_page"]
    if item.get("filter_reason"):
        result["暂存原因"] = item["filter_reason"]
    return result


# 细粒度拆分：每条概念簇最多覆盖 2 个展示学段。
# 继承原簇的匹配规则，仅用 bands 限定具体学段；跨学段通用项不进入展示轨道。
# 顺序在 expand_clusters() 中按原簇顺序与子项顺序统一重排。
SPLIT_SPEC: dict[str, list[dict[str, Any]]] = {
    "math-number-place": [
        {"id": "math-number-early", "concept": "数数、比较与10以内数", "group": "数与运算", "short": "中美都从学前数数起步，中国1-2年级把数的意义讲得更明确。", "us_bands": [0, 1], "cn_bands": [0, 1], "cn_preschool_regex": r"点数|数数|数词|总数|按数取物|一一对应|多少|数的意义|数概念", "cn_preschool_core_regex": r"点数|数数|数词|总数|按数取物"},
        {"id": "math-number-place-value", "concept": "万以内数、位值与十进制", "group": "数与运算", "short": "双方小学中高段建立位值概念，中国分段更明确。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "math-number-rational", "concept": "有理数、实数与数轴", "group": "数的扩展", "short": "初中阶段中国把有理数、实数与数轴系统化。", "us_bands": [4], "cn_bands": [4], "cn_exclude_ids": ["ma-j1-con-1f1ef921"], "cn_core_regex": r"有理数|实数|数轴|负数|相反数|绝对值"},
    ],
    "math-four-operations": [
        {"id": "math-add-sub-early", "concept": "数量分合与10以内加减法", "group": "数与运算", "short": "中美学前已做数量分合，1-2年级继续10以内加减。", "us_bands": [0, 1], "cn_bands": [0, 1], "cn_preschool_regex": r"合在一起|加减运算|分成|分给|[“”]加[“”]|[“”]减[“”]|拿取", "cn_preschool_core_regex": r"合在一起|加减运算|[“”]加[“”]|[“”]减[“”]"},
        {"id": "math-multi-div", "concept": "多位数乘除与四则混合运算", "group": "数与运算", "short": "小学中高段扩展到乘除与混合运算。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "math-rational-operations", "concept": "有理数运算与运算律", "group": "数的扩展", "short": "初中把运算扩展到有理数并总结运算律。", "us_bands": [4], "cn_bands": [4]},
    ],
    "math-fractions-decimals": [
        {"id": "math-fractions-intro", "concept": "分数与小数初步认识", "group": "数的扩展", "short": "双方在小学中段初步认识分数和小数。", "us_bands": [2], "cn_bands": [2], "cn_exclude_ids": ["ma-x2-aca-b84ede75"]},
        {"id": "math-fractions-operations", "concept": "分数小数运算与有理数延伸", "group": "数的扩展", "short": "美国延伸到初中，中国在小学高段集中完成运算。", "us_bands": [3, 4], "cn_bands": [3]},
    ],
    "math-equations-algebra": [
        {"id": "math-algebra-foundations", "concept": "运算关系与字母表示数", "group": "代数与统计", "short": "美国低龄用运算关系铺垫，中国在小学高段引入字母表示数。", "us_bands": [0, 1], "cn_bands": [3]},
        {"id": "math-equations-basic", "concept": "等式性质与一元一次方程", "group": "代数与统计", "short": "3-4年级到5-6年级双方都进入等式与方程。", "us_bands": [2, 3], "cn_bands": [3, 4], "us_text_regex": r"equation|unknown|symbol for the unknown|letter standing|inequality"},
        {"id": "math-equations-advanced", "concept": "方程组、不等式与代数应用", "group": "代数与统计", "short": "初中阶段中国把方程与不等式组织得更系统。", "us_bands": [4], "cn_bands": [4]},
    ],
    "math-geometry": [
        {"id": "math-shapes-early", "concept": "图形辨认与分类", "group": "图形与测量", "short": "中美学前已辨认形状，小学低段继续命名和分类。", "us_bands": [0, 1], "cn_bands": [0, 1], "cn_preschool_regex": r"形状|几何图形|形体结构|图形"},
        {"id": "math-shapes-properties", "concept": "角、三角形与四边形", "group": "图形与测量", "short": "小学中高段进入边、角和常见图形的性质。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "math-geometry-proof", "concept": "图形变换、相似与证明", "group": "图形与测量", "short": "初中阶段中国把定义、性质和证明串成体系。", "us_bands": [4], "cn_bands": [4]},
    ],
    "math-measurement": [
        {"id": "math-measure-early", "concept": "长度、质量与时间等可测量属性", "group": "图形与测量", "short": "中美学前已感知大小、长短和轻重，小学低段引入常用单位。", "us_bands": [0, 1], "cn_bands": [0, 1], "cn_preschool_regex": r"大小|高矮|长短|粗细|厚薄|轻重|量的相对性|测量|多少"},
        {"id": "math-area-perimeter-volume", "concept": "面积、周长与体积", "group": "图形与测量", "short": "小学中高段集中学习面积、周长和体积。", "us_bands": [2, 3], "cn_bands": [2, 3], "us_exclude_ids": ["n02209", "n02210", "n02211", "n02212", "n02213", "n02214", "n02215", "n02216", "n02217", "n02218", "n02219"], "cn_exclude_ids": ["ma-x2-con-cb89f248", "ma-x2-con-0124f5b2"], "cn_core_regex": r"周长|面积|体积"},
        {"id": "math-measure-advanced", "concept": "立体度量与几何应用", "group": "图形与测量", "short": "初中阶段美国继续立体度量，本套中国资料未收同粒度条目。", "us_bands": [4], "cn_bands": [4], "cn_exclude_ids": ["ma-j1-con-78d121e8"]},
    ],
    "math-statistics": [
        {"id": "math-data-early", "concept": "数据分类与简单图表", "group": "代数与统计", "short": "中国学前已有简单记录，小学低段双方继续分类和图表。", "us_bands": [0, 1], "cn_bands": [0, 1], "cn_preschool_regex": r"记录表|统计图|数量关系|记录"},
        {"id": "math-data-basic", "concept": "平均数、可能性与统计图", "group": "代数与统计", "short": "小学中高段学习平均数、统计图和可能性。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "math-statistics-inference", "concept": "抽样、散点图与统计推断", "group": "代数与统计", "short": "初中阶段中国把抽样、数字特征和概率组织完整。", "us_bands": [4], "cn_bands": [4]},
    ],
    "science-matter": [
        {"id": "science-matter-daily", "concept": "溶解、传热等生活现象", "group": "物质与化学", "short": "中国幼儿园和中段已有生活现象感知。", "us_bands": [1], "cn_bands": [0, 1]},
        {"id": "science-matter-properties", "concept": "物质分类与物理变化", "group": "物质与化学", "short": "小学中高段双方都做性质观察和分类。", "us_bands": [3], "cn_bands": [2, 3]},
        {"id": "science-matter-reaction", "concept": "化学反应与质量守恒", "group": "物质与化学", "short": "初中阶段双方进入化学反应与守恒。", "us_bands": [4], "cn_bands": [4]},
    ],
    "science-force-motion": [
        {"id": "science-force-early", "concept": "推拉、磁铁与简单机械", "group": "运动与能量", "short": "低龄和小学低段从推拉、磁铁和简单机械起步。", "us_bands": [0, 1], "cn_bands": [1]},
        {"id": "science-motion-basic", "concept": "运动快慢与力的初步", "group": "运动与能量", "short": "小学中高段开始描述运动快慢和力的作用。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "science-force-advanced", "concept": "摩擦力、浮力与定量探究", "group": "运动与能量", "short": "初中阶段中国把力和运动做成定量实验体系。", "us_bands": [4], "cn_bands": [4]},
    ],
    "science-energy-electricity": [
        {"id": "science-energy-daily", "concept": "光、声、热的生活感知", "group": "运动与能量", "short": "中国幼儿园已有感知，美国小学低段开始系统讲光声。", "us_bands": [1], "cn_bands": [0]},
        {"id": "science-energy-basic", "concept": "能量形式与简单电路", "group": "运动与能量", "short": "小学中高段双方学习能量形式、传热和简单电路。", "us_bands": [2, 3], "cn_bands": [2, 3], "cn_exclude_ids": ["sc-x2-con-a10d38f0", "sc-x3-con-b59a3b7c"]},
        {"id": "science-energy-advanced", "concept": "波、能量转化与守恒", "group": "运动与能量", "short": "初中阶段中国更强调能量转化、守恒和实验。", "us_bands": [4], "cn_bands": [4]},
    ],
    "science-life-genetics": [
        {"id": "science-life-early", "concept": "常见动植物与生长变化", "group": "生命科学", "short": "中国幼儿园已有生命感知，美国小学低段观察动植物。", "us_bands": [1], "cn_bands": [0, 1]},
        {"id": "science-genetics-basic", "concept": "繁殖、遗传与细胞", "group": "生命科学", "short": "小学中高段进入繁殖、遗传和细胞初步。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "science-evolution", "concept": "进化证据与生物分类", "group": "生命科学", "short": "初中阶段美国偏进化证据，中国偏显微观察与分类。", "us_bands": [4], "cn_bands": [4], "us_exclude_ids": ["n05317", "n05324", "n05327"], "us_core_regex": r"evolution|common ancestor|natural selection|fossil|mutation|species"},
    ],
    "science-ecology-environment": [
        {"id": "science-ecology-early", "concept": "动植物与环境", "group": "生态与地球", "short": "低龄和小学低段认识动植物与环境的关系。", "us_bands": [0, 1], "cn_bands": [0, 1]},
        {"id": "science-food-chain", "concept": "食物链与物质循环", "group": "生态与地球", "short": "小学阶段双方学习食物链、栖息地和物质循环。", "us_bands": [2, 3], "cn_bands": [3]},
        {"id": "science-ecology-project", "concept": "生态系统调查与保护", "group": "生态与地球", "short": "初中阶段中国把调查、设计和制作结合起来。", "us_bands": [4], "cn_bands": [4]},
    ],
    "science-human-body": [
        {"id": "science-body-early", "concept": "感官与健康行为", "group": "生命科学", "short": "低龄和小学低段从感官体验和健康行为起步。", "us_bands": [0, 1], "cn_bands": [0, 1]},
        {"id": "science-body-basic", "concept": "身体结构、食品安全与健康管理", "group": "生命科学", "short": "小学中高段到初中，美国讲结构更细，中国偏安全与管理。", "us_bands": [2, 3], "cn_bands": [2, 4]},
    ],
    "science-earth-space": [
        {"id": "science-space-early", "concept": "天体现象观察", "group": "生态与地球", "short": "低龄和小学低段观察日、月、星等天体现象。", "us_bands": [0, 1], "cn_bands": [1], "us_exclude_ids": ["n01708"]},
        {"id": "science-earth-basic", "concept": "太阳系与地球现象", "group": "生态与地球", "short": "小学中高段学习太阳系、地球和地表现象。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "science-earth-advanced", "concept": "板块构造与地质解释", "group": "生态与地球", "short": "初中阶段中国用板块构造解释火山和地震。", "us_bands": [4], "cn_bands": [4], "cn_core_regex": r"板块构造|火山|地震"},
    ],
    "science-weather-water": [
        {"id": "science-weather-early", "concept": "天气与季节感知", "group": "生态与地球", "short": "中国幼儿园已有天气与季节感知，美国从低龄记录天气。", "us_bands": [0], "cn_bands": [0, 1]},
        {"id": "science-water-basic", "concept": "天气数据与水循环", "group": "生态与地球", "short": "小学中高段学习天气因素、降水和水循环。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "science-climate-data", "concept": "气候规律与数据分析", "group": "生态与地球", "short": "初中阶段中国用气温降水数据归纳气候规律。", "us_bands": [], "cn_bands": [4]},
    ],
    "science-inquiry-experiment": [
        {"id": "science-observe", "concept": "观察与简单调查", "group": "探究与工程", "short": "低龄和小学低段以观察、提问和简单调查为主。", "us_bands": [0, 1], "cn_bands": [0, 1]},
        {"id": "science-experiment", "concept": "实验设计与器材使用", "group": "探究与工程", "short": "小学中高段开始设计实验、使用器材和记录证据。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "science-project", "concept": "跨学科项目与工程设计", "group": "探究与工程", "short": "初中阶段中国的必做实验和项目制作更突出。", "us_bands": [], "cn_bands": [4]},
    ],
    "geo-map-skills": [
        {"id": "geo-direction-early", "concept": "方位词与位置", "group": "地图与定位", "short": "中国幼儿园从上下前后里外起步，美国低龄开始定位。", "us_bands": [0], "cn_bands": [0]},
        {"id": "geo-map-basic", "concept": "地图图例与方向", "group": "地图与定位", "short": "小学阶段双方学习图例、方向和简单地图阅读。", "us_bands": [1, 2], "cn_bands": [2]},
        {"id": "geo-map-advanced", "concept": "比例尺与区域地图应用", "group": "地图与定位", "short": "小学高段到初中，中国把比例尺和经纬网做成技能链。", "us_bands": [3, 4], "cn_bands": [3, 4], "cn_exclude_ids": ["sc-x3-con-bdce7510", "sc-x3-con-b59a3b7c", "ge-j1-con-459f1b15", "ge-j1-con-1e079e79", "ge-j1-con-5f8d68c4", "ge-j1-con-bd667659"], "cn_core_regex": r"比例尺|图例|经纬|量距|坐标|直线距离"},
    ],
    "geo-continents-oceans": [
        {"id": "geo-continents-basic", "concept": "大洲大洋与国家常识", "group": "世界地理", "short": "美国小学低中段以大洲大洋和国家名称为主。", "us_bands": [1, 2], "cn_bands": []},
        {"id": "geo-continents-analysis", "concept": "世界区域定位与分析", "group": "世界地理", "short": "初中阶段中国用地图分析大洲位置、气候与人口经济。", "us_bands": [3, 4], "cn_bands": [4]},
    ],
    "geo-coordinates-earth-motion": [
        {"id": "geo-hemisphere", "concept": "赤道、半球与时区", "group": "地图与定位", "short": "美国小学低中段以赤道、半球和时区的生活化认识为主。", "us_bands": [1, 2], "cn_bands": []},
        {"id": "geo-coordinates", "concept": "经纬网定位与地球运动", "group": "地图与定位", "short": "小学高段到初中，中国把经纬网和地球运动讲成体系。", "us_bands": [3], "cn_bands": [3, 4]},
    ],
    "geo-physical": [
        {"id": "geo-land-basic", "concept": "地形与自然资源常识", "group": "自然地理", "short": "小学低中段双方接触地形、河流和自然资源常识。", "us_bands": [1, 2], "cn_bands": [1, 2]},
        {"id": "geo-physical-analysis", "concept": "气候、河流与区域自然地理", "group": "自然地理", "short": "小学高段到初中，中国用等高线和气候因素做区域分析。", "us_bands": [3, 4], "cn_bands": [4]},
    ],
    "geo-human": [
        {"id": "geo-culture-basic", "concept": "文化、城市与区域常识", "group": "人文地理", "short": "美国低龄和小学低段把文化、城市内容嵌在历史单元里。", "us_bands": [0, 1], "cn_bands": []},
        {"id": "geo-population", "concept": "人口、聚落与迁移", "group": "人文地理", "short": "小学5-6年级美国持续出现人口、移民和城市内容。", "us_bands": [2, 3], "cn_bands": [], "us_exclude_ids": ["n02038", "n02514", "n02579", "n03219", "n04156", "n03247"], "us_text_regex": r"population|immigrant|immigration|migration|urban|settlement|cities|city life"},
        {"id": "geo-region-development", "concept": "全球化、区域发展与家乡调查", "group": "人文地理", "short": "初中阶段中国把人口、聚落和区域发展组织成独立主题。", "us_bands": [4], "cn_bands": [4]},
    ],
    "geo-admin-divisions": [
        {"id": "geo-admin-basic", "concept": "州与省：层级识别", "group": "区域对照", "short": "美国学前和1-2年级认识所在州，中国7-9年级识别省级行政区。", "us_bands": [0, 1], "cn_bands": [4]},
        {"id": "geo-admin-capitals", "concept": "州府与省会：名称与行政中心", "group": "区域对照", "short": "美国5-6年级记50州及州府，中国7-9年级记省级行政区简称和行政中心。", "us_bands": [3], "cn_bands": [4]},
    ],
    "lang-listen-speak": [
        {"id": "lang-listen-early", "concept": "听懂日常语言与对话", "group": "听说与口语", "short": "中美学前都从听懂指令、日常对话与礼貌表达起步。", "us_bands": [0, 1], "cn_bands": [0, 1],
         "us_text_regex": r"\blisten|listening|\bspeak|speaking|conversation|dialogue|oral language|respond|talk about",
         "cn_text_regex": r"注意听|听懂|倾听|交谈|对话|讲述|口语|回应|说话|普通话|大声说|礼貌用语"},
        {"id": "lang-listen-mid", "concept": "课堂讨论与复述转述", "group": "听说与口语", "short": "小学中高段，双方都要求课堂讨论、复述与转述。", "us_bands": [2, 3], "cn_bands": [2, 3],
         "us_text_regex": r"discussion|discuss|retell|recount|summarize.*oral|respond",
         "cn_text_regex": r"交流|讨论|复述|转述|讲述.*见闻|朗读|发言"},
        {"id": "lang-listen-late", "concept": "演讲、辩论与观点表达", "group": "听说与口语", "short": "初中阶段，双方都要求即席讲话、主题演讲与有观点的表达。", "us_bands": [4], "cn_bands": [4],
         "us_text_regex": r"\bdebate|oral presentation|defend.*position|state.*view|speech",
         "cn_text_regex": r"演讲|即席讲话|有准备.*发言|讨论问题|发表自己的看法|观点"},
    ],
    "lang-emergent-literacy": [
        {"id": "lang-literacy-early", "concept": "图书、符号与书写准备", "group": "识字与读写准备", "short": "学前到1-2年级，双方建立图书、符号意识与书写准备。", "us_bands": [0, 1], "cn_bands": [0, 1],
         "us_text_regex": r"print awareness|identify.*print|letter|phoneme|phonics|blend|book.*cover|turn.*page|rhyming",
         "cn_text_regex": r"图书|画册|标记|符号|笔画|汉字|拼音|认读|写字|翻书|涂涂|画画"},
        {"id": "lang-decode-characters", "concept": "拼读解码与识字写字", "group": "识字与读写准备", "short": "小学低中段，美国练拼读解码，中国练识字写字与查字典。", "us_bands": [1, 2], "cn_bands": [1, 2],
         "us_text_regex": r"decod|sight word|blend.*sound|read.*word|fluen",
         "cn_text_regex": r"识字|写字|拼音|汉字|笔画|部首|查字典|认识常用汉字"},
    ],
    "lang-reading": [
        {"id": "lang-reading-basic", "concept": "朗读、理解与复述", "group": "阅读理解", "short": "小学低中段，双方都从朗读、理解内容到复述故事。", "us_bands": [1, 2], "cn_bands": [1, 2],
         "us_text_regex": r"\bretell|read aloud|comprehension|describe characters|understand.*text",
         "cn_text_regex": r"朗读|默读|课文|词句|阅读|理解.*内容|复述"},
        {"id": "lang-reading-analysis", "concept": "推断、概括与文本分析", "group": "阅读理解", "short": "小学高段到初中，双方都进入推断、概括、证据与评价。", "us_bands": [3, 4], "cn_bands": [3, 4],
         "us_text_regex": r"infer|summariz|main idea|text evidence|analyz|interpret|evaluate|author.*purpose|point of view",
         "cn_text_regex": r"概括.*内容|分析主要内容|推想.*词句|思想感情|评价.*作品|揣摩|品味.*语言|领悟.*表达方法|区分观点与材料|作出自己的判断|理清思路"},
    ],
    "lang-writing": [
        {"id": "lang-writing-early", "concept": "涂画、口述与写话起步", "group": "写作与表达", "short": "学前到1-2年级，双方从涂画口述过渡到写话与短句。", "us_bands": [0, 1], "cn_bands": [0, 1],
         "us_text_regex": r"dictate|caption|draw.*represent|write.*letter|label.*picture|copy.*letter",
         "cn_text_regex": r"写自己的|愿意写|写话|涂涂|画画|口述|画.*表示|写写画画"},
        {"id": "lang-writing-composition", "concept": "篇章写作、体裁与修改", "group": "写作与表达", "short": "小学高段到初中，双方完成叙事、说明、议论文与修订。", "us_bands": [3, 4], "cn_bands": [3, 4],
         "us_text_regex": r"narrative|essay|draft|revise|paragraph|composition|write.*story|persuasive|expository",
         "cn_text_regex": r"习作|作文|记实|想象作文|读书笔记|应用文|修改.*习作|分段表述"},
    ],
    "lang-literature": [
        {"id": "lang-poetry-early", "concept": "儿歌、童谣与故事入门", "group": "文学与诗歌", "short": "学前到1-2年级，双方用儿歌、韵诗、童话与故事入门。", "us_bands": [0, 1], "cn_bands": [0, 1],
         "us_text_regex": r"nursery rhyme|fairy tale|poem|rhyming|storybook",
         "cn_text_regex": r"儿歌|童谣|古诗|童话|故事|寓言|复述"},
        {"id": "lang-genre-study", "concept": "诗歌、神话与小说戏剧", "group": "文学与诗歌", "short": "小学中高段，体裁扩展到诗歌、神话、小说、散文与戏剧。", "us_bands": [2, 3], "cn_bands": [2, 3],
         "us_text_regex": r"\bpoetry|fiction|myth|legend|literary|drama|novel|fable",
         "cn_text_regex": r"古诗|诗文|寓言|神话|小说|散文|背诵|文学|叙事性作品"},
    ],
    "culture-symbols": [
        {"id": "culture-symbols-early", "concept": "国旗、国歌与国家象征", "group": "国家认同", "short": "低龄认识国旗国歌等国家符号，中国还结合升旗仪式实践。", "us_bands": [0, 1], "cn_bands": [0, 1],
         "us_text_regex": r"American flag|Statue of Liberty|national anthem|national symbol|Stars and Stripes|bald eagle",
         "cn_text_regex": r"国旗|国歌|国徽|国家象征|红领巾|升旗"},
    ],
    "culture-holiday-heritage": [
        {"id": "culture-holiday-mid", "concept": "节日、庆典与风俗体验", "group": "文化传承", "short": "小学中高段，美国记节日庆典，中国体验传统节日与风俗。", "us_bands": [2, 4], "cn_bands": [2, 4],
         "us_text_regex": r"Thanksgiving|Independence Day|Columbus Day|Christmas|holiday|celebration|festival|National holiday",
         "cn_text_regex": r"传统节日|节日|风俗|文化体验|风土人情|中华优秀传统文化|习俗"},
    ],
    "culture-heritage-stories": [
        {"id": "culture-stories-mid", "concept": "神话、传说与传统故事", "group": "文化传承", "short": "小学低中段，双方用民间故事、神话传说传递文化价值。", "us_bands": [1, 2], "cn_bands": [1, 2],
         "us_text_regex": r"folktale|fairy tale|\bfable|legend|myth|Paul Bunyan|John Henry|\bhero",
         "cn_text_regex": r"神话|传说|成语故事|民间故事|寓言|传统美德|历史故事|智慧"},
        {"id": "culture-heritage-late", "concept": "英雄、传统与文化传承", "group": "文化传承", "short": "小学高段到初中，美国讲英雄与遗产，中国强调传统文化与自信。", "us_bands": [3, 4], "cn_bands": [3, 4],
         "us_text_regex": r"\bhero|ancient civilization|heritage|tradition|\bmyth|folk hero|cultural heritage",
         "cn_text_regex": r"传统文化|文化遗产|传统美德|中华优秀|文化自信|感悟.*文化",
         "us_exclude_ids": ["n03055", "n03485", "n05452"]},
    ],
    "culture-diversity": [
        {"id": "culture-diversity-early", "concept": "本民族与多元人群", "group": "多元理解", "short": "低龄认识本土部落、多民族大家庭与相互尊重。", "us_bands": [0, 1], "cn_bands": [0, 1],
         "us_text_regex": r"Native American|ways of life|cultural diversity|different Native American|tribe or nation|different faiths",
         "cn_text_regex": r"自己的民族|多民族|各民族|互相尊重|不同.*民族"},
        {"id": "culture-diversity-world", "concept": "世界文化与中外差异", "group": "多元理解", "short": "小学高段到初中，双方扩展到世界主要国家与文化多样性。", "us_bands": [3, 4], "cn_bands": [3, 4],
         "us_text_regex": r"multicultural|world culture|immigrant|heritage|other countries|different cultures",
         "cn_text_regex": r"世界主要国家|文化多样|中外文化|文化习俗|国际理解|各国",
         "us_exclude_ids": ["n03350", "n03353", "n04156"]},
    ],
}

# 微指标层：人工挑选、可直接核对原文的能力点。
# 证据按来源条目 ID 定位；展示轨道仍按现有口径最多两个学段，深度按参数逐项列出。
MICRO_CLAIMS: list[dict[str, Any]] = [
    {
        "id": "micro-motor-hop", "domain": "儿童发展", "order": 1,
        "concept": "单脚连续向前跳", "group": "动作与平衡",
        "short": "中国写成小班2米、中班5米、大班8米的递进，美国只列动作形式，不设距离。",
        "us_bands": [0], "cn_bands": [0],
        "us_evidence": ["n00006"],
        "cn_evidence": ["ps-h-a2-g2-x-03", "ps-h-a2-g2-z-03", "ps-h-a2-g2-d-03"],
        "axes": [
            ["量化阈值", "无距离要求", "2米 → 5米 → 8米"],
            ["年级递进", "学前一条目标", "小班 / 中班 / 大班三级"],
            ["场景条件", "有或无障碍物，避免碰撞", "向前连续跳（直线）"],
            ["动作形式", "单脚跳或双脚交替", "单脚连续"],
        ],
        "emphasis": "中国有量化递进",
        "note": "两边都在学前出现单脚跳；差别不在“有没有”，而在中国把距离写成可测的小中大递进，美国只描述动作方式。",
    },
    {
        "id": "micro-motor-signal", "domain": "儿童发展", "order": 2,
        "concept": "按信号停止或开始动作", "group": "动作与平衡",
        "short": "同为听信号做动作，美国放在学前运动目标，中国放到小学体育的反应能力训练。",
        "us_bands": [0], "cn_bands": [2, 4],
        "us_evidence": ["n00001"],
        "cn_evidence": ["pe-x2-con-33c71382", "pe-x3-con-4df653fd", "pe-j1-con-784b5c3a"],
        "axes": [
            ["首次年级", "幼儿园前班", "小学中段（3-4年级）"],
            ["信号类型", "开始 / 停止", "正反口令、变向口令"],
            ["年级递进", "学前一条", "3-4 → 5-6 → 7-9 年级逐级"],
            ["动作难度", "走跑跳等基本动作", "变向跑、起动与制动、追逐跑"],
        ],
        "emphasis": "美国更早，中国后段成体系",
        "note": "中国学前的“听从长辈要求”属于社会性服从，不是同一功能，另列在“执行单步口头指令”；这里只比对运动信号反应。",
    },
    {
        "id": "micro-motor-stairs", "domain": "儿童发展", "order": 3,
        "concept": "双脚交替上下楼梯", "group": "动作与平衡",
        "short": "两边都写在学前，中国额外要求“灵活”，美国只要求交替。",
        "us_bands": [0], "cn_bands": [0],
        "us_evidence": ["n00002"],
        "cn_evidence": ["ps-h-a2-g1-x-02"],
        "axes": [
            ["动作要求", "上、下楼梯交替双脚", "双脚灵活交替上下楼梯"],
            ["流畅度", "无明确要求", "明确要求“灵活”"],
            ["递进", "学前一条", "小班一条，后段未单列"],
            ["量化", "无", "无"],
        ],
        "emphasis": "中国多一项流畅度要求",
        "note": "这是同一动作的近距离对照：功能相同，主要差别在中国把“灵活”写进目标措辞。",
    },
    {
        "id": "micro-motor-balance", "domain": "儿童发展", "order": 4,
        "concept": "平衡：变换姿势与窄道行走", "group": "动作与平衡",
        "short": "美国停在原地与宽平衡木，中国从直线走到斜坡、荡桥和间隔物体。",
        "us_bands": [0], "cn_bands": [0],
        "us_evidence": ["n00003", "n00004"],
        "cn_evidence": ["ps-h-a2-g1-x-01", "ps-h-a2-g1-z-01", "ps-h-a2-g1-d-01"],
        "axes": [
            ["条件递进", "原地变换姿势 → 宽平衡木", "地面直线 → 窄低物体 → 斜坡荡桥"],
            ["表面宽度", "宽 bench / beam", "较窄、有一定间隔"],
            ["量化", "无距离", "均为“一段距离”，无米数"],
            ["进阶层级", "两条学前目标", "小 / 中 / 大班三级"],
        ],
        "emphasis": "中国场景递进更清楚",
        "note": "同属学前平衡能力；差别在中国把支撑面从宽到窄逐级收紧，美国只给出两个并列条件。",
    },
    {
        "id": "micro-motor-throw", "domain": "儿童发展", "order": 5,
        "concept": "定向投掷与投准", "group": "投掷与协调",
        "short": "中国给出2米、4米、5米的投掷距离，美国强调按指示方向和逐渐提高的准确度。",
        "us_bands": [0], "cn_bands": [0],
        "us_evidence": ["n00008", "n07200"],
        "cn_evidence": ["ps-h-a2-g2-x-02", "ps-h-a2-g2-z-02", "ps-h-a2-g2-d-02"],
        "axes": [
            ["量化阈值", "无距离", "2米 → 4米 → 5米"],
            ["精度要求", "“increasing accuracy”", "以距离为指标"],
            ["目标设置", "高度和距离不同的靶", "向前投掷沙包"],
            ["年级递进", "两条学前目标", "小班 / 中班 / 大班三级"],
        ],
        "emphasis": "两边深度维度不同",
        "note": "不能只说“都练投掷”：美国写的是按指示方向与靶位准确度，中国写的是可测距离递进。",
    },
    {
        "id": "micro-motor-catch", "domain": "儿童发展", "order": 6,
        "concept": "抛接球与接物", "group": "投掷与协调",
        "short": "美国把双人接豆袋的距离写成1.5英尺，中国写成自抛自接、连续拍球的递进。",
        "us_bands": [0], "cn_bands": [0],
        "us_evidence": ["n00009"],
        "cn_evidence": ["ps-h-a2-g1-x-05", "ps-h-a2-g1-z-05", "ps-h-a2-g1-d-05"],
        "axes": [
            ["互动形式", "成人与幼儿对接", "向上抛球 → 自抛自接 → 连续拍球"],
            ["量化", "相距1.5英尺", "无距离，以连续性要求递进"],
            ["递进", "学前一条", "小 / 中 / 大班三级"],
            ["对象", "豆袋", "球"],
        ],
        "emphasis": "美国有距离，中国有连续性递进",
        "note": "两边都从学前做接物，但深度写在不同参数上：美国量化空间，中国量化动作连续性。",
    },
    {
        "id": "micro-motor-rules", "domain": "儿童发展", "order": 7,
        "concept": "遵守游戏规则与轮流", "group": "常规与协作",
        "short": "美国从遵守简单游戏规则起步，中国从提醒下遵守写到理解并共同制定规则。",
        "us_bands": [0], "cn_bands": [0],
        "us_evidence": ["n00035", "n00031", "n00011"],
        "cn_evidence": ["ps-s-a2-g2-x-01", "ps-s-a2-g2-z-01", "ps-s-a2-g2-d-01"],
        "axes": [
            ["规则来源", "既有简单游戏规则", "遵守 → 理解意义 → 与同伴协商制定"],
            ["递进", "学前并列目标", "小班 / 中班 / 大班三级"],
            ["成人提示", "未分层", "提醒下 → 基本遵守 → 自主协商"],
            ["轮流要求", "wait turn to speak", "对大家都喜欢的东西能轮流、分享"],
        ],
        "emphasis": "中国有规则内化递进",
        "note": "中国的目标从“他律”走向“共制规则”，美国在学前阶段主要列遵守与轮流行为。",
    },
    {
        "id": "micro-motor-calm", "domain": "儿童发展", "order": 8,
        "concept": "从兴奋转为平静", "group": "常规与协作",
        "short": "美国把它写成身体放松动作，中国写成情绪识别与缓解的三级递进。",
        "us_bands": [0], "cn_bands": [0],
        "us_evidence": ["n00007"],
        "cn_evidence": ["ps-h-a1-g2-x-02", "ps-h-a1-g2-z-02", "ps-h-a1-g2-d-01", "ps-h-a1-g2-d-02"],
        "axes": [
            ["机制", "放松肌肉，从高活动转安静专注", "识别情绪原因并努力缓解"],
            ["成人支持", "未分层", "安抚 → 提醒 → 自主缓解"],
            ["递进", "学前一条", "小 / 中 / 大班三级"],
            ["输出", "身体状态", "情绪表达适度、随活动需要转换"],
        ],
        "emphasis": "功能接近，机制不同",
        "note": "这是跨领域的近似对标：同是“从激动到平静”，美国落在身体调节策略，中国落在情绪认知与社会性。",
    },
    {
        "id": "micro-routine-sleep", "domain": "儿童发展", "order": 1,
        "concept": "每天睡眠时长与午睡", "group": "睡眠与照护",
        "short": "中国明确每天11-12小时、午睡约2小时；美国文件不规定作息。",
        "us_bands": [], "cn_bands": [0],
        "us_evidence": [],
        "cn_evidence": ["ps-h-a1-g1-s-02", "ps-h-a3-g1-x-01", "ps-h-a3-g1-z-01"],
        "axes": [
            ["量化阈值", "无对应条目", "每天11～12小时，午睡约2小时"],
            ["起始年级", "—", "小班：提醒下按时睡起并坚持午睡"],
            ["递进", "—", "中班：每天按时睡觉起床并坚持午睡"],
            ["文件口径", "学科内容序列", "发展指标 + 教育建议"],
        ],
        "emphasis": "仅中国有，属文件类型差异",
        "flag": "仅中国有 · 文件类型差异，不做能力高低判断",
        "note": "不能解释成美国不要求午睡；两套文件管的事不同，一份列学科内容，一份列发展与生活指标。",
    },
    {
        "id": "micro-routine-hygiene", "domain": "儿童发展", "order": 2,
        "concept": "洗手、刷牙与餐桌礼仪", "group": "卫生与自理",
        "short": "美国把洗手和餐桌礼仪并列成一条，中国把洗手刷牙写成三级递进。",
        "us_bands": [0], "cn_bands": [0],
        "us_evidence": ["n00025"],
        "cn_evidence": ["ps-h-a3-g1-x-06", "ps-h-a3-g1-z-06", "ps-h-a3-g1-d-06"],
        "axes": [
            ["频次", "未量化", "每天早晚刷牙、饭前便后洗手"],
            ["递进", "学前一条综合目标", "提醒下 → 方法基本正确 → 主动且正确"],
            ["范围", "如厕、洗手、餐具与餐巾", "刷牙、洗手"],
            ["自主性", "independent / appropriate", "在提醒下 → 主动"],
        ],
        "emphasis": "中国有频次与主动性递进",
        "note": "两边都从学前要求个人卫生；美国的条目把如厕、洗手、餐具使用放在同一条，中国则按年龄细化方法与主动性。",
    },
    {
        "id": "micro-routine-screen", "domain": "儿童发展", "order": 3,
        "concept": "连续看电视的时长上限", "group": "睡眠与照护",
        "short": "中国给出15、20、30分钟的年龄上限，美国文件没有屏幕时长条目。",
        "us_bands": [], "cn_bands": [0],
        "us_evidence": [],
        "cn_evidence": ["ps-h-a3-g1-x-05", "ps-h-a3-g1-z-05", "ps-h-a3-g1-d-05"],
        "axes": [
            ["量化阈值", "无对应条目", "小班15 / 中班20 / 大班30分钟"],
            ["递进", "—", "年龄越大上限越高"],
            ["配套要求", "—", "不在光线过强或过暗处看书"],
            ["文件口径", "学科内容序列", "发展指标 + 教育建议"],
        ],
        "emphasis": "仅中国有，属文件类型差异",
        "flag": "仅中国有 · 文件类型差异，不做能力高低判断",
        "note": "与睡眠条目同类：这是照护指标而非学科知识点，单列是为了呈现文件管辖范围不同。",
    },
    {
        "id": "micro-routine-selfcare", "domain": "儿童发展", "order": 4,
        "concept": "穿脱衣物与物品归位", "group": "卫生与自理",
        "short": "美国只要求用后归位，中国从穿脱鞋袜写到系鞋带和按类别整理。",
        "us_bands": [0], "cn_bands": [0],
        "us_evidence": ["n00041"],
        "cn_evidence": ["ps-h-a3-g2-x-01", "ps-h-a3-g2-z-01", "ps-h-a3-g2-d-02", "ps-h-a3-g2-x-02", "ps-h-a3-g2-z-02", "ps-h-a3-g2-d-03"],
        "axes": [
            ["穿衣技能", "无", "帮助下穿脱 → 自己穿脱扣钮扣 → 系鞋带"],
            ["整理技能", "玩具与材料用后归位", "放回原处 → 整理物品 → 按类别整理"],
            ["递进", "学前一条", "小 / 中 / 大班三级"],
            ["自主性", "after use", "在帮助下 → 自己 → 按类别"],
        ],
        "emphasis": "中国自理技能链更完整",
        "note": "两边都有“用后归位”；中国另把穿衣与整理拆成可观察的分龄技能，美国只在学前工作习惯中列一条。",
    },
    {
        "id": "micro-routine-safety", "domain": "儿童发展", "order": 5,
        "concept": "不跟陌生人走与求助信息", "group": "安全与求助",
        "short": "美国要求记住姓名、地址和电话，中国把行为规则、求助方式和防灾知识分层写出。",
        "us_bands": [0], "cn_bands": [0],
        "us_evidence": ["n07203"],
        "cn_evidence": ["ps-h-a3-g3-x-01", "ps-h-a3-g3-x-03", "ps-h-a3-g3-z-04", "ps-h-a3-g3-d-01"],
        "axes": [
            ["能力类型", "记忆个人信息", "行为规则 + 求助方式 + 防灾知识"],
            ["递进", "一条 Level II 目标", "小班 → 中班 → 大班三级"],
            ["信息内容", "地址、电话、出生日期", "自己和家长的名字、电话号码"],
            ["情境", "未限定", "陌生人、公共场所走失、开门、防灾"],
        ],
        "emphasis": "中国情境更具体",
        "note": "两边都涉及“走失时能说出信息”，但中国把它嵌在陌生人、走失和开门等具体情境中。",
    },
    {
        "id": "micro-arts-movement", "domain": "艺术", "order": 1,
        "concept": "随音乐做动作与节奏精度", "group": "音乐与律动",
        "short": "美国K-2三年重复同一条动作目标，中国从跟随动作走到基本准确的节奏与音调。",
        "us_bands": [0, 1], "cn_bands": [0],
        "us_evidence": ["n00497", "n01001", "n01559"],
        "cn_evidence": ["ps-a-a2-g2-x-02", "ps-a-a2-g2-z-03", "ps-a-a2-g2-d-01"],
        "axes": [
            ["年级递进", "K / 1 / 2 年级目标文字相同", "小班 → 中班 → 大班，逐年提高"],
            ["精度要求", "无准确度要求", "大班要求基本准确的节奏和音调"],
            ["输出形式", "行进、走、单脚跳、摇摆", "身体动作、拍手踏脚、敲击、唱歌、律动"],
            ["条件", "随音乐做相应动作", "熟悉音乐 → 基本节奏 → 表现情绪或情景"],
        ],
        "emphasis": "中国有精度递进",
        "note": "同是“随音乐动起来”，差别在美国把同一目标连续三年重复，中国把它拆成动作、节拍、音准的递进。",
    },
    {
        "id": "micro-arts-visual", "domain": "艺术", "order": 2,
        "concept": "线条与色彩：名作欣赏 vs 自由表现", "group": "美术与创造",
        "short": "美国K起认线条色彩和名家作品，中国指南强调不设范画、画自己想画的人或事物。",
        "us_bands": [0], "cn_bands": [0],
        "us_evidence": ["n00455", "n00465", "n00473"],
        "cn_evidence": ["ps-a-a2-g2-x-04", "ps-a-a2-g2-s-05"],
        "axes": [
            ["学习目标", "识别并使用线条、色彩；认识作品", "用线条色彩画出自己想画的人或事物"],
            ["作品角色", "名作与艺术家是教学内容", "不宜提供范画，不要求照画"],
            ["起始年级", "幼儿园（K）", "小班（3-4岁）"],
            ["输出", "观察、讨论、使用形式要素", "涂画、粘贴、手工表现所见所想"],
        ],
        "emphasis": "功能不同：欣赏知识 vs 自由表现",
        "note": "两边都从线条色彩起步，但美国把作品与艺术家当知识内容，中国把“不设范画”当教学原则。",
    },
    {
        "id": "micro-arts-singing", "domain": "艺术", "order": 3,
        "concept": "唱短歌与音准", "group": "音乐与律动",
        "short": "美国K-2以无伴奏、伴奏与齐唱为主，中国从模仿学唱走到基本准确的节奏和音调。",
        "us_bands": [0, 1], "cn_bands": [0],
        "us_evidence": ["n00506", "n01015", "n01575"],
        "cn_evidence": ["ps-a-a2-g2-x-01", "ps-a-a2-g2-z-01", "ps-a-a2-g2-d-01"],
        "axes": [
            ["年级递进", "K / 1 / 2 年级同一条", "模仿学唱 → 音量适中基本准确 → 节奏音调基本准确"],
            ["精度要求", "未写音准", "中班起出现“基本准确”"],
            ["组织形式", "无伴奏、伴奏、齐唱", "模仿、自哼自唱、即兴编词"],
            ["起始年级", "幼儿园（K）", "小班（3-4岁）"],
        ],
        "emphasis": "中国有准确度递进",
        "note": "美国重复演唱形式，中国把“准确”作为可进阶的目标，这是同一主题下深度写法的差别。",
    },
    {
        "id": "micro-arts-rhythm", "domain": "艺术", "order": 4,
        "concept": "稳定节拍与敲打节奏", "group": "音乐与律动",
        "short": "美国K起就认拍并尝试打拍，中国到中班才要求用身体或物品敲出基本节奏。",
        "us_bands": [0, 1], "cn_bands": [0],
        "us_evidence": ["n00495", "n01000", "n01558"],
        "cn_evidence": ["ps-a-a2-g2-z-03", "ps-a-a2-g2-d-01"],
        "axes": [
            ["起始时间", "幼儿园（K）", "中班（4-5岁）"],
            ["工具", "未指定，play a steady beat", "拍手、踏脚或可敲击物品"],
            ["递进", "K 认拍并尝试 → 1-2年级延续", "敲打基本节奏 → 基本准确的节奏"],
            ["精度", "无“准确”表述", "大班出现“基本准确”"],
        ],
        "emphasis": "美国更早，中国工具更具体",
        "note": "两边都练稳定拍；美国起步早且不指定工具，中国起步稍晚但把身体动作和打击物写清楚。",
    },
    {
        "id": "micro-arts-appreciation", "domain": "艺术", "order": 5,
        "concept": "欣赏作品并表达理解", "group": "美术与创造",
        "short": "美国让学生谈第一印象、细节和创作意图，中国要求用表情、动作、语言表达理解。",
        "us_bands": [0, 1], "cn_bands": [0],
        "us_evidence": ["n00473"],
        "cn_evidence": ["ps-a-a1-g2-x-02", "ps-a-a1-g2-z-02", "ps-a-a1-g2-d-01"],
        "axes": [
            ["对象", "具体绘画作品与艺术家", "绘画、泥塑及多种艺术形式"],
            ["表达方式", "语言讨论：第一印象、细节、为何这样画", "表情、动作、语言；联想与情绪反应"],
            ["递进", "K 起观察与讨论", "小班观看 → 中班联想 → 大班表达理解"],
            ["知识要求", "认识线条、色彩等要素", "未要求形式术语"],
        ],
        "emphasis": "表达通道不同",
        "note": "同为“看懂作品并说出来”，美国偏语言化的作品分析，中国允许表情与动作，并强调联想和情绪。",
    },
    {
        "id": "micro-arts-drama", "domain": "艺术", "order": 6,
        "concept": "角色扮演与自编自演", "group": "表演与戏剧",
        "short": "美国从简单哑剧和团体游戏入门，中国到大班要求自编自演并搭配服饰道具布景。",
        "us_bands": [0, 1], "cn_bands": [0],
        "us_evidence": ["n00013", "n00011", "n01029"],
        "cn_evidence": ["ps-a-a2-g1-z-01", "ps-a-a2-g2-d-03"],
        "axes": [
            ["形式", "哑剧、团体游戏、歌剧概念", "歌唱律动舞蹈表演 → 自编自演故事"],
            ["产出", "模仿动作与扮演", "选择搭配服饰、道具或布景"],
            ["递进", "学前哑剧 → 1年级认识歌剧", "中班参与表演 → 大班自编自演"],
            ["创作要求", "以参与和模仿为主", "明确要求自编与自主搭配"],
        ],
        "emphasis": "中国产出更完整",
        "note": "两边都有表演，但中国大班把“编、演、舞美搭配”合在一条目标里，美国学前主要列模仿与集体游戏。",
    },
]

# 原有五个领域的微指标拆解：按能力点重新组织证据，深度仍按参数逐项列出。
DOMAIN_MICRO_CLAIMS: list[dict[str, Any]] = [
    {
        "id": "micro-math-count-cardinality", "domain": "数学",
        "concept": "数数、基数与数量上限", "group": "数与运算",
        "short": "美国从4枚硬币数到100，中国从5以内点数走到万以内认读。",
        "us_bands": [0, 1], "cn_bands": [0, 1],
        "us_evidence": ["n00155", "n00547", "n00549", "n00543"],
        "cn_evidence": ["ps-c-a2-g2-x-03", "ma-x1-aca-3169de58"],
        "axes": [
            ["数量上限", "4枚硬币 → 数到100", "5以内点数 → 万以内认读"],
            ["基数", "Count to tell the number of objects", "说出总数、按数取物"],
            ["递进", "学前 / K / 1年级", "小班 / 小学1-2年级"],
        ],
        "emphasis": "上限与方式不同",
        "note": "两边都从点数起步，但美国把目标写成数到100，中国把“说出总数、按数取物”与认读写大数连成主线。",
    },
    {
        "id": "micro-math-add-sub-10", "domain": "数学",
        "concept": "10以内加减与算理", "group": "数与运算",
        "short": "美国要求K年级在10以内解题并熟练算到5，中国从合并拿取的意义走到20以内熟练口算。",
        "us_bands": [0, 1], "cn_bands": [0, 1],
        "us_evidence": ["n00557", "n00560", "n01046"],
        "cn_evidence": ["ps-c-a2-g2-d-02", "ma-x1-con-3757b0ba", "ma-x1-aca-3169de58"],
        "axes": [
            ["数量范围", "10以内应用题，5以内熟练", "理解意义 → 20以内熟练口算"],
            ["算式与情境", "word problems within 10", "合并、拿取等实际情境"],
            ["算理", "properties of operations", "知道减法是加法的逆运算"],
        ],
        "emphasis": "中国算理表述更集中",
        "note": "功能相同但深度写法不同：美国列解题范围与熟练度，中国把操作意义、算理和口算速度写在同一条。",
    },
    {
        "id": "micro-math-fractions-intro", "domain": "数学",
        "concept": "分数的等值分割与分数单位", "group": "数的扩展",
        "short": "双方都在小学中段建立分数概念，美国强调等分与1/b，中国强调分数单位。",
        "us_bands": [2], "cn_bands": [2],
        "us_evidence": ["n02200", "n02201"],
        "cn_evidence": ["ma-x2-con-7d214454"],
        "axes": [
            ["概念抓手", "整体分成b等份中的1份", "感悟分数单位"],
            ["运算延伸", "同分母分数加减", "同分母分数与一位小数加减"],
            ["起始年级", "3年级", "小学3-4年级"],
        ],
        "emphasis": "阶段相当，表述角度不同",
        "note": "同一阶段的概念起点，美国用等分操作定义分数，中国用分数单位把分数与小数放在同一条。",
    },
    {
        "id": "micro-math-shapes", "domain": "数学",
        "concept": "图形分割与特征分类", "group": "图形与测量",
        "short": "美国1年级辨认半圆、四分之一圆等图形并推理属性，中国3-4年级按边角特征分类三角形和四边形。",
        "us_bands": [1, 2], "cn_bands": [2],
        "us_evidence": ["n01084"],
        "cn_evidence": ["ma-x2-con-0124f5b2", "ma-x2-con-cb89f248"],
        "axes": [
            ["任务", "辨认半圆、四分之一圆等图形并推理属性", "按特征分类三角形、四边形"],
            ["属性", "形状名称与属性", "边、角、角的大小关系"],
            ["起始年级", "1年级", "小学3-4年级"],
        ],
        "emphasis": "起步不同，后段汇合到图形性质",
        "note": "美国低年级先按半圆、四分之一圆等名称推理属性，中国把边角性质集中到中段；两边最终都进入图形属性。",
    },
    {
        "id": "micro-math-data", "domain": "数学",
        "concept": "数据收集、整理与集中量数", "group": "代数与统计",
        "short": "中国从收集整理描述一路写到平均数与百分数，美国中期跳到用集中量数概括数据。",
        "us_bands": [2, 3], "cn_bands": [2, 3],
        "us_evidence": ["n04329"],
        "cn_evidence": ["ma-x2-con-892fcdb0", "ma-x3-tip-7ca9a590"],
        "axes": [
            ["过程", "用集中量数概括数据集", "收集 → 整理 → 描述 → 分析"],
            ["工具", "measure of center", "统计图、平均数、百分数"],
            ["递进", "中段到高段", "3-4年级到5-6年级连续推进"],
        ],
        "emphasis": "中国过程链更完整",
        "note": "美国这条直接讲集中量数的意义，中国把数据统计的全过程写成教学主线。",
    },
    {
        "id": "micro-science-observe-tools", "domain": "科学",
        "concept": "观察、提问与工具使用", "group": "探究与工程",
        "short": "中国从好奇提问起步并明确工具使用，美国从按属性描述物体起步。",
        "us_bands": [0, 1], "cn_bands": [0, 1],
        "us_evidence": ["n00181", "n03602"],
        "cn_evidence": ["ps-c-a1-g1-x-01", "ps-c-a1-g1-x-02", "sc-x1-con-0fbd7e24"],
        "axes": [
            ["起点", "按可辨属性识别描述", "接触自然、提问、摆弄物品"],
            ["工具", "未单列低龄工具", "锤子、剪刀、放大镜等"],
            ["递进", "学前描述 → 小学调查", "小班兴趣 → 1-2年级工具体验"],
        ],
        "emphasis": "中国工具要求更具体",
        "note": "两边都从观察起步，差别在中国把“好奇提问”和“工具带来的便利”写成可观察的目标。",
    },
    {
        "id": "micro-science-experiment-measure", "domain": "科学",
        "concept": "实验设计与测量器材", "group": "探究与工程",
        "short": "美国强调计划与实施调查，中国把温度计、量筒、电子秤的使用写进中段要求。",
        "us_bands": [2, 3], "cn_bands": [2, 3],
        "us_evidence": ["n02238", "n03602"],
        "cn_evidence": ["sc-x2-con-0bafd236", "sc-x2-con-63432192"],
        "axes": [
            ["核心动作", "planning and conducting investigations", "观察比较 + 正确使用测量工具"],
            ["量化工具", "未列具体器材", "温度计、量筒、电子秤"],
            ["产出", "设计与实施", "用测量数据描述物体特点"],
        ],
        "emphasis": "中国器材与数据更具体",
        "note": "同属探究能力，美国写探究过程，中国把器材操作和用数据描述结果并列写出。",
    },
    {
        "id": "micro-science-cells-genetics", "domain": "科学",
        "concept": "细胞、遗传与生命现象", "group": "生命科学",
        "short": "美国从4年级起进入细胞与染色体机制，中国同期以动植物观察和分类为主。",
        "us_bands": [2, 3], "cn_bands": [2, 3],
        "us_evidence": ["n02913", "n04410"],
        "cn_evidence": ["sc-x2-con-33783426", "sc-x3-con-6bfe551c"],
        "axes": [
            ["解释层级", "细胞是生命最小单位、染色体作用", "观察分类、自然笔记、调查关系"],
            ["对象", "微观机制", "动植物与生态环境"],
            ["起始年级", "4年级起", "小学3-4年级起"],
        ],
        "emphasis": "美国更偏机制，中国更偏观察调查",
        "note": "同一生命主题下的深度分歧：美国下探到细胞与染色体，中国更多做外部现象与关系调查。",
    },
    {
        "id": "micro-science-heat", "domain": "科学",
        "concept": "热现象与热传递", "group": "运动与能量",
        "short": "中国中段探究热胀冷缩，美国高段解释热如何穿过或隔绝容器壁。",
        "us_bands": [3], "cn_bands": [2],
        "us_evidence": ["n04356"],
        "cn_evidence": ["sc-x2-con-04320c93"],
        "axes": [
            ["任务", "解释热传递与隔热", "探究热胀冷缩现象"],
            ["深度", "机制解释", "现象观察与认识"],
            ["起始年级", "5-6年级", "小学3-4年级"],
        ],
        "emphasis": "中国更早，美国更偏机制",
        "note": "不是简单的先后：中国先做现象探究，美国在更高年级追问热传递机制。",
    },
    {
        "id": "micro-science-earth-motion", "domain": "科学",
        "concept": "地球自转与昼夜", "group": "生态与地球",
        "short": "美国1年级用自转解释日出日落，中国在初中用模型或软件演示自转方向与周期。",
        "us_bands": [1], "cn_bands": [4],
        "us_evidence": ["n01093"],
        "cn_evidence": ["ge-j1-con-459f1b15", "ge-j1-con-5f8d68c4"],
        "axes": [
            ["解释对象", "日出日落的原因", "自转与公转的方向、周期"],
            ["工具", "无明确要求", "地球仪或软件演示"],
            ["起始年级", "1年级", "初中7-9年级"],
        ],
        "emphasis": "起步年级差距很大",
        "note": "同一现象在两套文件里的学段落差很大，不能只看“都讲地球运动”就判定接近。",
    },
    {
        "id": "micro-geo-map-skills", "domain": "地理",
        "concept": "地图方向、经纬度与图例", "group": "地图技能",
        "short": "美国低年级认图例和四方向，中国到初中才系统要求经纬度、量距和空间分布描述。",
        "us_bands": [0, 1], "cn_bands": [4],
        "us_evidence": ["n00831", "n00832", "n02491"],
        "cn_evidence": ["ge-j1-con-6d706eb0"],
        "axes": [
            ["技能", "图例与东南西北", "方向、经纬度、量距、图例、空间分布"],
            ["复杂度", "识别与查找", "判读与描述分布特征"],
            ["起始年级", "K-1年级", "初中7-9年级"],
        ],
        "emphasis": "中国更晚但维度更多",
        "note": "同为地图技能，美国起步早，中国在初中把多项技能合并成一条综合要求。",
    },
    {
        "id": "micro-geo-admin-units", "domain": "地理",
        "concept": "州与省：层级识别", "group": "区域认知",
        "short": "美国从社区到州逐层命名，中国初中要求识别34个省级行政区并记住简称和行政中心。",
        "us_bands": [0, 1], "cn_bands": [4],
        "us_evidence": ["n00414", "n00830", "n01487"],
        "cn_evidence": ["ge-j1-con-0e9d5223"],
        "axes": [
            ["识别对象", "社区、城市、州、大洲、国家", "34个省级行政区"],
            ["记忆要求", "命名与定位", "简称与行政中心"],
            ["起始年级", "K-2年级", "初中7-9年级"],
        ],
        "emphasis": "中国记忆要求更具体",
        "note": "功能对标的是行政区划层级；差别在中国把数量和简称行政中心写成明确记忆指标。",
    },
    {
        "id": "micro-geo-world-levels", "domain": "地理",
        "concept": "大洲、国家与区域分析", "group": "区域认知",
        "short": "美国低年级先背大洲国家层级，中国初中转向分析国家自然与人文地理的联系。",
        "us_bands": [0, 1], "cn_bands": [4],
        "us_evidence": ["n00830", "n00834"],
        "cn_evidence": ["ge-j1-con-95c69719", "ge-j1-con-9caeddb0"],
        "axes": [
            ["任务", "说出大洲、国家、州、社区", "分析某国人文特点及与自然环境的联系"],
            ["认知层级", "识记", "联系与解释"],
            ["起始年级", "K-2年级", "初中7-9年级"],
        ],
        "emphasis": "中国更偏分析",
        "note": "同是认识世界，美国低龄做层级命名，中国后段做区域综合分析。",
    },
    {
        "id": "micro-geo-earth-rotation", "domain": "地理",
        "concept": "地球自转与公转的周期", "group": "地球运动",
        "short": "美国1年级讲自转造成昼夜，中国初中用地球仪或软件说明自转和公转的方向与周期。",
        "us_bands": [1], "cn_bands": [4],
        "us_evidence": ["n01093"],
        "cn_evidence": ["ge-j1-con-459f1b15", "ge-j1-con-5f8d68c4"],
        "axes": [
            ["说明对象", "日出日落的原因", "自转与公转的方向和周期"],
            ["媒介", "叙述", "地球仪或软件演示"],
            ["起始年级", "1年级", "初中7-9年级"],
        ],
        "emphasis": "中国有量化周期要求",
        "note": "与科学领域的地球运动条目互为佐证：同一概念在两套文件中的年级跨度非常大。",
    },
    {
        "id": "micro-geo-region-culture", "domain": "地理",
        "concept": "区域自然环境与文化景观", "group": "区域认知",
        "short": "美国3-5年级列区域常识，中国初中要求说明自然环境与地方文化景观的关系。",
        "us_bands": [2, 3], "cn_bands": [4],
        "us_evidence": ["n02038", "n03188"],
        "cn_evidence": ["ge-j1-con-525c5cc2"],
        "axes": [
            ["任务", "城市与气候带常识", "野外考察或资料说明自然与文化景观关系"],
            ["方法", "识记", "考察、资料分析、说明"],
            ["起始年级", "3-5年级", "初中7-9年级"],
        ],
        "emphasis": "中国方法要求更完整",
        "note": "同属区域认知，美国偏事实清单，中国把考察、资料与解释放在一起。",
    },
    {
        "id": "micro-lang-listen-early", "domain": "语言与读写",
        "concept": "听懂日常语言并作出回应", "group": "听说与口语",
        "short": "美国学前强调语言互动机会，中国小班直接写听懂会话并回应。",
        "us_bands": [0, 1], "cn_bands": [0, 1],
        "us_evidence": ["n00049", "n00052"],
        "cn_evidence": ["ps-l-a1-g1-x-01", "ps-l-a1-g1-x-02", "ch-x1-sta-e5f0321c"],
        "axes": [
            ["起点", "大量听说互动机会", "注意听并回应、听懂日常会话"],
            ["进阶", "成人引导对话", "复述大意、完整讲述小故事"],
            ["起始年级", "学前", "小班 / 小学1-2年级"],
        ],
        "emphasis": "中国目标更可观察",
        "note": "美国写的是语言环境策略，中国写的是儿童可观察到的听与回应行为。",
    },
    {
        "id": "micro-lang-decode", "domain": "语言与读写",
        "concept": "拼读解码与识字写字", "group": "识字与书写",
        "short": "美国练音素拼读并走向流利阅读，中国用1600/800到2500/1600的字数和查字典界定进度。",
        "us_bands": [1, 2], "cn_bands": [1, 2],
        "us_evidence": ["n00716", "n02472"],
        "cn_evidence": ["ch-x1-sta-3b5f1ed2", "ch-x2-sta-835c454c"],
        "axes": [
            ["核心任务", "音素混合成词、流利解码", "识字、写字、偏旁笔顺、查字典"],
            ["量化", "无字数", "1600/800 → 2500/1600字"],
            ["递进", "1年级到4年级流利", "1-2年级到3-4年级累计"],
        ],
        "emphasis": "对象与量化方式都不同",
        "note": "同为“学会阅读”的起步，美国以拼音文字解码为主线，中国以汉字数量与工具使用为主线。",
    },
    {
        "id": "micro-lang-read-basic", "domain": "语言与读写",
        "concept": "朗读、理解与复述", "group": "阅读理解",
        "short": "美国此段以听读理解各类文本为主，中国把正确流利有感情朗读和默读写进同一条。",
        "us_bands": [1, 2], "cn_bands": [1, 2],
        "us_evidence": ["n00664"],
        "cn_evidence": ["ch-x1-sta-8aef276c", "ch-x2-sta-f3c0e535"],
        "axes": [
            ["输入方式", "听读虚构与非虚构文本", "朗读课文并学习默读"],
            ["输出", "听读理解文本", "复述大意、体会词句作用"],
            ["情感要求", "未写明", "正确、流利、有感情"],
        ],
        "emphasis": "中国朗读要求更细",
        "note": "美国此段以听读理解切入，中国把朗读方式、理解词句和情感表达合并为一条阶梯目标。",
    },
    {
        "id": "micro-lang-read-analysis", "domain": "语言与读写",
        "concept": "推断、概括与观点辩护", "group": "阅读理解",
        "short": "美国高段要求概括观点并为自己的立场辩护，中国要求联系上下文推断并质疑。",
        "us_bands": [3, 4], "cn_bands": [3, 4],
        "us_evidence": ["n03016", "n05393"],
        "cn_evidence": ["ch-x3-sta-8ce0d999", "ch-j1-sta-e85ea8a4"],
        "axes": [
            ["核心能力", "概括要点、为新信息辩护", "推想词句、辨别感情色彩、提出看法"],
            ["证据意识", "defend one’s own point of view", "观点与材料之间的联系"],
            ["起始年级", "5年级起", "小学5-6年级起"],
        ],
        "emphasis": "阶段接近，论证表述不同",
        "note": "两边同段进入分析性阅读；美国突出立场辩护，中国突出词句效果与材料联系。",
    },
    {
        "id": "micro-lang-writing", "domain": "语言与读写",
        "concept": "篇章写作、体裁与修改", "group": "写作与表达",
        "short": "美国列叙事、议论文、说明文等体裁和结构分析，中国把记实想象作文、修改交流和每学年16次写进同一条。",
        "us_bands": [3, 4], "cn_bands": [3, 4],
        "us_evidence": ["n03039", "n05444"],
        "cn_evidence": ["ch-x3-sta-f2697454", "ch-x3-sta-cd4fdb06"],
        "axes": [
            ["体裁", "叙事文、议论文、说明文等", "记实作文、想象作文、常见应用文"],
            ["结构", "分析段落与整体关系", "分段表述、根据表达需要"],
            ["量化要求", "无次数", "课内习作每学年16次左右"],
        ],
        "emphasis": "中国有频次与修改指标",
        "note": "同是篇章写作，美国把体裁与结构铺开，中国把修改与习作次数写成可检查的指标。",
    },
    {
        "id": "micro-culture-symbols", "domain": "文化",
        "concept": "国旗、国歌与国家象征", "group": "国家认同",
        "short": "美国低龄认识国旗与自由女神像，中国把认识国歌和升旗站好写成行为要求。",
        "us_bands": [0, 1], "cn_bands": [0, 1],
        "us_evidence": ["n00450", "n00451", "n01466"],
        "cn_evidence": ["ps-s-a2-g3-x-04", "ps-s-a2-g3-z-04", "po-x1-con-fba1a414"],
        "axes": [
            ["对象", "国旗、自由女神像", "国旗、国歌、国徽"],
            ["行为", "识别与了解意义", "奏国歌升国旗站好、学唱国歌"],
            ["起始年级", "K-2年级", "小班 / 小学1-2年级"],
        ],
        "emphasis": "中国有仪式行为要求",
        "note": "同是国家认同启蒙，美国以符号识别为主，中国把仪式中的身体行为写进目标。",
    },
    {
        "id": "micro-culture-fable-moral", "domain": "文化",
        "concept": "寓言、神话与寓意", "group": "文化传承",
        "short": "美国要求识别寓言和神话的寓意，中国从阅读童话寓言到分享神话启示。",
        "us_bands": [1, 2], "cn_bands": [1, 2],
        "us_evidence": ["n00689"],
        "cn_evidence": ["ch-x1-sta-49e1f5af", "ch-x2-con-93d1694f"],
        "axes": [
            ["任务", "identify the moral or lesson", "阅读感受 → 口头或书面分享启示"],
            ["文本", "fable、folktale、myth", "童话、寓言、中国神话传说"],
            ["输出", "识别", "分享交流"],
        ],
        "emphasis": "中国更强调表达输出",
        "note": "两边都用传统故事传价值，美国停在识别寓意，中国要求用口头或书面表达启示。",
    },
    {
        "id": "micro-culture-heritage", "domain": "文化",
        "concept": "英雄、传统与文化传承", "group": "文化传承",
        "short": "美国高段分析文学中的原型与主题，中国要求有理有据表达传统美德观点。",
        "us_bands": [3, 4], "cn_bands": [3, 4],
        "us_evidence": ["n03168", "n05452"],
        "cn_evidence": ["ch-x3-con-d8ead4a9"],
        "axes": [
            ["任务", "追溯原型情节、人物类型和主题", "结合实例有理有据表达观点"],
            ["对象", "神话传说与文学作品", "中华传统美德、社会公德短论"],
            ["起始年级", "5年级起", "小学5-6年级起"],
        ],
        "emphasis": "分析对象不同",
        "note": "同段进入文化传承，美国偏文学结构分析，中国偏现实事例中的观点表达。",
    },
    {
        "id": "micro-culture-diversity-early", "domain": "文化",
        "concept": "本民族与多元人群", "group": "多元理解",
        "short": "美国从认识一个部落或民族入手，中国直接建立56个民族大家庭与相互尊重的意识。",
        "us_bands": [0, 1], "cn_bands": [0, 1],
        "us_evidence": ["n00416"],
        "cn_evidence": ["ps-s-a2-g3-d-03", "po-x1-con-779ffc19"],
        "axes": [
            ["对象", "至少一个 Native American tribe or nation", "自己的民族与56个民族"],
            ["要求", "熟悉生活方式", "知道并相互尊重、团结友爱"],
            ["起始年级", "K-2年级", "大班 / 小学1-2年级"],
        ],
        "emphasis": "范围与表述不同",
        "note": "都是多元理解启蒙；美国从具体部落切入，中国从整体民族框架切入。",
    },
    {
        "id": "micro-culture-world", "domain": "文化",
        "concept": "世界文化与中外差异", "group": "多元理解",
        "short": "美国用移民史解释文化变化，中国以主要国家基本信息、节日和风土人情做体验。",
        "us_bands": [3, 4], "cn_bands": [3, 4],
        "us_evidence": ["n03350", "n03353", "n06906"],
        "cn_evidence": ["en-x3-con-a15b8f74", "en-x3-con-db09e52c"],
        "axes": [
            ["路径", "移民、铁路、迁移原因", "国家基本信息、节日、文化标志物"],
            ["深度", "因果分析", "感知与体验"],
            ["起始年级", "5年级起", "小学5-6年级起"],
        ],
        "emphasis": "美国偏历史因果，中国偏文化体验",
        "note": "同段扩展到世界文化，但一个从历史迁移切入，一个从国家文化信息切入。",
    },
]

# 微指标逐条解读：把参数表里的差异读成一句可核对的判断，避免只给维度不给结论。
MICRO_INTERPRETATIONS: dict[str, str] = {
    "micro-motor-hop": "两侧都在学前出现单脚跳，但美国只把它列为移动方式，中国从小班2米、中班5米到大班8米逐年加码。美国写避障防碰撞，中国写直线连续，结论只能是这份美国文本不写距离。",
    "micro-motor-signal": "美国学前就要求按信号开始／停止，中国最早在小学3-4年级体育用正反口令、变向跑训练反应。学前“听从长辈要求”属于社会性服从，不算同一功能。",
    "micro-motor-stairs": "两边都写交替双脚上下楼梯，中国多一个“灵活”。没有距离或速度标准，差异只在表述精度，不能把“灵活”换算成量化门槛。",
    "micro-motor-balance": "美国是原地换姿势和宽平衡木，中国从地面直线、窄低物体走到斜坡、荡桥，并分小中大三级。差异在情境复杂度，两边都没有米数。",
    "micro-motor-throw": "美国先按指示方向投、再提高靶的准度，中国用沙包投2米、4米、5米作年龄刻度。两侧都练投掷，但这段文本一个以靶为准，一个以距离为标。",
    "micro-motor-catch": "美国是两人1.5英尺对接豆袋，中国从抛接球到连续拍球逐年加难。一个控制距离，一个控制动作连续性，不能看成同一种接物训练。",
    "micro-motor-rules": "美国要求遵守现成游戏规则，中国从提醒下遵守走到与同伴协商制定规则。差别在规则由谁定、由谁维持，不是“守规则”三个字。",
    "micro-motor-calm": "美国的“平静”是从高活动转到身体放松、安静专注，中国是识别情绪原因并自行缓解。同在学前起步，但一个调活动强度，一个调情绪。",
    "micro-routine-sleep": "这是单侧项：中国给出每天11-12小时、午睡约2小时并从小班坚持，Core Knowledge 是学科内容序列不写作息。两份文件功能不同，不能解读成美国不要求午睡。",
    "micro-routine-hygiene": "中国把早晚刷牙、饭前便后洗手写成固定要求并分三级递进，美国把如厕洗手和餐具使用并列成一条自理目标。自主性都有，只有中国拆成可观察阶段。",
    "micro-routine-screen": "中国按小班15、中班20、大班30分钟递增，并配光线要求；Core Knowledge 没有屏幕时长条目。这是文本覆盖范围差异，不能写成美国允许无限看电视。",
    "micro-routine-selfcare": "美国只写用后归位，中国从帮助下穿脱、扣钮扣到系鞋带，从放回原处到按类别整理。两边都重自主，差别是中国把它拆成小中大三级。",
    "micro-routine-safety": "美国是记住地址、电话和出生日期，中国把姓名电话放进走失、陌生人、开门、防灾情境并要求求助。差别是“记住信息”和“遇到情况会做”。",
    "micro-arts-movement": "美国K／1／2三年文字相同，只要求随音乐行进、走、单脚跳、摇摆；中国小班到大班从跟随动作走到拍手踏脚、敲击和基本准确的节奏音调。一个重持续参与，一个重递进精度。",
    "micro-arts-visual": "两边都从线条色彩入手，但美国引入作品与艺术家并要求讨论形式要素，中国要求画出自己想画的人或事、不宜提供范画。名作在美国是内容，在中国是教学禁忌。",
    "micro-arts-singing": "美国K／1／2重复演唱形式，中国从模仿学唱走到节奏音调基本准确。美国写唱的形式，中国把唱得准写成进阶目标。",
    "micro-arts-rhythm": "美国从K起认拍、打拍、认重音，中国从中班拍手踏脚敲基本节奏到大班基本准确。美国更早且抽象，中国稍晚但工具和精度更具体。",
    "micro-arts-appreciation": "美国要求用语言讨论作品细节、为何这样画和形式要素，中国允许表情、动作、语言并强调联想与情绪。差别在表达通道和分析要求，不是欣赏有无。",
    "micro-arts-drama": "美国从哑剧、团体游戏到认识歌剧，以模仿参与为主；中国从中班表演走到大班自编自演并配服饰道具。中国把编、演、舞美合成完整产出。",
    "micro-math-count-cardinality": "美国把数数与4枚硬币、数到100绑定，中国要求点数5以内、说出总数、按数取物再认读到万以内。任务形态不同，不能按数量上限判难易。",
    "micro-math-add-sub-10": "美国K年级做10以内应用题、5以内熟练，中国大班理解加减意义后到20以内口算。美国提运算性质，中国点明减法是加法的逆运算。",
    "micro-math-fractions-intro": "两边都在3-4年级建立分数概念：美国用整体等分定义1/b，中国用分数单位统整分数和小数，并都接到同分母加减。进度相近，概念语言不同。",
    "micro-math-shapes": "美国1年级把图形分成二分之一、四分之一并辨认属性，中国3-4年级按边角特征分类并用量角器画角。相差约两年，认知动作也不同。",
    "micro-math-data": "美国直接讲集中量数和变异量数，中国从收集、整理、描述到分析走完整过程并接平均数、百分数。一个聚焦概括量，一个铺成统计流程。",
    "micro-science-observe-tools": "美国从五感描述物体属性切入，中国从好奇提问、摆弄物品走到1-2年级用放大镜等工具并和徒手比较。两边都培养观察，抓手不同。",
    "micro-science-experiment-measure": "美国写设计与实施调查，中国把观察比较和温度计、量筒、电子秤取数并列，并要求用数据描述物体。会不会做实验和会不会用仪器取数是两回事。",
    "micro-science-cells-genetics": "美国4年级讲细胞是生命最小单位、6年级讲染色体，中国同期以动植物观察、分类和自然笔记为主。同一段文本选择的解释层级不同，不能说中国不讲生命科学。",
    "micro-science-heat": "中国3-4年级探究热胀冷缩现象，美国5-6年级解释热如何穿过或隔绝容器壁。中国先做现象、美国后讲机制，年级和认知层级是两回事。",
    "micro-science-earth-motion": "美国1年级用自转解释日出日落，中国初中要求说出自转公转方向和周期并用地球仪或软件演示。一个解释现象，一个描述天文参数。",
    "micro-geo-map-skills": "美国低年级认图例和四方向，4年级才用经纬度读图；中国初中把方向、经纬度、量距、图例和分布描述合在一条。美国逐年加码，中国集中合成。",
    "micro-geo-admin-units": "美国从社区、州到50州名称多年铺垫，中国初中一次完成34个省级行政区的识别、简称和行政中心。对比的是各自行政区划，不是同一张地图的难易。",
    "micro-geo-world-levels": "美国低年级说大洲国家州社区并背诵七大洲，中国初中分析某国人文与自然联系及因地制宜发展。都叫世界地理，但一侧是名录，一侧是关系分析。",
    "micro-geo-earth-rotation": "同一份地球运动证据：科学条看美国1年级解释昼夜、中国初中讲运动参数；地理条则看中国用模型说明自转公转。两条并排读才能看出定位差异。",
    "micro-geo-region-culture": "美国低年级列城市、气候带等常识，中国初中通过考察或资料说明自然环境与地方文化景观的关系。差别是知道区域事实和解释区域差异成因。",
    "micro-lang-listen-early": "美国规定环境要提供大量听说互动和成人邀请对话，中国小班直接要求注意听、回应、听懂日常会话。一个是输入条件，一个是行为指标。",
    "micro-lang-decode": "美国练音素混合成词并走向自动解码，中国练识字、笔顺和查字典，字数从1600／800到2500／1600。文字系统不同，只能看各自把什么写成可测进度。",
    "micro-lang-read-basic": "美国从听读虚构与非虚构文本切入，中国直接要求正确、流利、有感情地朗读并学默读。朗读在美国此段不是主线，在中国是显性目标。",
    "micro-lang-read-analysis": "美国5年级概括推出结论、8年级为自己立场辩护并随证据调整；中国5-6年级推想词句，初中提出看法并合作探讨。论证立场与词句细读是两种深化方式。",
    "micro-lang-writing": "美国列报道、摘要、研究论文并分析段落结构，中国列记实、想象、应用文并写每学年16次左右习作。一个偏体裁结构，一个偏频次与修改流程。",
    "micro-culture-symbols": "美国把国旗、自由女神像作为历史与国家知识来认识，中国写国旗国歌国徽并要求奏国歌时站好、学唱。一个偏认知，一个同时是仪式行为规范。",
    "micro-culture-fable-moral": "美国1年级直接要求识别寓言、民间故事、神话的寓意，中国先谈阅读感受，3-4年级再分享寓意和启示。一个把寓意当可识别结论，一个当交流内容。",
    "micro-culture-heritage": "美国8年级追溯文学原型和主题源流，中国5-6年级结合实例有理有据表达传统美德观点。都讲传统，但任务是文学源流分析和观点表达。",
    "micro-culture-diversity-early": "美国从具体部落的生活方式和多个族群切入，中国从自己的民族和56个民族大家庭意识切入。都是多元理解启蒙，一个重实景，一个重共同体框架。",
    "micro-culture-world": "5-6年级两侧同讲世界文化，美国用宅地法、铁路、移民劳动解释文化变化，中国用国家信息、节日、文化标志物建立印象。是因果分析和体验感知的差异。",
}

# 原有概念簇逐簇解读：沿用微指标口径，把首次、后续覆盖与深度差异连起来读。
CONCEPT_INTERPRETATIONS: dict[str, str] = {
    "math-number-early": "两边都从学前数数起步，但中国小班就要求点数5以内、说出总数并按数取物，美国同时铺开配对、规律和比较。首次相同不等于后续组织密度相同。",
    "math-number-place-value": "双方3-4年级建立位值和十进制意识，差别在中国5-6、7-9年级继续接有理数、实数和数轴，美国则一路铺到初中运算律。起点接近，抽象路径不同。",
    "math-number-rational": "美国7年级把分数运算推广到有理数四则，中国7-9年级同时讲负数、数轴、相反数、绝对值和实数，还把不等式解集画在数轴。不是谁更早讲负数，而是支架不同。",
    "math-add-sub-early": "两边学前都做数量分合，中国中班直接写“2和3合在一起是5”，美国从分物配对起步。美国小学各年级反复回返，中国大班到1-2年级集中讲算理算法。",
    "math-multi-div": "双方中高段进入乘除与混合运算，美国用乘除within100解应用题、用符号表示未知数，中国把多位数乘除与十进制、转化思想连起来。后段中国集中，美国回返多。",
    "math-rational-operations": "美国7年级把分数规则推广到有理数四则，中国7-9年级把数系扩张、乘方开方、代数式代入和数轴连成主线。会算有理数和把运算推广成代数结构不是一回事。",
    "math-fractions-intro": "双方3年级附近建立分数概念：美国把1/b定义为整体等分b份中的1份，中国同时引入分数小数并点出分数单位。美国铺到初中，中国集中在小学两段。",
    "math-fractions-operations": "美国5年级做小数乘除、小数点移动和多位数运算，中国5-6年级把整数除法与分数关系、简单分数小数四则连起来。一个贯穿后段，一个学段集中。",
    "math-ratio-percent": "美国6年级用ratio reasoning，中国5-6年级把比、比例、按比分配、比例尺并列并加方格纸缩放。美国初中7年级继续调用，中国后段没有独立回返。",
    "math-negative-rational": "美国6年级对应中国5-6年级的负数认识，但中国那条只是主题活动情境；真正的系统在7-9年级，美国7-8年级扩展到有理数方程和根式。见过和系统学要分开。",
    "math-algebra-foundations": "美国从幼儿园大班用putting together等运算关系铺垫并持续到小学，中国5-6年级才用等式性质和字母表示数显式化。首次提前不等于终局深度。",
    "math-equations-basic": "双方进入等式与一元一次方程时间接近：美国小学中段铺垫、8年级解含科学记数法的方程，中国5-6年级学等式性质、初中集中解方程和不等式。路径不同。",
    "math-equations-advanced": "美国7年级用运算性质生成等价表达式、展开因式分解，中国7-9年级把一元一次方程、分式方程、方程组和不等式组做成工具箱。前者为代数准备，后者成体系。",
    "math-functions": "双方初中系统学函数，美国8年级定义为输入到输出的唯一规则并用y=mx+b讲图像，中国从常量、变量、自变量、函数值到一次函数。术语顺序差异不是内容缺失。",
    "math-shapes-early": "两边学前都从形状感知分类起步，中国初中把定义、基本事实和证明串成体系，美国走向变换、相似和勾股。早期辨认相同，后段一个走证明、一个走度量。",
    "math-shapes-properties": "3-4年级双方进入图形性质：美国讨论不同类别共享属性，中国认识角、量角画角并按边角分类。属性辨析与边角分类是两种认知抓手，不要只比谁先提三角形。",
    "math-geometry-proof": "美国7年级做尺规作图、图形关系和比例尺，初中接相似勾股；中国7-9年级把轴对称、平移旋转的性质、基本事实和证明连成体系。应用与证明链条不同。",
    "math-measure-early": "两边学前都有可测量属性意识：美国描述比较长度重量，中国用大小高矮长短等词感知并一一对应。后段美国继续立体度量应用，中国转向相似图形面积比。",
    "math-area-perimeter-volume": "双方中段学面积周长体积，美国把时间、液体体积、质量一起推进并到初中做柱锥球体积，中国按学段铺开并接几何推理。后段走向不同。",
    "math-measure-advanced": "美国7年级用圆面积周长公式解决角度、面积、表面积和体积的实际问题，中国7-9年级把圆、弧、弦、圆周角、垂径定理放进推理链。公式应用与几何化不同。",
    "math-data-early": "中国大班已用记录表、统计图表示数量关系，美国早期数据意识嵌在属性比较中；后段美国8年级用双向表、散点图看关联，中国初中集中讲抽样和概率。",
    "math-data-basic": "中段双方做数据整理表达：美国低年级图表活动延续到初中关联分析，中国3-4年级走完整过程、5-6年级接平均数和百分数。统计过程完整度与关联抓手各有侧重。",
    "math-statistics-inference": "美国8年级用双向表和散点图判断双变量关联，中国7-9年级讲扇形图、平均数、中位数、众数、加权平均数和抽样。都超出读图，但不是同一条推断路线。",
    "science-matter-daily": "中国中班已感知溶解传热等生活性质，美国2年级从观察分类和物质定义起步；后段美国系统讲守恒与化学反应，中国初中物理化学分科深化。生活经验早不等于概念系统。",
    "science-matter-properties": "美国5年级围绕有质量、占空间讲性质和守恒，中国3-4年级观察透光性并用温度计、量筒、电子秤取数、联系用途。操作链与概念定义是两种深度。",
    "science-matter-reaction": "美国7年级从颜色气味温度变化判断反应、讲反应物生成物，中国7-9年级用天平、密度、酸碱度测定并推理燃烧等现象。征兆判断与定量推理路径不同。",
    "science-atoms-bonds": "双方初中讲原子分子元素，美国给定义，中国把纯净物、混合物、单质、化合物、元素放进同一分类体系并接科学史。给出定义与建立层级不是一回事。",
    "science-force-early": "美国幼儿园大班用push/pull定义力，中国1-2年级从开关门窗、推拉抽屉识别。美国小学各年级回返到初中定量表达，中国初中集中做摩擦力、浮力等必做实验。",
    "science-motion-basic": "美国3年级直接说力能改变运动状态，中国3-4年级从交通事故视频、工具使用切入。后段美国用速度等于距离除以时间做定量表达，中国把比较快慢的方法定义成速度并探究。",
    "science-force-advanced": "美国8年级给速度和力的量化表达，中国7-9年级列摩擦力、斜面、浮力、凸透镜成像、电流电压等必做实验。可操作实验清单与量化概念公式是两种写法。",
    "science-energy-daily": "中国幼儿园已有溶解传热的生活感知，美国1年级起持续讲光和声并在4-6年级高密度展开。中国5-6年级开始实验、初中集中讲能量转化守恒。生活感知早与覆盖连续要分开。",
    "science-energy-basic": "美国3-4年级从磁力距离、能量应用切入，中国同期做热胀冷缩实验和气象记录；美国小学多年级连续覆盖，中国初中把能量转化守恒与实验探究集中。覆盖连续不等于原理化程度。",
    "science-energy-advanced": "美国7年级把化学反应吸放热纳入能量观、8年级延到波与声，中国7-9年级把能量转化守恒与多个实验探究并列。实验原理并重与概念接续不同。",
    "science-life-early": "中国小班已认识常见动植物，美国1-2年级从亲代照护和多样性观察起步。中国首次更早，但美国初中7-8年级走细胞、遗传、进化证据链这条不同的深线。",
    "science-genetics-basic": "美国4年级给出细胞是生命最小单位，中国3-4年级做动物分类、自然笔记、茎中水分运输和牙齿比较。后段美国走遗传与共同祖先证据链，中国走显微观察与建模。",
    "science-evolution": "美国7年级从消化、细胞呼吸、葡萄糖能量谈生命并接进化证据，中国7-9年级用细胞建模、人体系统模型和显微观察深化。结构观察与遗传解释链不能合并成单一深浅。",
    "science-ecology-early": "美国幼儿园大班讲植物从环境获取所需、人类也是动物，中国大班从环保和珍惜生命切入。后段美国5年级讲食物网物质循环，中国项目研究、调查并制作生态瓶。",
    "science-food-chain": "美国3年级从环境对性状和生命周期的影响切入，中国5-6年级调查废水废气、微生物和生态平衡。后段美国讲食物网物质流动，中国接调查与保护设计。",
    "science-ecology-project": "美国7年级明确物质沿食物链流动、食物网由食物链构成，中国7-9年级调查池塘森林农田海岸或校园并接富集、传染病。系统概念与调查制作是两种深化。",
    "science-body-early": "美国幼儿园大班从视觉器官等结构讲起，中国小班用多种感官探索并把健康行为写进生活要求。后段美国3-5年级进到腺体激素，中国初中偏食品安全与健康行为。",
    "science-body-basic": "美国3年级讲肌肉、随意与不随意肌，中国3-4年级做健康档案、肺活量和呼吸保健项目、初中聚焦食品安全。身体结构与健康管理是两种不同功能。",
    "science-space-early": "美国幼儿园大班讲太阳是恒星、阳光温暖地表，中国1-2年级观察描述月相；美国5年级高密度天体观测、8年级讲日月食证据，中国小学持续观察、初中转地质原理。",
    "science-earth-basic": "美国3年级把空气当混合物并一路讲到日月食观测证据，中国3-4年级测影长、做月球表面模型，初中转板块构造解释火山地震。现象观测与原理模型后段不同。",
    "science-earth-advanced": "美国7年级从自然资源和可再生能源讲人与地球，中国7-9年级用地球仪或软件演示自转公转并用板块构造解释火山地震。资源使用与运动模型不同。",
    "science-weather-early": "中国小班已感知天气对活动的影响、中班感知季节，美国幼儿园大班定义天气并收集温度降水风速数据。中国生活感知更早，美国数据化更早。",
    "science-water-basic": "美国小学把天气因素与气候分类连续推进，中国3-4年级用气温计和天气符号记录并联系季节适应，初中用气温降水数据描述规律。记录工具与分类框架两种抓手。",
    "science-climate-data": "这条几乎只有中国后段有直接证据：初中7-9年级阅读气温降水数据、绘制气温曲线和降水柱状图。不是美国不讲气候，而是这组分科文本里没写成同粒度任务。",
    "science-observe": "双方学前都有观察提问，美国按五感属性描述，中国从好奇摆弄切入。后段中国把实验器材和项目制作写进初中，美国小学2-5年级持续做调查和工程设计。",
    "science-experiment": "美国3年级用planning and conducting investigations组织探究，中国3-4年级用温度计、量筒、电子秤取数。中国初中把必做实验做成清单，美国持续做调查与工程设计。",
    "science-project": "中国初中把观察、测量、实验探究和项目制作并列，器材步骤很具体；美国小学2-5年级更多以工程设计出现，初中独立项目命中少。不能说美国没有项目。",
    "geo-direction-early": "中国小班理解上下前后里外、中班用方位词描述方向，美国幼儿园大班直接定位北美、阿拉斯加和夏威夷。后段美国在历史区域单元调用地图，中国做成独立技能链。",
    "geo-map-basic": "小学双方学图例方向：美国1年级明确key/legend并找四方向，中国把图例方向放到1-2年级到中段连续要求。后段美国仍多在历史单元调用，中国初中系统用比例尺图例经纬。",
    "geo-map-advanced": "中国5-6年级到初中把比例尺、等高线、经纬网做成技能链，美国5年级已用经纬度、坐标、度数和投影读图。早期读图经验与后段系统化不是一回事。",
    "geo-continents-basic": "美国1-2年级说大洲大洋国家名称，中国学前到小学无同名独立主题；但中国初中用地图分析大洲位置、热量带、降水与人口经济。首次优势被后续深度反转。",
    "geo-continents-analysis": "中国初中用地图说明海陆分布并把大洲位置与气候地形人口经济联系，美国初中仍把大洲大洋当区域背景知识。同叫世界地理，名词与分析变量不同。",
    "geo-hemisphere": "美国1-2年级从生活定位认识赤道、南北半球和两极并逐步加入时区，中国5-6年级才初步接触、初中系统学经纬线定位。先给概念名和后给完整方法要分开。",
    "geo-coordinates": "美国5年级已用经纬度、坐标、度数和时区读图，中国5-6年级到初中把经纬网定位与地球运动做成体系。早期读图经验与后段工具系统化不宜写成谁缺失。",
    "geo-land-basic": "1-2年级双方接触地形河流和自然资源，美国多嵌在历史区域单元做背景，中国小学零散感知、初中集中学等高线地形图并接气候因素。嵌入式背景与地图原理任务不同。",
    "geo-physical-analysis": "美国5年级讲气候带河流常识并在区域单元继续调用，中国7-9年级用等高线、分层设色图识别地形并分析气候影响因素。区域常识调用与可判读任务表现方式不同。",
    "geo-culture-basic": "美国学前到初中把文化城市内容嵌在历史单元并接到全球化传播，中国初中把人口、聚落、区域差异和家乡调查做成独立主题。组织形式差异大于阶段差异。",
    "geo-population": "美国3-4年级起人口移民城市内容多嵌在历史区域单元并延伸到全球化，中国把人口聚落迁移放到初中独立主题。出现频率不等于主题独立性。",
    "geo-region-development": "美国初中用“机会之地”“熔炉与马赛克”讲移民与文化，中国7-9年级用人口聚落区域发展和因地制宜整合人文自然。历史叙事与区域框架两种综合方式。",
    "geo-admin-basic": "州和省都是一级行政区，可直接对标：美国从说所在州、州与社区到50州名称、州府多年铺垫，中国初中一次完成34个省级行政区识别、简称和行政中心。",
    "geo-admin-capitals": "美国5年级记50州及州府，中国7-9年级记省级行政区简称和行政中心。都是名录型要求，时间差不能写成理解深度差。",
    "lang-listen-early": "双方学前从听懂日常语言起步：美国写大量听说互动和成人邀请对话，中国小班要求注意听、回应、听懂会话。后段美国靠讨论规则与口头报告，中国把复述、即席讲话写成学段目标。",
    "lang-listen-mid": "3-4年级双方要求课堂讨论复述转述：美国明确讨论前阅读整理、讨论中保持注意参与，中国把朗读默读、把握内容、圈点批注、质疑连成链。讨论规则与读思说链条抓手不同。",
    "lang-listen-late": "7-9年级双方进入有观点表达：美国要求按场合切换正式与非正式英语、演讲标准发音，中国把倾听、观点与材料联系、文明得体交流写成目标。语体形式与观点材料关系是不同维度。",
    "lang-literacy-early": "学前到1-2年级双方建立图书符号和书写准备：美国从印刷品意识走向拼读解码和流利朗读，中国从图书兴趣走向识字写字拼音查字典。字母拼读与汉字识字不是同一任务。",
    "lang-decode-characters": "美国1年级把音素混合成词作为解码核心、4年级转向自动解码，中国1-2年级以1600／800字和偏旁笔顺查字典为核心、3-4年级累计2500／1600。看可测进度定义，不比文字系统难易。",
    "lang-reading-basic": "1-2年级双方从朗读理解到复述：美国从听读虚构与非虚构切入，中国直接要求正确流利有感情朗读并学默读。后段美国进入推断概括和文本证据，中国概括分析、体会表达效果。",
    "lang-reading-analysis": "5-6年级到初中双方进入推断概括证据评价：美国把概括、推出结论、作者意图和观点连成链，中国推想词句、辨别感情色彩、初中评价成体系。论证证据意识与词句细读两种深化。",
    "lang-writing-early": "学前到1-2年级双方从非文字表达过渡到写话：美国用口述图注、口述信件起步，中国小班涂画、中班注意写画姿势。后段美国完成叙事说明议论与修订，中国完成记实想象作文与应用文。",
    "lang-writing-composition": "双方高段完成篇章写作修订：美国5年级分析结构、写报道摘要说明研究论文并关注统一连贯，中国5-6年级写记实想象作文和读书笔记、把交换修改与每学年16次习作写进目标。",
    "lang-poetry-early": "学前到1-2年级双方用儿歌韵诗童话入门：美国记诵儿歌、拍节拍、手指游戏，中国说儿歌童谣、复述短故事并要求成人讲读。后段美国扩到神话戏剧小说与文学术语，中国加古诗文和寓言。",
    "lang-genre-study": "3-4年级体裁扩到诗歌神话小说散文戏剧：美国朗读诗歌散文、独立读较长虚构作品，中国复述叙事作品、诵读诗文累计背诵50篇段、课外阅读不少于40万字。读析术语与积累量不同。",
    "culture-symbols-early": "国家符号应按共同记忆功能对标：美国学前认识国旗、自由女神像并在历史音乐单元反复出现，中国小班认识国旗国歌、中班升旗站好并在1-2年级借少先队实践。认知与实践两种方式。",
    "culture-holiday-mid": "节日看文化传承功能：美国感恩节、独立日贯穿K-8历史单元，中国从身边风俗体验到小学传统文化和初中文化传承。历史叙事节点与文化体验主题不宜逐项比对。",
    "culture-stories-mid": "故事人物不可直接对照，但用传统故事传递价值高度可比：美国用民间故事、传说、神话和英雄人物，中国用神话、成语、寓言、历史故事贯穿小学初中。差别在载体和表达语言。",
    "culture-heritage-late": "美国5年级讲神话传说与视觉多媒体手法、8年级追溯原型主题，中国5-6年级读传统美德短论并结合实例表达观点。都讲传统，但一个是文学源流分析，一个是观点表达任务。",
    "culture-diversity-early": "双方学前起步：美国从本土部落和多元人群切入、偏社会实景，中国从自己的民族和56个民族大家庭切入、偏共同体意识。高年级美国接世界文化与移民，中国由英语文化课明确世界国家。",
    "culture-diversity-world": "5-6年级到初中双方扩展到世界文化：美国用宅地法、横贯大陆铁路、移民劳动解释变化，中国用国家信息、节日、文化标志物做感知体验。因果分析与文化印象不是谁更深。",
}

# 概念簇简表：每条只给“起步 / 后续 / 差异”三行，避免复用父级深度文案造成重复。
CONCEPT_AXES: dict[str, tuple[str, str]] = {
    "math-number-early": ("配对、规律、比较等前置经验", "点数5以内、说总数、按数取物"),
    "math-number-place-value": ("多位数运算与四舍五入", "万以上数、十进制与多位数乘除"),
    "math-number-rational": ("分数运算推广到有理数四则", "负数、数轴、绝对值、实数与解集"),
    "math-add-sub-early": ("分物配对后小学各年级回返", "中班2和3合5，大班10以内加减"),
    "math-multi-div": ("乘除within100解应用题", "多位数乘除与十进制、转化"),
    "math-rational-operations": ("运算性质生成等价式、因式分解", "方程、分式、方程组、不等式组"),
    "math-fractions-intro": ("整体等分定义1/b", "分数单位统整分数和小数"),
    "math-fractions-operations": ("小数乘除与小数点移动", "整数除法与分数关系、简单四则"),
    "math-ratio-percent": ("ratio reasoning贯穿初中", "比、比例、比例尺与方格纸缩放"),
    "math-negative-rational": ("有理数方程和根式", "负数、有理数系统到初中"),
    "math-algebra-foundations": ("用putting together铺垫运算关系", "等式性质与字母表示数"),
    "math-equations-basic": ("小学铺垫、8年级含科学记数法", "等式性质到方程与不等式"),
    "math-equations-advanced": ("等价表达式与因式分解", "方程、分式、方程组工具箱"),
    "math-functions": ("输入输出规则与y=mx+b图像", "常量、变量、自变量到一次函数"),
    "math-shapes-early": ("走向变换、相似、勾股", "定义、基本事实与证明体系"),
    "math-shapes-properties": ("讨论类别共享属性", "量角画角、按边角分类"),
    "math-geometry-proof": ("尺规作图、比例尺、相似勾股", "轴对称平移旋转性质与证明"),
    "math-measure-early": ("长度重量描述比较", "大小高矮长短与一一对应"),
    "math-area-perimeter-volume": ("时间、液体体积、质量一并推进", "学段铺开并接几何推理"),
    "math-measure-advanced": ("圆公式解决角度面积体积", "圆、弧、弦、圆周角推理链"),
    "math-data-early": ("数据意识嵌入属性比较", "记录表、统计图表示数量关系"),
    "math-data-basic": ("图表活动延续到关联分析", "完整统计过程接平均数百分数"),
    "math-statistics-inference": ("双向表、散点图判断关联", "扇形图、集中量与抽样概率"),
    "science-matter-daily": ("观察分类与物质定义", "溶解传热的生活感知"),
    "science-matter-properties": ("有质量、占空间与守恒", "透光性、量具取数与用途"),
    "science-matter-reaction": ("征兆判断与反应物生成物", "天平、密度、酸碱度定量推理"),
    "science-atoms-bonds": ("原子分子元素定义", "物质分类层级与科学史"),
    "science-force-early": ("push/pull定义力并回返到初中", "开关门窗、推拉抽屉到必做实验"),
    "science-motion-basic": ("速度公式定量表达", "比较快慢的方法并探究"),
    "science-force-advanced": ("速度与力的量化表达", "摩擦力浮力凸透镜电流等实验"),
    "science-energy-daily": ("光和声连续覆盖到6年级", "生活感知后集中能量转化守恒"),
    "science-energy-basic": ("磁力距离、能量应用", "热胀冷缩与气象记录后实验"),
    "science-energy-advanced": ("吸放热纳入能量观、波与声", "转化守恒与多实验探究并列"),
    "science-life-early": ("亲代照护与多样性观察", "认识常见动植物更早"),
    "science-genetics-basic": ("细胞、遗传、共同祖先证据链", "显微观察与建模"),
    "science-evolution": ("消化呼吸到进化证据", "细胞、人体系统模型与显微观察"),
    "science-ecology-early": ("环境获取所需、食物网物质循环", "环保珍惜生命、项目制作生态瓶"),
    "science-food-chain": ("性状与生命周期受环境影响", "废水废气微生物与生态平衡"),
    "science-ecology-project": ("食物链食物网系统概念", "校园生态调查与富集传染病"),
    "science-body-early": ("视觉器官结构到腺体激素", "多感官探索与健康行为"),
    "science-body-basic": ("随意与不随意肌", "健康档案、肺活量、食品安全"),
    "science-space-early": ("恒星与高密度天体观测", "月相观察到初中地质原理"),
    "science-earth-basic": ("空气成分与日月食证据", "影长、月球模型到板块构造"),
    "science-earth-advanced": ("自然资源与可再生能源", "地球仪软件演示自转公转"),
    "science-weather-early": ("天气定义与温度降水风速数据", "天气季节对活动的影响"),
    "science-water-basic": ("天气因素与气候分类连续推进", "气温计天气符号记录与数据分析"),
    "science-climate-data": ("分科文本未写成同粒度任务", "气温降水数据绘曲线柱状图"),
    "science-observe": ("五感属性描述、调查工程设计", "好奇摆弄到实验器材项目制作"),
    "science-experiment": ("调查探究组织方式", "量具取数与必做实验清单"),
    "science-project": ("工程设计为主", "观察测量实验制作并列"),
    "geo-direction-early": ("定位北美、阿拉斯加、夏威夷", "上下前后里外到方位词"),
    "geo-map-basic": ("图例四方向、历史单元调用", "图例方向连续要求到初中系统"),
    "geo-map-advanced": ("经纬度、坐标、投影读图", "比例尺、等高线、经纬网技能链"),
    "geo-continents-basic": ("大洲大洋国家名称", "初中大洲位置与气候人口经济"),
    "geo-continents-analysis": ("大洲作区域背景", "地图分析大洲位置与要素联系"),
    "geo-hemisphere": ("赤道半球两极及时区", "5-6年级初步、初中经纬线定位"),
    "geo-coordinates": ("经纬度坐标时区读图", "经纬网定位与地球运动体系"),
    "geo-land-basic": ("地形河流作历史背景", "等高线地形图与气候因素"),
    "geo-physical-analysis": ("气候带河流常识调用", "等高线分层设色与气候影响因素"),
    "geo-culture-basic": ("文化城市嵌在历史单元", "人口聚落区域差异与家乡调查"),
    "geo-population": ("人口移民城市嵌历史单元", "人口聚落迁移独立主题"),
    "geo-region-development": ("机会之地、熔炉与马赛克叙事", "人口聚落区域与因地制宜框架"),
    "geo-admin-basic": ("州与州府多年铺垫", "34个省级行政区、简称、行政中心"),
    "geo-admin-capitals": ("50州及州府", "省级行政区简称和行政中心"),
    "lang-listen-early": ("听说互动与成人邀请对话", "注意听、回应、听懂会话"),
    "lang-listen-mid": ("讨论前整理与讨论中参与", "朗读默读、圈点批注、质疑"),
    "lang-listen-late": ("正式与非正式语体切换", "观点与材料联系、文明得体交流"),
    "lang-literacy-early": ("印刷品意识到拼读解码", "图书兴趣到识字写字拼音查字典"),
    "lang-decode-characters": ("音素混合与自动解码", "识字量、偏旁笔顺、查字典"),
    "lang-reading-basic": ("听读虚构与非虚构、文本证据", "正确流利有感情朗读与默读"),
    "lang-reading-analysis": ("概括结论、作者意图与观点", "推想词句、感情色彩与评价"),
    "lang-writing-early": ("口述图注信件到结构修订", "涂画姿势到记实想象应用文"),
    "lang-writing-composition": ("体裁结构与统一连贯", "习作频次、交换修改"),
    "lang-poetry-early": ("儿歌拍节拍到文学术语", "童谣复述到古诗文寓言"),
    "lang-genre-study": ("朗读诗歌散文、读析术语", "背诵50篇段、课外40万字"),
    "culture-symbols-early": ("国旗与自由女神像的历史认知", "国旗国歌国徽与升旗仪式"),
    "culture-holiday-mid": ("感恩节独立日历史节点", "风俗体验到文化传承主题"),
    "culture-stories-mid": ("民间故事、传说、神话英雄", "神话成语寓言历史故事"),
    "culture-heritage-late": ("神话传说与原型主题", "传统美德短论与观点表达"),
    "culture-diversity-early": ("本土部落与多元人群实景", "本民族与56个民族大家庭"),
    "culture-diversity-world": ("宅地法铁路移民解释变化", "国家信息、节日、文化标志物感知"),
}

# 家长视角的“差异”再提炼：只覆盖高价值条目，不做自动批量生成。
DIFF_REFINEMENTS: dict[str, dict[str, str]] = {
    "math-number-early": {
        "axis": "跳数",
        "us": "2年级明确数到1000，按5/10/100跳数",
        "cn": "中国侧未作独立要求；相近为1-2年级认、读、写万以内数",
        "reading": "两边都从学前数数起步；到2年级美国把跳数写成明确要求，中国侧未把按5/10/100跳数列为独立要求。",
    },
    "micro-math-count-cardinality": {
        "axis": "任务形态",
        "us": "4枚硬币→数到100；2年级按5/10/100跳数",
        "cn": "5以内点数→万以内认读；未列跳数要求",
        "reading": "同样叫数数，美国接上硬币和跳数，中国接上点数和数位认读；数量上限不能单独判难易。",
    },
    "micro-math-add-sub-10": {
        "axis": "熟练口径",
        "us": "K年级10以内解题，5以内熟练",
        "cn": "大班理解意义，1-2年级20以内熟练口算",
        "reading": "美国先要求会用在10以内情境，中国把熟练口径提到20以内并补上加减互逆。",
    },
    "micro-science-experiment-measure": {
        "axis": "器材取数",
        "us": "写设计与实施调查，未点名温度计等量具",
        "cn": "明确温度计、量筒、电子秤取数",
        "reading": "美国看会不会做调查，中国把用仪器拿数据写成可检查要求，家长更容易判断练习是否到位。",
    },
    "micro-science-cells-genetics": {
        "axis": "解释层级",
        "us": "4年级细胞、6年级染色体",
        "cn": "同期以动植物观察、分类和自然笔记为主",
        "reading": "同一段生命科学，美国更早讲机制，中国先铺现象与分类；不能简单说谁讲得多。",
    },
    "micro-lang-read-basic": {
        "axis": "朗读",
        "us": "此段以听读理解各类文本为主",
        "cn": "正确、流利、有感情朗读并学默读",
        "reading": "中国把朗读写成显性目标，美国此段更重听读理解，家里的练法会不同。",
    },
    "micro-lang-writing": {
        "axis": "写法与频次",
        "us": "叙事文、议论文、说明文与段落结构",
        "cn": "记实/想象/应用文，每学年约16次习作并修改",
        "reading": "美国偏体裁和结构分析，中国同时管写多少和修改流程，两个都是可观察的练习抓手。",
    },
    "micro-arts-visual": {
        "axis": "范画",
        "us": "K起认线条色彩、讨论名家作品",
        "cn": "要求画自己想画的人或事，不宜提供范画",
        "reading": "美国把名作当学习材料，中国明确不设范画；判断“像不像”之前先看各自定义的目标。",
    },
    "micro-motor-hop": {
        "axis": "量化标准",
        "us": "只列单脚跳形式，不写距离",
        "cn": "小班2米、中班5米、大班8米",
        "reading": "同样叫单脚跳，中国给了可测距离，美国只写动作形式；这直接影响家里怎么练。",
    },
}


def apply_diff_refinements(rows: list[dict[str, Any]]) -> None:
    """把人工提炼的家长视角差异写回原有“差异”行，不新增展示层。"""
    for row in rows:
        spec = DIFF_REFINEMENTS.get(row["id"])
        if not spec:
            continue
        axes = row.setdefault("深度参数", [])
        refined = ["差异：" + spec["axis"], spec["us"], spec["cn"]]
        for idx, axis in enumerate(axes):
            if axis and str(axis[0]).startswith("差异"):
                axes[idx] = refined
                break
        else:
            axes.append(refined)
        if spec.get("reading"):
            row["深度解读"] = spec["reading"]


# Final wording corrections after the audit. Evidence-level fixes live in the
# matchers/specs above; these patches only repair narrative fields whose old
# wording no longer matches the corrected evidence.
AUDIT_ROW_FIXES: dict[str, dict[str, Any]] = {
    "geo-map-basic": {
        "短结论": "美国小学阶段学习图例、方向和简单地图阅读，本套中国资料未收同粒度条目。",
        "关系": "本数据中仅美国有",
        "单侧原因": "本数据未收录对侧同粒度条目",
        "深度解读": "美国1年级起把图例、四方向和读图写成技能；本套中国资料的3-4年级证据未落到图例方向，系统地图技能出现在后段。",
    },
    "geo-map-advanced": {
        "关系": "两边都有，5-6年级到初中中国把比例尺做成技能链。",
        "深度解读": "中国5-6年级到初中把比例尺、图例、经纬网做成技能链，美国5年级已用经纬度、坐标和投影读图。早期读图经验与后段系统化不是一回事。",
    },
    "science-earth-advanced": {
        "短结论": "初中阶段中国用板块构造解释火山地震，美国此组证据偏资源与日月食。",
        "深度解读": "中国7-9年级把自转公转模型与板块构造解释并列写出；美国同段这组证据主要讲自然资源和日月食，概念覆盖不同，不宜直接判深浅。",
    },
    "science-matter-properties": {
        "短结论": "中国3-4年级先做性质观察，美国5年级系统讲性质与守恒。",
    },
    "science-evolution": {
        "关系": "两边都有，阶段接近，证据侧重不同。",
    },
    "geo-population": {
        "短结论": "小学5-6年级美国持续出现人口、移民和城市内容。",
        "单侧原因": "本套资料未作独立要求",
    },
    "science-climate-data": {
        "关系": "本数据中仅中国有",
        "单侧原因": "本套资料未作独立要求",
    },
    "geo-direction-early": {
        "关系": "中国小班用方位词起步，美国大班直接做大洲定位。",
    },
    "geo-continents-basic": {
        "单侧原因": "本数据未收录对侧对应概念",
        "重评说明": "本数据未收录对侧对应概念；仅指本套资料中只在该侧找到对应概念，不代表另一侧绝对缺失。",
    },
}

# 这些单侧行的另一侧有相关内容，只是本套资料未单列同类条目；不能再写成
# “另一侧没有形成对应簇”。
for _soft_id in (
    "one-us-ela-poetry", "one-us-ela-speaking", "one-us-ela-grammar",
    "one-cn-chinese-grammar", "one-us-math-sorting", "one-us-math-ratios",
    "one-us-math-functions", "one-us-culture-religions", "one-cn-math-estimate",
    "one-us-science-collisions", "one-cn-chem-resources",
):
    AUDIT_ROW_FIXES[_soft_id] = {
        "单侧原因": "另一侧有相关内容，本条按本侧独立成条口径列出",
        "重评说明": "另一侧有相关内容但已归入其他簇；仅指本套资料的条目组织方式，不代表另一侧绝对缺失。",
    }


def apply_audit_row_fixes(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        if row.get("类型") == "单侧概念簇":
            for key in ("短结论", "深度解读", "重评关系", "重评说明", "说明"):
                value = row.get(key)
                if isinstance(value, str):
                    row[key] = (
                        value.replace("中国侧未在本数据中形成对应簇", "另一侧未在本数据中单列同类条目")
                        .replace("美国侧未在本数据中形成对应簇", "另一侧未在本数据中单列同类条目")
                    )
            for key, value in row.get("深度对标", {}).items():
                if isinstance(value, str):
                    row["深度对标"][key] = (
                        value.replace("中国侧未在本数据中形成对应簇", "另一侧未在本数据中单列同类条目")
                        .replace("美国侧未在本数据中形成对应簇", "另一侧未在本数据中单列同类条目")
                    )
        fixes = AUDIT_ROW_FIXES.get(row["id"])
        if not fixes:
            continue
        for key, value in fixes.items():
            if key == "深度对标" and isinstance(value, dict):
                row.setdefault(key, {}).update(value)
            elif isinstance(value, str):
                row[key] = normalize_stage_text(value)
            else:
                row[key] = value


def short_stage_label(value: str) -> str:
    text = str(value or "").replace("美国", "").replace("中国", "")
    text = re.sub(r"（[^）]*）", "", text)
    text = text.replace("幼儿园大班K", "大班K").replace("幼儿园大班", "大班K")
    text = text.replace("幼儿园前班", "学前")
    text = text.replace("幼儿园小班", "小班").replace("幼儿园中班", "中班")
    text = text.replace("幼儿园", "学前").replace("小学", "").replace("初中", "")
    text = text.strip() or "无"
    return "大班K" if text == "大班" else text


def short_follow_label(value: str) -> str:
    if not value or str(value).startswith("无") or str(value).startswith("不适用"):
        return "无"
    parts = re.split(r"[、,，]", str(value))
    return "→".join(short_stage_label(part) for part in parts if part.strip())


def concept_axes(row: dict[str, Any]) -> list[list[str]]:
    us_diff, cn_diff = CONCEPT_AXES[row["id"]]
    return [
        ["起步", short_stage_label(row["美国"]["首次年级"]), short_stage_label(row["中国"]["首次年级"])],
        ["后续", short_follow_label(row["美国"].get("后续学段")), short_follow_label(row["中国"].get("后续学段"))],
        ["差异", us_diff, cn_diff],
    ]


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>中美课程标准 · 概念对照</title>
<style>
  :root {
    --bg: #f7f5f4;
    --surface: #fffdfc;
    --surface-2: #f4efee;
    --border: #e5dcda;
    --text: #2f2928;
    --muted: #7d7472;
    --us: #42657d;
    --us-soft: #e9eff3;
    --cn: #8b4c4c;
    --cn-soft: #f4e7e7;
    --warn: #8a6a35;
    --warn-soft: #f5efe2;
    --radius: 14px;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 16px;
    line-height: 1.5;
    -webkit-text-size-adjust: 100%;
  }
  header {
    position: sticky;
    top: 0;
    z-index: 10;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 8px 12px calc(7px + env(safe-area-inset-top));
  }
  .head-top { display: flex; align-items: center; gap: 7px; }
  h1 { margin: 0; font-size: 18px; font-weight: 650; letter-spacing: .01em; }
  .badge {
    font-size: 12px; color: var(--cn); background: var(--cn-soft);
    border-radius: 999px; padding: 2px 8px; white-space: nowrap;
  }
  .sub { margin: 1px 0 6px; font-size: 13px; color: var(--muted); }
  .tabs { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; }
  .tabs button {
    border: 1px solid var(--border); background: var(--surface-2); color: var(--muted);
    border-radius: 8px; padding: 7px 0; font-size: 11px; cursor: pointer;
  }
  .tabs button.active {
    background: var(--cn); border-color: var(--cn); color: #fff;
  }
  .tabs button .count {
    margin-left: 2px; opacity: .72; font-variant-numeric: tabular-nums;
  }
  .tabs button.active .count { opacity: .9; }
  .filter-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; margin-top: 4px; }
  .filter-row button {
    border: 1px solid var(--border); background: var(--surface); color: var(--muted);
    border-radius: 8px; padding: 5px 0; font-size: 11px; cursor: pointer;
  }
  .filter-row button.active { background: var(--cn); border-color: var(--cn); color: #fff; }
  .side-note { margin: 5px 0 0; font-size: 11px; color: var(--muted); }
  .empty { padding: 24px 12px; text-align: center; color: var(--muted); font-size: 13px; }
  main { padding: 10px 12px 24px; max-width: 480px; margin: 0 auto; }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 11px 12px 10px;
    box-shadow: 0 1px 3px rgba(47, 41, 40, .04);
  }
  .card-top { display: flex; justify-content: space-between; align-items: center; }
  .group {
    font-size: 12px; color: var(--cn); background: var(--cn-soft);
    padding: 2px 8px; border-radius: 999px;
  }
  .pager { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--muted); }
  .pager-label { position: relative; display: inline-block; }
  .pager-label::after {
    content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 2px;
    border-radius: 2px; background: linear-gradient(to right, var(--cn) var(--pct, 0%), var(--border) var(--pct, 0%));
  }
  .pager button {
    border: 1px solid var(--border); background: var(--surface-2); color: var(--muted);
    border-radius: 6px; padding: 1px 6px 2px; font-size: 13px; line-height: 1.2; cursor: pointer;
  }
  h2 { margin: 5px 0 2px; font-size: 22px; line-height: 1.25; }
  .takeaway {
    margin: 0 0 7px; font-size: 15px; color: var(--muted);
    line-height: 1.45; min-height: 44px;
  }
  .track { border-top: 1px solid var(--border); padding-top: 5px; }
  .track-head, .track-row {
    display: grid;
    grid-template-columns: 34px repeat(5, 1fr);
    align-items: center;
    text-align: center;
  }
  .track-head { font-size: 11px; color: var(--muted); margin-bottom: 1px; }
  .track-row { height: 22px; }
  .side { font-size: 13px; text-align: left; font-weight: 600; }
  .us-label { color: var(--us); }
  .cn-label { color: var(--cn); }
  .cell { display: flex; justify-content: center; align-items: center; height: 100%; }
  .dot { width: 10px; height: 10px; border-radius: 50%; display: block; }
  .dot.us { background: var(--us); }
  .dot.cn { background: var(--cn); }
  .flag {
    display: inline-block; font-size: 11px; color: var(--warn);
    background: var(--warn-soft); border-radius: 999px;
    padding: 2px 8px; margin-bottom: 6px;
  }
  .axes { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 2px; }
  .axes th, .axes td {
    border-bottom: 1px solid var(--border);
    padding: 6px 5px; text-align: left; vertical-align: top;
  }
  .axes tbody th { width: 52px; color: var(--muted); font-weight: 500; }
  .axes th.us, .axes td.us { width: calc(50% - 26px); color: var(--us); }
  .axes th.cn, .axes td.cn { width: calc(50% - 26px); color: var(--cn); }
  .axes tr:last-child th, .axes tr:last-child td { border-bottom: 0; }
  .reading {
    margin: 7px 0 2px; padding: 7px 9px;
    background: var(--surface-2); border-radius: 8px;
    font-size: 12px; line-height: 1.55; color: var(--text);
  }
  .reading p { margin: 0; }
  .reading .reading-label { color: var(--muted); font-weight: 600; }
  .evidence { margin-top: 8px; border-top: 1px solid var(--border); padding-top: 7px; }
  .evidence-label { margin: 0 0 5px; font-size: 11px; color: var(--muted); font-weight: 600; }
  .ev-block { margin-bottom: 7px; }
  .ev-block h3 { margin: 0 0 2px; font-size: 13px; color: var(--us); }
  .ev-block.cn h3 { color: var(--cn); }
  .ev-item + .ev-item { margin-top: 6px; }
  .ev-grade { margin: 0 0 3px; font-size: 12px; color: var(--text); font-weight: 600; }
  .ev-content {
    background: var(--surface-2); border-radius: 8px; padding: 5px 7px;
  }
  .ev-text { margin: 0; font-size: 13px; line-height: 1.45; color: var(--text); }
  .ev-content .ev-source + .ev-text { margin-top: 6px; }
  .ev-source { margin: 2px 0 0; font-size: 11px; color: var(--muted); }
  footer { margin-top: 10px; font-size: 12px; color: var(--muted); text-align: center; }
  footer a { color: var(--cn); text-decoration: none; }
  @media (max-width: 360px) {
    main { padding-left: 9px; padding-right: 9px; }
    .card { padding-left: 10px; padding-right: 10px; }
    .axes { font-size: 11px; }
  }
</style>
</head>
<body>
<header>
  <div class="head-top">
    <h1>中美课程标准 · 概念对照</h1>
    <span class="badge" id="badge"></span>
  </div>
  <p class="sub">数学 / 科学 / 地理 / 语言 / 文化 / 儿童发展 / 艺术 · 按概念顺序单条阅读</p>
  <nav class="tabs" id="tabs"></nav>
  <div class="filter-row" id="comparability"></div>
</header>
<main>
  <section class="card" id="card"></section>
  <footer>
    本页精选七个领域的 <span id="total"></span> 条概念，不是课标全部内容；“仅美国 / 仅中国”表示本套资料中只在该侧找到对应概念，不代表另一侧绝对缺失。
  </footer>
</main>
<script id="dataset" type="application/json">__PAYLOAD__</script>
<script>
const DATA = JSON.parse(document.getElementById("dataset").textContent);
const DOMAINS = ["数学", "科学", "地理", "语言与读写", "文化", "儿童发展", "艺术"];
const DOMAIN_LABELS = {"数学": "数学", "科学": "科学", "地理": "地理", "语言与读写": "语言", "文化": "文化", "儿童发展": "儿童发展", "艺术": "艺术"};
const BANDS = ["学前", "1-2年级", "3-4年级", "5-6年级", "7-9年级"];
const BAND_MAP = {
  "幼儿园前班": [0], "幼儿园大班K": [0],
  "小班（3-4岁）": [0], "中班（4-5岁）": [0], "大班（5-6岁）": [0], "幼儿园通用": [0],
  "小学1年级": [1], "小学2年级": [1], "小学1-2年级": [1],
  "小学3年级": [2], "小学4年级": [2], "小学3-4年级": [2],
  "小学5年级": [3], "小学6年级": [3], "小学5-6年级": [3],
  "初中7年级": [4], "初中8年级": [4], "初中7-9年级": [4],
  "小学1-6年级": [1, 2, 3], "全学段通用": [0, 1, 2, 3, 4],
  "学前": [0], "1-2年级": [1], "3-4年级": [2], "5-6年级": [3], "7-9年级": [4]
};
const GRADE_RANK = {
  "美国幼儿园前班（对应中国小班、中班）": 0,
  "幼儿园小班（3-4岁）": 0.1,
  "幼儿园小班/中班/大班（通用）": 0.2,
  "幼儿园中班（4-5岁）": 0.3,
  "美国幼儿园大班（K）": 0.4,
  "幼儿园大班（5-6岁）": 0.4,
  "小学1-6年级": 1,
  "小学1-2年级": 1,
  "美国小学1年级": 1,
  "美国小学2年级": 2,
  "美国小学3年级": 3,
  "小学3-4年级": 3,
  "美国小学4年级": 4,
  "美国小学5年级": 5,
  "小学5-6年级": 5,
  "美国小学6年级": 6,
  "美国初中7年级": 7,
  "初中7-9年级": 7,
  "美国初中8年级": 8
};
function gradeRank(ev) {
  const key = ev && ev["年级"];
  return GRADE_RANK[key] === undefined ? 99 : GRADE_RANK[key];
}
const allRowsByDomain = {};
DOMAINS.forEach(function(d) {
  allRowsByDomain[d] = DATA["概念簇"].filter(function(r) { return r["领域"] === d; })
    .sort(function(a, b) { return a.story_order - b.story_order; });
});
const state = { domain: "数学", comparability: "可比", idx: 0 };
const card = document.getElementById("card");
const tabs = document.getElementById("tabs");
const filterBar = document.getElementById("comparability");
const FILTERS = [["可比", "可比项"], ["仅中国", "仅中国"], ["仅美国", "仅美国"], ["全部", "全部"]];
function visibleRows() {
  return allRowsByDomain[state.domain].filter(function(r) {
    return state.comparability === "全部" || r["可比性"] === state.comparability;
  });
}
function renderFilters() {
  const domainRows = allRowsByDomain[state.domain];
  filterBar.innerHTML = FILTERS.map(function(pair) {
    const value = pair[0], label = pair[1];
    const n = value === "全部"
      ? domainRows.length
      : domainRows.filter(function(r) { return r["可比性"] === value; }).length;
    return "<button data-comparability=\"" + value + "\"" +
      (value === state.comparability ? " class=\"active\"" : "") + ">" +
      label + " " + n + "</button>";
  }).join("");
  filterBar.querySelectorAll("button").forEach(function(btn) {
    btn.addEventListener("click", function() {
      state.comparability = btn.dataset.comparability;
      state.idx = 0;
      renderTabs();
      renderFilters();
      render();
    });
  });
}

function esc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function plainEvidence(value) {
  return String(value == null ? "" : value).replace(/^\[暂存\]\s*/, "");
}
const SOURCE_SHORT = {
  "Core Knowledge Sequence 2023 · k8": "Core Knowledge K-8",
  "Core Knowledge Sequence 2023 · preschool": "Core Knowledge 学前",
  "教育部《3-6岁儿童学习与发展指南》（2012）": "《3-6岁指南》",
  "moe-cn-2022-chinese": "《语文课标2022》",
  "moe-cn-2022-politics": "《道法课标2022》",
  "moe-cn-2022-english": "《英语课标2022》",
  "moe-cn-2022-history": "《历史课标2022》",
  "moe-cn-2022-pe": "《体育与健康课标2022》"
};
function sourceRef(ev) {
  if (!ev) return "";
  const source = SOURCE_SHORT[ev["来源"]] || String(ev["来源"] || "")
    .replace(/^.*《/, "《").replace(/教育部/, "");
  const page = ev["来源页"] == null ? "" : " · 第" + ev["来源页"] + "页";
  return source + page;
}
function bandsFor(label) {
  return BAND_MAP[label] || [];
}
function domainCount(domain) {
  return state.comparability === "全部"
    ? allRowsByDomain[domain].length
    : allRowsByDomain[domain].filter(function(r) { return r["可比性"] === state.comparability; }).length;
}
function renderTabs() {
  tabs.innerHTML = DOMAINS.map(function(d) {
    return "<button data-domain=\"" + d + "\"" + (d === state.domain ? " class=\"active\"" : "") + ">" +
      (DOMAIN_LABELS[d] || d) + " <span class=\"count\">" + domainCount(d) + "</span></button>";
  }).join("");
  tabs.querySelectorAll("button").forEach(function(btn) {
    btn.addEventListener("click", function() {
      state.domain = btn.dataset.domain;
      state.idx = 0;
      renderTabs();
      renderFilters();
      render();
    });
  });
}
function trackCells(row, side) {
  const present = new Set();
  row["展示轨道"][side].forEach(function(label) {
    bandsFor(label).forEach(function(band) { present.add(band); });
  });
  const cls = side === "美国" ? "us" : "cn";
  return BANDS.map(function(_, band) {
    return "<span class=\"cell\">" + (present.has(band) ? "<i class=\"dot " + cls + "\"></i>" : "") + "</span>";
  }).join("");
}
function activeSides(row) {
  if (row["可比性"] === "仅美国") return ["美国"];
  if (row["可比性"] === "仅中国") return ["中国"];
  return ["美国", "中国"];
}
function oneSidedNote(row) {
  if (!row["可比性"] || row["可比性"] === "可比") return "";
  const other = row["可比性"] === "仅美国" ? "中国" : "美国";
  return "<p class=\"ev-source\">" + other + "：本资料未涵盖（" +
    esc(row["单侧原因"] || "本数据未收录对侧对应概念") + "）</p>";
}
function sideEvidence(row, side) {
  const evs = (row[side]["最早证据"] || []).slice();
  const later = row[side]["后续代表证据"];
  if (later) evs.push(later);
  return evs.sort(function(a, b) { return gradeRank(a) - gradeRank(b); });
}
function evidenceItemHtml(grade, evs) {
  const body = evs.map(function(ev) {
    const ref = sourceRef(ev);
    return "<p class=\"ev-text\">" + esc(plainEvidence(ev && ev["文本"])) + "</p>" +
      (ref ? "<p class=\"ev-source\">" + esc(ref) + "</p>" : "");
  }).join("");
  return "<div class=\"ev-item\">" +
    "<p class=\"ev-grade\">" + esc(grade) + "</p>" +
    "<div class=\"ev-content\">" + body + "</div>" +
    "</div>";
}
function evidenceHtml(row) {
  return activeSides(row).map(function(side) {
    const evs = sideEvidence(row, side);
    const isCn = side === "中国";
    let html = "<div class=\"ev-block" + (isCn ? " cn" : "") + "\"><h3>" + side + "</h3>";
    if (!evs.length) {
      html += "<div class=\"ev-content\"><p class=\"ev-text\">无对应条目</p></div>";
    } else {
      let grade = null;
      let group = [];
      function flush() {
        if (group.length) html += evidenceItemHtml(grade, group);
      }
      evs.forEach(function(ev) {
        const nextGrade = ev && ev["年级"];
        if (nextGrade !== grade) {
          flush();
          grade = nextGrade;
          group = [];
        }
        group.push(ev);
      });
      flush();
    }
    return html + "</div>";
  }).join("") + oneSidedNote(row);
}
function axesHtml(row) {
  let html = "";
  if (row["可比性"] && row["可比性"] !== "可比") {
    html += "<div class=\"reading\"><p><span class=\"reading-label\">说明：</span>" +
      esc(row["单侧原因"] || "本数据未收录对侧对应概念") + "。" +
      esc(row["深度解读"] || row["短结论"]) + "</p></div>";
    return html;
  }
  if (row["深度参数"] && row["深度参数"].length) {
    if (row["单侧标记"]) html += "<span class=\"flag\">" + esc(row["单侧标记"]) + "</span>";
    html += "<table class=\"axes\"><tbody>";
    row["深度参数"].forEach(function(axis) {
      html += "<tr><th>" + esc(axis[0]) + "</th><td class=\"us\">" + esc(axis[1]) + "</td><td class=\"cn\">" + esc(axis[2]) + "</td></tr>";
    });
    html += "</tbody></table>";
  }
  if (row["深度解读"]) {
    html += "<div class=\"reading\"><p><span class=\"reading-label\">解读：</span>" + esc(row["深度解读"]) + "</p></div>";
  }
  return html;
}
function render() {
  const list = visibleRows();
  if (!list.length) {
    card.innerHTML = "<div class=\"empty\">当前筛选下暂无条目。</div>";
    return;
  }
  const row = list[state.idx];
  const pct = ((state.idx + 1) / list.length * 100).toFixed(2) + "%";
  const oneSided = row["可比性"] && row["可比性"] !== "可比";
  const sides = oneSided ? [row["可比性"] === "仅美国" ? "美国" : "中国"] : ["美国", "中国"];
  const labelCls = function(side) { return side === "美国" ? "us-label" : "cn-label"; };
  const trackRows = sides.map(function(side) {
    return "<div class=\"track-row\"><span class=\"side " + labelCls(side) + "\">" + side + "</span>" +
      trackCells(row, side) + "</div>";
  }).join("");
  const missingNote = oneSided
    ? "<p class=\"side-note\">另一侧：本资料未涵盖（" + esc(row["单侧原因"] || "本数据未收录对侧对应概念") + "）</p>"
    : "";
  card.innerHTML =
    "<div class=\"card-top\"><span class=\"group\">" + esc(row["分组"]) +
    (oneSided ? " · " + esc(row["可比性"]) : "") + "</span>" +
    "<span class=\"pager\" style=\"--pct:" + pct + "\"><button id=\"prev\" aria-label=\"上一条\">←</button>" +
    "<span class=\"pager-label\">概念 " + (state.idx + 1) + " / " + list.length + "</span>" +
    "<button id=\"next\" aria-label=\"下一条\">→</button></span></div>" +
    "<h2>" + esc(row["概念簇"]) + "</h2>" +
    "<p class=\"takeaway\">" + esc(row["短结论"]) + "</p>" +
    "<div class=\"track\">" +
    "<div class=\"track-head\"><span></span>" + BANDS.map(function(b) { return "<span>" + b + "</span>"; }).join("") + "</div>" +
    trackRows + missingNote +
    "</div>" +
    axesHtml(row) +
    "<div class=\"evidence\"><p class=\"evidence-label\">证据</p>" +
    evidenceHtml(row) + "</div>";

  document.getElementById("prev").addEventListener("click", function() {
    state.idx = (state.idx - 1 + list.length) % list.length;
    render();
  });
  document.getElementById("next").addEventListener("click", function() {
    state.idx = (state.idx + 1) % list.length;
    render();
  });
}
document.addEventListener("keydown", function(e) {
  const list = visibleRows();
  if (!list.length) return;
  if (e.key === "ArrowRight") { state.idx = (state.idx + 1) % list.length; render(); }
  if (e.key === "ArrowLeft") { state.idx = (state.idx - 1 + list.length) % list.length; render(); }
});
document.getElementById("badge").textContent = "精选 " + DATA["概念簇"].length + " 条";
document.getElementById("total").textContent = DATA["概念簇"].length;
renderTabs();
renderFilters();
render();
</script>
</body>
</html>
"""


def expand_clusters() -> list[dict[str, Any]]:
    """把粗粒度簇拆成每条最多 2 个展示学段的细粒度簇。"""
    expanded: list[dict[str, Any]] = []
    for cluster in CLUSTERS:
        base = STORY_META[cluster["id"]]
        specs = SPLIT_SPEC.get(cluster["id"])
        if not specs:
            item = dict(cluster)
            item["_parent"] = cluster["id"]
            item["_group"] = base["group"]
            item["_short"] = base["short"]
            item["_base_order"] = base["order"]
            expanded.append(item)
            continue
        for index, spec in enumerate(specs):
            item = dict(cluster)
            item["id"] = spec["id"]
            item["concept"] = spec["concept"]
            item["_parent"] = cluster["id"]
            item["_group"] = spec["group"]
            item["_short"] = spec["short"]
            item["_base_order"] = base["order"] + index * 0.01
            item["us"] = dict(cluster["us"])
            item["cn"] = dict(cluster["cn"])
            item["us"]["bands"] = spec["us_bands"]
            item["cn"]["bands"] = spec["cn_bands"]
            if spec.get("us_text_regex"):
                item["us"]["text_regex"] = spec["us_text_regex"]
            if spec.get("cn_text_regex"):
                item["cn"]["text_regex"] = spec["cn_text_regex"]
            if spec.get("cn_preschool_regex"):
                item["cn"]["preschool_regex"] = spec["cn_preschool_regex"]
            if spec.get("cn_preschool_core_regex"):
                item["cn"]["preschool_core_regex"] = spec["cn_preschool_core_regex"]
            if spec.get("us_exclude_ids"):
                item["us"]["exclude_ids"] = set(spec["us_exclude_ids"])
            if spec.get("cn_exclude_ids"):
                item["cn"]["exclude_ids"] = set(spec["cn_exclude_ids"])
            if spec.get("us_core_regex"):
                item["us"]["core_regex"] = spec["us_core_regex"]
            if spec.get("cn_core_regex"):
                item["cn"]["core_regex"] = spec["cn_core_regex"]
            if spec.get("us_topic_regex"):
                item["us"]["topic_regex"] = spec["us_topic_regex"]
            expanded.append(item)

    for domain in ("数学", "科学", "地理", "语言与读写", "文化"):
        subset = [item for item in expanded if item["domain"] == domain]
        subset.sort(key=lambda item: item["_base_order"])
        for order, item in enumerate(subset, 1):
            item["story_order"] = order
    return expanded


STAGE_LABEL_RULES = [
    ("小学低年级", "1-2年级"),
    ("小学低段", "1-2年级"),
    ("小学中年级", "3-4年级"),
    ("小学中段", "3-4年级"),
    ("小学高年级", "5-6年级"),
    ("小学高段", "5-6年级"),
    ("小学低", "1-2年级"),
    ("小学中", "3-4年级"),
    ("小学高", "5-6年级"),
    ("初中阶段", "7-9年级"),
    ("幼儿园阶段", "学前"),
    ("低龄", "学前"),
]


def normalize_stage_text(value: Any) -> Any:
    """把面向读者的学段叙述统一成家长可读的年级带。"""
    if not isinstance(value, str):
        return value
    for old, new in STAGE_LABEL_RULES:
        value = value.replace(old, new)
    return value


BAND_LABELS = ["学前", "1-2年级", "3-4年级", "5-6年级", "7-9年级"]


def micro_evidence(item: dict[str, Any], side: str) -> dict[str, Any]:
    """微指标证据沿用统一字段，保留完整原文，避免截断造成前后不完整。"""
    return evidence(item, side)


def micro_distribution(
    items: list[dict[str, Any]], side: str, bands: list[int]
) -> list[dict[str, Any]]:
    counts = {band: 0 for band in bands}
    for item in items:
        band = us_band(item) if side == "美国" else cn_band(item)
        if band in counts:
            counts[band] += 1
    return [
        {"年级": BAND_LABELS[band], "命中": counts[band], "展示": counts[band], "暂存": 0}
        for band in bands
    ]


# 单侧概念簇：从两套源资料中未被现有可比簇占用的主题生成。
# “仅美国/仅中国”只表示本数据集中只在该侧形成概念簇，不代表绝对意义上的课程有无。
ONE_SIDED_SPECS: list[dict[str, Any]] = [
    {
        "id": "one-us-ela-poetry", "side": "美国", "domain": "语言与读写", "group": "文学与诗歌",
        "concept": "诗歌体裁与赏析", "short": "本套美国资料把诗歌单列为跨年级阅读线索，另一侧有相关内容但未单列同类条目。",
        "subjects": ["English Language Arts"], "topic_regex": "Poetry", "text_regex": "poem|poetry|rhyme|verse|haiku|sonnet", "text_only": True,
        "exclude_ids": ["n00260", "n00261", "n00262"],
    },
    {
        "id": "one-us-ela-punctuation", "side": "美国", "domain": "语言与读写", "group": "写作与表达",
        "concept": "大小写与标点规范", "short": "本套美国资料把拼写与标点写成独立的语言目标，中国侧未在本数据中形成对应簇。",
        "subjects": ["English Language Arts"], "topic_regex": "Capitalization and Punctuation", "text_regex": ".*",
    },
    {
        "id": "one-us-ela-conventions", "side": "美国", "domain": "语言与读写", "group": "写作与表达",
        "concept": "语言规则与句子结构", "short": "本套美国资料单列语言规则训练，中国侧未在本数据中形成对应簇。",
        "subjects": ["English Language Arts"], "topic_regex": "Language Conventions", "text_regex": ".*",
    },
    {
        "id": "one-us-ela-research", "side": "美国", "domain": "语言与读写", "group": "写作与表达",
        "concept": "资料查询与研究写作", "short": "本套美国资料把资料查找、整理与成文连成一条线，中国侧未在本数据中形成对应簇。",
        "subjects": ["English Language Arts"], "topic_regex": "Conducting Research", "text_regex": ".*",
    },
    {
        "id": "one-us-ela-grammar", "side": "美国", "domain": "语言与读写", "group": "写作与表达",
        "concept": "语法知识", "short": "本套美国资料把语法项目单列为年级目标，另一侧有相关内容但未单列同类条目。",
        "subjects": ["English Language Arts"], "topic_regex": "Grammar", "text_regex": ".*",
    },
    {
        "id": "one-us-ela-narrative", "side": "美国", "domain": "语言与读写", "group": "写作与表达",
        "concept": "叙事写作进阶", "short": "本套美国资料把叙事写作按年级细化，中国侧未在本数据中形成对应簇。",
        "subjects": ["English Language Arts"], "topic_regex": "Narrative Writing", "text_regex": ".*",
    },
    {
        "id": "one-us-music-elements", "side": "美国", "domain": "艺术", "group": "音乐与律动",
        "concept": "音乐要素：节奏、旋律与音色", "short": "本套美国资料把音乐要素作为独立目标贯穿K-8，中国侧未在本数据中形成对应簇。",
        "subjects": ["Music"], "topic_regex": "Elements of Music", "text_regex": ".*",
    },
    {
        "id": "one-us-music-listening", "side": "美国", "domain": "艺术", "group": "音乐与律动",
        "concept": "音乐聆听与理解", "short": "本套美国资料单列聆听与理解曲目，中国侧未在本数据中形成对应簇。",
        "subjects": ["Music"], "topic_regex": "Listening and Understanding", "text_regex": ".*",
    },
    {
        "id": "one-us-art-elements", "side": "美国", "domain": "艺术", "group": "美术与创造",
        "concept": "美术要素与视觉表达", "short": "本套美国资料把色彩、线条、构图等美术要素单列，中国侧未在本数据中形成对应簇。",
        "subjects": ["Visual Arts"], "topic_regex": "Elements of Art", "text_regex": ".*",
    },
    {
        "id": "one-us-art-history", "side": "美国", "domain": "艺术", "group": "美术与创造",
        "concept": "艺术史与流派", "short": "本套美国资料按时期和流派组织艺术史内容，中国侧未在本数据中形成对应簇。",
        "subjects": ["Visual Arts"], "topic_regex": "Art History", "text_regex": ".*",
    },
    {
        "id": "one-us-presidents", "side": "美国", "domain": "文化", "group": "国家认同",
        "concept": "总统与政治制度", "short": "本套美国资料把总统与政治制度单列，中国侧未在本数据中形成对应簇。",
        "subjects": ["History and Geography"], "topic_regex": "Presidents and Politics", "text_regex": ".*",
    },
    {
        "id": "one-us-westward", "side": "美国", "domain": "文化", "group": "国家认同",
        "concept": "西进运动与国家叙事", "short": "本套美国资料以历史事件叙述国家形成，中国侧未在本数据中形成对应簇。",
        "subjects": ["History and Geography"], "topic_regex": "Westward Expansion", "text_regex": ".*",
    },
    {
        "id": "one-us-civil-war", "side": "美国", "domain": "文化", "group": "国家认同",
        "concept": "内战、原因与重建", "short": "本套美国资料把内战原因、冲突与后果连成专题，中国侧未在本数据中形成对应簇。",
        "subjects": ["History and Geography"], "topic_regex": "The Civil War", "text_regex": ".*",
    },
    {
        "id": "one-us-ancient", "side": "美国", "domain": "文化", "group": "文化传承",
        "concept": "古代文明的持久思想", "short": "本套美国资料单列古代文明的思想遗产，中国侧未在本数据中形成对应簇。",
        "subjects": ["History and Geography"], "topic_regex": "Lasting Ideas from Ancient Civilizations", "text_regex": ".*",
    },
    {
        "id": "one-us-exploration", "side": "美国", "domain": "文化", "group": "多元理解",
        "concept": "探索、贸易与文化交流", "short": "本套美国资料以探索与贸易解释文化接触，中国侧未在本数据中形成对应簇。",
        "subjects": ["History and Geography"], "topic_regex": "Exploration, Trade, and Settlement", "text_regex": ".*",
    },
    {
        "id": "one-us-world-geography", "side": "美国", "domain": "地理", "group": "世界地理",
        "concept": "世界地理专题", "short": "本套美国资料单列世界地理专题，中国侧未在本数据中形成对应簇。",
        "subjects": ["History and Geography"], "topic_regex": "World Geography", "text_regex": ".*",
    },
    {
        "id": "one-us-science-biographies", "side": "美国", "domain": "科学", "group": "探究与工程",
        "concept": "科学家传记与科学史", "short": "本套美国资料把科学家生平作为独立内容，中国侧未在本数据中形成对应簇。",
        "subjects": ["Science"], "topic_regex": "Science Biographies", "text_regex": ".*",
    },
    {
        "id": "one-cn-poetry-recite", "side": "中国", "domain": "语言与读写", "group": "文学与诗歌",
        "concept": "优秀诗文背诵篇目", "short": "本套中国资料给出分学段古诗文背诵篇目，美国侧未在本数据中形成对应簇。",
        "subjects": ["语文"], "text_regex": "优秀诗文背诵推荐篇目",
    },
    {
        "id": "one-cn-character-list", "side": "中国", "domain": "语言与读写", "group": "识字与书写",
        "concept": "识字写字基本字表", "short": "本套中国资料以基本字表规定识字写字进度，美国侧未在本数据中形成对应簇。",
        "subjects": ["语文"], "text_regex": "识字、写字教学基本字表",
    },
    {
        "id": "one-cn-critical-reading", "side": "中国", "domain": "语言与读写", "group": "阅读理解",
        "concept": "思辨性阅读与表达", "short": "本套中国资料把思辨性阅读单列为学习任务群，美国侧未在本数据中形成对应簇。",
        "subjects": ["语文"], "text_regex": "思辨性阅读与表达",
    },
    {
        "id": "one-cn-practical-reading", "side": "中国", "domain": "语言与读写", "group": "阅读理解",
        "concept": "实用性阅读与交流", "short": "本套中国资料单列实用文本阅读与交流，美国侧未在本数据中形成对应簇。",
        "subjects": ["语文"], "text_regex": "实用性阅读与交流",
    },
    {
        "id": "one-cn-whole-book", "side": "中国", "domain": "语言与读写", "group": "阅读理解",
        "concept": "整本书阅读", "short": "本套中国资料把整本书阅读列为独立任务群，美国侧未在本数据中形成对应簇。",
        "subjects": ["语文"], "text_regex": "整本书阅读",
    },
    {
        "id": "one-cn-language-cross", "side": "中国", "domain": "语言与读写", "group": "写作与表达",
        "concept": "语文跨学科学习", "short": "本套中国资料单列跨学科语文实践，美国侧未在本数据中形成对应簇。",
        "subjects": ["语文"], "text_regex": "跨学科学习",
    },
    {
        "id": "one-cn-morality", "side": "中国", "domain": "文化", "group": "国家认同",
        "concept": "道德与法治课程内容", "short": "本套中国资料把道德与法治单列为课程内容，美国侧未在本数据中形成对应簇。",
        "subjects": ["道德与法治"], "text_regex": "课程内容",
    },
    {
        "id": "one-cn-labor-tasks", "side": "中国", "domain": "文化", "group": "文化传承",
        "concept": "劳动任务群", "short": "本套中国资料用任务群组织劳动教育，美国侧未在本数据中形成对应簇。",
        "subjects": ["劳动"], "text_regex": "任务群",
    },
    {
        "id": "one-cn-labor-craft", "side": "中国", "domain": "文化", "group": "文化传承",
        "concept": "传统工艺制作", "short": "本套中国资料把传统工艺制作写入劳动内容，美国侧未在本数据中形成对应簇。",
        "subjects": ["劳动"], "text_regex": "传统工艺制作",
    },
    {
        "id": "one-cn-pe-health", "side": "中国", "domain": "儿童发展", "group": "卫生与自理",
        "concept": "体育与健康：健康教育", "short": "本套中国资料把健康教育列为体育课程专题，美国侧未在本数据中形成对应簇。",
        "subjects": ["体育与健康"], "text_regex": "健康教育",
    },
    {
        "id": "one-cn-pe-fitness", "side": "中国", "domain": "儿童发展", "group": "动作与平衡",
        "concept": "体育与健康：体能", "short": "本套中国资料把体能单列为学段内容，美国侧未在本数据中形成对应簇。",
        "subjects": ["体育与健康"], "text_regex": "体能",
    },
    {
        "id": "one-cn-pe-sports", "side": "中国", "domain": "儿童发展", "group": "投掷与协调",
        "concept": "专项运动技能", "short": "本套中国资料列出专项运动技能的具体要求，美国侧未在本数据中形成对应簇。",
        "subjects": ["体育与健康"], "text_regex": "项目具体要求",
    },
    {
        "id": "one-cn-science-environment", "side": "中国", "domain": "科学", "group": "生态与地球",
        "concept": "人类活动与环境", "short": "本套中国资料单列人类活动与环境专题，美国侧未在本数据中形成对应簇。",
        "subjects": ["科学"], "text_regex": "人类活动与环境",
    },
    {
        "id": "one-cn-art-music", "side": "中国", "domain": "艺术", "group": "音乐与律动",
        "concept": "音乐学科内容", "short": "本套中国资料把音乐作为艺术课程分科内容，美国侧未在本数据中形成对应簇。",
        "subjects": ["艺术"], "text_regex": "音乐",
    },
    {
        "id": "one-cn-art-drama", "side": "中国", "domain": "艺术", "group": "表演与戏剧",
        "concept": "戏剧（含戏曲）", "short": "本套中国资料单列戏剧与戏曲内容，美国侧未在本数据中形成对应簇。",
        "subjects": ["艺术"], "text_regex": "戏剧（含戏曲）",
    },
    {
        "id": "one-cn-art-dance", "side": "中国", "domain": "艺术", "group": "表演与戏剧",
        "concept": "舞蹈", "short": "本套中国资料把舞蹈列为艺术课程分科内容，美国侧未在本数据中形成对应簇。",
        "subjects": ["艺术"], "text_regex": "舞蹈",
    },
    {
        "id": "one-cn-art-film", "side": "中国", "domain": "艺术", "group": "表演与戏剧",
        "concept": "影视与数字媒体艺术", "short": "本套中国资料单列影视与数字媒体艺术，美国侧未在本数据中形成对应簇。",
        "subjects": ["艺术"], "text_regex": "影视（含数字媒体艺术）",
    },
]

ONE_SIDED_EXTRA: list[dict[str, Any]] = [
    # 美国：数学
    {
        "id": "one-us-math-sorting", "side": "美国", "domain": "数学", "group": "数与运算",
        "concept": "分类、配对与规律", "short": "本套美国资料把分类、配对与规律列为学前数学推理目标，另一侧有相关内容但未单列同类条目。",
        "subjects": ["Mathematics"], "topic_regex": "Mathematical Reasoning and Number Sense", "text_regex": "I-MR1|I-MR2",
    },
    {
        "id": "one-us-math-shapes", "side": "美国", "domain": "数学", "group": "图形与测量",
        "concept": "图形识别与分类", "short": "本套美国资料单列学前图形识别与分类，中国侧未在本数据中形成对应簇。",
        "subjects": ["Mathematics"], "topic_regex": "Mathematical Reasoning and Number Sense", "text_regex": "I-MR3",
    },
    {
        "id": "one-us-math-counting", "side": "美国", "domain": "数学", "group": "数与运算",
        "concept": "学前数数与数量对应", "short": "本套美国资料把学前数数、数量对应和序数写成连续目标，中国侧未在本数据中形成对应簇。",
        "subjects": ["Mathematics"], "topic_regex": "Mathematical Reasoning and Number Sense", "text_regex": "I-MR4",
    },
    {
        "id": "one-us-math-number-system", "side": "美国", "domain": "数学", "group": "数的扩展",
        "concept": "数系与有理数运算", "short": "本套美国资料把数系、公因数与有理数写成独立主题，中国侧未在本数据中形成对应簇。",
        "subjects": ["Mathematics"], "topic_regex": "The Number System", "text_regex": ".*",
    },
    {
        "id": "one-us-math-ratios", "side": "美国", "domain": "数学", "group": "数与运算",
        "concept": "比与比例关系", "short": "本套美国资料单列比与比例关系，另一侧有相关内容但未单列同类条目。",
        "subjects": ["Mathematics"], "topic_regex": "Ratios and Proportional Relationships", "text_regex": ".*",
    },
    {
        "id": "one-us-math-functions", "side": "美国", "domain": "数学", "group": "代数",
        "concept": "函数初步", "short": "本套美国资料把函数作为初中独立主题，另一侧有相关内容但未单列同类条目。",
        "subjects": ["Mathematics"], "topic_regex": "Functions", "text_regex": ".*",
    },
    # 美国：科学
    {
        "id": "one-us-science-genetics", "side": "美国", "domain": "科学", "group": "生命科学",
        "concept": "遗传基础", "short": "本套美国资料单列遗传主题，中国侧未在本数据中形成对应簇。",
        "subjects": ["Science"], "topic_regex": "Genetics", "text_regex": ".*",
    },
    {
        "id": "one-us-science-respiration", "side": "美国", "domain": "科学", "group": "生命科学",
        "concept": "细胞呼吸", "short": "本套美国资料把细胞呼吸列为独立内容，中国侧未在本数据中形成对应簇。",
        "subjects": ["Science"], "topic_regex": "Cellular Respiration", "text_regex": ".*",
    },
    {
        "id": "one-us-science-metabolic", "side": "美国", "domain": "科学", "group": "物质与化学",
        "concept": "代谢反应", "short": "本套美国资料把代谢反应单列为科学内容，中国侧未在本数据中形成对应簇。",
        "subjects": ["Science"], "topic_regex": "Metabolic Reactions", "text_regex": ".*",
    },
    {
        "id": "one-us-science-forces", "side": "美国", "domain": "科学", "group": "运动与能量",
        "concept": "远距离作用力", "short": "本套美国资料单列磁力、电力等非接触作用力，中国侧未在本数据中形成对应簇。",
        "subjects": ["Science"], "topic_regex": "Forces at a Distance", "text_regex": ".*",
    },
    {
        "id": "one-us-science-collisions", "side": "美国", "domain": "科学", "group": "运动与能量",
        "concept": "碰撞中的能量转移", "short": "本套美国资料在碰撞主题下列能量转移，另一侧有相关内容但未单列同类条目。",
        "subjects": ["Science"], "topic_regex": "Collisions", "text_regex": ".*",
    },
    {
        "id": "one-us-science-geohazard", "side": "美国", "domain": "科学", "group": "生态与地球",
        "concept": "地震与火山", "short": "本套美国资料单列地震与火山主题，中国侧未在本数据中形成对应簇。",
        "subjects": ["Science"], "topic_regex": "Earthquakes and Volcanoes", "text_regex": ".*",
    },
    {
        "id": "one-us-science-stars", "side": "美国", "domain": "科学", "group": "生态与地球",
        "concept": "恒星与星空规律", "short": "本套美国资料把恒星和可预测的天象写成独立主题，中国侧未在本数据中形成对应簇。",
        "subjects": ["Science"], "topic_regex": "Stars", "text_regex": ".*",
    },
    {
        "id": "one-us-science-hazards", "side": "美国", "domain": "科学", "group": "生态与地球",
        "concept": "自然灾害与安全", "short": "本套美国资料单列自然灾害主题，中国侧未在本数据中形成对应簇。",
        "subjects": ["Science"], "topic_regex": "Natural Hazards", "text_regex": ".*",
    },
    {
        "id": "one-us-science-geoevent", "side": "美国", "domain": "科学", "group": "生态与地球",
        "concept": "地质事件对人类的影响", "short": "本套美国资料单列地质事件对人类的影响，中国侧未在本数据中形成对应簇。",
        "subjects": ["Science"], "topic_regex": "How Geologic Events can Affect People", "text_regex": ".*",
    },
    # 美国：地理 / 语言 / 文化 / 儿童发展 / 艺术
    {
        "id": "one-us-geo-rivers", "side": "美国", "domain": "地理", "group": "自然地理",
        "concept": "世界重要河流", "short": "本套美国资料单列世界重要河流，中国侧未在本数据中形成对应簇。",
        "subjects": ["History and Geography"], "topic_regex": "Important Rivers of the World", "text_regex": ".*",
    },
    {
        "id": "one-us-ela-speaking", "side": "美国", "domain": "语言与读写", "group": "听说与口语",
        "concept": "课堂听说与讨论", "short": "本套美国资料把听说与课堂讨论按年级列出，另一侧有相关内容但未单列同类条目。",
        "subjects": ["English Language Arts"], "topic_regex": "Listening and Speaking", "text_regex": "discussion|discuss|oral presentation|speech|conversation|dialogue|ask questions|respond to questions", "text_only": True,
        "exclude_ids": ["n00234", "n00235", "n00236"],
    },
    {
        "id": "one-us-ela-fiction", "side": "美国", "domain": "语言与读写", "group": "文学与诗歌",
        "concept": "虚构类文学阅读", "short": "本套美国资料单列虚构类文学作品阅读，中国侧未在本数据中形成对应簇。",
        "subjects": ["English Language Arts"], "topic_regex": "Fiction", "text_regex": ".*",
    },
    {
        "id": "one-us-culture-religions", "side": "美国", "domain": "文化", "group": "多元理解",
        "concept": "世界宗教与多元理解", "short": "本套美国资料单列世界宗教史，另一侧有相关内容但未单列同类条目。",
        "subjects": ["History and Geography"], "topic_regex": "History of World Religions", "text_regex": ".*",
    },
    {
        "id": "one-us-child-movement-space", "side": "美国", "domain": "儿童发展", "group": "动作与平衡",
        "concept": "空间中的身体控制", "short": "本套美国资料把学前身体空间控制写成目标，中国侧未在本数据中形成对应簇。",
        "subjects": ["Movement and Coordination"], "topic_regex": "Movement and Coordination", "text_regex": "I-MC2|I-MC5",
    },
    {
        "id": "one-us-child-movement-cooperate", "side": "美国", "domain": "儿童发展", "group": "投掷与协调",
        "concept": "协作与模仿动作", "short": "本套美国资料单列同伴协作与模仿动作，中国侧未在本数据中形成对应簇。",
        "subjects": ["Movement and Coordination"], "topic_regex": "Movement and Coordination", "text_regex": "I-MC3|I-MC10",
    },
    {
        "id": "one-us-child-self", "side": "美国", "domain": "儿童发展", "group": "常规与协作",
        "concept": "自我认识与身体部位", "short": "本套美国资料把姓名、身体部位等自我认识列为学前目标，中国侧未在本数据中形成对应簇。",
        "subjects": ["Social and Emotional Development"], "topic_regex": "Autonomy and Social Skills", "text_regex": "I-AS1|I-AS2",
    },
    {
        "id": "one-us-child-social", "side": "美国", "domain": "儿童发展", "group": "常规与协作",
        "concept": "问候与同伴互动", "short": "本套美国资料单列问候、请求与同伴互动规则，中国侧未在本数据中形成对应簇。",
        "subjects": ["Social and Emotional Development"], "topic_regex": "Autonomy and Social Skills", "text_regex": "I-AS5",
    },
    {
        "id": "one-us-child-rules", "side": "美国", "domain": "儿童发展", "group": "常规与协作",
        "concept": "规则、责任与任务转换", "short": "本套美国资料把规则遵守、分内职责和任务转换列为目标，中国侧未在本数据中形成对应簇。",
        "subjects": ["Social and Emotional Development"], "topic_regex": "Autonomy and Social Skills", "text_regex": "I-AS6",
    },
    {
        "id": "one-us-child-workhabits", "side": "美国", "domain": "儿童发展", "group": "常规与协作",
        "concept": "坚持与工作习惯", "short": "本套美国资料单列学前坚持完成任务的工作习惯，中国侧未在本数据中形成对应簇。",
        "subjects": ["Social and Emotional Development"], "topic_regex": "Work Habits", "text_regex": ".*",
    },
    {
        "id": "one-us-art-architecture", "side": "美国", "domain": "艺术", "group": "美术与创造",
        "concept": "建筑与空间艺术", "short": "本套美国资料单列建筑艺术内容，中国侧未在本数据中形成对应簇。",
        "subjects": ["Visual Arts"], "topic_regex": "Architecture", "text_regex": ".*",
    },
    {
        "id": "one-us-art-sculpture", "side": "美国", "domain": "艺术", "group": "美术与创造",
        "concept": "雕塑艺术", "short": "本套美国资料单列雕塑内容，中国侧未在本数据中形成对应簇。",
        "subjects": ["Visual Arts"], "topic_regex": "Sculpture", "text_regex": ".*",
    },
    {
        "id": "one-us-music-songs", "side": "美国", "domain": "艺术", "group": "音乐与律动",
        "concept": "歌曲与歌唱", "short": "本套美国资料把歌曲与歌唱按年级列出，中国侧未在本数据中形成对应簇。",
        "subjects": ["Music"], "topic_regex": "Songs", "text_regex": ".*",
    },
    {
        "id": "one-us-music-composers", "side": "美国", "domain": "艺术", "group": "音乐与律动",
        "concept": "作曲家与作品", "short": "本套美国资料单列作曲家及其作品，中国侧未在本数据中形成对应簇。",
        "subjects": ["Music"], "topic_regex": "Composers and Their Music", "text_regex": ".*",
    },
    # 中国：数学（替换原来的单一“数量关系”簇）
    {
        "id": "one-cn-math-life", "side": "中国", "domain": "数学", "group": "数与运算",
        "concept": "生活情境中的数量关系", "short": "本套中国资料把生活情境中的数量关系单列，美国侧未在本数据中形成对应簇。",
        "subjects": ["数学"], "text_regex": "生活情境|生活.*问题|实际情境",
    },
    {
        "id": "one-cn-math-pattern", "side": "中国", "domain": "数学", "group": "数与运算",
        "concept": "变化规律与探索", "short": "本套中国资料单列变化规律与探索要求，美国侧未在本数据中形成对应簇。",
        "subjects": ["数学"], "text_regex": "变化规律|探索简单规律|规律",
    },
    {
        "id": "one-cn-math-estimate", "side": "中国", "domain": "数学", "group": "数与运算",
        "concept": "估算方法", "short": "本套中国资料把估算作为独立要求，另一侧有相关内容但未单列同类条目。",
        "subjects": ["数学"], "text_regex": "估算",
    },
    {
        "id": "one-cn-math-model", "side": "中国", "domain": "数学", "group": "代数",
        "concept": "常见数量关系模型", "short": "本套中国资料单列总价、路程、正比例等数量关系模型，美国侧未在本数据中形成对应簇。",
        "subjects": ["数学"], "text_regex": "总价|路程|成正比的量|等量",
    },
    {
        "id": "one-cn-math-preschool", "side": "中国", "domain": "数学", "group": "数与运算",
        "concept": "学前数学认知", "short": "本套中国资料在学前指南中单列数学认知，美国侧未在本数据中形成对应簇。",
        "subjects": ["科学"], "text_regex": "数学认知",
    },
    # 中国：科学
    {
        "id": "one-cn-science-inquiry", "side": "中国", "domain": "科学", "group": "探究与工程",
        "concept": "科学探究", "short": "本套中国资料把科学探究单列为课程内容，美国侧未在本数据中形成对应簇。",
        "subjects": ["科学"], "text_regex": "科学探究",
    },
    {
        "id": "one-cn-science-strategy", "side": "中国", "domain": "科学", "group": "探究与工程",
        "concept": "科学教学策略建议", "short": "本套中国资料单列科学教学策略建议，美国侧未在本数据中形成对应簇。",
        "subjects": ["科学"], "text_regex": "教学策略建议",
    },
    {
        "id": "one-cn-science-content", "side": "中国", "domain": "科学", "group": "综合与工程",
        "concept": "科学课程内容", "short": "本套中国资料单列科学课程内容条目，美国侧未在本数据中形成对应簇。",
        "subjects": ["科学"], "text_regex": "content",
    },
    {
        "id": "one-cn-physics-engineering", "side": "中国", "domain": "科学", "group": "探究与工程",
        "concept": "物理学与工程实践", "short": "本套中国资料把物理学与工程实践列为主题，美国侧未在本数据中形成对应簇。",
        "subjects": ["物理"], "text_regex": "物理学与工程实践",
    },
    {
        "id": "one-cn-chem-resources", "side": "中国", "domain": "科学", "group": "物质与化学",
        "concept": "化学与资源环境健康", "short": "本套中国资料单列化学与资源、环境、健康、材料的联系，另一侧有相关内容但未单列同类条目。",
        "subjects": ["化学"], "text_regex": "资源综合利用|保护环境|维护人体健康|常见的能源和资源", "exclude_ids": ["ch-j1-con-a0181ce0"],
    },
    # 中国：地理
    {
        "id": "one-cn-geo-hometown-field", "side": "中国", "domain": "地理", "group": "区域与行政",
        "concept": "家乡野外考察", "short": "本套中国资料把家乡野外考察单列为地理实践，美国侧未在本数据中形成对应簇。",
        "subjects": ["地理"], "text_regex": "野外考察",
    },
    {
        "id": "one-cn-geo-hometown-dev", "side": "中国", "domain": "地理", "group": "人文地理",
        "concept": "家乡发展与规划", "short": "本套中国资料单列家乡环境、生产发展与规划，美国侧未在本数据中形成对应簇。",
        "subjects": ["地理"], "text_regex": "发展规划|家乡环境",
    },
    {
        "id": "one-cn-geo-polar", "side": "中国", "domain": "地理", "group": "世界地理",
        "concept": "极地科学与环境保护", "short": "本套中国资料单列南北极科学考察与环境保护，美国侧未在本数据中形成对应簇。",
        "subjects": ["地理"], "text_regex": "南极、北极|极地",
    },
    {
        "id": "one-cn-geo-country-impact", "side": "中国", "domain": "地理", "group": "人文地理",
        "concept": "国家对自然环境的改造", "short": "本套中国资料单列国家改造自然环境的影响分析，美国侧未在本数据中形成对应簇。",
        "subjects": ["地理"], "text_regex": "改造活动|自然环境的影响",
    },
    {
        "id": "one-cn-geo-practice", "side": "中国", "domain": "地理", "group": "区域与行政",
        "concept": "地理实验与考察方案", "short": "本套中国资料把地理实验和考察方案设计列为内容要求，美国侧未在本数据中形成对应簇。",
        "subjects": ["地理"], "text_regex": "地理实验|考察方案",
    },
    # 中国：语言 / 文化 / 儿童发展 / 艺术
    {
        "id": "one-cn-english-strategies", "side": "中国", "domain": "语言与读写", "group": "英语学习策略",
        "concept": "英语学习策略", "short": "本套中国资料把英语学习策略单列为内容要求，美国侧未在本数据中形成对应簇。",
        "subjects": ["英语"], "text_regex": "学习策略内容要求",
    },
    {
        "id": "one-cn-english-themes", "side": "中国", "domain": "语言与读写", "group": "英语主题内容",
        "concept": "英语主题内容要求", "short": "本套中国资料按主题组织英语内容要求，美国侧未在本数据中形成对应簇。",
        "subjects": ["英语"], "text_regex": "主题内容要求",
    },
    {
        "id": "one-cn-chinese-grammar", "side": "中国", "domain": "语言与读写", "group": "写作与表达",
        "concept": "语法修辞知识", "short": "本套中国资料单列语法修辞知识说明，另一侧有相关内容但未单列同类条目。",
        "subjects": ["语文"], "text_regex": "随文学习基本的词汇、语法知识|语法知识",
    },
    {
        "id": "one-cn-chinese-extra-reading", "side": "中国", "domain": "语言与读写", "group": "阅读理解",
        "concept": "课内外读物建议", "short": "本套中国资料给出课内外读物建议，美国侧未在本数据中形成对应簇。",
        "subjects": ["语文"], "text_regex": "课内外读物",
    },
    {
        "id": "one-cn-history-ancient", "side": "中国", "domain": "文化", "group": "文化传承",
        "concept": "中国古代历史线索", "short": "本套中国资料单列中国古代历史基本线索，美国侧未在本数据中形成对应簇。",
        "subjects": ["历史"], "text_regex": "中国古代历史",
    },
    {
        "id": "one-cn-history-modern", "side": "中国", "domain": "文化", "group": "国家认同",
        "concept": "中国近代历史与革命传统", "short": "本套中国资料单列中国近代历史与革命传统，美国侧未在本数据中形成对应簇。",
        "subjects": ["历史"], "text_regex": "中国近代历史|中国共产党",
    },
    {
        "id": "one-cn-history-world", "side": "中国", "domain": "文化", "group": "多元理解",
        "concept": "世界历史与文明交流", "short": "本套中国资料单列世界古代史与世界近代史，美国侧未在本数据中形成对应簇。",
        "subjects": ["历史"], "text_regex": "世界古代史|世界近代史",
    },
    {
        "id": "one-cn-labor-cleaning", "side": "中国", "domain": "文化", "group": "文化传承",
        "concept": "清洁与卫生劳动", "short": "本套中国资料把清洁与卫生列为劳动任务群，美国侧未在本数据中形成对应簇。",
        "subjects": ["劳动"], "text_regex": "清洁与卫生",
    },
    {
        "id": "one-cn-child-posture", "side": "中国", "domain": "儿童发展", "group": "卫生与自理",
        "concept": "幼儿体态与姿势", "short": "本套中国资料单列幼儿正确姿势与体态要求，美国侧未在本数据中形成对应簇。",
        "subjects": ["健康"], "text_regex": "坐直|站直|姿势|体态",
    },
    {
        "id": "one-cn-child-emotion", "side": "中国", "domain": "儿童发展", "group": "常规与协作",
        "concept": "幼儿情绪管理", "short": "本套中国资料单列幼儿情绪稳定与转换要求，美国侧未在本数据中形成对应簇。",
        "subjects": ["健康"], "text_regex": "情绪",
    },
    {
        "id": "one-cn-child-peer", "side": "中国", "domain": "儿童发展", "group": "常规与协作",
        "concept": "幼儿同伴交往", "short": "本套中国资料单列幼儿同伴交往与分享要求，美国侧未在本数据中形成对应簇。",
        "subjects": ["社会"], "text_regex": "人际交往|一起游戏|同伴",
    },
    {
        "id": "one-cn-child-movement", "side": "中国", "domain": "儿童发展", "group": "动作与平衡",
        "concept": "基本运动技能", "short": "本套中国资料把移动性、非移动性和操控性技能列为体育内容，美国侧未在本数据中形成对应簇。",
        "subjects": ["体育与健康"], "text_regex": "移动性技能|非移动性技能|操控性技能",
    },
    {
        "id": "one-cn-art-feel", "side": "中国", "domain": "艺术", "group": "艺术感知与欣赏",
        "concept": "幼儿感受与欣赏", "short": "本套中国资料把感受与欣赏列为学前艺术子领域，美国侧未在本数据中形成对应簇。",
        "subjects": ["艺术"], "text_regex": "感受与欣赏|自然界",
    },
    {
        "id": "one-cn-art-create", "side": "中国", "domain": "艺术", "group": "艺术表现与创造",
        "concept": "幼儿表现与创造", "short": "本套中国资料把表现与创造列为学前艺术子领域，美国侧未在本数据中形成对应簇。",
        "subjects": ["艺术"], "text_regex": "表现与创造|涂涂画画|自哼自唱",
    },
    {
        "id": "one-cn-art-content", "side": "中国", "domain": "艺术", "group": "美术与创造",
        "concept": "艺术课程内容", "short": "本套中国资料单列艺术课程内容条目，美国侧未在本数据中形成对应簇。",
        "subjects": ["艺术"], "text_regex": "content",
    },
    {
        "id": "one-cn-art-academic", "side": "中国", "domain": "艺术", "group": "艺术综合",
        "concept": "艺术学业质量标准", "short": "本套中国资料单列艺术学业质量标准，美国侧未在本数据中形成对应簇。",
        "subjects": ["艺术"], "text_regex": "academic",
    },
]

ONE_SIDED_SPECS.extend(ONE_SIDED_EXTRA)


def build_micro_rows(
    us_items: list[dict[str, Any]], cn_items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """把人工挑选的微指标拼成与原有概念簇同构的数据行。"""
    us_index = {item["id"]: item for item in us_items}
    cn_index = {item["id"]: item for item in cn_items}
    rows: list[dict[str, Any]] = []
    domain_counts: dict[str, int] = {}
    original_domains = {"数学", "科学", "地理", "语言与读写", "文化"}

    for spec in MICRO_CLAIMS + DOMAIN_MICRO_CLAIMS:
        domain = spec["domain"]
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        order = domain_counts[domain] + (100 if domain in original_domains else 0)
        missing_us = [uid for uid in spec["us_evidence"] if uid not in us_index]
        missing_cn = [uid for uid in spec["cn_evidence"] if uid not in cn_index]
        if missing_us or missing_cn:
            raise ValueError(
                f"微指标 {spec['id']} 的证据 ID 找不到：美国 {missing_us} / 中国 {missing_cn}"
            )
        us_evs = [us_index[uid] for uid in spec["us_evidence"]]
        cn_evs = [cn_index[uid] for uid in spec["cn_evidence"]]
        # 展示轨道只记录证据实际命中的学段，不渲染空心/零命中点。
        us_bands = [
            band for band in spec["us_bands"]
            if any(us_band(item) == band for item in us_evs)
        ]
        cn_bands = [
            band for band in spec["cn_bands"]
            if any(cn_band(item) == band for item in cn_evs)
        ]
        us_labels = [BAND_LABELS[band] for band in us_bands]
        cn_labels = [BAND_LABELS[band] for band in cn_bands]

        if not us_evs:
            relation = "本数据中仅中国有"
        elif not cn_evs:
            relation = "本数据中仅美国有"
        else:
            relation = "两边都有，按微指标人工比对"

        row: dict[str, Any] = {
            "id": spec["id"],
            "领域": spec["domain"],
            "概念簇": spec["concept"],
            "story_order": order,
            "分组": spec["group"],
            "短结论": normalize_stage_text(spec["short"]),
            "类型": "微指标",
            "展示轨道": {
                "美国": us_labels,
                "中国": cn_labels,
                "点型": "实心",
            },
            "美国": {
                "是否有证据": bool(us_evs),
                "首次年级": (
                    US_GRADE_LABELS.get(us_evs[0]["grade"], us_evs[0]["grade"])
                    if us_evs else None
                ),
                "命中条目数": len(us_evs),
                "涉及学科": sorted({item["subject"] for item in us_evs}),
                "最早证据": [micro_evidence(item, "美国") for item in us_evs],
                "学段分布": micro_distribution(us_evs, "美国", us_bands),
                "后续学段": "不适用（微指标逐条列出）",
                "后续命中数": 0,
                "后续代表证据": None,
            },
            "中国": {
                "是否有证据": bool(cn_evs),
                "首次年级": cn_evs[0]["grade"] if cn_evs else None,
                "命中条目数": len(cn_evs),
                "展示条目数": len(cn_evs),
                "暂存条目数": 0,
                "涉及学科": sorted({item["subject"] for item in cn_evs}),
                "最早证据": [micro_evidence(item, "中国") for item in cn_evs],
                "学段分布": micro_distribution(cn_evs, "中国", cn_bands),
                "后续学段": "不适用（微指标逐条列出）",
                "后续命中数": 0,
                "后续代表证据": None,
            },
            "学段覆盖": {
                "美国学段数": len(us_bands),
                "中国学段数": len(cn_bands),
                "口径": "微指标展示学段由证据实际命中数反推，证据按来源条目 ID 核对。",
                "对比": f"美国 {len(us_bands)} 个展示学段 / 中国 {len(cn_bands)} 个展示学段",
            },
            "关系": relation,
            "侧重": normalize_stage_text(spec["emphasis"]),
            "说明": normalize_stage_text(spec["note"]),
            "深度对标": {
                "美国": normalize_stage_text("；".join(axis[1] for axis in spec["axes"])),
                "中国": normalize_stage_text("；".join(axis[2] for axis in spec["axes"])),
                "终局关系": normalize_stage_text(spec["short"]),
                "说明": normalize_stage_text(spec["note"]),
            },
            "重评关系": normalize_stage_text(spec["short"]),
            "重评说明": normalize_stage_text(spec["note"]),
            "深度参数": [[normalize_stage_text(cell) for cell in axis] for axis in spec["axes"]],
            "深度解读": MICRO_INTERPRETATIONS[spec["id"]],
            "单侧标记": spec.get("flag"),
        }
        rows.append(row)
    return rows


def build_one_sided_rows(
    us_items: list[dict[str, Any]],
    cn_items: list[dict[str, Any]],
    used_ids: set[str],
) -> list[dict[str, Any]]:
    """从源资料中未被可比簇占用的主题生成单侧概念簇。"""
    domain_counts: dict[str, int] = {}
    rows: list[dict[str, Any]] = []

    for spec in ONE_SIDED_SPECS:
        side = spec["side"]
        other = "中国" if side == "美国" else "美国"
        cfg = {
            "subjects": spec["subjects"],
            "topic_regex": spec.get("topic_regex", ""),
            "text_regex": spec.get("text_regex", ".*"),
            "text_only": spec.get("text_only", False),
            "exclude_ids": set(spec.get("exclude_ids", ())),
        }
        matcher = us_matches if side == "美国" else cn_matches
        pool = us_items if side == "美国" else cn_items
        hits = [
            item for item in pool
            if item.get("status") == "展示"
            and item.get("id") not in used_ids
            and matcher(item, cfg)
        ]
        if not hits:
            raise ValueError(f"单侧概念簇 {spec['id']} 没有命中可用证据")
        hits.sort(key=(us_sort_key if side == "美国" else cn_sort_key))
        for item in hits:
            used_ids.add(item["id"])

        domain = spec["domain"]
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        order = 200 + domain_counts[domain]
        dist = stage_distribution(hits, side)
        labels = display_track(dist, side)[:2]
        first = hits[0]
        first_label = (
            US_GRADE_LABELS.get(first["grade"], first["grade"])
            if side == "美国" else first["grade"]
        )
        subjects = sorted({item["subject"] for item in hits if item["subject"]})
        reason = spec.get("reason", "本数据未收录对侧对应概念")
        note = "仅指本套资料中只在该侧找到对应概念，不代表另一侧绝对缺失。"

        present_side: dict[str, Any] = {
            "是否有证据": True,
            "首次年级": first_label,
            "命中条目数": len(hits),
            "涉及学科": subjects,
            "最早证据": [evidence(item, side) for item in hits[:4]],
            "学段分布": dist,
            "后续学段": "不适用（单侧概念簇）",
            "后续命中数": 0,
            "后续代表证据": None,
        }
        absent_side: dict[str, Any] = {
            "是否有证据": False,
            "首次年级": None,
            "命中条目数": 0,
            "涉及学科": [],
            "最早证据": [],
            "学段分布": [],
            "后续学段": "不适用（无命中）",
            "后续命中数": 0,
            "后续代表证据": None,
        }
        if side == "中国":
            present_side["展示条目数"] = len(hits)
            present_side["暂存条目数"] = 0
            absent_side["展示条目数"] = 0
            absent_side["暂存条目数"] = 0
        else:
            absent_side["展示条目数"] = 0
            absent_side["暂存条目数"] = 0

        short = normalize_stage_text(spec["short"])
        row: dict[str, Any] = {
            "id": spec["id"],
            "领域": domain,
            "概念簇": spec["concept"],
            "story_order": order,
            "分组": spec["group"],
            "短结论": short,
            "展示轨道": {"美国": [], "中国": [], "点型": "实心"},
            "美国": present_side if side == "美国" else absent_side,
            "中国": present_side if side == "中国" else absent_side,
            "学段覆盖": {
                "美国学段数": len(labels) if side == "美国" else 0,
                "中国学段数": len(labels) if side == "中国" else 0,
                "口径": "单侧概念只记录有证据一侧的展示学段。",
                "对比": f"{side} {len(labels)} 个展示学段 / {other} 本资料未涵盖",
            },
            "关系": f"本数据中仅{side}有",
            "侧重": "单侧概念簇",
            "说明": note,
            "深度对标": {
                "美国": short if side == "美国" else "本资料未涵盖",
                "中国": short if side == "中国" else "本资料未涵盖",
                "终局关系": short,
                "说明": note,
            },
            "重评关系": short,
            "重评说明": reason + "；" + note,
            "深度参数": [],
            "深度解读": short,
            "可比性": side,
            "单侧原因": reason,
            "类型": "单侧概念簇",
        }
        row["展示轨道"][side] = labels
        rows.append(row)
    return rows


def build() -> None:
    us_items, cn_items = load_corpus()
    rows: list[dict[str, Any]] = []
    all_hit_ids: set[str] = set()
    clusters = expand_clusters()

    for cluster in clusters:
        us_hits = [i for i in us_items if us_matches(i, cluster["us"])]
        cn_hits = [i for i in cn_items if cn_matches(i, cluster["cn"])]
        all_hit_ids.update(item["id"] for item in us_hits if item.get("id"))
        all_hit_ids.update(item["id"] for item in cn_hits if item.get("id"))
        us_core_text = cluster["us"].get("core_regex")
        if us_core_text:
            us_core = re.compile(us_core_text, re.I)
            us_hits.sort(
                key=lambda i: (
                    us_sort_key(i),
                    0 if us_core.search(str(i.get("text", ""))) else 1,
                )
            )
        else:
            us_hits.sort(key=us_sort_key)
        core_text = cluster["cn"].get("core_regex") or cluster["cn"].get("preschool_core_regex")
        if core_text:
            core_pattern = re.compile(core_text, re.I)
            cn_hits.sort(
                key=lambda i: (
                    cn_sort_key(i),
                    0 if core_pattern.search(str(i.get("text", ""))) else 1,
                )
            )
        else:
            cn_hits.sort(key=cn_sort_key)

        us_first = us_hits[0] if us_hits else None
        cn_first = cn_hits[0] if cn_hits else None
        us_subjects = sorted({i["subject"] for i in us_hits})
        cn_subjects = sorted({i["subject"] for i in cn_hits if i["subject"]})
        us_kept = sum(1 for i in us_hits if i["status"] == "展示")
        cn_kept = sum(1 for i in cn_hits if i["status"] == "展示")
        cn_excluded = sum(1 for i in cn_hits if i["status"] == "暂存")

        us_later = later_items(us_hits, "美国")
        cn_later = later_items(cn_hits, "中国")
        us_distribution = stage_distribution(us_hits, "美国")
        cn_distribution = stage_distribution(cn_hits, "中国")
        review = DEPTH_REVIEW[cluster["_parent"]]

        row = {
            "id": cluster["id"],
            "领域": cluster["domain"],
            "概念簇": cluster["concept"],
            "story_order": cluster["story_order"],
            "分组": cluster["_group"],
            "短结论": cluster["_short"],
            "展示轨道": {
                "美国": display_track(us_distribution, "美国"),
                "中国": display_track(cn_distribution, "中国"),
                "点型": "实心",
            },
            "美国": {
                "是否有证据": bool(us_hits),
                "首次年级": US_GRADE_LABELS.get(us_first["grade"], us_first["grade"]) if us_first else None,
                "命中条目数": len(us_hits),
                "涉及学科": us_subjects,
                "最早证据": [evidence(i, "美国") for i in us_hits[:4]],
                "学段分布": us_distribution,
                "后续学段": format_stage_list(us_later, "美国") if us_hits else "不适用（无命中）",
                "后续命中数": len(us_later),
                "后续代表证据": representative_evidence(us_hits, "美国", cluster["us"]),
            },
            "中国": {
                "是否有证据": bool(cn_hits),
                "首次年级": cn_first["grade"] if cn_first else None,
                "命中条目数": len(cn_hits),
                "展示条目数": cn_kept,
                "暂存条目数": cn_excluded,
                "涉及学科": cn_subjects,
                "最早证据": [evidence(i, "中国") for i in cn_hits[:4]],
                "学段分布": cn_distribution,
                "后续学段": format_stage_list(cn_later, "中国") if cn_hits else "不适用（无命中）",
                "后续命中数": len(cn_later),
                "后续代表证据": representative_evidence(cn_hits, "中国", cluster["cn"]),
            },
            "学段覆盖": {
                "美国学段数": len(us_distribution),
                "中国学段数": len(cn_distribution),
                "口径": "美国按具体年级计；中国按课标学段单元计，通用/跨学段项按1个单元计。",
                "对比": f"美国 {len(us_distribution)} 个具体年级 / 中国 {len(cn_distribution)} 个学段单元",
            },
            "关系": cluster.get("manual_relation") or relation_between(us_first, cn_first),
            "侧重": cluster["emphasis"],
            "说明": cluster["relation_note"],
            "深度对标": review,
            "重评关系": review["终局关系"],
            "重评说明": review["说明"],
        }
        for key in ("短结论", "关系", "侧重", "说明", "重评关系", "重评说明"):
            row[key] = normalize_stage_text(row[key])
        row["深度对标"] = {
            key: normalize_stage_text(value) for key, value in review.items()
        }
        row["深度解读"] = CONCEPT_INTERPRETATIONS[row["id"]]
        row["深度参数"] = concept_axes(row)
        rows.append(row)

    rows.extend(build_micro_rows(us_items, cn_items))

    used_ids: set[str] = set(all_hit_ids)
    for row in rows:
        for side in ("美国", "中国"):
            for ev in row[side]["最早证据"]:
                if ev.get("来源条目"):
                    used_ids.add(ev["来源条目"])
            later = row[side].get("后续代表证据")
            if later and later.get("来源条目"):
                used_ids.add(later["来源条目"])
    rows.extend(build_one_sided_rows(us_items, cn_items, used_ids))

    for row in rows:
        us_ok = bool(row["美国"]["是否有证据"])
        cn_ok = bool(row["中国"]["是否有证据"])
        if us_ok and cn_ok:
            row["可比性"] = "可比"
            row["单侧原因"] = ""
        elif us_ok:
            row["可比性"] = "仅美国"
            if "文件类型差异" in str(row.get("单侧标记") or ""):
                row["单侧原因"] = "文件类型差异"
            else:
                row["单侧原因"] = row.get("单侧原因") or "内容仅一侧出现"
        elif cn_ok:
            row["可比性"] = "仅中国"
            if "文件类型差异" in str(row.get("单侧标记") or ""):
                row["单侧原因"] = "文件类型差异"
            else:
                row["单侧原因"] = row.get("单侧原因") or "内容仅一侧出现"
        else:
            row["可比性"] = "可比"
            row["单侧原因"] = ""

    apply_diff_refinements(rows)
    apply_audit_row_fixes(rows)

    dataset = {
        "版本": "audit-fixed-v9",
        "用途": f"中美课程标准对照底稿：81个原有概念簇 + 44条微指标 + {len(ONE_SIDED_SPECS)}条单侧概念簇；其中高价值条目的差异行已按家长视角人工提炼。页面可按可比项/仅中国/仅美国/全部筛选。",
        "年级对应": {
            "美国幼儿园前班": "中国幼儿园小班、中班",
            "美国K": "中国幼儿园大班",
            "美国1-6年级": "中国小学1-6年级",
            "美国7-8年级": "中国初中7-9年级",
            "说明": "美国数据止于8年级；中国数据含初中7-9年级，中国9年级没有美国对应项。",
        },
        "口径": [
            "首次年级按本数据集中命中的最早条目计算；中国课标按学段发布，结果显示为年级区间而非内部学段代码。",
            "数据底稿把页面展示条目和被具体内容筛选隐藏的暂存条目都纳入并分别计数；面向展示的展示轨道与短结论不带暂存状态。",
            "中国各年级通用（未细分）的条目不会被当作最早出现，只在缺少年级明确条目时作为证据。",
            "首次年级保留原有口径；“关系”列只反映首次阶段，“重评关系”列综合首次、后续覆盖和内容深度。",
            "后续学段指首次命中之后再次出现的具体年级/学段；中国“各年级通用（未细分）”和“小学1-6年级”不计为后续，只保留在学段分布中。",
            "内容深度依据后续代表证据的层级与表述做定性判断，不等于课时数量；数据底稿中的中国暂存条目仍明确标注状态，展示字段不采用。",
            "学段覆盖对比中，美国按具体年级计，中国按课标学段单元计；通用/跨学段项按1个单元计，不宜当作完全同口径的段数比较。",
            "细粒度规则：每条概念簇在展示轨道上最多覆盖2个学段；跨学段通用项（全学段通用、小学1-6年级、幼儿园通用）不进入展示轨道，仅在底稿中保留。",
            "阅读顺序按人工校对后的概念叙事顺序（story_order）排列，不按计算出的首次年级排序；页面默认不提供排序开关。",
            "展示轨道所有点统一为实心，不区分展示/暂存，也不对首次出现做特殊标记；首次信息只保留在短结论和证据中。",
            "语言与读写、文化两个领域按功能对标：美国 ELA/Language and Literacy 对 中国语文/学前语言；不把中国“英语/日语/俄语”等外语学科当作母语能力对标。",
            "文化领域按“国家认同、文化传承、多元理解”等功能对照，不按具体节日、人物、符号的字面对应；具体对象不同不代表功能不同。",
            "“本数据中仅美国有/仅中国有”只代表这两套数据，不代表绝对意义上的课程有无。",
            "“仅美国/仅中国”表示本数据集中只在该侧找到对应概念；单侧原因区分文件类型差异、内容仅一侧出现与本数据未收录对侧对应概念，均不做能力高低判断。",
            "单侧概念簇只绘制有证据一侧的轨道，另一侧显示本资料未涵盖；可比项仍保留双侧轨道与差异表。",
            "微指标层是人工挑选、可直接核对原文的能力点，证据按来源条目 ID 定位；每条最多指定两个展示学段，仍统一为实心点。",
            "微指标的深度按量化阈值、年级递进、场景条件、输出或动作形式等参数逐项列出，不合并成单一深/浅判断。",
            "微指标单侧项（如睡眠时长、屏幕时长）标注文件类型差异，只说明两套文件管辖范围不同，不做能力高低判断。",
            "微指标与原有81个概念簇并存，不改写原有匹配规则、首次年级计算或深度判断。",
            "儿童发展合并原有幼儿动作与生活作息条目；AAP 按年龄指南属于另一个独立任务，不在本数据中。",
        ],
        "数据源": {
            "美国": "Core Knowledge Sequence 2023（PreSchool + K-8）",
            "中国": "教育部《3-6岁儿童学习与发展指南》（2012）与义务教育课程标准（2022年版）16科",
        },
        "概念簇": rows,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "concept-comparison.json"
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(dataset, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    csv_path = OUT_DIR / "concept-comparison.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "领域",
                "概念簇",
                "美国首次年级",
                "中国首次年级",
                "关系",
                "侧重",
                "美国命中",
                "中国命中",
                "中国展示",
                "中国暂存",
                "美国最早证据",
                "中国最早证据",
                "说明",
                "美国后续学段",
                "中国后续学段",
                "美国学段分布",
                "中国学段分布",
                "学段覆盖对比",
                "美国后续证据",
                "中国后续证据",
                "深度对标",
                "重评关系",
                "重评说明",
                "学科内顺序",
                "分组",
                "短结论",
                "美国展示轨道",
                "中国展示轨道",
                "类型",
                "可比性",
                "单侧原因",
                "单侧标记",
                "深度参数",
                "深度解读",
            ]
        )
        for row in rows:
            us_evidence = row["美国"]["最早证据"][0] if row["美国"]["最早证据"] else {}
            cn_evidence = row["中国"]["最早证据"][0] if row["中国"]["最早证据"] else {}
            us_later_evidence = row["美国"]["后续代表证据"] or {}
            cn_later_evidence = row["中国"]["后续代表证据"] or {}
            cn_later_text = ""
            if cn_later_evidence:
                cn_later_text = f"[{cn_later_evidence.get('状态', '')}] {cn_later_evidence.get('文本', '')}"
            writer.writerow(
                [
                    row["领域"],
                    row["概念簇"],
                    row["美国"]["首次年级"] or "未找到",
                    row["中国"]["首次年级"] or "未找到",
                    row["关系"],
                    row["侧重"],
                    row["美国"]["命中条目数"],
                    row["中国"]["命中条目数"],
                    row["中国"]["展示条目数"],
                    row["中国"]["暂存条目数"],
                    us_evidence.get("文本", ""),
                    cn_evidence.get("文本", ""),
                    row["说明"],
                    row["美国"]["后续学段"],
                    row["中国"]["后续学段"],
                    format_distribution(row["美国"]["学段分布"], "美国"),
                    format_distribution(row["中国"]["学段分布"], "中国"),
                    row["学段覆盖"]["对比"],
                    us_later_evidence.get("文本", ""),
                    cn_later_text,
                    f"美国：{row['深度对标']['美国']} 中国：{row['深度对标']['中国']}",
                    row["重评关系"],
                    row["重评说明"],
                    row["story_order"],
                    row["分组"],
                    row["短结论"],
                    "、".join(row["展示轨道"]["美国"]),
                    "、".join(row["展示轨道"]["中国"]),
                    row.get("类型", "概念簇"),
                    row.get("可比性", "可比"),
                    row.get("单侧原因", ""),
                    row.get("单侧标记") or "",
                    "；".join(
                        f"{axis[0]}：美国 {axis[1]} / 中国 {axis[2]}"
                        for axis in row.get("深度参数", [])
                    ),
                    row.get("深度解读", ""),
                ]
            )

    md_path = OUT_DIR / "concept-comparison-preview.md"
    lines = [
        "# 中美核心知识点概念簇对照（数据底稿）",
        "",
        "- 年级按用户指定口径显示：美国幼儿园前班对应中国小班、中班；美国K对应大班；美国7-8年级对应中国初中。",
        "- 数据底稿同时保留页面展示条目和被筛选隐藏的暂存条目用于核对；面向展示的字段不带暂存状态。",
        "- 除首次年级外，本版同时列出后续学段、学段覆盖、后续代表证据与深度对标，避免只看首次出现造成误判。",
        "- 原有数学、科学、地理、语言与读写、文化五个领域的81个概念簇保持不变。",
        f"- 共 {len(rows)} 条：81 个原有概念簇 + 44 条微指标 + {len(ONE_SIDED_SPECS)} 条单侧概念簇；逐条解读与“起步／后续／差异”三行简表保留。",
        "- 页面筛选：可比项（默认）／仅中国／仅美国／全部；“仅”只表示本套资料中只在该侧找到对应概念，不代表另一侧绝对缺失。",
        "- 微指标单侧项标注文件类型差异，不做能力高低判断。",
        "- 这里只整理数据，没有网页。",
        "",
        "| 领域 | 概念簇 | 美国首次 | 中国首次 | 关系 | 侧重 | 命中（美 / 中展示 / 中暂存） |",
        "| --- | --- | --- | --- | --- | --- | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {领域} | {概念簇} | {us} | {cn} | {关系} | {侧重} | {a} / {b} / {c} |".format(
                **row,
                us=row["美国"]["首次年级"] or "未找到",
                cn=row["中国"]["首次年级"] or "未找到",
                a=row["美国"]["命中条目数"],
                b=row["中国"]["展示条目数"],
                c=row["中国"]["暂存条目数"],
            )
        )
    lines.extend(
        [
            "",
            "## 阅读顺序与一句话结论",
            "",
            "默认按人工校对后的概念顺序逐条阅读；展示轨道所有点统一为实心，不区分展示/暂存。",
            "",
            "| 领域 | 顺序 | 分组 | 概念簇 | 短结论 | 美国展示轨道 | 中国展示轨道 |",
            "| --- | ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for row in sorted(rows, key=lambda r: (r["领域"], r["story_order"])):
        lines.append(
            "| {领域} | {order} | {group} | {concept} | {short} | {us} | {cn} |".format(
                **row,
                order=row["story_order"],
                group=row["分组"],
                concept=row["概念簇"],
                short=row["短结论"],
                us="、".join(row["展示轨道"]["美国"]) or "无",
                cn="、".join(row["展示轨道"]["中国"]) or "无",
            )
        )
    lines.extend(
        [
            "",
            "## 后续覆盖与深度对标",
            "",
            "| 概念簇 | 美国后续 | 中国后续 | 学段覆盖 | 终局关系 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| {concept} | {us} | {cn} | {coverage} | {relation} |".format(
                concept=row["概念簇"],
                us=row["美国"]["后续学段"],
                cn=row["中国"]["后续学段"],
                coverage=row["学段覆盖"]["对比"],
                relation=row["重评关系"],
            )
        )
    lines.extend(["", "## 逐簇说明", ""])
    for row in rows:
        lines.append(f"- **{row['领域']} · {row['概念簇']}**：{row['说明']}")
        lines.append(f"  - 后续与深度：{row['重评说明']}")
    lines.extend(
        [
            "",
            "## 深度参数（概念簇三行简表 + 微指标细表）",
            "",
            "微指标不再把深度压成单一档位，而是把可比较的参数并排列出。",
            "",
            "| 领域 | 微指标 | 深度维度 | 美国 | 中国 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        for axis in row.get("深度参数", []):
            lines.append(
                f"| {row['领域']} | {row['概念簇']} | {axis[0]} | {axis[1]} | {axis[2]} |"
            )
    lines.extend(["", "## 逐条解读", ""])
    for row in rows:
        lines.append(f"### {row['领域']} · {row['概念簇']}（{row.get('类型', '概念簇')}）")
        lines.append("")
        lines.append(row["深度解读"])
        lines.append("")
    lines.extend(
        [
            "",
            "## 口径提醒",
            "",
            "- “关系”列保留首次出现口径；“重评关系”列综合首次、后续覆盖与内容深度。",
            "- 中国“各年级通用（未细分）”和“小学1-6年级”保留在学段分布中，但不计为后续学段。",
            "- 每条概念簇在展示轨道上最多覆盖2个学段；跨学段通用项不进入轨道，仅在底稿保留。",
            "- 阅读顺序按 story_order 人工校对排列，不按首次年级排序；页面默认不提供排序开关。",
            "- 展示轨道所有点统一为实心，不区分展示/暂存，也不对首次出现做特殊标记；暂存仅保留在数据底稿用于核对。",
            "- 内容深度是定性判断，不等于课时数量；暂存证据仍按被筛选隐藏的条目处理。",
            "- 学段覆盖中，美国按具体年级计，中国按课标学段单元计；通用/跨学段项按1个单元计，不是完全同口径比较。",
            "- 美国数据止于8年级；中国数据含初中7-9年级，中国9年级没有美国对应项。",
            "- 中国课标按学段发布，本表显示为年级区间，不伪造具体年级。",
            "- “本数据中仅美国有/仅中国有”只代表这两套数据，不代表绝对意义上的课程有无。",
            "- 微指标的证据按来源条目 ID 定位，与原有概念簇的正则匹配互不影响。",
            "- 微指标的深度按参数逐项列出；单侧项只说明文件管辖范围不同，不代表能力高低。",
            "- 微指标与原有81个概念簇并存，原有数据未作改写。",
            "- 儿童发展合并原有幼儿动作与生活作息条目；AAP 按年龄指南属于另一个独立任务。",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    html_path = OUT_DIR / "index.html"
    payload = json.dumps(dataset, ensure_ascii=False).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__PAYLOAD__", payload)
    html_path.write_text(html, encoding="utf-8")

    print(f"wrote {json_path.relative_to(ROOT)}")
    print(f"wrote {csv_path.relative_to(ROOT)}")
    print(f"wrote {md_path.relative_to(ROOT)}")
    print(f"wrote {html_path.relative_to(ROOT)}")
    print(f"rows: {len(rows)} ({len(MICRO_CLAIMS) + len(DOMAIN_MICRO_CLAIMS)} micro claims)")


if __name__ == "__main__":
    build()
