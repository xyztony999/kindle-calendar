"""每日一言：Hitokoto API + 内置离线古诗词兜底（按日轮换，确定性）。"""

from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import urlsplit

import requests

log = logging.getLogger(__name__)

# 固定常量地址，无动态拼接；请求前仍做协议/主机校验并禁止重定向
HITOKOTO_URL = "https://v1.hitokoto.cn/?c=i&c=d&max_length=28&encode=json"
ALLOWED_HOSTS = {"v1.hitokoto.cn"}
ZENQUOTES_URL = "https://zenquotes.io/api/today"
ZENQUOTES_HOSTS = {"zenquotes.io"}

# 公有领域古诗词摘句（离线兜底，按当年第几天轮换）
OFFLINE_QUOTES: list[dict[str, str]] = [
    {"text": "山川湖海，皆是文章。", "from": "集句"},
    {"text": "晚来天欲雪，能饮一杯无。", "from": "白居易《问刘十九》"},
    {"text": "行到水穷处，坐看云起时。", "from": "王维《终南别业》"},
    {"text": "人间有味是清欢。", "from": "苏轼《浣溪沙》"},
    {"text": "风烟俱净，天山共色。", "from": "吴均《与朱元思书》"},
    {"text": "晚风庭院月初凉。", "from": "李清照《浣溪沙》"},
    {"text": "一蓑烟雨任平生。", "from": "苏轼《定风波》"},
    {"text": "山光悦鸟性，潭影空人心。", "from": "常建《题破山寺后禅院》"},
    {"text": "春水碧于天，画船听雨眠。", "from": "韦庄《菩萨蛮》"},
    {"text": "闲敲棋子落灯花。", "from": "赵师秀《约客》"},
    {"text": "此心安处是吾乡。", "from": "苏轼《定风波》"},
    {"text": "细雨鱼儿出，微风燕子斜。", "from": "杜甫《水槛遣心》"},
    {"text": "白日依山尽，黄河入海流。", "from": "王之涣《登鹳雀楼》"},
    {"text": "明月松间照，清泉石上流。", "from": "王维《山居秋暝》"},
    {"text": "陌上花开，可缓缓归矣。", "from": "钱镠"},
    {"text": "雪沫乳花浮午盏，蓼茸蒿笋试春盘。", "from": "苏轼《浣溪沙》"},
    {"text": "小舟从此逝，江海寄余生。", "from": "苏轼《临江仙》"},
    {"text": "云破月来花弄影。", "from": "张先《天仙子》"},
    {"text": "落霞与孤鹜齐飞，秋水共长天一色。", "from": "王勃《滕王阁序》"},
    {"text": "纸上得来终觉浅，绝知此事要躬行。", "from": "陆游《冬夜读书示子聿》"},
    {"text": "山寺月中寻桂子，郡亭枕上看潮头。", "from": "白居易《忆江南》"},
    {"text": "欲把西湖比西子，淡妆浓抹总相宜。", "from": "苏轼《饮湖上初晴后雨》"},
    {"text": "稻花香里说丰年，听取蛙声一片。", "from": "辛弃疾《西江月》"},
    {"text": "且将新火试新茶，诗酒趁年华。", "from": "苏轼《望江南》"},
    {"text": "庐山烟雨浙江潮。", "from": "苏轼《观潮》"},
    {"text": "吹灭读书灯，一身都是月。", "from": "孙玉石《吹灭读书灯》"},
    {"text": "我有一瓢酒，可以慰风尘。", "from": "韦应物《简卢陟》"},
    {"text": "秋阴不散霜飞晚，留得枯荷听雨声。", "from": "李商隐《宿骆氏亭》"},
    {"text": "卧看满天云不动，不知云与我俱东。", "from": "陈与义《襄邑道中》"},
    {"text": "梅子留酸软齿牙，芭蕉分绿与窗纱。", "from": "杨万里《闲居初夏》"},
    {"text": "逢人问道归何处，笑指船儿是此家。", "from": "杨万里《舟过谢潭》"},
]

# 公有领域英文短句。在线失败、过宽，或英文离线模式时使用。
EN_QUOTES: list[dict[str, str]] = [
    {"text": "To be, or not to be.", "from": "Shakespeare"},
    {"text": "All the world's a stage.", "from": "Shakespeare"},
    {"text": "Parting is such sweet sorrow.", "from": "Shakespeare"},
    {"text": "I wandered lonely as a cloud.", "from": "Wordsworth"},
    {"text": "The child is father of the man.", "from": "Wordsworth"},
    {"text": "If Winter comes, can Spring be far behind?", "from": "Shelley"},
    {"text": "A thing of beauty is a joy for ever.", "from": "Keats"},
    {"text": "Beauty is truth, truth beauty.", "from": "Keats"},
    {"text": "Tyger, tyger, burning bright.", "from": "Blake"},
    {"text": "Hope is the thing with feathers.", "from": "Dickinson"},
    {"text": "I celebrate myself.", "from": "Whitman"},
    {"text": "I am the master of my fate.", "from": "Henley"},
]

