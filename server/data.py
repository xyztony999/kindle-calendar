"""聚合各数据源，构建对外统一的 dashboard payload（纯 JSON 可序列化）。"""

from __future__ import annotations

from datetime import datetime

from server import almanac, astro, holidays, quotes
from server.aqi import AirQuality
from server.settings import PAGE_IDS, enabled_pages, settings_version
from server.weather import WeatherData


def build_payload(
    config: dict,
    weather: WeatherData,
    now: datetime,
    aqi: AirQuality | None = None,
    settings: dict | None = None,
    events: list[dict] | None = None,
    countdowns: list[dict] | None = None,
) -> dict:
    lat, lon = config["latitude"], config["longitude"]

    hourly = [
        {
            "time": p.time,
            "temperature": p.temperature,
            "precip": p.precipitation_probability,
            "code": p.code,
        }
        for p in weather.hourly
    ]

    # 未来 6 小时最大降水概率（展示用）
    cutoff = now.strftime("%Y-%m-%dT%H")
    window = [h for h in hourly if h["time"] >= cutoff][:6]
    precip_prob = max((h["precip"] for h in window), default=0)

    if settings:
        pages = enabled_pages(settings) or ["today"]
        version = settings_version(settings)
        quote = quotes.get_quote(now, settings["quote"]["mode"], settings["quote"].get("custom"))
        page_names = {
            item["page_id"]: item["name"]
            for item in settings.get("pages") or []
            if item.get("name")
        }
    else:
        pages = list(PAGE_IDS)
        version = ""
        quote = quotes.get_quote(now)
        page_names = {}

    almanac_data = almanac.almanac_for(now)
    if events:
        # 今天命中的纪念日并入节日备注行（页眉 notes / 月历角标优先级共用）
        today_iso = now.date().isoformat()
        anniv_today = [
            str(e.get("title") or "")
            for e in events
            if isinstance(e, dict) and e.get("source") == "anniv" and e.get("iso_date") == today_iso and e.get("title")
        ]
        if anniv_today:
            almanac_data = {**almanac_data, "festivals": list(almanac_data.get("festivals") or []) + anniv_today[:2]}

    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "location": config["location_name"],
        "pages": pages,
        "page_names": page_names,
        "settings_version": version,
        "clock": {
            "now": now.strftime("%H:%M"),
            "minutes": now.hour * 60 + now.minute,
            "iso": now.isoformat(timespec="seconds"),
        },
        "date": almanac_data,
        "holiday": holidays.day_info(now.date()),
        "weather": {
            "current": {
                "temperature": weather.current.temperature,
                "humidity": weather.current.humidity,
                "wind_speed": weather.current.wind_speed,
                "code": weather.current.code,
                "description": weather.current.description,
            },
            "daily": [
                {
                    "date": d.date,
                    "temp_max": d.temp_max,
                    "temp_min": d.temp_min,
                    "code": d.code,
                    "description": d.description,
                }
                for d in weather.daily
            ],
            "hourly": hourly,
            "precip_prob": precip_prob,
        },
        "sun": astro.day_summary(now, lat, lon),
        "aqi": None if aqi is None else {"us_aqi": aqi.us_aqi, "level_zh": aqi.level, "fetched_at": now.isoformat(timespec="seconds")},
        "events": events or [],
        "countdowns": countdowns or [],
        "quote": quote,
    }


def data_fingerprint(payload: dict) -> str:
    """内容指纹：剔除随分钟变化的时间字段，用于分区渲染缓存失效判断。"""
    import hashlib
    import json

    stable = {k: v for k, v in payload.items() if k not in ("generated_at", "clock")}
    return hashlib.sha256(
        json.dumps(stable, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:32]
