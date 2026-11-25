#!/usr/bin/env python3
"""Build canonical data for the 2022 compulsory-education subject standards.

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
    "politics": {
        "id": "moe-cn-2022-politics",
        "title": "义务教育道德与法治课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/02-义务教育道德与法治课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "history": {
        "id": "moe-cn-2022-history",
        "title": "义务教育历史课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/04-义务教育历史课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "geography": {
        "id": "moe-cn-2022-geography",
        "title": "义务教育地理课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/09-义务教育地理课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "science": {
        "id": "moe-cn-2022-science",
        "title": "义务教育科学课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/10-义务教育科学课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "physics": {
        "id": "moe-cn-2022-physics",
        "title": "义务教育物理课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/11-义务教育物理课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "chemistry": {
        "id": "moe-cn-2022-chemistry",
        "title": "义务教育化学课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/12-义务教育化学课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "biology": {
        "id": "moe-cn-2022-biology",
        "title": "义务教育生物学课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/13-义务教育生物学课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "information": {
        "id": "moe-cn-2022-information",
        "title": "义务教育信息科技课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/14-义务教育信息科技课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "japanese": {
        "id": "moe-cn-2022-japanese",
        "title": "义务教育日语课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/07-义务教育日语课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "russian": {
        "id": "moe-cn-2022-russian",
        "title": "义务教育俄语课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/08-义务教育俄语课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "pe": {
        "id": "moe-cn-2022-pe",
        "title": "义务教育体育与健康课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/15-义务教育体育与健康课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "arts": {
        "id": "moe-cn-2022-arts",
        "title": "义务教育艺术课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/16-义务教育艺术课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
    "labor": {
        "id": "moe-cn-2022-labor",
        "title": "义务教育劳动课程标准（2022年版）",
        "issuer": "中华人民共和国教育部",
        "published": "2022-04-21",
        "url": NOTICE_URL,
        "local_file": "source/17-义务教育劳动课程标准（2022年版）.pdf",
        "pdf_offset": 7,
    },
}

SUBJECTS = OrderedDict([
    ("chinese", "语文"), ("math", "数学"), ("english", "英语"),
    ("politics", "道德与法治"), ("history", "历史"), ("geography", "地理"),
    ("science", "科学"), ("physics", "物理"), ("chemistry", "化学"),
    ("biology", "生物学"), ("information", "信息科技"),
    ("pe", "体育与健康"), ("arts", "艺术"), ("labor", "劳动"),
    ("japanese", "日语"), ("russian", "俄语"),
])
STAGES = OrderedDict([
    ("x1", "小学低段（1-2年级）"),
    ("x2", "小学中段（3-4年级）"),
    ("x3", "小学高段（5-6年级）"),
    ("j1", "初中（7-9年级）"),
    ("p", "小学1-6年级"),
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
    "appendix": "课标附录",
}

# OCR confusions seen in the scanned standards. Only unambiguous visual errors
# are corrected here; substantive wording is left as scanned.
TABLE_CELL_LABELS = {
    "范畴", "主题群", "子主题内容", "级别", "内容要求", "学习策略", "策略",
    "元认知", "认知", "交际", "情感管理", "听做", "说唱", "玩演", "视听", "续表",
    "生活与学习", "做人与做事", "社会服务与人际", "沟通", "文学、艺术与体育",
    "历史、社会与文化", "科学与技术", "自然生态", "环境保护", "灾害防范", "宇宙探索",
    "学习主题", "主题", "学段", "年级", "领域", "学习任务", "学习活动",
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
    "课程内客": "课程内容",
    "箸帚": "扫帚",
    "器血": "器皿",
    "目常": "日常",
    "保键": "保健",
    "新兴体育类运助": "新兴体育类运动",
    "不解奋斗": "不懈奋斗",
}


# --- Appendix data -------------------------------------------------------
# The scanned appendices of the MOE Chinese standard are not reliably
# machine-readable.  The lists below are curated from the official PDF
# (appendices 1-5) and cross-checked against the official table descriptions.
# They are kept here so the public data layer stays deterministic.

APPENDIX_POEMS_PRIMARY = """
江南(江南可采莲)|汉乐府
长歌行(青青园中葵)|汉乐府
敕勒歌(敕勒川)|北朝民歌
咏鹅(鹅鹅鹅)|骆宾王
风(解落三秋叶)|李峤
咏柳(碧玉妆成一树高)|贺知章
回乡偶书(少小离家老大回)|贺知章
凉州词(黄河远上白云间)|王之涣
登鹳雀楼(白日依山尽)|王之涣
春晓(春眠不觉晓)|孟浩然
凉州词(葡萄美酒夜光杯)|王翰
出塞(秦时明月汉时关)|王昌龄
芙蓉楼送辛渐(寒雨连江夜入吴)|王昌龄
鹿柴(空山不见人)|王维
送元二使安西(渭城朝雨浥轻尘)|王维
九月九日忆山东兄弟(独在异乡为异客)|王维
静夜思(床前明月光)|李白
古朗月行(小时不识月)|李白
望庐山瀑布(日照香炉生紫烟)|李白
赠汪伦(李白乘舟将欲行)|李白
黄鹤楼送孟浩然之广陵(故人西辞黄鹤楼)|李白
早发白帝城(朝辞白帝彩云间)|李白
望天门山(天门中断楚江开)|李白
别董大(千里黄云白日曛)|高适
绝句(两个黄鹂鸣翠柳)|杜甫
春夜喜雨(好雨知时节)|杜甫
绝句(迟日江山丽)|杜甫
江畔独步寻花(黄师塔前江水东)|杜甫
枫桥夜泊(月落乌啼霜满天)|张继
滁州西涧(独怜幽草涧边生)|韦应物
渔歌子(西塞山前白鹭飞)|张志和
塞下曲(月黑雁飞高)|卢纶
游子吟(慈母手中线)|孟郊
早春呈水部张十八员外(天街小雨润如酥)|韩愈
望洞庭(湖光秋月两相和)|刘禹锡
浪淘沙(九曲黄河万里沙)|刘禹锡
赋得古原草送别(离离原上草)|白居易
池上(小娃撑小艇)|白居易
忆江南(江南好)|白居易
小儿垂钓(蓬头稚子学垂纶)|胡令能
悯农(锄禾日当午)|李绅
悯农(春种一粒粟)|李绅
江雪(千山鸟飞绝)|柳宗元
寻隐者不遇(松下问童子)|贾岛
山行(远上寒山石径斜)|杜牧
清明(清明时节雨纷纷)|杜牧
江南春(千里莺啼绿映红)|杜牧
蜂(不论平地与山尖)|罗隐
江上渔者(江上往来人)|范仲淹
元日(爆竹声中一岁除)|王安石
泊船瓜洲(京口瓜洲一水间)|王安石
书湖阴先生壁(茅檐长扫净无苔)|王安石
六月二十七日望湖楼醉书(黑云翻墨未遮山)|苏轼
饮湖上初晴后雨(水光潋滟晴方好)|苏轼
惠崇春江晚景(竹外桃花三两枝)|苏轼
题西林壁(横看成岭侧成峰)|苏轼
夏日绝句(生当作人杰)|李清照
三衢道中(梅子黄时日日晴)|曾几
示儿(死去元知万事空)|陆游
秋夜将晓出篱门迎凉有感(三万里河东入海)|陆游
四时田园杂兴(昼出耘田夜绩麻)|范成大
四时田园杂兴(梅子金黄杏子肥)|范成大
小池(泉眼无声惜细流)|杨万里
晓出净慈寺送林子方(毕竟西湖六月中)|杨万里
春日(胜日寻芳泗水滨)|朱熹
观书有感(半亩方塘一鉴开)|朱熹
题临安邸(山外青山楼外楼)|林升
游园不值(应怜屐齿印苍苔)|叶绍翁
乡村四月(绿遍山原白满川)|翁卷
墨梅(我家洗砚池头树)|王冕
石灰吟(千锤万凿出深山)|于谦
竹石(咬定青山不放松)|郑燮
所见(牧童骑黄牛)|袁枚
己亥杂诗(九州生气恃风雷)|龚自珍
村居(草长莺飞二月天)|高鼎
"""

APPENDIX_POEMS_JUNIOR = """
关雎(关关雎鸠)|《诗经》
蒹葭(蒹葭苍苍)|《诗经》
十五从军征(十五从军征)|汉乐府
观沧海(东临碣石)|曹操
饮酒(结庐在人境)|陶潜
木兰辞(唧唧复唧唧)|北朝民歌
送杜少府之任蜀州(城阙辅三秦)|王勃
登幽州台歌(前不见古人)|陈子昂
次北固山下(客路青山外)|王湾
使至塞上(单车欲问边)|王维
闻王昌龄左迁龙标遥有此寄(杨花落尽子规啼)|李白
行路难(金樽清酒斗十千)|李白
黄鹤楼(昔人已乘黄鹤去)|崔颢
望岳(岱宗夫如何)|杜甫
春望(国破山河在)|杜甫
茅屋为秋风所破歌(八月秋高风怒号)|杜甫
白雪歌送武判官归京(北风卷地白草折)|岑参
酬乐天扬州初逢席上见赠(巴山楚水凄凉地)|刘禹锡
卖炭翁(卖炭翁)|白居易
钱塘湖春行(孤山寺北贾亭西)|白居易
雁门太守行(黑云压城城欲摧)|李贺
赤壁(折戟沉沙铁未销)|杜牧
泊秦淮(烟笼寒水月笼沙)|杜牧
夜雨寄北(君问归期未有期)|李商隐
无题(相见时难别亦难)|李商隐
相见欢(无言独上西楼)|李煜
渔家傲(塞下秋来风景异)|范仲淹
浣溪沙(一曲新词酒一杯)|晏殊
登飞来峰(飞来山上千寻塔)|王安石
江城子(老夫聊发少年狂)|苏轼
水调歌头(明月几时有)|苏轼
渔家傲(天接云涛连晓雾)|李清照
游山西村(莫笑农家腊酒浑)|陆游
南乡子(何处望神州)|辛弃疾
破阵子(醉里挑灯看剑)|辛弃疾
过零丁洋(辛苦遭逢起一经)|文天祥
天净沙·秋思(枯藤老树昏鸦)|马致远
山坡羊·潼关怀古(峰峦如聚)|张养浩
己亥杂诗(浩荡离愁白日斜)|龚自珍
满江红(小住京华)|秋瑾
《论语》十二章(学而时习之；吾日三省吾身；吾十有五而志于学；温故而知新；学而不思则罔；贤哉回也；知之者不如好之者；不义而富且贵；三人行；子在川上曰；三军可夺帅也；博学而笃志)|《论语》
曹刿论战|《左传》
《孟子》三则(鱼我所欲也；得道多助，失道寡助；天将降大任于是人也)|《孟子》
《庄子》一则(北冥有鱼……亦若是则已矣。)|《庄子》
《礼记》一则(虽有嘉肴)|《礼记》
《吕氏春秋》一则(伯牙鼓琴……世无足复为鼓琴者。)|《吕氏春秋》
邹忌讽齐王纳谏|《战国策》
出师表|诸葛亮
桃花源记|陶潜
答谢中书书|陶弘景
三峡|郦道元
杂说(四)|韩愈
陋室铭|刘禹锡
小石潭记|柳宗元
岳阳楼记|范仲淹
醉翁亭记|欧阳修
爱莲说|周敦颐
记承天寺夜游|苏轼
送东阳马生序(余幼时即嗜学……况才之过于余者乎)|宋濂
湖心亭看雪|张岱
"""

BASIC_CHARS_BY_STROKES = OrderedDict([
    ("1", "一"),
    ("2", "二十厂七儿八人入几九了刀力又"),
    ("3", "三干工土才下大小口上山巾千个广门己子也女飞习马"),
    ("4", "王开天元云木五不太友车牙比切止少日中贝内水见午牛手气毛长片爪反父从今分公月风六文方火户心双书"),
    ("5", "玉打正去古本可左右石平北旦目电田叫四生禾们白他瓜用册外冬鸟包主市立半让出奶加皮母"),
    ("6", "动老地耳共机过在百有页光当早虫同吃回网肉年先竹自向后行全会合爷多冰交衣问字羊关米灯江阳阴好她妈羽红"),
    ("7", "进远走把花村更豆医来时里足男吵听吹财钉我利每体你住身近坐岛饭床库间快灾迟张"),
    ("8", "玩青现顶抬直林画雨到非果国明忠和的金爸采朋鱼狗饱京放河学空房视话织经"),
    ("9", "春城草面轻背点是星昨看胆胖亮美前首洗穿语说孩"),
    ("10", "班起都校样桌铅笔饿高站海家被祥课"),
    ("11", "理雪常晚船盒彩猫着情"),
    ("12", "煮期晴跑短道裤"),
    ("13", "跳"),
])

APPENDIX_READING = [
    "童话：安徒生童话、格林童话、叶圣陶《稻草人》、张天翼《宝葫芦的秘密》。",
    "寓言：中国古今寓言、《伊索寓言》。",
    "故事：成语故事、神话故事、民间故事、中外历史故事。",
    "诗歌散文作品：鲁迅《朝花夕拾》、冰心《繁星·春水》、《艾青诗选》、方志敏《可爱的中国》、《革命烈士诗抄》、中外童谣、儿童诗歌。",
    "长篇名著：吴承恩《西游记》、施耐庵《水浒传》、老舍《骆驼祥子》、罗广斌和杨益言《红岩》、埃德加·斯诺《红星照耀中国》、斯威夫特《格列佛游记》、夏洛蒂·勃朗特《简·爱》、高尔基《童年》、奥斯特洛夫斯基《钢铁是怎样炼成的》。",
    "科普科幻作品：《十万个为什么》、儒勒·凡尔纳《海底两万里》。",
]

APPENDIX_GRAMMAR = [
    "词的分类：名词、动词、形容词、数词、量词、代词、副词、介词、连词、助词、语气词、叹词。",
    "短语的结构：并列式、偏正式、主谓式、动宾式、补充式。",
    "单句的成分：主语、谓语、宾语、定语、状语、补语。",
    "复句的类型：并列、递进、选择、转折、因果、假设、条件。",
    "常用标点符号：句号、问号、感叹号、逗号、顿号、分号、冒号、引号、括号、破折号、省略号、书名号。",
    "常见修辞手法：比喻、拟人、夸张、排比、对偶、反复、设问、反问。",
]

# A few all-stage items actually spell out separate grade bands.  Split only
# those curated cases; genuinely cross-stage items stay under 全学段.
GRADE_BAND_RE = re.compile(
    r"(?P<band>1[～~—-]2|3[～~—-]4|5[～~—-]6|7[～~—-]9|1[～~—-]6|1[～~—-]4|5[～~—-]9|56|79|一[～~—-]二|三[～~—-]四|五[～~—-]六|七[～~—-]九)年级"
)
BAND_STAGES = {
    "1～2": ["x1"], "3～4": ["x2"], "5～6": ["x3"], "7～9": ["j1"],
    "1-2": ["x1"], "3-4": ["x2"], "5-6": ["x3"], "7-9": ["j1"],
    "1~2": ["x1"], "3~4": ["x2"], "5~6": ["x3"], "7~9": ["j1"],
    "1—2": ["x1"], "3—4": ["x2"], "5—6": ["x3"], "7—9": ["j1"],
    "一二": ["x1"], "三四": ["x2"], "五六": ["x3"], "七九": ["j1"],
    "1～6": ["p"], "1-6": ["p"], "1~6": ["p"], "1—6": ["p"],
    "1～4": ["x1", "x2"], "1-4": ["x1", "x2"], "1~4": ["x1", "x2"],
    "5～9": ["x3", "j1"], "5-9": ["x3", "j1"], "5~9": ["x3", "j1"],
    "12": ["x1"], "34": ["x2"], "56": ["x3"], "79": ["j1"],
    "16": ["p"], "14": ["x1", "x2"], "59": ["x3", "j1"],
    "一二": ["x1"], "三四": ["x2"], "五六": ["x3"], "七九": ["j1"],
}
CIRCLED_RE = re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩]")
LINE_BREAK_RE = re.compile(r"(?<=[\u4e00-\u9fa5。；;：:])(?=[①②③④⑤⑥⑦⑧⑨⑩])")


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
        line = re.sub(r"[IVX]?\s*义务教育[\u4e00-\u9fa5]{2,8}课程标准（2022年版）", "", line)
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
    seed = f"{subject}|{stage}|{domain}|{topic}|{item_type}|{text}"
    if subject not in ("chinese", "math", "english"):
        seed = f"{counter}|{seed}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
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


def item_uid(item: dict) -> str:
    subject = item["subject_key"]
    seed = "|".join([
        subject, item["stage_key"], item["domain"], item["topic"],
        item["type"], item["text"],
    ])
    if subject not in ("chinese", "math", "english"):
        seed = f"{item.get('seq', 0)}|{seed}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
    return f"{subject[:2]}-{item['stage_key']}-{item['type'][:3]}-{digest}"


def parse_appendix_chinese() -> list[dict]:
    """Curated, concrete lists from the appendices of the 2022 Chinese standard."""
    source = SOURCES["chinese"]
    items: list[dict] = []
    counter = 0

    def add(stage: str, topic: str, text: str, page: int) -> None:
        nonlocal counter
        counter += 1
        items.append(make_item(
            counter, "chinese", source["id"], stage, "课标附录", topic,
            "appendix", text, page, page + source["pdf_offset"],
        ))

    for group, raw, page in (
        ("1-6年级（75篇）", APPENDIX_POEMS_PRIMARY, 58),
        ("7-9年级（60篇/段）", APPENDIX_POEMS_JUNIOR, 61),
    ):
        stage = "p" if group.startswith("1-6") else "j1"
        for line in raw.strip().splitlines():
            title, author = line.split("|", 1)
            add(stage, "优秀诗文背诵推荐篇目", f"{title}（{author}）", page)

    total = sum(len(chars) for chars in BASIC_CHARS_BY_STROKES.values())
    if total != 300:
        raise SystemExit(f"basic character table must contain 300 chars, got {total}")
    for strokes, chars in BASIC_CHARS_BY_STROKES.items():
        add("x1", "识字、写字教学基本字表",
            f"{strokes}画（{len(chars)}字）：{' '.join(chars)}", 66)
    add("p", "义务教育语文课程常用字表",
        "字表一收2500字，可作为第三学段（5-6年级）识字、写字教学评价的依据；完整字表见官方 PDF 附录5。", 70)
    add("p", "义务教育语文课程常用字表",
        "字表二收1000字；两个字表合计3500个常用汉字。完整字表见官方 PDF 附录5。", 70)
    for text in APPENDIX_READING:
        add("p", "关于课内外读物的建议", text, 64)
    for text in APPENDIX_GRAMMAR:
        add("p", "关于语法修辞知识的说明", text, 65)
    return items


def unique(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


def split_stage_bands(items: list[dict]) -> list[dict]:
    """Split only curated all-stage items that contain explicit grade bands."""
    out: list[dict] = []
    for item in items:
        if item.get("stage_key") != "all" or item.get("type") == "appendix":
            out.append(item)
            continue
        text = item["text"]
        matches = list(GRADE_BAND_RE.finditer(text))
        if not matches:
            out.append(item)
            continue
        prefix = text[:matches[0].start()].strip("：:，,。；; ")
        segments: list[tuple[list[str], str, str]] = []
        for idx, match in enumerate(matches):
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            segment = text[start:end].strip("：:，,。；; ")
            raw_band = match.group("band")
            label = raw_band.replace("～", "-").replace("~", "-").replace("—", "-")
            band_key = raw_band.replace("～", "").replace("~", "").replace("—", "").replace("-", "")
            stages = BAND_STAGES.get(band_key, BAND_STAGES.get(raw_band, []))
            if not stages:
                continue
            if segment.startswith("及以上各学段") or segment.startswith("及以上"):
                stages = ["x2", "x3", "j1"] if "3" in band_key else stages
            if not segment:
                if segments:
                    old_stages, old_text, old_label = segments[-1]
                    segments[-1] = (unique(old_stages + stages), old_text, old_label)
                else:
                    segments.append((stages, "", label))
                continue
            if segments and not segments[-1][1]:
                stages = unique(segments[-1][0] + stages)
                label = segments[-1][2]
                segments[-1] = (stages, segment, label)
            else:
                segments.append((stages, segment, label))
        if not segments or not any(text for _, text, _ in segments):
            out.append(item)
            continue
        for stages, segment, label in segments:
            if not segment:
                continue
            body = segment
            if body.startswith("及以上"):
                body = re.sub(r"^及以上(?:各学段)?[：:]?", "", body).strip()
                head = f"{prefix}{label}及以上：" if prefix else f"{label}及以上："
            else:
                head = f"{prefix}（{label}）：" if prefix else f"{label}："
            for stage in stages:
                new = dict(item)
                new["stage_key"] = stage
                new["stage"] = STAGES[stage]
                new["text"] = head + body
                new["uid"] = item_uid(new)
                out.append(new)
    return out


def add_line_breaks(items: list[dict]) -> list[dict]:
    """Keep multi-point items as one record but make internal points visible."""
    for item in items:
        text = item.get("text", "")
        if CIRCLED_RE.search(text):
            item["text"] = LINE_BREAK_RE.sub("\n", text)
            item["uid"] = item_uid(item)
    return items


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


# Page ranges of the 课程内容 chapter in the scanned PDFs (1-based PDF pages).
# The printed page number is PDF page minus 7 for every standard.
GENERIC_PAGES = {
    "politics": (24, 49),
    "history": (16, 58),
    "geography": (16, 37),
    "science": (23, 118),
    "physics": (16, 45),
    "chemistry": (17, 43),
    "biology": (16, 39),
    "information": (19, 50),
    "pe": (17, 113),
    "arts": (21, 106),
    "labor": (20, 40),
    "japanese": (14, 29),
    "russian": (17, 32),
}

# Subjects whose content chapter is written for junior high only.
JUNIOR_ONLY = {"history", "geography", "physics", "chemistry", "biology", "russian"}

# Standards whose core content is published as two-column tables; OCR flattens
# the columns, so keep one neutral item type instead of guessing the column.
FLAT_TYPE_STANDARDS = {"politics", "science", "physics", "chemistry", "biology"}

# Science tables put four stage columns side by side; OCR cannot reliably tell
# which column a row belongs to, so keep these items at the all-stage level.
FORCE_ALL_STAGE = {"science"}

# These standards write 课程内容 as running prose or wide tables rather than
# numbered paragraphs; collect text up to sentence-ending punctuation.
PROSE_STANDARDS = {"japanese", "russian", "pe", "arts", "labor"}

STAGE_HEAD_RE = re.compile(r"第([一二三四])学段")
LEVEL_HEAD_RE = re.compile(r"达到水平([一二三四])目标要求")
TYPE_HEAD_RE = re.compile(
    r"^[【\[]?\s*(内容要求|学业要求|教学提示|内容标准|学业质量标准)\s*[\]】]?$"
)
TYPE_LABEL_RE = re.compile(r"^(内容要求|素养表现|活动建议)[:：]\s*(.*)$")
TASK_GROUP_RE = re.compile(r"^任务群\s*\d+\s*[:：]\s*(.+)$")
CN_HEAD_RE = re.compile(
    r"^[（(]([一二三四五六七八九十]+)[）)]\s*(.+)$|^([一二三四五六七八九十]+)[、．.]\s*(.+)$"
)
NUM_HEAD_RE = re.compile(r"^(\d+)[．.、]\s*(.+)$")
CN_ITEM_RE = re.compile(r"^[（(](\d+)[）)]\s*")
NUM_ITEM_RE = re.compile(r"^(\d+)[．.、]\s*")
BULLET_RE = re.compile(r"^[·•●▪]\s*")
GRADE_RANGE_RE = re.compile(r"^([1-9])[~～\-]([1-9])$")
STAGE_START = {"1": "x1", "3": "x2", "5": "x3", "7": "j1"}
SECTION_RE = re.compile(
    r"^[一二三四五六七]、\s*(课程内容|学业质量|课程实施|课程目标|劳动素养要求)$"
)
TYPE_FROM_HEAD = {
    "内容要求": "content", "内容标准": "content",
    "学业要求": "academic", "学业质量标准": "academic", "素养表现": "academic",
    "教学提示": "tip", "活动建议": "tip",
}


def parse_generic(key: str) -> list[dict]:
    """Generic outline parser for standards without a bespoke parser.

    Heuristics: Chinese-numeral headings define domains, Arabic-numeral short
    headings define topics, 【…】 lines define item types, and 第N学段 lines
    define stages. Numbered paragraphs become individual items.
    """
    source = SOURCES[key]
    pages = load_ocr(key)
    start, end = GENERIC_PAGES[key]
    flat_type = key in FLAT_TYPE_STANDARDS
    force_all = key in FORCE_ALL_STAGE
    prose = key in PROSE_STANDARDS
    items: list[dict] = []
    counter = 0
    stage = "j1" if key in JUNIOR_ONLY else ""
    domain = ""
    topic = ""
    item_type = "content"
    buffer: list[str] = []
    buf_page = 0

    def add(text: str, page: int) -> None:
        nonlocal counter
        text = tidy(buffer + [text]) if text else tidy(buffer)
        if not text or len(text) < 8:
            return
        counter += 1
        items.append(make_item(
            counter, key, source["id"], stage or "all", domain or "课程内容",
            topic or item_type, item_type, text,
            page - source["pdf_offset"], page,
        ))

    def flush() -> None:
        nonlocal buffer
        if buffer:
            add("", buf_page)
        buffer = []

    for pdf_page, raw_lines in pages:
        if pdf_page < start or pdf_page > end:
            continue
        for line in clean_lines(raw_lines):
            m = SECTION_RE.match(line)
            if m:
                flush()
                if m.group(1) != "课程内容":
                    domain = topic = ""
                    item_type = "content"
                    break
                continue
            m = STAGE_HEAD_RE.search(line) if (len(line) <= 30 and not force_all) else None
            if m:
                flush()
                stage = {"一": "x1", "二": "x2", "三": "x3", "四": "j1"}[m.group(1)]
                continue
            m = LEVEL_HEAD_RE.match(line) if not force_all else None
            if m:
                flush()
                stage = {"一": "x1", "二": "x2", "三": "x3", "四": "j1"}[m.group(1)]
                continue
            m = GRADE_RANGE_RE.match(line)
            if m and not force_all and m.group(1) in STAGE_START:
                flush()
                stage = STAGE_START[m.group(1)]
                continue
            if TYPE_HEAD_RE.match(line):
                flush()
                if not flat_type:
                    item_type = TYPE_FROM_HEAD[TYPE_HEAD_RE.match(line).group(1)]
                topic = ""
                continue
            m = TYPE_LABEL_RE.match(line)
            if m:
                flush()
                if not flat_type:
                    item_type = TYPE_FROM_HEAD[m.group(1)]
                rest = m.group(2).strip()
                buffer = [rest] if rest else []
                buf_page = pdf_page
                continue
            m = TASK_GROUP_RE.match(line)
            if m:
                flush()
                topic = m.group(1).strip()
                continue
            if len(line) <= 20:
                hit = next((kw for kw in TYPE_FROM_HEAD if kw in line), None)
                if hit:
                    flush()
                    if not flat_type:
                        item_type = TYPE_FROM_HEAD[hit]
                    topic = ""
                    continue
            # PE table rows like "四、五对五足球" are not section headings.
            if re.match(r"^[一二三四]、\s*五对五", line):
                continue
            m = CN_HEAD_RE.match(line)
            if m:
                flush()
                domain = (m.group(2) or m.group(4)).strip()
                topic = ""
                continue
            m = NUM_HEAD_RE.match(line)
            if m:
                rest = m.group(2).strip()
                if len(rest) <= 20 and not rest.endswith(("。", "；", "，", "：")):
                    flush()
                    topic = rest
                    continue
                flush()
                buffer = [rest]
                buf_page = pdf_page
                continue
            m = CN_ITEM_RE.match(line)
            if m:
                flush()
                buffer = [CN_ITEM_RE.sub("", line, count=1)]
                buf_page = pdf_page
                continue
            if BULLET_RE.match(line):
                flush()
                buffer = [BULLET_RE.sub("", line, count=1)]
                buf_page = pdf_page
                continue
            if (not buffer and (not prose or not topic) and len(line) <= 14
                    and not line.endswith(("。", "；", "，", "：", "、"))
                    and not re.search(r"\d", line)):
                topic = line
                continue
            if prose:
                if not buffer:
                    buf_page = pdf_page
                buffer.append(line)
                if len(buffer) >= 6 or (len(buffer) >= 2 and re.search(r"[。！？]$", line)):
                    flush()
                continue
            if buffer:
                buffer.append(line)
    flush()
    return items


# --- Concrete-content filter -------------------------------------------------
# The public viewer keeps only items that give parents/teachers something
# checkable: a number, an observable action plus a concrete object, or a clear
# academic requirement. Rhetorical curriculum language, teaching instructions
# and OCR table debris are archived separately instead of being displayed.

FILTER_VERSION = "concrete-v1"
FILTER_RULE = (
    "保留含数字、可观察动作与具体对象的条目；剔除概念定义、教学口吻、"
    "笼统目标表述与 OCR 表格碎片。"
)
F_NUM = re.compile(
    r"\d+\s*(?:个|种|项|次|年级|周|分钟|米|千米|厘米|字|词|句|篇|首|道|题|名|人|%|％)"
    r"|共\d|每周|不少于|至少|左右|以上|以下|累计"
)
F_ACTION = re.compile(
    r"认识|知道|了解|掌握|学会|会用|会|能|说出|背诵|朗读|书写|写|使用|运用|理解|"
    r"完成|设计|制作|观察|记录|计算|测量|演唱|演奏|绘制|识别|区分|比较|列举|举例|"
    r"说明|分析|评价|提出|解决|开展|体验|感受|推测|解释|总结|归纳|概括|整理|查找|"
    r"搜索|编程|实验|操作|探究|阐释|迁移|应用|实践|表达|交流|感知|发现|控制|切断|"
    r"保护|预防|制订|制定|独立识字|识字"
)
F_OBJECT = re.compile(
    r"汉字|词语|古诗|课文|字典|词典|检字|句子|语法|单词|句型|作文|分数|小数|整数|"
    r"方程|三角形|图形|公式|电流表|电压表|电压|频率|家庭电路|用电|实验|器材|植物|"
    r"动物|人体|健康|疾病|运动|动作|技能|软件|网络|数据|算法|编程|音乐|歌曲|节拍|"
    r"乐器|绘画|色彩|作品|劳动|工具|材料|项目|流程|规则|方法|语篇|句式|段落|主题|"
    r"文化|体能|机体|剧目|演出|图集|图片|浮力|金属块|测力计|盐水|电器|说明书|滤镜|"
    r"问题|情境|技术|活动|学习|传染病|传染源|人群|措施|事件|人物|现象|史事|线索|"
    r"家乡|环境|规划|建议|跳绳|礼仪|家庭|父母|长辈|祖辈|故事|传统|家风|计划"
)
F_META = re.compile(
    r"引导学生|指导学生|鼓励学生|要求学生|学生应该|学生应|要引导|应引导|应注重|"
    r"注重|重视|关注|评价要|教学建议|教材编写|课程资源|教学研究|教师培训|奠定基础|"
    r"具有重要意义|核心素养|育人价值|课程目标|课程理念|课程性质|设计思路|总体要求|"
    r"内涵|是学生学习|是学生在|必须经历|有机融合|相辅相成|贯穿始终|旨在|力求|着力|"
    r"进一步|不断|让学生|要提供|必须亲身经历|提供足够"
)
F_WEAK_META = re.compile(
    r"培养|促进|提升|增强|树立|激发|感悟|体会|积极|主动|良好|重要|基本|充分|有效|"
    r"合理|科学|逐步|不断"
)
F_TABLE_SUBJECTS = {"politics", "science", "physics", "chemistry", "biology", "pe"}


def filter_garble(text: str, subject_key: str) -> str:
    """Return a reason when OCR text looks like a table fragment, else ''."""
    if subject_key == "pe" and len(text) >= 25 and not re.search(r"[。！？；]", text):
        return "garbled-pe-no-sentence"
    if len(text) >= 35 and not re.search(r"[。！？；，、：]", text):
        return "garbled-no-punct"
    if re.search(r"([\u4e00-\u9fa5]{2,4})\1", text) or re.search(r"(?:的|了|在|和){2,}", text):
        return "garbled-dup-word"
    if re.search(r"<[\u4e00-\u9fa5]", text):
        return "garbled-broken-angle"
    if "）" in text and "（" in text and text.find("）") < text.find("（"):
        return "garbled-broken-paren"
    grams = [text[i:i + 4] for i in range(len(text) - 3)]
    if grams:
        repeats = max(Counter(grams).values())
        punct = len(re.findall(r"[，。；、：]", text))
        if repeats >= 4 and (len(text) < 180 or punct < 6):
            return "garbled-repeat-gram"
        if repeats == 3 and len(text) < 180 and punct < 5:
            return "garbled-repeat-gram"
    if len(text) >= 25 and text.endswith(("、", "，", "的", "了", "和")):
        return "garbled-trailing"
    return ""


def classify_concrete(item: dict) -> tuple[str, str]:
    """Return ('keep', '') or ('drop', reason) for one curriculum item."""
    text = re.sub(r"^\d+(?:\.\d+)*[.、]?\s*", "", item["text"])
    number = bool(F_NUM.search(text))
    actions = len(F_ACTION.findall(text))
    objects = len(F_OBJECT.findall(text))
    meta = len(F_META.findall(text))
    weak = len(F_WEAK_META.findall(text))

    if item.get("type") == "appendix":
        return "keep", ""
    garble = filter_garble(text, item.get("subject_key", ""))
    if garble:
        return "drop", garble
    if item.get("type") in ("tip", "note", "theme") and not number:
        return "drop", "type-noncontent"
    if meta >= 1 and (not number or meta >= 2):
        return "drop", "meta"
    if weak >= 2 and actions < 2 and not number:
        return "drop", "weak-meta"
    if number and actions >= 1:
        return "keep", ""
    if actions >= 1 and objects >= 1 and len(text) <= 260:
        return "keep", ""
    if item.get("type") == "academic" and actions >= 1 and len(text) <= 200:
        return "keep", ""
    return "drop", "no-concrete"


def filter_items(items: list[dict]) -> tuple[list[dict], list[dict]]:
    kept: list[dict] = []
    excluded: list[dict] = []
    for item in items:
        decision, reason = classify_concrete(item)
        if decision == "keep":
            kept.append(item)
        else:
            archived = dict(item)
            archived["filter_reason"] = reason
            excluded.append(archived)
    return kept, excluded


def build() -> tuple[dict, list[dict]]:
    all_items: list[dict] = []
    all_items.extend(parse_chinese())
    all_items.extend(parse_math())
    all_items.extend(parse_english())
    for key in GENERIC_PAGES:
        if (OCR / f"{key}.txt").exists():
            all_items.extend(parse_generic(key))
    all_items.extend(parse_appendix_chinese())
    # Classify the original OCR items first; stage splitting and line breaks
    # are presentation-level transforms of items that already passed.
    kept, excluded = filter_items(all_items)
    kept = split_stage_bands(kept)
    kept = add_line_breaks(kept)
    return {
        "meta": {
            "title": "中国小学初中课程标准知识点",
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
                "appendix": "教育部课程标准附录中的具体清单",
            },
            "appendix_note": "附录清单依据教育部 2022 年版课标 PDF 整理；扫描表格无法可靠自动识别的部分已人工校对，完整原表请以官方 PDF 为准。",
            "filter": {
                "version": FILTER_VERSION,
                "rule": FILTER_RULE,
                "kept": len(kept),
                "excluded": len(excluded),
            },
        },
        "items": kept,
    }, excluded


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


def write_excluded(excluded: list[dict]) -> None:
    archive = {
        "meta": {
            "title": "中国课程标准未展示条目（暂存）",
            "filter_version": FILTER_VERSION,
            "filter_rule": FILTER_RULE,
            "count": len(excluded),
            "notice": "这些条目不是删除，只是不符合当前「只展示干货」的筛选标准；可从原始 OCR 重新构建。",
        },
        "items": excluded,
    }
    (DATA / "primary-secondary-excluded.json").write_text(
        json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    fields = [
        "uid", "seq", "subject", "subject_key", "stage", "stage_key",
        "domain", "topic", "type", "text", "source_page", "source_pdf_page",
        "source_id", "filter_reason",
    ]
    with (DATA / "primary-secondary-excluded.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in excluded:
            writer.writerow({k: item.get(k, "") for k in fields})


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    data, excluded = build()
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
    write_excluded(excluded)
    print("items", len(data["items"]))
    print("excluded", len(excluded))
    print("by reason", dict(Counter(x["filter_reason"] for x in excluded)))
    print("by subject", dict(Counter(x["subject"] for x in data["items"])))
    print("by type", dict(Counter(x["type"] for x in data["items"])))


if __name__ == "__main__":
    main()