_day_cache: dict[str, dict] = {}
_en_cache: dict[str, dict] = {}


def _check_url(url: str, hosts: set[str] | None = None) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "https" and parts.hostname in (hosts or ALLOWED_HOSTS)


def local_en_quote(now: datetime) -> dict:
    return dict(EN_QUOTES[now.timetuple().tm_yday % len(EN_QUOTES)])


def footer_fits(text: str, source: str, width: int = 758) -> bool:
    """页脚缩到基准 16px 后是否还放得下。过宽则改用本地短句。"""
    from PIL import Image, ImageDraw

    from server.render import style

    img = Image.new("L", (max(width, 1), 52), 255)
    draw = ImageDraw.Draw(img)
    line = f"「{text}」"
    if source:
        line += f" ——{source}"
    sx = width / 646
    font = style.get_font(max(15, round(16 * sx)), "")
    return style.tracked_width(draw, line, font) <= width - 12


def _fetch_zenquotes() -> dict | None:
    if not _check_url(ZENQUOTES_URL, ZENQUOTES_HOSTS):
        return None
    try:
        resp = requests.get(ZENQUOTES_URL, timeout=8, allow_redirects=False)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            data = data[0] if data else {}
        if not isinstance(data, dict):
            return None
        text = (data.get("q") or "").strip()
        if not text:
            return None
        return {"text": text, "from": (data.get("a") or "").strip()}
    except Exception as exc:
        log.warning("zenquotes 拉取失败: %s", exc)
        return None


def english_quote(
    now: datetime,
    mode: str = "online",
    custom: list | None = None,
    width: int = 758,
) -> dict:
    """英文页脚。在线用 ZenQuotes 当日一句；失败或过宽用本地短句。自定义原样。"""
    if mode == "custom":
        items = [item for item in (custom or []) if (item.get("text") or "").strip()]
        if items:
            picked = items[now.timetuple().tm_yday % len(items)]
            return {"text": picked["text"].strip(), "from": (picked.get("from") or "").strip()}
        return local_en_quote(now)
    if mode == "offline":
        return local_en_quote(now)

    key = now.strftime("%Y-%m-%d")
    cached = _en_cache.get(key)
    if cached is not None:
        return dict(cached)

    quote = _fetch_zenquotes()
    if quote is not None and not footer_fits(quote["text"], quote["from"], width):
        quote = None
    if quote is None:
        quote = local_en_quote(now)

    stale = [item for item in _en_cache if not item.startswith(key)]
    for item in stale:
        _en_cache.pop(item, None)
    _en_cache[key] = quote
    return dict(quote)


def get_quote(now: datetime, mode: str = "online", custom: list | None = None) -> dict:
    """按来源取当日一言。online 当天内缓存；offline/custom 按年内第几天轮换。"""
    if mode == "offline":
        return dict(OFFLINE_QUOTES[now.timetuple().tm_yday % len(OFFLINE_QUOTES)])
    if mode == "custom":
        items = [item for item in (custom or []) if (item.get("text") or "").strip()]
        if items:
            picked = items[now.timetuple().tm_yday % len(items)]
            return {"text": picked["text"].strip(), "from": (picked.get("from") or "").strip()}
        return dict(OFFLINE_QUOTES[now.timetuple().tm_yday % len(OFFLINE_QUOTES)])

    key = now.strftime("%Y-%m-%d")
    cached = _day_cache.get(key)
    if cached is not None:
        return cached

    quote: dict | None = None
    if _check_url(HITOKOTO_URL):
        try:
            resp = requests.get(HITOKOTO_URL, timeout=8, allow_redirects=False)
            resp.raise_for_status()
            data = resp.json()
            text = (data.get("hitokoto") or "").strip()
            if text:
                quote = {"text": text[:32], "from": (data.get("from") or "").strip()[:16]}
        except Exception as exc:
            log.warning("hitokoto 拉取失败: %s", exc)

    if quote is None:
        quote = OFFLINE_QUOTES[now.timetuple().tm_yday % len(OFFLINE_QUOTES)]

    _day_cache.clear()  # 只保留当天
    _day_cache[key] = quote
    return quote
