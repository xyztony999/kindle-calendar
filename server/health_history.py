"""数据源健康历史：按节拍快照到 data/health_history.json（单 JSON 数组，保留 7 天）。

结构与 HeartbeatLog/quotes_meta 同构：坏文件即弃、tmp+os.replace 原子写。
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

RETAIN_DAYS = 7
MAX_POINTS = 7 * 24 * 4  # 15 分钟一拍的理论上限，双保险

_lock = threading.Lock()
_path: Path | None = None
_points: list[dict] = []


def _file(settings_path: Path) -> Path:
    return settings_path.with_name("health_history.json")


def init(settings_path: Path) -> None:
    """启动时载入历史（坏文件即弃）。"""
    global _path, _points
    with _lock:
        _path = _file(settings_path)
        _points = []
        try:
            raw = json.loads(_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("points"), list):
                _points = [p for p in raw["points"] if isinstance(p, dict) and isinstance(p.get("at"), str)]
        except (OSError, ValueError):
            _points = []


def record(sources: dict) -> None:
    """拍一个全量快照：sources 为 sources_health() 的 {"sources": [...]}。"""
    global _points
    if _path is None:
        return
    now = datetime.now(timezone.utc)
    at = now.isoformat(timespec="seconds")
    snapshot = {}
    for item in sources.get("sources") or []:
        if not isinstance(item, dict) or "id" not in item:
            continue
        snapshot[str(item["id"])] = {"ok": bool(item.get("ok")), "error": str(item.get("error") or "")}
    with _lock:
        _points = [p for p in _points if p["at"] >= (now - timedelta(days=RETAIN_DAYS)).isoformat(timespec="seconds")]
        _points.append({"at": at, "sources": snapshot})
        _points = _points[-MAX_POINTS:]
        tmp = _path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps({"points": _points}, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, _path)
        except OSError as exc:
            # 历史记录失败不影响任何主流程
            import logging

            logging.getLogger(__name__).warning("健康历史写入失败: %s", exc)


def series() -> dict:
    """按源分组的时间序列（管理端点阵图数据）。"""
    with _lock:
        points = list(_points)
    series: dict[str, list] = {key: [] for key in ("weather", "aqi", "quote", "ics")}
    for point in points:
        for source_id, state in (point.get("sources") or {}).items():
            if source_id in series:
                series[source_id].append({"at": point["at"], **state})
    return {"sources": series}
