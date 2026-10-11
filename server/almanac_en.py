"""英文历法对照。词表与 api-en-locale.md 第 4.4.7–4.4.11 节一致。表外宜忌和没有通行译名的节日留中文。"""

from __future__ import annotations

_MONTH = {
    "正": "1st",
    "二": "2nd",
    "三": "3rd",
    "四": "4th",
    "五": "5th",
    "六": "6th",
    "七": "7th",
    "八": "8th",
    "九": "9th",
    "十": "10th",
    "冬": "11th",
    "腊": "12th",
}

_DAY = {
    "初一": "1st",
    "初二": "2nd",
    "初三": "3rd",
    "初四": "4th",
    "初五": "5th",
    "初六": "6th",
    "初七": "7th",
    "初八": "8th",
    "初九": "9th",
    "初十": "10th",
    "十一": "11th",
    "十二": "12th",
    "十三": "13th",
    "十四": "14th",
    "十五": "15th",
    "十六": "16th",
    "十七": "17th",
    "十八": "18th",
    "十九": "19th",
    "二十": "20th",
    "廿一": "21st",
    "廿二": "22nd",
    "廿三": "23rd",
    "廿四": "24th",
    "廿五": "25th",
    "廿六": "26th",
    "廿七": "27th",
    "廿八": "28th",
    "廿九": "29th",
    "三十": "30th",
}

_STEM = {
    "甲": "Jia",
    "乙": "Yi",
    "丙": "Bing",
    "丁": "Ding",
    "戊": "Wu",
    "己": "Ji",
    "庚": "Geng",
    "辛": "Xin",
    "壬": "Ren",
    "癸": "Gui",
}
_BRANCH = {
    "子": "zi",
    "丑": "chou",
    "寅": "yin",
    "卯": "mao",
    "辰": "chen",
    "巳": "si",
    "午": "wu",
    "未": "wei",
    "申": "shen",
    "酉": "you",
    "戌": "xu",
    "亥": "hai",
}

SOLAR_TERM = {
    "立春": "Start of Spring",
    "雨水": "Rain Water",
    "惊蛰": "Awakening of Insects",
    "春分": "Spring Equinox",
    "清明": "Pure Brightness",
    "谷雨": "Grain Rain",
    "立夏": "Start of Summer",
    "小满": "Grain Buds",
    "芒种": "Grain in Ear",
    "夏至": "Summer Solstice",
    "小暑": "Minor Heat",
    "大暑": "Major Heat",
    "立秋": "Start of Autumn",
    "处暑": "End of Heat",
    "白露": "White Dew",
    "秋分": "Autumn Equinox",
    "寒露": "Cold Dew",
    "霜降": "Frost's Descent",
    "立冬": "Start of Winter",
    "小雪": "Minor Snow",
    "大雪": "Major Snow",
    "冬至": "Winter Solstice",
    "小寒": "Minor Cold",
    "大寒": "Major Cold",
}

# None 表示没有通行译名，画面留中文。
FESTIVAL = {
    "元旦": "New Year's Day",
    "元旦节": "New Year's Day",
    "腊八节": "Laba Festival",
    "情人节": "Valentine's Day",
    "除夕": "Chinese New Year's Eve",
    "春节": "Spring Festival",
    "元宵节": "Lantern Festival",
    "妇女节": "Women's Day",
    "植树节": "Arbor Day",
    "消费者权益日": "Consumer Rights Day",
    "龙头节": None,
    "全国中小学生安全教育日": None,
    "愚人节": "April Fools' Day",
    "劳动节": "Labour Day",
    "青年节": "Youth Day",
    "母亲节": "Mother's Day",
    "全国助残日": None,
    "儿童节": "Children's Day",
    "端午节": "Dragon Boat Festival",
    "父亲节": "Father's Day",
    "建党节": "CPC Founding Day",
    "建军节": "Army Day",
    "七夕节": "Qixi Festival",
    "教师节": "Teachers' Day",
    "全民国防教育日": None,
    "中秋节": "Mid-Autumn Festival",
    "国庆节": "National Day",
    "世界住房日": "World Habitat Day",
    "重阳节": "Double Ninth Festival",
    "万圣节前夜": "Halloween",
    "万圣节": "All Saints' Day",
    "感恩节": "Thanksgiving",
    "平安夜": "Christmas Eve",
    "圣诞节": "Christmas",
    "清明节": "Qingming Festival",
}

