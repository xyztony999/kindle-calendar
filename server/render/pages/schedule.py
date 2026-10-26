"""日程与倒计时系统积木。"""

from __future__ import annotations

from datetime import date, timedelta

from PIL import Image, ImageDraw

from server.locale import is_en
from server.render import style as style
from server.render.regions import Rect


def _font(sx: float, base: int, font_path: str):
    return style.get_font(max(15, round(base * sx)), font_path)


def _truncate(draw, text: str, font, width: int) -> str:
    if style.tracked_width(draw, text, font) <= width or not text:
        return text
    out = text
    while out and style.tracked_width(draw, out + "…", font) > width:
        out = out[:-1]
    return (out + "…") if out else ""


def _day_events(payload: dict, iso: str) -> list[dict]:
    items = [e for e in (payload.get("events") or []) if isinstance(e, dict) and e.get("iso_date") == iso and e.get("title")]
    items.sort(key=lambda e: (0 if e.get("all_day") else 1, str(e.get("time") or "00:00")))
    return items


def render_schedule(payload: dict, rect: Rect, font_path: str, options: dict | None = None) -> Image.Image:
    opts = options or {}
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646
    english = is_en(payload)

    iso = str((payload.get("date") or {}).get("iso") or date.today().isoformat())
    today = date.fromisoformat(iso)
    tomorrow = (today + timedelta(days=1)).isoformat()
    show_tomorrow = bool(opts.get("show_tomorrow", False))

    today_items = _day_events(payload, iso)
    cap = 4 if show_tomorrow else 6
    lines: list[tuple[str, str, int]] = []  # (左侧时间/标记, 标题, 填充)
    for e in today_items[:cap]:
        left = (english and "All day" or "全天") if e.get("all_day") else str(e.get("time") or "")
        lines.append((left, str(e.get("title") or ""), style.INK))
    if not today_items:
        lines.append(("", english and "No events today" or "今日无日程", style.MID))
    if show_tomorrow:
        lines.append(("", english and "Tomorrow" or "明天", style.MID))
        for e in _day_events(payload, tomorrow)[:3]:
            left = (english and "All day" or "全天") if e.get("all_day") else str(e.get("time") or "")
            lines.append((left, str(e.get("title") or ""), style.INK))

    f_time = _font(sx, 24, font_path)
    f_title = _font(sx, 27, font_path)
    left_w = int(92 * sx)
    row_h = rect.h // max(len(lines), 1)
    for i, (left, title, fill) in enumerate(lines):
        y_mid = i * row_h + row_h // 2
        if left:
            style.draw_text(draw, (6, y_mid - int(13 * sx)), left, f_time, style.MID if fill == style.INK else fill)
        tx = left_w + 6 if left else 10
        style.draw_text(draw, (tx, y_mid - int(15 * sx)), _truncate(draw, title, f_title, rect.w - tx - 10), f_title, fill)
        if i < len(lines) - 1:
            style.hairline(draw, 10, (i + 1) * row_h, rect.w - 10, style.RULE)
    return img


def render_countdown(payload: dict, rect: Rect, font_path: str, options: dict | None = None) -> Image.Image:
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646
    english = is_en(payload)
    items = [c for c in (payload.get("countdowns") or []) if isinstance(c, dict) and c.get("name")][:3]
    if not items:
        f_hint = _font(sx, 24, font_path)
        style.draw_text_center(draw, rect.w // 2, rect.h // 2 - 14, english and "No countdowns" or "暂无纪念日", f_hint, style.MID)
        return img

    f_days = _font(sx, 30, font_path)
    f_name = _font(sx, 26, font_path)
    row_h = rect.h // len(items)
    for i, item in enumerate(items):
        days = int(item.get("days") or 0)
        y_mid = i * row_h + row_h // 2
        name = str(item.get("name") or "")
        if days == 0:
            left = english and "Today" or "今天"
            style.draw_text(draw, (6, y_mid - int(16 * sx)), left, f_days, style.INK)
            style.draw_text(draw, (int(150 * sx), y_mid - int(14 * sx)), name, f_name, style.INK)
        else:
            left = f"{days}" + (english and " d" or " 天")
            style.draw_text(draw, (6, y_mid - int(16 * sx)), left, f_days, style.MID)
            style.draw_text(draw, (int(150 * sx), y_mid - int(14 * sx)), _truncate(draw, name, f_name, rect.w - int(160 * sx)), f_name, style.INK)
        if i < len(items) - 1:
            style.hairline(draw, 10, (i + 1) * row_h, rect.w - 10, style.RULE)
    return img
