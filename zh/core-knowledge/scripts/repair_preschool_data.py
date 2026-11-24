"""One-off repair for Preschool data accuracy issues found in full review.

Scope: grade == "Preschool" only. Fixes:
- truncated English bullets restored from the raw PDF text
- overview/subheading fragments reclassified or merged
- shifted Chinese translations replaced with matching translations
- Level I / Level II rows merged by the PDF parser split into separate items
- stray K-grade bullet removed from the Preschool set
"""

import json
import os
import re
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SOURCE = os.path.join(DATA, "knowledge.json")
BACKUP = os.path.join(DATA, "knowledge-before-preschool-repair.json")
EXPORT = os.path.join(BASE, "scripts", "export_tables.py")
NEW_UID_START = 7200

CODE_EN = re.compile(r"\bII-[A-Z]{2,5}\d+(?:\.\d+)?[a-z]?\b")
CODE_ZH = re.compile(r"II-[A-Z]{2,5}\d+(?:\.\d+)?[a-z]?\b")

PATCH = {
    # --- truncated English restored from raw text ---------------------------------
    "n00001": {"en": "I-MC1.1 Stop and/or start movement in response to a signal."},
    "n00004": {"en": "I-MC2.3a Maintain balance while walking forward on a wide bench or beam."},
    "n00011": {"en": "I-MC4.1a Play group games such as Farmer in the Dell, Follow the Leader, Hot Potato, London Bridge, Mother May I?, Ring Around the Rosie, Simon Says."},
    "n00142": {
        "en": "I-MR3.2 Match rectangular, square, circular, and triangular shapes to outlines of the same configuration and size.",
        "zh": "I-MR3.2 将长方形、正方形、圆形和三角形与相同形状和大小的轮廓配对。",
    },
    "n00216": {
        "en": "I-VA2.7a Cut straight lines: Use various tools and techniques in completing art projects.",
        "zh": "I-VA2.7a 沿直线剪：使用各种工具和技术完成艺术作品。",
    },

    # --- overview / subheading fragments -----------------------------------------
    "n00019": {
        "zh": "概述：本节的基本目标聚焦于发展使幼儿能够在班级群体的社会环境中独立发挥作用的情绪与社会技能。这些技能包括发展对自我及其能力的认识，从身体意象开始。儿童还将学习与他人互动所必需的人际与社会技能，例如作为群体一员的“给予与索取”，以及根据群体要求有时延迟或推迟自己当下的愿望。这些目标标志着一个独立、有能力、能够在群体情境中为自己的行为负责的个体的初步发展。"
    },
    "n00022": {
        "en": "Internalize and conceptualize an image of one’s body",
        "zh": "内化并形成对自己身体的意象。",
        "type": "note",
    },
    "n00038": {
        "zh": "概述：儿童日后在幼儿园及以后如何对待学业任务，其基础是在学前阶段的游戏和活动中，通过所遇到的经验与期望一步步奠定的。本节着重温和地引导儿童形成开展不同活动的方法：发展记忆技能、听从指令、坚持完成任务、确定活动所需的材料和步骤、评价并修正自己的工作等。"
    },
    "n00044": {
        "en": "Expressing a Point of View/Imagining—giving an opinion, pretending, and assuming the role or perspective of another, making up a story",
        "zh": "表达观点／想象——给出意见、假装、扮演他人的角色或从他人的视角出发、编故事。",
        "type": "note",
    },
    "n00045": {
        "en": "Predicting—anticipating and saying what is likely to happen next",
        "zh": "预测——预期并说出接下来可能发生的事。",
        "type": "note",
    },
    "n00046": {
        "en": "Vocabulary—acquiring increasingly precise and varied ways to express nuances of meaning",
        "zh": "词汇——获得越来越精确、多样的方式表达意义的细微差别。",
        "type": "note",
    },
    "n00047": {
        "en": "Syntax—learning the grammar of language word order in a sentence; word endings to reflect singular and plural, past and present; and specific ways of connecting words and phrases that indicate different relationships, e.g., cause-effect, temporal, etc.",
        "zh": "句法——学习句子中词序的语法；用词的结尾形式表示单复数、过去和现在；以及用特定方式连接词和短语，表示不同关系，如因果、时间等。",
        "type": "note",
    },
    "n00049": {
        "en": "Frequent language interaction, with many opportunities to listen and talk",
        "zh": "频繁的语言互动，有大量倾听和说话的机会。",
        "type": "note",
    },
    "n00050": {
        "en": "Adult models of high quality talk that keep in mind children’s need to first hear many “language examples” in order to build a receptive language base: use of a variety of vocabulary, including occasional “rare words” (multi-syllable words that might normally be considered “outside a preschooler’s vocabulary”); use of a variety of syntactical forms such as complex sentences that relate ideas; talk that is informative and illustrates reflection and problem solving; etc.",
        "zh": "成人提供高质量谈话的示范，并牢记儿童需要先听到大量“语言范例”以建立接受性语言基础：使用多种词汇，包括偶尔的“稀有词”（多音节词，通常可能被视为超出学前儿童词汇范围）；使用多种句法形式，如联系想法的复杂句；提供信息性强、体现反思和解决问题的谈话；等等。",
        "type": "note",
    },
    "n00051": {
        "en": "Adult responses that reflect and incorporate what the child has said but also expand upon his or her comments",
        "zh": "成人的回应既反映并接纳儿童所说的话，也对其评论加以扩展。",
        "type": "note",
    },
    "n00052": {
        "en": "Adult comments and behaviors that invite further conversation on the child’s part:",
        "zh": "成人引发儿童进一步交谈的评论和行为：",
        "type": "note",
    },
    "n00053": {
        "en": "Rephrasing of questions, in the absence of a response by the child, in a manner that gives hints about how to respond, moving from open-ended questions to those that offer a structured choice: “Where is the pirate going?” (no answer) “Is he going to look for the buried treasure or is he going to chase the other pirate boat?”",
        "zh": "如果儿童没有回应，以能提供作答提示的方式重述问题，从开放式问题逐步转为提供结构化选择的问题：“海盗要去哪里？”（无回答）“他是要去找埋藏的宝藏，还是去追另一艘海盗船？”",
        "type": "note",
    },
    "n00054": {
        "en": "Opportunities and invitations to use language in decontextualized settings—to talk about objects, events or experiences that are not part of the immediate environment: “What did you do at grandma’s house?” “How did you make the pinwheel?” “What are you going to do when you go on vacation?”",
        "zh": "提供并邀请儿童在脱离语境的情境中使用语言——谈论不属于眼前环境的物体、事件或经历：“你在奶奶家做了什么？”“你是怎么做出风车的？”“你度假时打算做什么？”",
        "type": "note",
    },
    "n00055": {
        "en": "Minimal use of directives (“Do this …,” “Don’t do this …,” etc.)",
        "zh": "尽量少用指令句（“做这个……”“别做这个……”等）。",
        "type": "note",
    },
    "n00101": {
        "en": (
            "Overview: The goals of this section focus on the language skills that children acquire when given the opportunity to hear the language of storybooks. "
            "In listening to and talking about stories that are read aloud, children build both listening and speaking skills. They are introduced to new vocabulary and formal written syntax, ways of linking and relating ideas. They also refine skills in: "
            "Narrating: understanding and describing illustrations, understanding and describing the setting, characters and events of stories and so on. "
            "Predicting: telling what will happen next in a story or suggesting a possible alternative ending. "
            "Imagining: telling their own stories, either based on illustrations or creating a story using their imagination. "
            "In addition, early experiences with books also lay the foundation for concepts and skills that children will later use as they begin to read and write. "
            "They learn about book format—the arrangement of covers, pages, individual printed words and letters—and they gain insight into the elements of a story—setting, characters, the pursuit of a goal or the resolution of a problem in a sequential series of events—an understanding that is instrumental for reading comprehension."
        ),
        "zh": (
            "概述：本节的目标聚焦于儿童在有机会听故事书语言时获得的语言技能。通过听朗读的故事并谈论这些故事，儿童发展听和说的技能。"
            "他们接触新词汇和正式的书面句法，学习连接和关联想法的方式，并进一步打磨以下技能："
            "叙述——理解并描述插图，理解并描述故事的背景、人物和事件等；"
            "预测——说出接下来可能发生的事，或提出可能的另一种结局；"
            "想象——根据自己的想象，或基于插图讲述自己的故事。"
            "此外，早期接触书籍也为儿童日后开始读写所需的技能和概念打下基础。"
            "他们学习书籍的形式——封面、书页、单个印刷词和字母的排列——并理解故事要素——背景、人物、目标的追求或问题的解决，以及按一系列事件展开的过程；这种理解有助于阅读理解。"
        ),
    },
    "n00118": {
        "en": (
            "Overview: This section builds on the language skills described in the preceding sections. "
            "The competencies described here go beyond oral language skills to early reading and writing skills. "
            "The goals ask children to add to their prior experiences with printed words in books by recognizing print in the daily environment and some ways it is used: to identify, to name or label (food, toys, streets, stores, etc.), to make lists, to report events, to give directions, to communicate messages, etc. "
            "The section focuses on the relation between oral language and print. "
            "The goals ask children to associate specific familiar spoken words, such as their own names or names of familiar objects, with specific written words. "
            "Children then go on to recognize that the distinct marks that make up each word are letters in our alphabet. "
            "Children learn that these letters have names through such means as singing the alphabet song. "
            "They learn to identify and name the specific letters in their own names. "
            "A crucial part of learning to read is developing phonemic awareness, the understanding that individual sounds are associated with individual letters and combinations of letters. "
            "To help children begin to develop phonemic awareness, the goals in this section ask children not only to refine their visual recognition of print but also to attend to the spoken sounds of language (for related topics, see the clapping and rhyming skills described in Nursery Rhymes, Poems, Fingerplays and Songs). "
            "Children are asked to take apart and put together smaller and smaller units of sound, from individual words in a sentence, to syllables in words, to the beginning sounds in individual words. "
            "The goals here also include the skills needed to produce print, that is, to write. "
            "At first, children are asked to perform manual activities that enhance both hand-eye coordination and small muscle control of the hand and fingers. "
            "They learn the proper way to hold a writing implement, as well as a variety of small designs and strokes that will eventually be combined to form letters. "
            "They are also asked to write their own names."
        ),
        "zh": (
            "概述：本节以前面几节描述的语言技能为基础。这里所描述的能力超越了口语技能，进入早期读写技能。"
            "目标要求儿童在以往书中印刷文字经验的基础上，认识日常环境中的印刷文字及其一些用途：用于识别、命名或标注（食物、玩具、街道、商店等）、列清单、报告事件、给出指示、传递信息等。"
            "本节关注口语与印刷文字之间的关系。目标要求儿童把特定的熟悉口语词，如自己的名字或熟悉物体的名称，与特定的书面形式对应起来。"
            "接着儿童认识到构成每个词的不同记号是字母表中的字母。儿童通过唱字母歌等方式学习这些字母有名称。"
            "他们学会识别并说出自己名字中的具体字母。学习阅读的一个关键部分是发展音位意识，即理解单个声音与单个字母及字母组合相对应。"
            "为帮助儿童开始发展音位意识，本节目标不仅要求儿童完善对印刷文字的视觉识别，还要求他们注意语言的声音（相关主题见“童谣、诗歌、手指谣和歌曲”中描述的拍手和押韵技能）。"
            "要求儿童把声音单位不断拆分和组合，从句子中的单个词，到词中的音节，再到单词的起始音。"
            "这里的目标还包括产生印刷文字所需的技能，也就是书写。起初，要求儿童完成一些手工活动，这些活动能增强手眼协调以及手和手指小肌肉的控制。"
            "他们学习握笔的正确方式，以及各种最终会组合成字母的小图案和笔画。还要求儿童书写自己的名字。"
        ),
    },
    "n00133": {
        "zh": "概述：幼儿似乎天生就会被周围可以触摸、操作和观察的物体所吸引。本节的目标建立在这种好奇心和探索欲望之上。在先接触具体物体、再接触图片的过程中，儿童被要求识别异同、对物体和形状分类、在物体序列中识别或创造规律，并使用简单的测量技能进行比较。他们还被要求量化小组物体、计数，并展示对“合起来”和“拿走”式加减法的基本理解。在每一种情况下，儿童都被要求从具体经验出发，过渡到用数学语言进行符号化表征，例如“多于”“少于”“更长”“更短”、数词（“三”“四”）、数字符号（“3”“4”）等。"
    },
    "n00164": {
        "zh": "概述：本节的焦点是内在时间感的发展；这种时间定向不仅是日后历史教学的参照点，也是通向个人自主的又一步，因为儿童需要能够安排时间、监控行为，并在一天、一周等时间中独立完成给定活动。首先要求儿童围绕各种时间线索组织和思考日常经验：按一天中的时段分类经历、按时间顺序排列事件，并开始使用日程表和日历等标准时间工具。还要求儿童从更大尺度思考时间的流逝，通过排列自己生活中的事件、思考家庭内部的关系以及生命历程中的阶段，发展过去—现在—未来的关系感。儿童还被要求通过把熟悉的当代物品与过去相似物品进行比较，从直接经验之外采取历史视角。最后，要求儿童用语言以及时间线和图画等图示方式象征性地表达这些经验。"
    },
    "n00180": {
        "zh": "概述：本节向儿童介绍一种系统观察、描述和解释周围世界的方法。应给予儿童大量机会，对生命世界和物质世界进行系统观察与动手探究。在这些经验的基础上，儿童可以从描述和解释所观察到的内容，进一步根据这些观察作出预测。"
    },
    "n00182": {
        "en": "Human bodies are made of many different parts",
        "zh": "人体由许多不同的部分组成。",
        "type": "note",
    },
    "n00184": {
        "en": "Humans need to do certain things to grow and stay healthy",
        "zh": "人类需要做一些事情才能成长并保持健康。",
        "type": "note",
    },
    "n00191": {
        "zh": "概述：本节的目标既包括聆听、欣赏各种形式的音乐，也包括创作音乐。听歌、唱歌和做手指谣也为练习口语技能提供机会。音乐有助于扩展和澄清各种概念，如大声与小声、快与慢等。此外，把注意力集中在辨别不同的环境声音或音乐声音上，有助于日后发展音位意识，即意识到语言由离散的声音组成。集体音乐活动、共同表演或演唱，也提供练习社交技能的机会。本节的基本目标要求儿童聆听并识别声音，判断成对声音是否相同，模仿声音和节奏序列，单独和与他人一起唱歌，并随音乐进行表现性动作。"
    },
    "n00206": {
        "zh": "概述：本节不仅关注创作艺术作品，也关注观察和欣赏各种艺术形式的作品。使用各种媒介和技术为感官探索、动手操作以及精细动作技能的发展提供丰富机会。此外，通过绘画，儿童首次尝试图形表征，这是书写的先兆。引导儿童观察艺术作品，有助于练习把注意力集中在视觉细节上；这对区分物体、图像、印刷文字和字母的视觉差异，以及欣赏艺术的基本要素都很重要。进一步观察和讨论艺术作品也为语言发展提供丰富机会。本节的基本目标要求儿童注意视觉细节，识别相同或不同的图像，使用各种媒介和技术创作具象和非具象艺术作品，以已知艺术家的风格创作，并观察、谈论包括自己作品在内的选定艺术作品。"
    },

    # --- shifted translations: Social and Emotional Development -------------------
    "n00020": {"zh": "I-AS1.1 识别并回应自己的姓和名（口头及书写形式）。"},
    "n00021": {"zh": "I-AS1.2 口头说出自己的名和姓。"},
    "n00023": {"zh": "I-AS2.1 说出身体部位的名称：手臂、耳朵、眼睛、脸、手指、脚、头发、手、头、腿、嘴、脖子、鼻子、肚子、脚趾。"},
    "n00024": {"zh": "I-AS2.2a 画一个简单的人物线条画（火柴人），例如包括头（有眼睛、鼻子、嘴）、身体、胳膊和腿的火柴人。"},
    "n00025": {"zh": "I-AS3.1a 练习良好的个人卫生习惯（独立上厕所、洗手等），使用适当的餐桌礼仪（自己用叉子、勺子和刀吃饭；正确使用餐巾），自己穿衣服等。"},
    "n00026": {"zh": "I-AS5.1a 认出同学和老师，并叫出他们的名字。"},
    "n00027": {"zh": "I-AS5.2 用“某先生”“某女士”或“某太太”称呼成年人。"},
    "n00028": {"zh": "I-AS5.3 回应并回以问候和道别。"},
    "n00029": {"zh": "I-AS5.4 礼貌地提出请求，并对别人满足请求的做法作出回应。"},
    "n00030": {"zh": "I-AS5.6 小组活动中别人讲话时专心倾听。"},
    "n00031": {"zh": "I-AS5.8 在小组中轮流等待发言。"},
    "n00032": {"zh": "I-AS6.3a 完成有助于群体福祉和运转的杂务与责任。"},
    "n00033": {"zh": "I-AS6.4 小组活动时坐在其他儿童中间，并保持自己的身体空间。"},

    # --- shifted translations: Time ----------------------------------------------
    "n00165": {"zh": "I-OT1.1a 理解并使用时间词描述日常发生的事情：今天—明天、以前—以后、现在、第一—最后、白天—早晨—下午—傍晚—夜晚、当天、星期、周末、从前、最终。"},
    "n00166": {"zh": "I-OT2.1 按一天中的时段对日常活动图片进行分类并描述：白天—夜晚、早晨—下午—傍晚。"},
    "n00167": {"zh": "I-OT2.2a 按时间顺序排列并描述三幅亲身经历过的、发生在不同时间的事件图片，或单一事件的三个阶段。"},
    "n00168": {"zh": "I-OT2.3a 说出今天是星期几。"},
    "n00169": {
        "zh": (
            "I-OT2.7 说出以下名称：时钟、日程表、日历。"
            "II-OT1.1b 理解并使用时间词描述日常发生的事情：今天—明天—昨天、总是—从不—有时、之前—之后、现在—立刻、第一—最后、开始—中间—结束、然后—接下来、已经、很快、在……期间—当……时等。"
        )
    },
    "n00170": {"zh": "I-OT2.9a 使用以图片呈现的日常活动表来描述一天中事件的顺序。"},
    "n00171": {"zh": "I-OT2.10 使用周历找出并说出今天是星期几。"},

    # --- shifted translations: Music ---------------------------------------------
    "n00192": {"zh": "I-MU1.1 识别声音传来的方向。"},
    "n00193": {"zh": "I-MU1.2 聆听并识别环境中的声音。"},
    "n00194": {"zh": "I-MU1.3a 听成对的声音，判断它们是完全相同还是明显不同，并指出相同还是不同。"},
    "n00195": {"zh": "I-MU1.4 指出听到声音的数量（最多四个）。"},
    "n00196": {"zh": "I-MU2.1 用声音或乐器，根据口头指令发出响或轻、长或短的声音。"},
    "n00197": {
        "zh": (
            "I-MU2.2 用声音模仿他人发出的孤立声音，近似地表现其强度、时长和音高。"
            "II-MU1.3b 听成对的声音，判断它们是完全相同还是略有不同，并指出相同还是不同。"
        )
    },

    # --- shifted translations: Visual Arts ---------------------------------------
    "n00207": {"zh": "I-VA1.1 识别成对的物体或图像是相同还是不同。"},
    "n00208": {"zh": "I-VA1.2a 玩需要配对相同图像的游戏，如宾果游戏。"},
    "n00209": {"zh": "I-VA1.3a 识别红、黄、蓝、绿、橙、紫、棕、黑、白等颜色。"},
    "n00210": {"zh": "I-VA1.4a 观察一组物体，将其移开视线、改动后再呈现，识别不同之处，以展示对视觉细节的记忆。"},
    "n00211": {"zh": "I-VA2.1 撕：使用各种工具和技术完成艺术作品。"},
    "n00212": {"zh": "I-VA2.2 粘贴：使用各种工具和技术完成艺术作品。"},
    "n00213": {"zh": "I-VA2.3 使用贴纸：使用各种工具和技术完成艺术作品。"},
    "n00214": {"zh": "I-VA2.4 折叠：使用各种工具和技术完成艺术作品。"},
    "n00215": {
        "zh": (
            "I-VA2.5 粘贴：使用各种工具和技术完成艺术作品。"
            "II-VA1.2b 玩需要配对相同图像的游戏，如多米诺骨牌游戏。"
        )
    },

    # --- duplicate vocabulary fragment and stray K grade -------------------------
    "n00159": {"en": "addition subtraction", "zh": "加法、减法"},
    "n00161": {
        "en": "cold empty first full heavy hot last light long(er) (est) middle narrow short(er) (est) tall(er) (est) thick thin wide",
        "zh": "冷、空、第一、满、重、热、最后、轻、长（更长/最长）、中间、窄、短（更短/最短）、高（更高/最高）、厚、薄、宽",
    },
    "n00185": {
        "en": "I-SC3.2a Select and use scissors to cut straight lines.",
        "zh": "I-SC3.2a 选择并使用剪刀沿直线剪。",
    },
}

