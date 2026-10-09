#!/usr/bin/env python3
"""本地预览台历整页 PNG，无需 Kindle。用法：python scripts/preview.py [page]

page ∈ today/week/month/detail/almanac，缺省 today（也可用 all 输出五页）。
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml

from server.data import build_payload
from server.render import PAGES, compose_page
from server.weather import fetch_weather


def main() -> None:
    page = sys.argv[1] if len(sys.argv) > 1 else "today"
    pages = list(PAGES) if page == "all" else [page if page in PAGES else "today"]

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
    for p in pages:
        img = compose_page(p, payload, screen["width"], screen["height"], config.get("font_path", ""))
        out = ROOT / f"preview_{p}.png" if len(pages) > 1 else ROOT / "preview.png"
        img.save(out)
        print(f"已保存: {out} ({p}, {screen['width']}x{screen['height']})")

    print(f"当前: {weather.current.temperature:.0f}° {weather.current.description}")
    print(f"农历: {payload['date']['lunar']} 节气: {payload['date']['solar_term']['name']} | {payload['sun']['sunrise']}~{payload['sun']['sunset']}")


if __name__ == "__main__":
    main()
