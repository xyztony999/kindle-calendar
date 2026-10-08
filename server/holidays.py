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

# 数据源（固定 URL 模板，仅 https，主机白名单校验）：
# Gitee 镜像优先（国内可达，年度数据更新无需重新部署镜像），官方 GitHub 次之，
# 都失败时回退内置 server/holidays_data/<年>.json
HOLIDAY_CN_SOURCES = (
    "https://raw.giteeusercontent.com/xyztony999/holiday-cn/raw/master/{year}.json",
    "https://raw.githubusercontent.com/NateScarlet/holiday-cn/master/{year}.json",
)
ALLOWED_HOSTS = {"raw.giteeusercontent.com", "raw.githubusercontent.com"}
YEAR_MIN, YEAR_MAX = 2020, 2100
CACHE_TTL = 12 * 3600

_lock = threading.Lock()
_cache: dict[int, dict[str, dict]] = {}  # year -> {"2026-10-01": {"name": "国庆节", "off": True}}
_fetched_at: dict[int, float] = {}

BUNDLED_DIR = Path(__file__).resolve().parent / "holidays_data"


def _parse_days(raw: dict) -> dict[str, dict]:
    return {d["date"]: {"name": d.get("name", ""), "off": bool(d.get("isOffDay"))} for d in raw.get("days", [])}


def _build_urls(year: int) -> list[str]:
    if not (YEAR_MIN <= year <= YEAR_MAX):
        return []
    urls: list[str] = []
    for tpl in HOLIDAY_CN_SOURCES:
        url = tpl.format(year=year)
        parts = urlsplit(url)
        if parts.scheme == "https" and parts.hostname in ALLOWED_HOSTS:
            urls.append(url)
    return urls


def _load_year(year: int) -> dict[str, dict]:
    now = time.time()
    with _lock:
        if year in _cache and now - _fetched_at.get(year, 0) < CACHE_TTL:
            return _cache[year]
    url_list = _build_urls(year)
    data: dict[str, dict] = {}
    for url in url_list:
        try:
            # 禁止重定向，避免跳转到未知主机
            resp = requests.get(url, timeout=10, allow_redirects=False)
            resp.raise_for_status()
            data = _parse_days(resp.json())
            if data:
                break
        except Exception as exc:
            log.warning("holiday-cn %s 拉取失败(%s): %s", year, urlsplit(url).hostname, exc)
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