# Four overview continuation fragments were merged into n00101.
DELETE = {"n00102", "n00103", "n00104", "n00105"}

# Items whose Level I and Level II rows were merged by the PDF parser.
SPLIT = {
    "n00013", "n00034", "n00035", "n00042", "n00065", "n00071", "n00085",
    "n00092", "n00097", "n00111", "n00115", "n00122", "n00124", "n00128",
    "n00130", "n00137", "n00143", "n00150", "n00156", "n00169", "n00176",
    "n00197", "n00204", "n00215", "n00225",
}

CLEANUP = [
    (" Critical Skill", ""),
    ("Critical Skill ", ""),
    ("Critical Skill", ""),
    ("inde- pendently", "independently"),
    ("contrib ute", "contribute"),
    ("deter mine", "determine"),
    ("illustra tion", "illustration"),
    ("appropri ate", "appropriate"),
    ("complet ing", "completing"),
    ("draw ing", "drawing"),
    ("yester day", "yesterday"),
    ("cur rent", "current"),
    ("back wards", "backwards"),
]


def clean(text):
    for old, new in CLEANUP:
        text = text.replace(old, new)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def split_pair(item, new_uid):
    en = item["en"]
    zh = item["zh"]
    men = CODE_EN.search(en)
    mzh = CODE_ZH.search(zh)
    if not men or not mzh:
        raise ValueError("cannot split %s: %s / %s" % (item["uid"], en[:80], zh[:80]))
    first = dict(item)
    first["en"] = en[: men.start()].strip()
    first["zh"] = zh[: mzh.start()].strip()
    first["level"] = "I"
    second = dict(item)
    second["uid"] = new_uid
    second["id"] = item["id"] + "-b"
    second["en"] = en[men.start() :].strip()
    second["zh"] = zh[mzh.start() :].strip()
    second["level"] = "II"
    second["emojis"] = []
    second["work"] = ""
    second["link"] = ""
    return first, second