YIJI = {
    "上梁": "Raise the beam",
    "乘船": "Board a boat",
    "习艺": "Learn a craft",
    "交易": "Trade",
    "伐木": "Fell timber",
    "会亲友": "Visit family",
    "作梁": "Make a beam",
    "作灶": "Build a stove",
    "修坟": "Repair a grave",
    "修造": "Build or repair",
    "修门": "Repair a door",
    "修饰垣墙": "Mend walls",
    "入学": "Start school",
    "入宅": "Move in",
    "入殓": "Encoffin",
    "冠笄": "Coming of age",
    "出火": "Move the hearth",
    "出行": "Travel",
    "出货财": "Send goods out",
    "分居": "Live apart",
    "割蜜": "Collect honey",
    "动土": "Break ground",
    "取渔": "Fish",
    "合寿木": "Assemble a coffin",
    "合帐": "Make bed curtains",
    "合脊": "Join the roof ridge",
    "启钻": "Open a tomb",
    "坏垣": "Break a wall",
    "塑绘": "Paint and model",
    "塞穴": "Plug holes",
    "嫁娶": "Marry",
    "安床": "Set the bed",
    "安机械": "Install machinery",
    "安碓磑": "Set a grain mill",
    "安葬": "Hold a burial",
    "安门": "Set a door",
    "安香": "Install incense",
    "定磉": "Set the plinth",
    "平治道涂": "Level the road",
    "开仓": "Open the granary",
    "开光": "Consecrate",
    "开厕": "Build a latrine",
    "开市": "Open shop",
    "开柱眼": "Cut mortises",
    "开池": "Dig a pond",
    "开渠": "Dig a ditch",
    "开生坟": "Dig a new grave",
    "归宁": "Visit parents",
    "归岫": "Return to the hills",
    "成服": "Start mourning dress",
    "扫舍": "Sweep the house",
    "拆卸": "Dismantle",
    "挂匾": "Hang a sign",
    "捕捉": "Trap game",
    "掘井": "Dig a well",
    "探病": "Visit the sick",
    "放水": "Release water",
    "教牛马": "Train livestock",
    "整手足甲": "Trim nails",
    "斋醮": "Hold a rite",
    "断蚁": "Stop ants",
    "普渡": "Hold a deliverance rite",
    "架马": "Set a frame",
    "栽种": "Plant",
    "求医": "See a doctor",
    "求嗣": "Pray for a child",
    "沐浴": "Bathe",
    "治病": "Treat illness",
    "牧养": "Raise animals",
    "理发": "Cut hair",
    "畋猎": "Hunt",
    "盖屋": "Raise a roof",
    "破土": "Break burial ground",
    "破屋": "Demolish a house",
    "祈福": "Pray for blessings",
    "祭祀": "Worship",
    "移徙": "Move house",
    "移柩": "Move the coffin",
    "立券": "Sign a contract",
    "立碑": "Set a stele",
    "竖柱": "Raise pillars",
    "筑堤": "Build a dyke",
    "纳婿": "Take a son-in-law",
    "纳畜": "Take in livestock",
    "纳财": "Take in wealth",
    "纳采": "Send betrothal gifts",
    "经络": "Treat meridians",
    "结网": "Make nets",
    "置产": "Acquire property",
    "行丧": "Hold a funeral",
    "补垣": "Mend a wall",
    "裁衣": "Cut out clothes",
    "解除": "Lift a taboo",
    "订盟": "Pledge marriage",
    "词讼": "Go to law",
    "诸事不宜": "Nothing is suitable",
    "谢土": "Thank the soil",
    "赴任": "Take up a post",
    "起基": "Lay the foundation",
    "进人口": "Add to the household",
    "造仓": "Build a storehouse",
    "造庙": "Build a shrine",
    "造桥": "Build a bridge",
    "造畜稠": "Build a pen",
    "造船": "Build a boat",
    "造车器": "Make vehicles",
    "酬神": "Thank the gods",
    "针灸": "Acupuncture",
    "问名": "Ask the name",
    "除服": "End mourning",
    "雇佣": "Hire help",
    "雕刻": "Carve",
    "馀事勿取": "Do nothing else",
}

