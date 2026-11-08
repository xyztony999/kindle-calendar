"""页眉日期格式：四种预设 + 花括号自定义模板。

预设 cn（默认）即现状：中文页「十一月八」、英文页「8 Nov」。
模板占位符 {Y} {M} {MM} {D} {DD} {CM} {CD} {W}；英文页 {CM}/{CD} 回退阿拉伯数字。
"""

from __future__ import annotations

import re
from datetime import date

from server.almanac import _day_cn, _month_cn
from server.locale import _MONTHS, _MONTHS_SHORT, _WEEKDAYS

DATE_FORMATS = ("cn", "md", "ymd", "dot", "custom")
# 上限按模板写法计（占位符本身占 3–4 字）：「{Y}年{M}月{D}日 周{W}」就有 17 字
TEMPLATE_MAX = 24
PLACEHOLDERS = ("Y", "M", "MM", "D", "DD", "CM", "CD", "W")
_TOKEN = re.compile(r"\{([^{}]*)\}")
_WEEKDAY_CN = "一二三四五六日"


def template_error(template: str, allowed: tuple = PLACEHOLDERS) -> str | None:
    """返回首个非法片段（未知占位符如 "{X}"，或未闭合的花括号如 "{W"），全部合法返回 None。"""
    for match in _TOKEN.finditer(template):
        if match.group(1) not in allowed:
            return match.group(0)
    rest = _TOKEN.sub("", template)
    for index, char in enumerate(rest):
        if char in "{}":
            return rest[index:index + 3]
    return None


def render_template(template: str, day: date, english: bool) -> str:
    values = {
        "Y": str(day.year),
        "M": str(day.month),
        "MM": f"{day.month:02d}",
        "D": str(day.day),
        "DD": f"{day.day:02d}",
        "CM": str(day.month) if english else _month_cn(day.month),
        "CD": str(day.day) if english else _day_cn(day.day),
        "W": _WEEKDAYS[day.weekday()] if english else _WEEKDAY_CN[day.weekday()],
    }
    return _TOKEN.sub(lambda match: values.get(match.group(1), match.group(0)), template)


def header_date_text(fmt: str, day: date, english: bool, template: str = "") -> str:
    if fmt == "custom" and template.strip() and template_error(template) is None:
        return render_template(template, day, english)
    if fmt == "md":
        return f"{_MONTHS_SHORT[day.month - 1]} {day.day}" if english else f"{day.month}月{day.day}日"
    if fmt == "ymd":
        return f"{day.day} {_MONTHS[day.month - 1]} {day.year}" if english else f"{day.year}年{day.month}月{day.day}日"
    if fmt == "dot":
        return f"{day.month:02d}.{day.day:02d}"
    return f"{day.day} {_MONTHS_SHORT[day.month - 1]}" if english else f"{_month_cn(day.month)}月{_day_cn(day.day)}"
