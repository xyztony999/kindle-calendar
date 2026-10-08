"""中国法定节假日 / 调休数据（NateScarlet/holiday-cn 年度 JSON，内存缓存）。

国内服务器访问 raw.githubusercontent.com 常被重置，拉取失败时回退到
内置数据 server/holidays_data/<年>.json（每年国务院办公厅发布后更新一次）。
两者都失败时返回空结果（页面不标注节假日），不影响其它数据。
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import date
from pathlib import Path
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

BUNDLED_DIR = Path(__file__).resolve().parent / "holidays_data"


def _parse_days(raw: dict) -> dict[str, dict]:
    return {d["date"]: {"name": d.get("name", ""), "off": bool(d.get("isOffDay"))} for d in raw.get("days", [])}


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
    data: dict[str, dict] = {}
    if url is not None:
        try:
            # 禁止重定向，避免跳转到未知主机
            resp = requests.get(url, timeout=10, allow_redirects=False)
            resp.raise_for_status()
            data = _parse_days(resp.json())
        except Exception as exc:
            log.warning("holiday-cn %s 拉取失败: %s", year, exc)
    if not data:
        bundled = BUNDLED_DIR / f"{year}.json"
        if bundled.is_file():
            try:
                data = _parse_days(json.loads(bundled.read_text(encoding="utf-8")))
                log.info("holiday-cn %s 使用内置数据（%d 天）", year, len(data))
            except Exception as exc:
                log.warning("holiday-cn %s 内置数据解析失败: %s", year, exc)
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
