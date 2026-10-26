# API：schedule-presets-clock12

- 版本：v1.0（2026-10-25）
- 无新 HTTP 接口；env/字形契约扩展向后兼容（旧设备静默忽略新变量）。

## 1. 时钟契约

### SYSTEM_OPTIONS
`clock.hour12`：bool，默认 False。

### env 新增（每页 + today legacy 无前缀）
```
CLOCK_<PAGE>_HOUR12=0|1
CLOCK_<PAGE>_SUF_W=<px>      # AM/PM 字形宽（24h 为 0）
CLOCK_<PAGE>_SUF_H=<px>
```

### 字形路由
`/r/<page>/clock/<glyph>.png`：glyph 正则 `^(?:[0-9:]|am|pm)$`；am/pm 仅在 hour12 模式生成；字形缓存 key 含 hour12。

### metrics_in(rect, hour12)
12h 时 total_w 追加后缀位（suf_w + gap）；digit/colon 公式不变。设备端单位数小时居中偏移量 = (DIGIT_W+GAP)/2，由设备自行计算。

## 2. settings schema 新增键（SCHEMA_VERSION 保持 3，缺失容错=默认）

| 键 | 结构 | 校验 | 默认 |
|---|---|---|---|
| `ics` | `{"urls": [str]}` | ≤3 条、https、≤500 字符 | `{"urls": []}` |
| `anniversaries` | `[{id,name,date,repeat}]` | ≤20；name 1–20；repeat∈none/yearly/lunar；none→date=YYYY-MM-DD，yearly/lunar→date=MM-DD | `[]` |
| `presets` | `[{id,name,created_at,snapshot}]` | ≤8；name 1–20；snapshot 含 pages/widget_defs/assets 数组 | `[]` |

旧 schema 导入（无新键）validate 容错，normalize 补默认。

## 3. payload 扩展（参与 data_fingerprint）

```json
"events": [{"iso_date": "2026-10-26", "time": "09:30", "all_day": false, "title": "周会", "source": "ics|anniv"}],
"countdowns": [{"name": "生日", "days": 15, "iso_date": "2026-11-10"}]
```
- events 覆盖今天起 7 天（ICS 展开纪念日命中）；countdowns 为未来 365 天内最近 5 条纪念日。
- 今天命中的纪念日名称并入 `date.festivals`（页眉备注行复用 show_notes）。

## 4. 新系统积木

| widget | DESIGN | 选项 | 渲染 |
|---|---|---|---|
| `schedule` | 646×244 | `show_tomorrow`(bool, False) + border | 当日事件 ≤6 行（时间+标题/全天标记/省略号），show_tomorrow 追加明日区块 |
| `countdown` | 646×132 | border | 「距 ··· N 天」×3，days=0 →「今天是 ···」高亮 |

`grid` 新选项 `show_event_dots`（bool, False）：查看月命中日画点。

## 5. 新字段（FIELD_DEFS）

`events.today_count`(number) / `events.next_title`(short_text) / `events.next_time`(time)。

## 6. 依赖

requirements.txt += `icalendar>=6`、`recurring-ical-events>=3`。
