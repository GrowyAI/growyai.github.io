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


def clean_text(text: Any, limit: int = 220) -> str:
    value = " ".join(str(text or "").split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


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
    pattern_text = cfg.get("text_regex")
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
    haystack = item["haystack"]
    if re.match(r"^(Overview|Teachers):", str(item["text"]).strip(), re.I):
        return False
    if cfg.get("exclude_regex") and re.search(cfg["exclude_regex"], haystack, re.I):
        return False
    if "bands" in cfg and us_band(item) not in cfg["bands"]:
        return False
    topic_ok = bool(re.search(cfg["topic_regex"], item["topic"] + " " + item["subtopic"], re.I))
    text_ok = bool(re.search(cfg["text_regex"], haystack, re.I))
    return topic_ok and text_ok


def cn_matches(item: dict[str, Any], cfg: dict[str, Any]) -> bool:
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
    haystack = item["haystack"]
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
        {"id": "math-number-rational", "concept": "有理数、实数与数轴", "group": "数的扩展", "short": "初中阶段中国把有理数、实数与数轴系统化。", "us_bands": [4], "cn_bands": [4]},
    ],
    "math-four-operations": [
        {"id": "math-add-sub-early", "concept": "数量分合与10以内加减法", "group": "数与运算", "short": "中美学前已做数量分合，1-2年级继续10以内加减。", "us_bands": [0, 1], "cn_bands": [0, 1], "cn_preschool_regex": r"合在一起|加减运算|分成|分给|[“”]加[“”]|[“”]减[“”]|拿取", "cn_preschool_core_regex": r"合在一起|加减运算|[“”]加[“”]|[“”]减[“”]"},
        {"id": "math-multi-div", "concept": "多位数乘除与四则混合运算", "group": "数与运算", "short": "小学中高段扩展到乘除与混合运算。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "math-rational-operations", "concept": "有理数运算与运算律", "group": "数的扩展", "short": "初中把运算扩展到有理数并总结运算律。", "us_bands": [4], "cn_bands": [4]},
    ],
    "math-fractions-decimals": [
        {"id": "math-fractions-intro", "concept": "分数与小数初步认识", "group": "数的扩展", "short": "双方在小学中段初步认识分数和小数。", "us_bands": [2], "cn_bands": [2]},
        {"id": "math-fractions-operations", "concept": "分数小数运算与有理数延伸", "group": "数的扩展", "short": "美国延伸到初中，中国在小学高段集中完成运算。", "us_bands": [3, 4], "cn_bands": [3]},
    ],
    "math-equations-algebra": [
        {"id": "math-algebra-foundations", "concept": "运算关系与字母表示数", "group": "代数与统计", "short": "美国低龄用运算关系铺垫，中国在小学高段引入字母表示数。", "us_bands": [0, 1], "cn_bands": [3]},
        {"id": "math-equations-basic", "concept": "等式性质与一元一次方程", "group": "代数与统计", "short": "小学高段到小学高年级双方都进入等式与方程。", "us_bands": [2, 3], "cn_bands": [3, 4]},
        {"id": "math-equations-advanced", "concept": "方程组、不等式与代数应用", "group": "代数与统计", "short": "初中阶段中国把方程与不等式组织得更系统。", "us_bands": [4], "cn_bands": [4]},
    ],
    "math-geometry": [
        {"id": "math-shapes-early", "concept": "图形辨认与分类", "group": "图形与测量", "short": "中美学前已辨认形状，小学低段继续命名和分类。", "us_bands": [0, 1], "cn_bands": [0, 1], "cn_preschool_regex": r"形状|几何图形|形体结构|图形"},
        {"id": "math-shapes-properties", "concept": "角、三角形与四边形", "group": "图形与测量", "short": "小学中高段进入边、角和常见图形的性质。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "math-geometry-proof", "concept": "图形变换、相似与证明", "group": "图形与测量", "short": "初中阶段中国把定义、性质和证明串成体系。", "us_bands": [4], "cn_bands": [4]},
    ],
    "math-measurement": [
        {"id": "math-measure-early", "concept": "长度、质量与时间等可测量属性", "group": "图形与测量", "short": "中美学前已感知大小、长短和轻重，小学低段引入常用单位。", "us_bands": [0, 1], "cn_bands": [0, 1], "cn_preschool_regex": r"大小|高矮|长短|粗细|厚薄|轻重|量的相对性|测量|多少"},
        {"id": "math-area-perimeter-volume", "concept": "面积、周长与体积", "group": "图形与测量", "short": "小学中高段集中学习面积、周长和体积。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "math-measure-advanced", "concept": "立体度量与几何应用", "group": "图形与测量", "short": "初中阶段美国继续立体度量，中国更多与几何推理结合。", "us_bands": [4], "cn_bands": [4]},
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
        {"id": "science-energy-basic", "concept": "能量形式与简单电路", "group": "运动与能量", "short": "小学中高段双方学习能量形式、传热和简单电路。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "science-energy-advanced", "concept": "波、能量转化与守恒", "group": "运动与能量", "short": "初中阶段中国更强调能量转化、守恒和实验。", "us_bands": [4], "cn_bands": [4]},
    ],
    "science-life-genetics": [
        {"id": "science-life-early", "concept": "常见动植物与生长变化", "group": "生命科学", "short": "中国幼儿园已有生命感知，美国小学低段观察动植物。", "us_bands": [1], "cn_bands": [0, 1]},
        {"id": "science-genetics-basic", "concept": "繁殖、遗传与细胞", "group": "生命科学", "short": "小学中高段进入繁殖、遗传和细胞初步。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "science-evolution", "concept": "进化证据与生物分类", "group": "生命科学", "short": "初中阶段美国偏进化证据，中国偏显微观察与分类。", "us_bands": [4], "cn_bands": [4]},
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
        {"id": "science-space-early", "concept": "天体现象观察", "group": "生态与地球", "short": "低龄和小学低段观察日、月、星等天体现象。", "us_bands": [0, 1], "cn_bands": [1]},
        {"id": "science-earth-basic", "concept": "太阳系与地球现象", "group": "生态与地球", "short": "小学中高段学习太阳系、地球和地表现象。", "us_bands": [2, 3], "cn_bands": [2, 3]},
        {"id": "science-earth-advanced", "concept": "板块构造与地质解释", "group": "生态与地球", "short": "初中阶段中国用板块构造解释火山和地震。", "us_bands": [4], "cn_bands": [4]},
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
        {"id": "geo-map-advanced", "concept": "比例尺与区域地图应用", "group": "地图与定位", "short": "小学高段到初中，中国把比例尺和经纬网做成技能链。", "us_bands": [3, 4], "cn_bands": [3, 4]},
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
        {"id": "geo-population", "concept": "人口、聚落与迁移", "group": "人文地理", "short": "小学中高段美国持续出现人口、移民和城市内容。", "us_bands": [2, 3], "cn_bands": []},
        {"id": "geo-region-development", "concept": "全球化、区域发展与家乡调查", "group": "人文地理", "short": "初中阶段中国把人口、聚落和区域发展组织成独立主题。", "us_bands": [4], "cn_bands": [4]},
    ],
    "geo-admin-divisions": [
        {"id": "geo-admin-basic", "concept": "州与省：层级识别", "group": "区域对照", "short": "美国学前和1-2年级认识所在州，中国7-9年级识别省级行政区。", "us_bands": [0, 1], "cn_bands": [4]},
        {"id": "geo-admin-capitals", "concept": "州府与省会：名称与行政中心", "group": "区域对照", "short": "美国5-6年级记50州及州府，中国7-9年级记省级行政区简称和行政中心。", "us_bands": [3], "cn_bands": [4]},
    ],
}


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
  .tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; }
  .tabs button {
    border: 1px solid var(--border); background: var(--surface-2); color: var(--muted);
    border-radius: 8px; padding: 7px 0; font-size: 15px; cursor: pointer;
  }
  .tabs button.active {
    background: var(--cn); border-color: var(--cn); color: #fff;
  }
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
  .pager { font-size: 12px; color: var(--muted); }
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
  .actions { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; }
  .actions button {
    border: 1px solid var(--border); background: var(--surface-2); color: var(--text);
    border-radius: 8px; padding: 8px 0; font-size: 14px; cursor: pointer;
  }
  .actions .primary { background: var(--cn); border-color: var(--cn); color: #fff; }
  .evidence { margin-top: 8px; border-top: 1px solid var(--border); padding-top: 7px; }
  .ev-block { margin-bottom: 7px; }
  .ev-block h3 { margin: 0 0 2px; font-size: 13px; color: var(--us); }
  .ev-block.cn h3 { color: var(--cn); }
  .ev-grade { margin: 0 0 2px; font-size: 11px; color: var(--muted); }
  .ev-text {
    margin: 0; font-size: 13px; line-height: 1.45; color: var(--text);
    background: var(--surface-2); border-radius: 8px; padding: 5px 7px;
  }
  footer { margin-top: 10px; font-size: 12px; color: var(--muted); text-align: center; }
  footer a { color: var(--cn); text-decoration: none; }
  @media (max-width: 360px) {
    main { padding-left: 9px; padding-right: 9px; }
    .card { padding-left: 10px; padding-right: 10px; }
  }
</style>
</head>
<body>
<header>
  <div class="head-top">
    <h1>中美课程标准 · 概念对照</h1>
    <span class="badge" id="badge"></span>
  </div>
  <p class="sub">数学 / 科学 / 地理 · 按概念顺序单条阅读</p>
  <nav class="tabs" id="tabs"></nav>
</header>
<main>
  <section class="card" id="card"></section>
  <footer>
    仅为数学、科学、地理的 <span id="total"></span> 个精选可比概念簇，不是课程标准全部知识点。
  </footer>
</main>
<script id="dataset" type="application/json">__PAYLOAD__</script>
<script>
const DATA = JSON.parse(document.getElementById("dataset").textContent);
const DOMAINS = ["数学", "科学", "地理"];
const BANDS = ["学前", "1-2年级", "3-4年级", "5-6年级", "7-9年级"];
const BAND_MAP = {
  "幼儿园前班": [0], "幼儿园大班K": [0],
  "小班（3-4岁）": [0], "中班（4-5岁）": [0], "大班（5-6岁）": [0], "幼儿园通用": [0],
  "小学1年级": [1], "小学2年级": [1], "小学1-2年级": [1],
  "小学3年级": [2], "小学4年级": [2], "小学3-4年级": [2],
  "小学5年级": [3], "小学6年级": [3], "小学5-6年级": [3],
  "初中7年级": [4], "初中8年级": [4], "初中7-9年级": [4],
  "小学1-6年级": [1, 2, 3], "全学段通用": [0, 1, 2, 3, 4]
};
const rowsByDomain = {};
DOMAINS.forEach(function(d) {
  rowsByDomain[d] = DATA["概念簇"].filter(function(r) { return r["领域"] === d; })
    .sort(function(a, b) { return a.story_order - b.story_order; });
});
const state = { domain: "数学", idx: 0 };
const card = document.getElementById("card");
const tabs = document.getElementById("tabs");

function esc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function plainEvidence(value) {
  return String(value == null ? "" : value).replace(/^\[暂存\]\s*/, "");
}
function bandsFor(label) {
  return BAND_MAP[label] || [];
}
function renderTabs() {
  tabs.innerHTML = DOMAINS.map(function(d) {
    return "<button data-domain=\"" + d + "\"" + (d === state.domain ? " class=\"active\"" : "") + ">" + d + "</button>";
  }).join("");
  tabs.querySelectorAll("button").forEach(function(btn) {
    btn.addEventListener("click", function() {
      state.domain = btn.dataset.domain;
      state.idx = 0;
      renderTabs();
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
function evidenceHtml(row) {
  const pairs = [
    ["美国", row["美国"]["最早证据"][0], row["美国"]["后续代表证据"], false],
    ["中国", row["中国"]["最早证据"][0], row["中国"]["后续代表证据"], true]
  ];
  return pairs.map(function(pair) {
    const side = pair[0], first = pair[1], later = pair[2], isCn = pair[3];
    let html = "<div class=\"ev-block" + (isCn ? " cn" : "") + "\"><h3>" + side + " · 最早</h3>";
    html += "<p class=\"ev-grade\">" + esc(first && first["年级"]) + "</p>";
    html += "<p class=\"ev-text\">" + esc(first && first["文本"]) + "</p>";
    html += "<h3>" + side + " · 后续</h3>";
    if (later) {
      html += "<p class=\"ev-grade\">" + esc(later["年级"]) + "</p>";
      html += "<p class=\"ev-text\">" + esc(plainEvidence(later["文本"])) + "</p>";
    } else {
      html += "<p class=\"ev-text\">无后续代表证据</p>";
    }
    return html + "</div>";
  }).join("");
}
function render() {
  const list = rowsByDomain[state.domain];
  const row = list[state.idx];
  card.innerHTML =
    "<div class=\"card-top\"><span class=\"group\">" + esc(row["分组"]) + "</span>" +
    "<span class=\"pager\">概念 " + (state.idx + 1) + " / " + list.length + "</span></div>" +
    "<h2>" + esc(row["概念簇"]) + "</h2>" +
    "<p class=\"takeaway\">" + esc(row["短结论"]) + "</p>" +
    "<div class=\"track\">" +
    "<div class=\"track-head\"><span></span>" + BANDS.map(function(b) { return "<span>" + b + "</span>"; }).join("") + "</div>" +
    "<div class=\"track-row\"><span class=\"side us-label\">美国</span>" + trackCells(row, "美国") + "</div>" +
    "<div class=\"track-row\"><span class=\"side cn-label\">中国</span>" + trackCells(row, "中国") + "</div>" +
    "</div>" +
    "<div class=\"actions\">" +
    "<button id=\"prev\">上一个</button>" +
    "<button id=\"evidence\">看证据</button>" +
    "<button id=\"next\" class=\"primary\">下一个</button>" +
    "</div>" +
    "<div class=\"evidence\" id=\"evidence-body\" hidden>" + evidenceHtml(row) + "</div>";

  document.getElementById("prev").addEventListener("click", function() {
    state.idx = (state.idx - 1 + list.length) % list.length;
    render();
  });
  document.getElementById("next").addEventListener("click", function() {
    state.idx = (state.idx + 1) % list.length;
    render();
  });
  const evidenceBtn = document.getElementById("evidence");
  const evidenceBody = document.getElementById("evidence-body");
  evidenceBtn.addEventListener("click", function() {
    evidenceBody.hidden = !evidenceBody.hidden;
    evidenceBtn.textContent = evidenceBody.hidden ? "看证据" : "收起证据";
  });
}
document.addEventListener("keydown", function(e) {
  const list = rowsByDomain[state.domain];
  if (e.key === "ArrowRight") { state.idx = (state.idx + 1) % list.length; render(); }
  if (e.key === "ArrowLeft") { state.idx = (state.idx - 1 + list.length) % list.length; render(); }
});
document.getElementById("badge").textContent = "精选 " + DATA["概念簇"].length + " 簇";
document.getElementById("total").textContent = DATA["概念簇"].length;
renderTabs();
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
            if spec.get("us_topic_regex"):
                item["us"]["topic_regex"] = spec["us_topic_regex"]
            expanded.append(item)

    for domain in ("数学", "科学", "地理"):
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


def build() -> None:
    us_items, cn_items = load_corpus()
    rows: list[dict[str, Any]] = []
    clusters = expand_clusters()

    for cluster in clusters:
        us_hits = [i for i in us_items if us_matches(i, cluster["us"])]
        cn_hits = [i for i in cn_items if cn_matches(i, cluster["cn"])]
        us_hits.sort(key=us_sort_key)
        core_text = cluster["cn"].get("preschool_core_regex")
        if core_text:
            core_pattern = re.compile(core_text)
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
        rows.append(row)

    dataset = {
        "版本": "concept-cluster-v4",
        "用途": "中美核心知识点概念簇对照的细粒度数据底稿：每条最多覆盖2个展示学段，保留首次、后续覆盖与深度判断，未生成网页。",
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
            "“本数据中仅美国有/仅中国有”只代表这两套数据，不代表绝对意义上的课程有无。",
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
                ]
            )

    md_path = OUT_DIR / "concept-comparison-preview.md"
    lines = [
        "# 中美核心知识点概念簇对照（数据底稿）",
        "",
        "- 年级按用户指定口径显示：美国幼儿园前班对应中国小班、中班；美国K对应大班；美国7-8年级对应中国初中。",
        "- 数据底稿同时保留页面展示条目和被筛选隐藏的暂存条目用于核对；面向展示的字段不带暂存状态。",
        "- 除首次年级外，本版同时列出后续学段、学段覆盖、后续代表证据与深度对标，避免只看首次出现造成误判。",
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
    print(f"concept clusters: {len(rows)}")


if __name__ == "__main__":
    build()