WUHOU = {
    "东风解冻": "East wind thaws the ice",
    "蛰虫始振": "Hibernating insects stir",
    "鱼陟负冰": "Fish rise under the ice",
    "獭祭鱼": "Otters set out fish",
    "候雁北": "Wild geese fly north",
    "草木萌动": "Plants begin to sprout",
    "桃始华": "Peach trees bloom",
    "仓庚鸣": "Orioles sing",
    "鹰化为鸠": "Hawks become doves",
    "玄鸟至": "Swallows arrive",
    "雷乃发声": "Thunder sounds",
    "始电": "Lightning begins",
    "桐始华": "Paulownia blooms",
    "田鼠化为鴽": "Moles become quails",
    "虹始见": "Rainbows appear",
    "萍始生": "Duckweed appears",
    "鸣鸠拂其羽": "Doves preen their feathers",
    "戴胜降于桑": "Hoopoes settle on mulberries",
    "蝼蝈鸣": "Frogs begin to croak",
    "蚯蚓出": "Earthworms come out",
    "王瓜生": "Snake gourds sprout",
    "苦菜秀": "Bitter herbs flower",
    "靡草死": "Tender grasses die back",
    "麦秋至": "Wheat ripens",
    "螳螂生": "Mantises hatch",
    "鵙始鸣": "Shrikes begin to call",
    "反舌无声": "Mimic birds fall silent",
    "鹿角解": "Deer shed their antlers",
    "蜩始鸣": "Cicadas begin to sing",
    "半夏生": "Pinellia sprouts",
    "温风至": "Warm winds arrive",
    "蟋蟀居壁": "Crickets keep to the walls",
    "鹰始挚": "Hawks begin to hunt",
    "腐草为萤": "Rotting grass becomes fireflies",
    "土润溽暑": "Soil turns damp and hot",
    "大雨行时": "Heavy rains set in",
    "凉风至": "Cool winds arrive",
    "白露降": "White dew settles",
    "寒蝉鸣": "Cicadas call in the cool",
    "鹰乃祭鸟": "Hawks set out birds",
    "天地始肃": "Heaven and earth grow stern",
    "禾乃登": "Grain comes in",
    "鸿雁来": "Wild geese arrive",
    "玄鸟归": "Swallows depart",
    "群鸟养羞": "Birds store up food",
    "雷始收声": "Thunder dies away",
    "蛰虫坯户": "Insects seal their burrows",
    "水始涸": "Waters begin to dry",
    "鸿雁来宾": "Wild geese arrive as guests",
    "雀入大水为蛤": "Sparrows enter the water as clams",
    "菊有黄花": "Chrysanthemums turn yellow",
    "豺乃祭兽": "Wolves set out their prey",
    "草木黄落": "Plants yellow and fall",
    "蛰虫咸俯": "Insects all lie low",
    "水始冰": "Water begins to freeze",
    "地始冻": "The ground begins to freeze",
    "雉入大水为蜃": "Pheasants enter the water as clams",
    "虹藏不见": "Rainbows stay hidden",
    "天气上升地气下降": "Sky qi rises and earth qi sinks",
    "闭塞而成冬": "The season closes into winter",
    "鹖鴠不鸣": "Crossbills stay silent",
    "虎始交": "Tigers begin to mate",
    "荔挺出": "Lycoris begins to sprout",
    "蚯蚓结": "Earthworms curl up",
    "麋角解": "Elk shed their antlers",
    "水泉动": "Springs begin to stir",
    "雁北乡": "Geese turn toward home",
    "鹊始巢": "Magpies start a nest",
    "雉始雊": "Pheasants begin to call",
    "鸡始乳": "Hens begin to lay",
    "征鸟厉疾": "Birds of prey fly hard and fast",
    "水泽腹坚": "Ice thickens through the marshes",
}


def lunar_phrase(text: str) -> str:
    """九月初二 → 2nd day, 9th lunar month。已经是英文的原样返回。"""
    if not text or "lunar month" in text:
        return text
    leap = text.startswith("闰")
    body = text[1:] if leap else text
    if "月" not in body:
        return text
    month, day = body.split("月", 1)
    month_en = _MONTH.get(month)
    day_en = _DAY.get(day)
    if not month_en or not day_en:
        return text
    if leap:
        return f"{day_en} day, leap {month_en} lunar month"
    return f"{day_en} day, {month_en} lunar month"


def lunar_cell(text: str) -> str:
    """月历格：初一写月份，其余只写日序。"""
    if not text or text.endswith(" month") or text.startswith("leap "):
        return text
    if text.endswith("月"):
        leap = text.startswith("闰")
        month = text[1:-1] if leap else text[:-1]
        month_en = _MONTH.get(month)
        if not month_en:
            return text
        return f"leap {month_en}" if leap else f"{month_en} month"
    return _DAY.get(text, text)


def ganzhi_pinyin(text: str) -> str:
    if not text or len(text) < 2 or text[0] not in _STEM or text[1] not in _BRANCH:
        return text
    return _STEM[text[0]] + _BRANCH[text[1]]


def solar_term_en(name: str) -> str:
    return SOLAR_TERM.get(name, name)


def yiji_en(items: list) -> list:
    return [YIJI.get(item, item) for item in items or []]


def wuhou_en(name: str) -> str:
    return WUHOU.get(name, name)


def festival_en(name: str) -> str:
    if name not in FESTIVAL:
        return name
    mapped = FESTIVAL[name]
    return name if mapped is None else mapped
