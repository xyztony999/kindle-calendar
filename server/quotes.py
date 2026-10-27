"""每日一言：本地语料库（默认）+ Hitokoto API + 内置离线古诗词兜底。"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import requests

log = logging.getLogger(__name__)

QUOTE_LIBRARY_PATH = Path(__file__).resolve().parent / "quotes_library.json"
# 刷新后的库与元数据落 data/（volume，升级镜像不丢）；镜像内置仅作首启兜底
LIBRARY_DATA_PATH = QUOTE_LIBRARY_PATH.parent.parent / "data" / "quotes_library.json"
LIBRARY_META_PATH = QUOTE_LIBRARY_PATH.parent.parent / "data" / "quotes_meta.json"
LIBRARY_TTL_S = int(os.environ.get("QUOTES_LIBRARY_TTL_S") or 7 * 86400)
LIBRARY_SOURCES = (
    "https://fastly.jsdelivr.net/gh/hitokoto-osc/sentences-bundle@master/sentences/{t}.json",
    "https://cdn.jsdelivr.net/gh/hitokoto-osc/sentences-bundle@master/sentences/{t}.json",
    "https://raw.githubusercontent.com/hitokoto-osc/sentences-bundle/master/sentences/{t}.json",
)
LIBRARY_TYPES = ("a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l")

# 固定常量地址，无动态拼接；请求前仍做协议/主机校验并禁止重定向
HITOKOTO_URL = "https://v1.hitokoto.cn/?c=i&c=d&max_length=28&encode=json"
ALLOWED_HOSTS = {"v1.hitokoto.cn"}
ZENQUOTES_URL = "https://zenquotes.io/api/today"
ZENQUOTES_HOSTS = {"zenquotes.io"}
# 服务器到 Cloudflare（hitokoto/zenquotes 均为 CF）跨洋链路晚高峰高丢包：
# 连接短、读取放宽，失败重试一次
ONLINE_TIMEOUT = (5, 12)
RETRY_ONCE_SLEEP_S = 1
LAST_GOOD_MAX_DAYS = 7

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
# 上次在线成功内容（粘性缓存）：失败时沿用 ≤7 天，替代直接跳离线库
_last_good: dict | None = None
_last_good_at: str = ""
_en_last_good: dict | None = None
_en_last_good_at: str = ""
# 语料库：热替换目标 + 刷新状态/元数据（内存态，持久化见 data/quotes_meta.json）
_library_sentences: list[dict] | None = None
_library_lock = threading.Lock()
_library_refreshing = threading.Event()
_library_meta: dict = {"updated": "", "count": 0, "fetched_at": None, "last_error": "", "refreshed_at": None}


def _days_old(now: datetime, day: str) -> int:
    try:
        then = datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        return 1 << 30
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    return max(0, (now - then).days)


def _sticky(now: datetime) -> dict | None:
    """粘性兜底：上次在线成功内容且未超龄。"""
    if _last_good and _days_old(now, _last_good_at) <= LAST_GOOD_MAX_DAYS:
        return dict(_last_good)
    return None


def _check_url(url: str, hosts: set[str] | None = None) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "https" and parts.hostname in (hosts or ALLOWED_HOSTS)


_library_sentences: list[dict] | None = None


def _load_library() -> list[dict]:
    """语料库：data/ 刷新版优先，缺失/损坏回落镜像内置；之后常驻内存。"""
    global _library_sentences
    with _library_lock:
        if _library_sentences is None:
            _library_sentences = _read_library_file(LIBRARY_DATA_PATH) or _read_library_file(QUOTE_LIBRARY_PATH)
            meta = _read_meta()
            _library_meta.update(
                updated=meta.get("updated", ""),
                count=len(_library_sentences),
                fetched_at=meta.get("fetched_at"),
                last_error=meta.get("last_error", ""),
                refreshed_at=meta.get("refreshed_at"),
            )
    return _library_sentences


def _read_library_file(path: Path) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        return [s for s in raw.get("sentences") or [] if isinstance(s, dict) and (s.get("hitokoto") or "").strip()]
    except (OSError, ValueError):
        return []


def _read_meta() -> dict:
    try:
        with open(LIBRARY_META_PATH, encoding="utf-8") as fh:
            raw = json.load(fh)
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_library(sentences: list[dict], updated: str) -> None:
    """原子写 data/ 库与元数据；任一失败抛异常由调用方保旧。"""
    LIBRARY_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "license": "AGPL-3.0",
        "source": "hitokoto.cn 开放句子库（hitokoto-osc/sentences-bundle）",
        "updated": updated,
        "types": {t: n for t, n in zip(LIBRARY_TYPES, ("动画", "漫画", "游戏", "文学", "原创", "网络", "其他", "影视", "诗词", "网易云", "哲学", "抖机灵"))},
        "sentences": sentences,
    }
    tmp = LIBRARY_DATA_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, LIBRARY_DATA_PATH)
    meta = {
        "updated": updated,
        "source": payload["source"],
        "count": len(sentences),
        "last_error": "",
        "fetched_at": datetime.utcnow().isoformat(timespec="seconds"),
        "refreshed_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
    tmp = LIBRARY_META_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, LIBRARY_META_PATH)


def _build_library(sentences: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in sentences:
        text = str(item.get("hitokoto") or "").strip()
        if not 4 <= len(text) <= 28:
            continue
        key = "".join(text.split())
        if key in seen:
            continue
        seen.add(key)
        out.append({"type": str(item.get("type") or "")[:1], "hitokoto": text, "from": str(item.get("from") or "").strip()[:24]})
    out.sort(key=lambda s: (s["type"], s["hitokoto"]))
    return out


def refresh_library(force: bool = False) -> dict:
    """重建语料库：逐分类加固拉取 → 过滤去重 → 原子写 data/ → 热替换。失败保旧。

    返回 {"ok", "count", "updated", "error"}；force=False 时 TTL 内直接跳过。
    忙守卫内置于本函数（Event set/clear），调用方无需再持锁。
    """
    from server.ics import _fetch_ics

    if _library_refreshing.is_set():
        return {"ok": False, "count": 0, "updated": "", "error": "已在刷新中"}
    _library_refreshing.set()
    try:
        meta = _read_meta()
        if not force and meta.get("refreshed_at"):
            try:
                age = time.time() - datetime.fromisoformat(meta["refreshed_at"]).timestamp()
            except ValueError:
                age = LIBRARY_TTL_S + 1
            if age <= LIBRARY_TTL_S:
                return {"ok": True, "count": int(meta.get("count") or 0), "updated": str(meta.get("updated") or ""), "error": "", "skipped": True}

        sentences: list[dict] = []
        last_error = ""
        for t in LIBRARY_TYPES:
            raw = None
            for template in LIBRARY_SOURCES:
                try:
                    raw = _fetch_ics(template.format(t=t))
                    break
                except Exception as exc:
                    last_error = f"{t}: {exc}"
                    log.warning("语料拉取失败 %s: %s", t, exc)
            if raw is None:
                return {"ok": False, "count": 0, "updated": "", "error": last_error or "全部源失败"}
            sentences.extend(json.loads(raw))
        built = _build_library(sentences)
        if len(built) < 100:
            return {"ok": False, "count": len(built), "updated": "", "error": "语料过少，疑似源异常"}
        updated = datetime.utcnow().strftime("%Y-%m-%d")
        _write_library(built, updated)
        with _library_lock:
            global _library_meta
            _library_sentences = built
            _library_meta = {"updated": updated, "count": len(built), "fetched_at": _library_meta.get("fetched_at"),
                             "last_error": "", "refreshed_at": datetime.utcnow().isoformat(timespec="seconds")}
        return {"ok": True, "count": len(built), "updated": updated, "error": ""}
    finally:
        _library_refreshing.clear()


def refresh_if_stale() -> None:
    """自动通道：TTL 过期才真正拉取；任何异常保旧不外抛。"""
    try:
        result = refresh_library(force=False)
        if result.get("error"):
            _status.update(error=f"语料库刷新失败: {result['error']}")
        elif result.get("ok") and not result.get("skipped"):
            log.info("语料库自动更新: %d 条 (%s)", result["count"], result["updated"])
    except Exception as exc:
        log.warning("语料库自动刷新失败: %s", exc)
        _status.update(error=f"语料库刷新失败: {exc}")


def library_quote(now: datetime, types: list[str] | None) -> dict:
    """本地语料库按日确定性选句：所选分类池内以年内第几天轮换。"""
    pool = _load_library()
    wanted = {t for t in (types or []) if isinstance(t, str)}
    if wanted:
        selected = [s for s in pool if s.get("type") in wanted]
        if selected:
            pool = selected
    if not pool:
        return dict(OFFLINE_QUOTES[now.timetuple().tm_yday % len(OFFLINE_QUOTES)])
    pick = pool[now.timetuple().tm_yday % len(pool)]
    return {"text": str(pick["hitokoto"]).strip(), "from": str(pick.get("from") or "").strip()[:16]}


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


# 数据源健康状态（内存态，供管理端展示）
_status: dict = {"ok": True, "at": None, "error": "", "enabled": True}


def health() -> dict:
    state = dict(_status)
    meta = _library_meta
    state["library_updated"] = meta.get("updated") or None
    state["library_count"] = int(meta.get("count") or 0)
    state["refreshing"] = _library_refreshing.is_set()
    return state


def _en_sticky(now: datetime) -> dict | None:
    if _en_last_good and _days_old(now, _en_last_good_at) <= LAST_GOOD_MAX_DAYS:
        return dict(_en_last_good)
    return None


def _fetch_zenquotes() -> dict | None:
    if not _check_url(ZENQUOTES_URL, ZENQUOTES_HOSTS):
        return None
    for attempt in (1, 2):
        try:
            resp = requests.get(ZENQUOTES_URL, timeout=ONLINE_TIMEOUT, allow_redirects=False)
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
            log.warning("zenquotes 拉取失败(第 %d 次): %s", attempt, exc)
            if attempt == 1:
                time.sleep(RETRY_ONCE_SLEEP_S)
    return None


def english_quote(
    now: datetime,
    mode: str = "online",
    custom: list | None = None,
    width: int = 758,
) -> dict:
    """英文页脚。library/offline 模式直接用本地短句（与中文"不联网"语义一致）。"""
    if mode in ("library", "offline"):
        return local_en_quote(now)
    if mode == "custom":
        items = [item for item in (custom or []) if (item.get("text") or "").strip()]
        if items:
            picked = items[now.timetuple().tm_yday % len(items)]
            return {"text": picked["text"].strip(), "from": (picked.get("from") or "").strip()}
        return local_en_quote(now)

    key = now.strftime("%Y-%m-%d")
    cached = _en_cache.get(key)
    if cached is not None:
        return dict(cached)

    quote = _fetch_zenquotes()
    if quote is not None and not footer_fits(quote["text"], quote["from"], width):
        quote = None
    if quote is None:
        quote = _en_sticky(now) or local_en_quote(now)
    else:
        global _en_last_good, _en_last_good_at
        _en_last_good, _en_last_good_at = dict(quote), now.strftime("%Y-%m-%d")

    stale = [item for item in _en_cache if not item.startswith(key)]
    for item in stale:
        _en_cache.pop(item, None)
    _en_cache[key] = quote
    return dict(quote)


def get_quote(now: datetime, mode: str = "online", custom: list | None = None, types: list[str] | None = None) -> dict:
    """按来源取当日一言。library/offline 为本地语料库；online 当天内缓存；custom 按年内第几天轮换。"""
    global _last_good, _last_good_at
    _status["enabled"] = mode == "online"
    if mode in ("library", "offline"):
        return library_quote(now, types)
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
    ok = False
    error = ""
    if _check_url(HITOKOTO_URL):
        for attempt in (1, 2):
            try:
                resp = requests.get(HITOKOTO_URL, timeout=ONLINE_TIMEOUT, allow_redirects=False)
                resp.raise_for_status()
                data = resp.json()
                text = (data.get("hitokoto") or "").strip()
                if text:
                    quote = {"text": text[:32], "from": (data.get("from") or "").strip()[:16]}
                    ok = True
                    break
                error = "hitokoto 空响应"
            except Exception as exc:
                error = str(exc)
                log.warning("hitokoto 拉取失败(第 %d 次): %s", attempt, exc)
            if attempt == 1:
                time.sleep(RETRY_ONCE_SLEEP_S)
    else:
        error = "目标地址被安全策略拦截"
    if ok:
        _last_good, _last_good_at = dict(quote), now.strftime("%Y-%m-%d")
    _status.update(ok=ok, error=error, at=now.isoformat(timespec="seconds"))

    if quote is None:
        quote = _sticky(now) or OFFLINE_QUOTES[now.timetuple().tm_yday % len(OFFLINE_QUOTES)]

    _day_cache.clear()  # 只保留当天
    _day_cache[key] = quote
    return quote
