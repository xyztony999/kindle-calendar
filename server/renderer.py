"""将天气与日历渲染为 Kindle 可用的 8 位灰度 PNG。"""

from __future__ import annotations

import calendar
import platform
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont
from zhdate import ZhDate

from server.icons import draw_weather_icon
from server.weather import WeatherData

WEEKDAYS_ZH = ["一", "二", "三", "四", "五", "六", "日"]


def _find_font(size: int, font_path: str = "") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path and Path(font_path).exists():
        return ImageFont.truetype(font_path, size)

    candidates: list[str] = []
    system = platform.system()
    if system == "Windows":
        candidates = [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
            r"C:\Windows\Fonts\simsun.ttc",
        ]
    elif system == "Darwin":
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        ]

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_text_in_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: int,
) -> None:
    x0, y0, x1, y1 = box
    tw, th = _text_size(draw, text, font)
    x = x0 + (x1 - x0 - tw) // 2
    y = y0 + (y1 - y0 - th) // 2 - 2
    draw.text((x, y), text, fill=fill, font=font)


def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: int,
    outline: int | None = None,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _lunar_str(dt: datetime) -> str:
    naive = dt.replace(tzinfo=None)
    lunar = ZhDate.from_datetime(naive)
    return lunar.chinese()[2:]


def render_dashboard(
    weather: WeatherData,
    *,
    width: int,
    height: int,
    location_name: str,
    timezone: str,
    font_path: str = "",
) -> Image.Image:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)

    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)

    margin = max(24, width // 40)
    font_large = _find_font(max(72, height // 14), font_path)
    font_medium = _find_font(max(28, height // 40), font_path)
    font_small = _find_font(max(22, height // 52), font_path)
    font_tiny = _find_font(max(18, height // 64), font_path)

    # ── 顶栏：公历 + 农历 ──
    header_h = height // 6
    _draw_rounded_rect(draw, (margin, margin, width - margin, header_h), 12, fill=240, outline=0, width=2)

    date_str = now.strftime("%Y年%m月%d日")
    lunar_str = f"农历{_lunar_str(now)}"
    weekday = WEEKDAYS_ZH[now.weekday()]

    draw.text((margin + 24, margin + 22), f"{date_str}  {lunar_str}", fill=0, font=font_medium)
    draw.text((margin + 24, margin + 62), f"星期{weekday}  {location_name}", fill=80, font=font_small)

    # ── 当前天气 ──
    weather_top = header_h + margin
    weather_h = height // 3
    _draw_rounded_rect(
        draw,
        (margin, weather_top, width - margin, weather_top + weather_h),
        12,
        fill=250,
        outline=0,
        width=2,
    )

    cur = weather.current
    icon_size = min(weather_h - 48, width // 4)
    icon_cx = width - margin - 24 - icon_size // 2
    icon_cy = weather_top + weather_h // 2
    draw_weather_icon(draw, cur.code, icon_cx, icon_cy, icon_size)

    temp_text = f"{cur.temperature:.0f}°"
    draw.text((margin + 32, weather_top + 28), temp_text, fill=0, font=font_large)
    draw.text((margin + 32, weather_top + weather_h - 72), cur.description, fill=0, font=font_medium)

    info_x = margin + 32
    info_y = weather_top + weather_h // 2 - 10
    draw.text((info_x, info_y), f"湿度 {cur.humidity}%", fill=60, font=font_small)
    draw.text((info_x, info_y + 36), f"风速 {cur.wind_speed:.0f} km/h", fill=60, font=font_small)

    # ── 5 日预报 ──
    forecast_top = weather_top + weather_h + margin
    forecast_h = height // 5
    _draw_rounded_rect(
        draw,
        (margin, forecast_top, width - margin, forecast_top + forecast_h),
        12,
        fill=255,
        outline=0,
        width=2,
    )

    draw.text((margin + 24, forecast_top + 12), "未来预报", fill=0, font=font_small)

    col_w = (width - 2 * margin - 48) // max(len(weather.daily), 1)
    mini_icon = min(col_w - 8, forecast_h // 3)
    for i, day in enumerate(weather.daily):
        col_x0 = margin + 24 + i * col_w
        col_cx = col_x0 + col_w // 2
        draw.text((col_x0 + 4, forecast_top + 40), day.date[5:], fill=80, font=font_tiny)
        draw_weather_icon(draw, day.code, col_cx, forecast_top + 40 + mini_icon // 2 + 8, mini_icon)
        desc = day.description if len(day.description) <= 4 else day.description[:4]
        desc_w, _ = _text_size(draw, desc, font_tiny)
        draw.text((col_cx - desc_w // 2, forecast_top + 40 + mini_icon + 12), desc, fill=0, font=font_tiny)
        temp_range = f"{day.temp_min:.0f}~{day.temp_max:.0f}°"
        temp_w, _ = _text_size(draw, temp_range, font_tiny)
        draw.text((col_cx - temp_w // 2, forecast_top + forecast_h - 28), temp_range, fill=60, font=font_tiny)

    # ── 月历 ──
    cal_top = forecast_top + forecast_h + margin
    cal_bottom = height - margin
    _draw_rounded_rect(
        draw,
        (margin, cal_top, width - margin, cal_bottom),
        12,
        fill=255,
        outline=0,
        width=2,
    )

    year, month = now.year, now.month
    draw.text((margin + 24, cal_top + 16), f"{year}年 {month}月", fill=0, font=font_medium)

    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(year, month)

    grid_x0 = margin + 24
    grid_x1 = width - margin - 24
    grid_top = cal_top + 56
    grid_bottom = cal_bottom - 16
    cell_w = (grid_x1 - grid_x0) // 7
    cell_h = (grid_bottom - grid_top) // (len(weeks) + 1)

    for j, wd in enumerate(WEEKDAYS_ZH):
        cell = (grid_x0 + j * cell_w, grid_top, grid_x0 + (j + 1) * cell_w, grid_top + cell_h)
        _draw_text_in_box(draw, cell, wd, font_tiny, 100)

    today = now.day
    day_font = font_small if cell_h >= 36 else font_tiny
    for row, week in enumerate(weeks):
        for col, day in enumerate(week):
            if day == 0:
                continue
            cell = (
                grid_x0 + col * cell_w,
                grid_top + (row + 1) * cell_h,
                grid_x0 + (col + 1) * cell_w,
                grid_top + (row + 2) * cell_h,
            )
            day_text = str(day)
            if day == today:
                cx = (cell[0] + cell[2]) // 2
                cy = (cell[1] + cell[3]) // 2
                tw, th = _text_size(draw, day_text, day_font)
                pad = 6
                radius = max(tw, th) // 2 + pad
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=0)
                _draw_text_in_box(draw, cell, day_text, day_font, 255)
            else:
                _draw_text_in_box(draw, cell, day_text, day_font, 0)

    return img
