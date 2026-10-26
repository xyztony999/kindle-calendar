"""ICS 日历订阅与本地纪念日：未来 7 天事件 + 倒计时。

ICS 部分沿用 holidays.py 的模式：模块级 TTL 缓存 + 锁 + 失败保旧数据；
纪念日部分纯本地计算（lunar-python 农历年度换算），随 settings 即时生效。

SSRF 防护：仅 https；DNS 解析出的全部 IP 必须为公网地址（阻断私网/环回/
链路本地/云元数据）；TLS 直连已校验的 IP 并用真实域名做 SNI/证书校验，
禁重定向——比按域名二次请求更能防 DNS rebinding。
"""

from __future__ import annotations

import http.client
import ipaddress
import logging
import socket
import ssl
import threading
import time
from datetime import date, datetime, timedelta, timezone as dt_timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

CACHE_TTL_S = 6 * 3600
FETCH_TIMEOUT_S = 8
MAX_BYTES = 2 * 1024 * 1024
MAX_EVENTS = 100
WINDOW_DAYS = 7
COUNTDOWN_DAYS = 365
COUNTDOWN_TOP = 5
TITLE_MAX = 40

_lock = threading.Lock()
_events: list[dict] = []
_fetched_at: float = 0.0
_status: dict = {"ok": True, "at": None, "error": "", "enabled": False}


def health() -> dict:
    with _lock:
        return dict(_status)


def _fetch_ics(url: str) -> str:
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ValueError("ICS 链接须为 https")
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("ICS 链接无效")
    port = parsed.port or 443
    ips: list[str] = []
    for info in socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP):
        ip = info[4][0]
        if not ipaddress.ip_address(ip).is_global:
            raise ValueError("ICS 主机解析到非公网地址")
        ips.append(ip)
    # 直连已校验 IP，SNI/证书仍按真实域名校验；不跟随重定向
    ctx = ssl.create_default_context()
    raw = socket.create_connection((ips[0], port), timeout=FETCH_TIMEOUT_S)
    try:
        tls = ctx.wrap_socket(raw, server_hostname=hostname)
        conn = http.client.HTTPSConnection(hostname, port, timeout=FETCH_TIMEOUT_S)
        conn.sock = tls
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        conn.request("GET", path, headers={"Host": hostname, "User-Agent": "kindle-calendar/2", "Accept-Encoding": "identity"})
        resp = conn.getresponse()
        if resp.status != 200:
            raise ValueError(f"ICS 返回 {resp.status}")
        body = resp.read(MAX_BYTES + 1)
    finally:
        raw.close()
    if len(body) > MAX_BYTES:
        raise ValueError("ics 超过 2MB")
    return body.decode("utf-8", errors="replace")


def _parse_events(raw: str, start: datetime, end: datetime, tz: ZoneInfo) -> list[dict]:
    from icalendar import Calendar
    from recurring_ical_events import of

    calendar = Calendar.from_ical(raw)
    events: list[dict] = []
    for comp in of(calendar).between(start, end):
        dtstart = comp.get("DTSTART")
        dt = getattr(dtstart, "dt", None) if dtstart is not None else None
        if dt is None:
            continue
        title = str(comp.get("SUMMARY") or "").strip()[:TITLE_MAX]
        if not title:
            continue
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=dt_timezone.utc)
            local = dt.astimezone(tz)
            events.append({"iso_date": local.date().isoformat(), "time": local.strftime("%H:%M"), "all_day": False, "title": title, "source": "ics"})
        else:
            events.append({"iso_date": dt.isoformat(), "time": None, "all_day": True, "title": title, "source": "ics"})
    return events


