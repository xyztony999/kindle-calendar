"""按用户矩形绘制系统积木、图片、文字和自定义数据积木。"""

from __future__ import annotations

from PIL import Image, ImageDraw

from server.fields import field_text
from server.layout import DESIGN, block_region_key, content_blank, field_label, find_block, http_region_names, iter_blocks, scale_box
from server.locale import is_en
from server.render import style as style
from server.render.pages import almanac as almanac_page
from server.render.pages import common, detail as detail_page, month as month_page, today, week as week_page
from server.render.regions import Rect


def _system_image(widget: str, payload: dict, rect: Rect, font_path: str, page: str, offset: int) -> Image.Image:
    if widget == "header":
        return common.render_header(payload, rect, font_path, page=page)
    if widget == "weather":
        return today.render_weather(payload, rect, font_path)
    if widget == "sun":
        return today.render_sun(payload, rect, font_path)
    if widget == "scene":
        return today.render_scene_region(payload, rect, font_path)
    if widget == "quote":
        return common.render_quote(payload, rect, font_path)
    if widget == "list":
        return week_page.render_list(payload, rect, font_path)
    if widget == "chart":
        return week_page.render_chart(payload, rect, font_path)
    if widget == "title":
        return month_page.render_title(payload, rect, font_path, offset=offset)
    if widget == "grid":
        return month_page.render_grid(payload, rect, font_path, offset=offset)
    if widget == "hourly":
        return detail_page.render_hourly(payload, rect, font_path)
    if widget == "indices":
        return detail_page.render_indices(payload, rect, font_path)
    if widget == "main":
        return almanac_page.render_main(payload, rect, font_path)
    return Image.new("L", (rect.w, rect.h), style.PAPER)


def paint_system(widget: str, payload: dict, target: Rect, font_path: str, page: str, offset: int = 0) -> Image.Image:
    width, height = DESIGN[widget]
    image = _system_image(widget, payload, Rect(0, 0, width, height), font_path, page, offset)
    if image.size != (target.w, target.h):
        image = image.resize((target.w, target.h), Image.Resampling.NEAREST)
    return image


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for char in text:
        trial = line + char
        if style.tracked_width(draw, trial, font) <= max_w or not line:
            line = trial
        else:
            lines.append(line)
            line = char
    if line:
        lines.append(line)
    return lines or [""]


def _fit_font(draw, text: str, font_path: str, width: int, height: int, start: int):
    size = max(15, start)
    font = style.get_font(size, font_path)
    lines = _wrap(draw, text, font, max(1, width))
    while size > 15 and len(lines) * (size + 4) > height:
        size -= 2
        font = style.get_font(size, font_path)
        lines = _wrap(draw, text, font, max(1, width))
    return font, lines, size


