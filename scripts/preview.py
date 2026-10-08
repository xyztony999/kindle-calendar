#!/usr/bin/env python3
"""本地预览台历整页 PNG，无需 Kindle。"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml

from server.data import build_payload
from server.render import compose
from server.weather import fetch_weather


def main() -> None:
    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        config_path = ROOT / "config.example.yaml"

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    screen = config["screen"]
    tz = ZoneInfo(config["timezone"])
    print("获取天气数据…")
    weather = fetch_weather(config["latitude"], config["longitude"], config["timezone"])

    payload = build_payload(config, weather, datetime.now(tz))
    img = compose(payload, screen["width"], screen["height"], config.get("font_path", ""))

    out = ROOT / "preview.png"
    img.save(out)
    print(f"已保存: {out} ({screen['width']}x{screen['height']})")
    print(f"当前: {weather.current.temperature:.0f}° {weather.current.description}")
    print(f"农历: {payload['date']['lunar']} 节气: {payload['date']['solar_term']['name']} | {payload['sun']['sunrise']}~{payload['sun']['sunset']}")


if __name__ == "__main__":
    main()
