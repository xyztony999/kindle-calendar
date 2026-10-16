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


def _data_lines(draw, text: str, font, width: int) -> list[str]:
    """Wrap CJK and unbroken identifiers using actual glyph bounds."""
    lines = []
    line = ""
    for char in text:
        if char == "\n":
            lines.append(line)
            line = ""
            continue
        left, _, right, _ = draw.textbbox((0, 0), line + char, font=font)
        if line and right - left > width:
            lines.append(line)
            line = char
        else:
            line += char
    lines.append(line)
    return lines


def _data_text(draw, text: str, box: tuple[int, int, int, int], font_path: str,
               start: int, fill: int = style.INK, align: str = "left", gap: int = 2) -> int:
    """Fit into a real pixel budget, then ellipsize the last visible line."""
    x, y, width, height = box
    if width < 1 or height < 1:
        return 0
    original = str(text or "—").replace("\r", "")
    text = original[:2048]
    size = max(1, min(start, height))
    minimum = min(size, 8)
    while True:
        font = style.get_font(size, font_path)
        lines = _data_lines(draw, text, font, width)
        bounds = [draw.textbbox((0, 0), line or "—", font=font) for line in lines]
        line_h = max(1, max(bottom - top for _, top, _, bottom in bounds))
        fits = (len(lines) * line_h + max(0, len(lines) - 1) * gap <= height
                and all(right - left <= width for left, _, right, _ in bounds))
        if fits or size <= minimum:
            break
        size = max(minimum, size - 2)
    capacity = max(0, (height + gap) // (line_h + gap))
    visible = lines[:capacity]
    truncated = len(visible) < len(lines) or len(original) > len(text)
    if visible:
        for index, line in enumerate(visible):
            suffix = "…" if (index == len(visible) - 1 and truncated) else ""
            while line and draw.textbbox((0, 0), line + suffix, font=font)[2] - draw.textbbox((0, 0), line + suffix, font=font)[0] > width:
                line = line[:-1]
                suffix = "…"
            rendered = line + suffix
            left, top, right, bottom = draw.textbbox((0, 0), rendered, font=font)
            if right - left > width or bottom - top > line_h:
                continue
            offset = (width - (right - left)) // 2 if align == "center" else width - (right - left) if align == "right" else 0
            draw.text((x + offset - left, y - top), rendered, font=font, fill=fill)
            y += line_h + gap
    return len(visible) * (line_h + gap)


def paint_custom(definition: dict | None, payload: dict, rect: Rect, font_path: str) -> Image.Image:
    image = Image.new("L", (rect.w, rect.h), style.PAPER)
    if not definition:
        return image
    draw = ImageDraw.Draw(image)
    lang = "en" if is_en(payload) else "zh"
    fields = list(definition.get("fields") or [])
    values = [field_text(payload, field) for field in fields]
    labels = [field_label(field, lang) for field in fields]
    if not fields:
        return image
    padding = min(4, max(0, (min(rect.w, rect.h) - 1) // 2))
    width, height = rect.w - 2 * padding, rect.h - 2 * padding
    appearance = definition.get("style", "rows")
    count = len(fields)
    if appearance == "hero":
        # Keep the legacy first-value emphasis, with a separate footer budget.
        hero_height = height if count == 1 else max(1, min(int(rect.h * 0.62), height - min(18, height // count) * (count - 1)))
        used = _data_text(draw, values[0], (padding, padding, width, hero_height), font_path,
                          max(20, int(rect.h * 0.42)))
        if count > 1:
            y = padding + min(hero_height, used)
            row_height = max(0, (height - (y - padding)) // (count - 1))
            small = max(15, int(rect.h * 0.42) // 2)
            for label, value in zip(labels[1:], values[1:]):
                _data_text(draw, f"{label}  {value}", (padding, y, width, row_height), font_path, small, style.MID)
                y += row_height
        return image
    if appearance in ("horizontal", "grid"):
        columns = count if appearance == "horizontal" else min(count, 2)
        rows = (count + columns - 1) // columns
        for index, (label, value) in enumerate(zip(labels, values)):
            col, row = index % columns, index // columns
            x0, x1 = padding + width * col // columns, padding + width * (col + 1) // columns
            y0, y1 = padding + height * row // rows, padding + height * (row + 1) // rows
            if appearance == "grid" and x1 - x0 >= 12 and y1 - y0 >= 12:
                draw.rectangle((x0, y0, x1 - 1, y1 - 1), outline=style.MID)
                x0, x1, y0, y1 = x0 + 3, x1 - 3, y0 + 3, y1 - 3
            cell_gap = min(4, max(0, (x1 - x0) // 8))
            cell_width = x1 - x0 - cell_gap
            label_height = max(1, (y1 - y0) // 3)
            value_height = max(0, y1 - y0 - label_height - 2)
            _data_text(draw, value, (x0, y0, cell_width, value_height), font_path,
                       min(48, max(18, value_height * 2 // 3)), align="center")
            _data_text(draw, label, (x0, y1 - label_height, cell_width, label_height), font_path,
                       min(22, max(10, label_height - 2)), style.MID, align="center")
        return image
    # Rows reserve distinct columns so long values cannot collide with labels.
    size = max(15, min(36, rect.h // (count + 1)))
    label_width = max(0, width * 2 // 5)
    column_gap = min(8, width // 8)
    for index, (label, value) in enumerate(zip(labels, values)):
        y0 = padding + height * index // count
        y1 = padding + height * (index + 1) // count
        _data_text(draw, label, (padding, y0, label_width, y1 - y0), font_path, size, style.MID)
        _data_text(draw, value, (padding + label_width + column_gap, y0, width - label_width - column_gap, y1 - y0),
                   font_path, size, align="right")
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
            definition = definitions.get(str(block.get("def") or ""))
            if definition is not None and block.get("style") in ("hero", "rows", "horizontal", "grid"):
                definition = {**definition, "style": block["style"]}
            out[region] = paint_custom(definition, payload, target, font_path)
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
