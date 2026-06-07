#!/usr/bin/env python3
"""本地预览台历 PNG，无需 Kindle。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml

from server.renderer import render_dashboard
from server.weather import fetch_weather


def main() -> None:
    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        config_path = ROOT / "config.example.yaml"

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    print("获取天气数据…")
    weather = fetch_weather(
        config["latitude"],
        config["longitude"],
        config["timezone"],
    )

    screen = config["screen"]
    img = render_dashboard(
        weather,
        width=screen["width"],
        height=screen["height"],
        location_name=config["location_name"],
        timezone=config["timezone"],
        font_path=config.get("font_path", ""),
    )

    out = ROOT / "preview.png"
    img.save(out)
    print(f"已保存: {out} ({screen['width']}x{screen['height']})")
    print(f"当前: {weather.current.temperature:.0f}° {weather.current.description}")


if __name__ == "__main__":
    main()
