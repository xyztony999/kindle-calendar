"""模板中心目录读取。未配置地址时返回空列表，不访问网络。"""

from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

import requests

from server.layout import accept_center_item

log = logging.getLogger(__name__)


def center_url() -> str:
    return os.environ.get("WIDGET_CENTER_URL", "").strip()


def fetch_center_items() -> list[dict]:
    url = center_url()
    if not url.startswith("https://"):
        return []
    parsed = urlparse(url)
    if not parsed.hostname:
        return []
    try:
        response = requests.get(url, timeout=3, allow_redirects=False)
    except Exception as exc:
        log.warning("模板中心不可达，按空目录处理: %s", exc)
        return []
    if response.is_redirect or response.status_code != 200:
        log.warning("模板中心返回 %s，按空目录处理", response.status_code)
        return []
    try:
        payload = response.json()
    except Exception:
        log.warning("模板中心不是 JSON，按空目录处理")
        return []
    raw_items = payload if isinstance(payload, list) else payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(raw_items, list):
        return []
    accepted: list[dict] = []
    for raw in raw_items[:50]:
        item = accept_center_item(raw)
        if item is not None:
            accepted.append(item)
    return accepted


def approved_data_items() -> list[dict]:
    return [item for item in fetch_center_items() if item.get("kind") == "data" and item.get("placeable")]