def paint_text(text: str, align: str, rect: Rect, font_path: str) -> Image.Image:
    image = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(image)
    font, lines, size = _fit_font(draw, text, font_path, rect.w - 8, rect.h - 8, max(18, rect.h // 3))
    line_h = size + 4
    y = max(0, (rect.h - line_h * len(lines)) // 2)
    for line in lines:
        if align == "center":
            style.draw_text_center(draw, rect.w // 2, y, line, font, style.INK)
        elif align == "right":
            style.draw_text_right(draw, rect.w - 4, y, line, font, style.INK)
        else:
            style.draw_text(draw, (4, y), line, font, style.INK)
        y += line_h
    return image


def paint_image(source: Image.Image | None, rect: Rect) -> Image.Image:
    canvas = Image.new("L", (rect.w, rect.h), style.PAPER)
    if source is None:
        return canvas
    image = source.convert("L")
    scale = min(rect.w / max(1, image.width), rect.h / max(1, image.height))
    tw, th = max(1, round(image.width * scale)), max(1, round(image.height * scale))
    fitted = style.ordered_dither(image.resize((tw, th), Image.Resampling.BOX))
    canvas.paste(fitted, ((rect.w - tw) // 2, (rect.h - th) // 2))
    return canvas


def paint_custom(definition: dict | None, payload: dict, rect: Rect, font_path: str) -> Image.Image:
    image = Image.new("L", (rect.w, rect.h), style.PAPER)
    if not definition:
        return image
    draw = ImageDraw.Draw(image)
    lang = "en" if is_en(payload) else "zh"
    fields = list(definition.get("fields") or [])
    values = [field_text(payload, field) for field in fields]
    labels = [field_label(field, lang) for field in fields]
    if definition.get("style") == "hero":
        hero = values[0] if values else "—"
        font, lines, size = _fit_font(draw, hero, font_path, rect.w - 8, max(20, int(rect.h * 0.62)), max(20, int(rect.h * 0.42)))
        y = 4
        for line in lines:
            style.draw_text(draw, (4, y), line, font, style.INK)
            y += size + 2
        small = style.get_font(max(15, size // 2), font_path)
        for label, value in zip(labels[1:], values[1:]):
            style.draw_text(draw, (4, y), f"{label}  {value}", small, style.MID)
            y += max(18, size // 2 + 4)
        return image
    count = max(1, len(fields))
    size = max(15, min(36, rect.h // (count + 1)))
    font = style.get_font(size, font_path)
    y = 4
    for label, value in zip(labels, values):
        style.draw_text(draw, (4, y), label, font, style.MID)
        style.draw_text_right(draw, rect.w - 4, y, value, font, style.INK)
        y += size + 6
    return image


def _target(block: dict, width: int, height: int) -> Rect:
    x, y, w, h = scale_box(int(block["x"]), int(block["y"]), int(block["w"]), int(block["h"]), width, height)
    return Rect(x, y, w, h)


def _offset_for(region: str) -> int:
    if region.endswith("-prev"):
        return -1
    if region.endswith("-next"):
        return 1
    return 0


def render_placed(page, payload, width, height, font_path, definitions, images) -> dict[str, Image.Image]:
    page_id = str(page.get("page_id") or "today")
    out: dict[str, Image.Image] = {}
    bx, by, bw, bh = content_blank(width, height)
    out["pageblank"] = Image.new("L", (bw, bh), style.PAPER)
    for region in http_region_names(page):
        if region == "pageblank":
            continue
        block = find_block(page, region)
        if block is None:
            continue
        target = _target(block, width, height)
        widget = block.get("widget")
        if widget in DESIGN:
            out[region] = paint_system(widget, payload, target, font_path, page_id, _offset_for(region))
        elif widget == "text":
            out[region] = paint_text(str(block.get("text") or ""), str(block.get("align") or "left"), target, font_path)
        elif widget == "image":
            out[region] = paint_image(images.get(str(block.get("asset") or "")), target)
        elif widget == "custom":
            out[region] = paint_custom(definitions.get(str(block.get("def") or "")), payload, target, font_path)
    return out


def placed_rect(page: dict, region: str, width: int, height: int) -> Rect:
    if region == "pageblank":
        x, y, w, h = content_blank(width, height)
        return Rect(x, y, w, h)
    block = find_block(page, region)
    if block is None:
        return Rect(0, 0, 1, 1)
    return _target(block, width, height)


def paste_page(page, payload, width, height, font_path, definitions, images, glyphs, metrics_for) -> Image.Image:
    from server.render.pages.today import render_glyphs

    canvas = Image.new("L", (width, height), style.PAPER)
    rendered = render_placed(page, payload, width, height, font_path, definitions, images)
    blank = placed_rect(page, "pageblank", width, height)
    canvas.paste(rendered["pageblank"], (blank.x, blank.y))
    for block in iter_blocks(page):
        if block.get("widget") == "clock":
            continue
        key = block_region_key(block)
        image = rendered.get(key)
        if image is None:
            continue
        rect = placed_rect(page, key, width, height)
        canvas.paste(image, (rect.x, rect.y))
    clock = next((block for block in iter_blocks(page) if block.get("widget") == "clock"), None)
    if clock is not None:
        rect = _target(clock, width, height)
        metrics = metrics_for(rect)
        if glyphs is None:
            glyphs = render_glyphs(metrics, font_path)
        hhmm = str((payload.get("clock") or {}).get("now") or "00:00")
        if len(hhmm) < 5:
            hhmm = "00:00"
        x = metrics.x
        for glyph in (hhmm[0], hhmm[1], ":", hhmm[3], hhmm[4]):
            cell = glyphs.get(glyph)
            if cell is None:
                continue
            canvas.paste(cell, (x, metrics.y))
            cell_w = metrics.colon_w if glyph == ":" else metrics.digit_w
            x += cell_w + metrics.gap
    return canvas