def refresh(urls: list[str], tz: ZoneInfo, now: datetime) -> list[dict]:
    """TTL 内直接用缓存；过期则拉取（部分成功即更新，全失败保旧数据）。"""
    global _events, _fetched_at
    with _lock:
        fresh = _fetched_at > 0 and time.time() - _fetched_at <= CACHE_TTL_S
        cached = list(_events)
    if not urls:
        with _lock:
            _events = []
            _fetched_at = time.time()
            _status.update(ok=True, error="", enabled=False, at=now.isoformat(timespec="seconds"))
        return []
    if fresh:
        return cached

    fetched: list[dict] = []
    ok_any = False
    last_error = ""
    for url in urls:
        try:
            raw = _fetch_ics(url)
            fetched.extend(_parse_events(raw, now.astimezone(dt_timezone.utc) - timedelta(days=1), now.astimezone(dt_timezone.utc) + timedelta(days=WINDOW_DAYS + 1), tz))
            ok_any = True
        except Exception as exc:
            last_error = str(exc)
            log.warning("ICS 拉取/解析失败 url=%s…: %s", url[:48], exc)
    if ok_any:
        with _lock:
            _events = fetched
            _fetched_at = time.time()
            _status.update(ok=True, error=last_error, enabled=True, at=now.isoformat(timespec="seconds"))
        return fetched
    log.warning("ICS 全部源拉取失败，沿用 %d 条旧数据", len(cached))
    with _lock:
        _status.update(ok=False, error=last_error or "全部源拉取失败", enabled=True, at=now.isoformat(timespec="seconds"))
    return cached


def current_events() -> list[dict]:
    with _lock:
        return list(_events)


def _lunar_to_solar(lunar_year: int, month: int, day: int) -> date | None:
    try:
        from lunar_python import Lunar

        solar = Lunar.fromYmd(lunar_year, month, day).getSolar()
        return date(solar.getYear(), solar.getMonth(), solar.getDay())
    except Exception:
        return None


def _occurrences(name: str, date_text: str, repeat: str, today: date) -> list[date]:
    """返回该条目今天起（含今天）的后续命中日期，升序。"""
    out: list[date] = []
    if repeat == "none":
        try:
            d = date.fromisoformat(date_text)
        except ValueError:
            return out
        if d >= today:
            out.append(d)
        return out
    try:
        month, day = int(date_text[:2]), int(date_text[3:5])
    except (ValueError, IndexError):
        return out
    if repeat == "yearly":
        for year in (today.year, today.year + 1):
            try:
                d = date(year, month, day)
            except ValueError:
                continue
            if d >= today:
                out.append(d)
        return out
    # lunar：农历月日每年对应的公历日期不同，取邻近农历年换算后筛选
    for lunar_year in range(today.year - 1, today.year + 3):
        d = _lunar_to_solar(lunar_year, month, day)
        if d is not None and d >= today:
            out.append(d)
    return sorted(set(out))


def anniversary_data(anniversaries: list[dict], today: date) -> tuple[list[dict], list[dict]]:
    """返回 (7 天窗口事件, 365 天倒计时)。days=0 表示今天。"""
    anniv_events: list[dict] = []
    countdowns: list[dict] = []
    for item in anniversaries or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        for d in _occurrences(name, str(item.get("date") or ""), str(item.get("repeat") or "none"), today):
            days = (d - today).days
            if days <= WINDOW_DAYS:
                anniv_events.append({"iso_date": d.isoformat(), "time": None, "all_day": True, "title": name, "source": "anniv"})
            if days <= COUNTDOWN_DAYS:
                countdowns.append({"name": name, "days": days, "iso_date": d.isoformat()})
    countdowns.sort(key=lambda c: c["days"])
    seen: set[str] = set()
    top: list[dict] = []
    for c in countdowns:
        key = f"{c['name']}@{c['iso_date']}"
        if key in seen:
            continue
        seen.add(key)
        top.append(c)
        if len(top) >= COUNTDOWN_TOP:
            break
    return anniv_events, top


def merge(ics_events: list[dict], anniv_events: list[dict], today: date) -> list[dict]:
    """合并 ICS 与纪念日事件，限定今天起 7 天，排序并截断。"""
    start_iso = today.isoformat()
    end_iso = (today + timedelta(days=WINDOW_DAYS)).isoformat()
    events = [e for e in (ics_events + anniv_events) if isinstance(e, dict) and start_iso <= str(e.get("iso_date")) <= end_iso]
    events.sort(key=lambda e: (str(e.get("iso_date")), e.get("time") or "99:99"))
    return events[:MAX_EVENTS]
