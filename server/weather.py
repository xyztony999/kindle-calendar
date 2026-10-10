"""从 Open-Meteo 获取天气数据（免费，无需 API Key）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
ALLOWED_HOSTS = {"api.open-meteo.com"}


def _check_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"blocked request target: {url}")


# WMO 天气代码 → 中文描述
WEATHER_CODES: dict[int, str] = {
    0: "晴",
    1: "大部晴朗",
    2: "局部多云",
    3: "多云",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "大毛毛雨",
    56: "冻毛毛雨",
    57: "冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "阵雨",
    82: "大阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴大冰雹",
}

# 与 Open-Meteo 对同一 WMO 代码公布的英文短语一致。
WEATHER_CODES_EN: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def describe_weather(code: int, lang: str = "zh") -> str:
    if lang == "en":
        return WEATHER_CODES_EN.get(code, "Unknown")
    return WEATHER_CODES.get(code, "未知")


@dataclass
class CurrentWeather:
    temperature: float
    humidity: int
    wind_speed: float
    code: int
    description: str


@dataclass
class DailyForecast:
    date: str
    temp_max: float
    temp_min: float
    code: int
    description: str


@dataclass
class HourlyPoint:
    time: str  # "2026-09-12T14:00"
    temperature: float
    precipitation_probability: int
    code: int


@dataclass
class WeatherData:
    current: CurrentWeather
    daily: list[DailyForecast]
    hourly: list[HourlyPoint]


def fetch_weather(latitude: float, longitude: float, timezone: str, timeout: float = 15) -> WeatherData:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "timezone": timezone,
        "forecast_days": 7,
        "forecast_hours": 24,
    }
    _check_url(OPEN_METEO_URL)
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=timeout, allow_redirects=False)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()

    current = data["current"]
    daily = data["daily"]
    hourly = data.get("hourly", {})

    current_weather = CurrentWeather(
        temperature=current["temperature_2m"],
        humidity=current["relative_humidity_2m"],
        wind_speed=current["wind_speed_10m"],
        code=current["weather_code"],
        description=describe_weather(current["weather_code"]),
    )

    forecasts: list[DailyForecast] = []
    for i in range(len(daily["time"])):
        code = daily["weather_code"][i]
        forecasts.append(
            DailyForecast(
                date=daily["time"][i],
                temp_max=daily["temperature_2m_max"][i],
                temp_min=daily["temperature_2m_min"][i],
                code=code,
                description=describe_weather(code),
            )
        )

    times = hourly.get("time", [])
    n = len(times)
    hourly_points = [
        HourlyPoint(
            time=times[i],
            temperature=hourly["temperature_2m"][i],
            precipitation_probability=hourly.get("precipitation_probability", [0] * n)[i] or 0,
            code=hourly.get("weather_code", [0] * n)[i] or 0,
        )
        for i in range(n)
    ]

    return WeatherData(current=current_weather, daily=forecasts, hourly=hourly_points)