def main():
    with open(SOURCE, encoding="utf-8") as f:
        data = json.load(f)

    if not os.path.exists(BACKUP):
        shutil.copyfile(SOURCE, BACKUP)

    preschool = [i for i in data["items"] if i.get("grade") == "Preschool"]
    by_uid = {i["uid"]: i for i in preschool}

    for uid, fields in PATCH.items():
        if uid not in by_uid:
            raise ValueError("missing uid for patch: " + uid)
        by_uid[uid].update(fields)

    for item in preschool:
        if "en" in item:
            item["en"] = clean(item["en"])

    kept = []
    new_uid = NEW_UID_START
    split_count = 0
    for item in data["items"]:
        if item.get("grade") != "Preschool":
            kept.append(item)
            continue
        if item["uid"] in DELETE:
            continue
        if item["uid"] in SPLIT:
            first, second = split_pair(item, "n%05d" % new_uid)
            kept.extend([first, second])
            new_uid += 1
            split_count += 1
        else:
            kept.append(item)

    data["items"] = kept
    if isinstance(data.get("meta"), dict):
        data["meta"]["item_count"] = len(kept)

    with open(SOURCE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        "patched %d items, deleted %d, split %d, total %d"
        % (len(PATCH), len(DELETE), split_count, len(kept))
    )
    subprocess.check_call([sys.executable, EXPORT])


if __name__ == "__main__":
    main()
