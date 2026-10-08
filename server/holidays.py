"""中国法定节假日 / 调休数据（NateScarlet/holiday-cn 年度 JSON，内存缓存）。

拉取失败时返回空结果（页面不标注节假日），不影响其它数据。
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import date
from urllib.parse import urlsplit

import requests

log = logging.getLogger(__name__)

# 仅允许访问的固定主机（holiday-cn 官方发布地址）；年份由服务端日期计算并做整数校验
HOLIDAY_CN_HOST = "raw.githubusercontent.com"
HOLIDAY_CN_PATH_PREFIX = "/NateScarlet/holiday-cn/master/"
ALLOWED_HOSTS = {HOLIDAY_CN_HOST}
YEAR_MIN, YEAR_MAX = 2020, 2100
CACHE_TTL = 12 * 3600

_lock = threading.Lock()
_cache: dict[int, dict[str, dict]] = {}  # year -> {"2026-10-01": {"name": "国庆节", "off": True}}
_fetched_at: dict[int, float] = {}


def _build_url(year: int) -> str | None:
    if not (YEAR_MIN <= year <= YEAR_MAX):
        return None
    url = f"https://{HOLIDAY_CN_HOST}{HOLIDAY_CN_PATH_PREFIX}{year}.json"
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS or not parts.path.startswith(HOLIDAY_CN_PATH_PREFIX):
        return None
    return url


def _load_year(year: int) -> dict[str, dict]:
    now = time.time()
    with _lock:
        if year in _cache and now - _fetched_at.get(year, 0) < CACHE_TTL:
            return _cache[year]
    url = _build_url(year)
    if url is None:
        return {}
    try:
        # 禁止重定向，避免跳转到未知主机
        resp = requests.get(url, timeout=10, allow_redirects=False)
        resp.raise_for_status()
        days = resp.json().get("days", [])
        data = {d["date"]: {"name": d.get("name", ""), "off": bool(d.get("isOffDay"))} for d in days}
    except Exception as exc:
        log.warning("holiday-cn %s 拉取失败: %s", year, exc)
        with _lock:
            return _cache.get(year, {})
    with _lock:
        _cache[year] = data
        _fetched_at[year] = now
    return data


def day_info(d: date) -> dict | None:
    """返回 {"type": "holiday"|"swap", "note": "休"|"班", "name": ...}，非节假日返回 None。"""
    info = _load_year(d.year).get(d.isoformat())
    if info is None:
        return None
    if info["off"]:
        return {"type": "holiday", "note": "休", "name": info["name"]}
    return {"type": "swap", "note": "班", "name": info["name"]}
