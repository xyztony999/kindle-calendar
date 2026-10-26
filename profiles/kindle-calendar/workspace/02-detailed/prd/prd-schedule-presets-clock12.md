# PRD：个人日程 + 版面快照 + 时钟 12 小时制（schedule-presets-clock12）

- 版本：v1.0（2026-10-25 Gate 1 确认，用户拍板 1A/2A/3B/4A）
- 前置：editor-manage（同轮未提交，叠加实现）
- 实施顺序：① 时钟 12h → ② 版面快照 → ③ 个人日程（每段独立验证）

## R1 时钟 12/24 小时制（完整形态：去前导零 + AM/PM 小字）

- R1.1 clock 积木新选项 `hour12`（bool，默认 False=24h 现状，未配置零回归）。
- R1.2 12h 显示：小时 1–12 **去前导零**（"9:05"），后缀 **AM/PM 小字**（高度约为数字 28%，底对齐）；整体在时钟块内居中（单位数小时时起点右移半个数字位）。
- R1.3 字形契约扩展：GLYPHS 增加 `am`/`pm`（仅 12h 模式生成）；`/r/<page>/clock/<glyph>.png` 路由正则放宽到 `am|pm`；字形缓存 key 加入模式。
- R1.4 env 契约扩展：每页新增 `CLOCK_<页>_HOUR12=0/1`、`CLOCK_<页>_SUF_W/SUF_H`（后缀字形宽高，24h 时为 0），today 附带 legacy 无前缀变量。旧版 dash.sh source 后静默忽略；24h 几何语义与现状完全一致。
- R1.5 设备端 dash.sh：`apply_clock` 读取新变量并计入几何指纹（模式/后缀尺寸变化 → 清 clock.last 重画）；`draw_clock` 重构为**可变格循环**（按 token 序：数字/冒号/空格=后缀；token 数变化时整只重画，否则逐格差分局刷）；`sync_glyphs` 按模式校验 11 或 13 个字形文件。
- R1.6 服务端预览（paste_page）与 env 同规则换算（24h canonical "HH:MM" → 12h 显示串 + 后缀 + 居中偏移）。
- R1.7 **不做**：legacy 固定版式路径（compose_page/today.compose，scripts/preview.py 用）维持 24h；秒显示。
- 部署注意：12h 生效需将新版 dash.sh 拷贝到 Kindle；旧设备继续 24h 不受影响。

## R2 版面快照（presets）

- R2.1 settings 顶层 `presets[]`（≤8）：`{id, name, created_at, snapshot: {pages, widget_defs, assets}}` **整包快照**（自洽，应用时不缺引用）。
- R2.2 管理端「页面与轮播」卡片内：`保存当前为方案`（输入名称）；方案行：名称+时间 | 应用 | 覆盖更新 | 删除（确认）| 导出（下载 JSON 文件）。
- R2.3 应用 = 替换内存 state 的 pages/widget_defs/assets 三块并标脏；**点保存才落库**；弹窗打开时先关弹窗。不做方案导入（设置导入导出已覆盖）。

## R3 个人日程（ICS + 纪念日/倒计时 + 月历标记）

### R3.1 ICS 订阅（方案 1A：settings + 管理端卡）
- settings `ics.urls`（≤3 条，强制 https，≤500 字符）；管理端「日程」卡片内增删。
- 数据源 `server/ics.py`：模块级 TTL 缓存（6h）+ 锁 + 失败保旧数据（抄 holidays.py 骨架）；单次拉取 timeout 8s、禁重定向、响应 ≤2MB；`icalendar + recurring-ical-events` 解析未来 7 天事件（含 RRULE 展开、时区处理），总量 ≤100。
- payload 新增 `events: [{iso_date, time|all_day, title, source: "ics"|"anniv"}]`（参与 data_fingerprint，分区缓存自动失效）；失败降级为旧缓存，无数据时日程积木显示「暂无日程」。

### R3.2 本地纪念日/倒计时
- settings `anniversaries[]`（≤20）：`{id, name(1-20), date, repeat}`；repeat ∈ `none`(YYYY-MM-DD 一次) / `yearly`(MM-DD 公历每年) / `lunar`(MM-DD 农历每年，lunar-python 年度换算)。
- 纪念日在未来 7 天的命中以 `all_day` 事件并入 payload.events（source=anniv）；今天命中同时并入页眉节日备注行（复用 show_notes，零渲染改动）。
- payload 另出 `countdowns: [{name, days, iso_date}]`（未来 365 天内最近 5 条，days=0 表示今天）。

### R3.3 新系统积木
- **「日程」schedule**（DESIGN 646×244）：当日事件列表（时间 + 标题，全天标「全天」），≤6 行，长标题省略；外观选项 `show_tomorrow`（默认关，开启追加明日区块）；空态「今日无日程」。
- **「倒计时」countdown**（DESIGN 646×132）：`countdowns` 渲染「距 ··· N 天」，days=0 高亮「今天是 ···」。
- 两积木自动获得通用 border 选项（现有注入循环覆盖 SYSTEM_WIDGETS）。

### R3.4 月历日程标记
- grid 新选项 `show_event_dots`（默认关）：查看月中任一天在 payload.events 有命中 → 日期数字右上角画小实心点。

### R3.5 新数据积木字段
- `events.today_count`（number）/ `events.next_title`（short_text，截断显示）/ `events.next_time`（time）。

## 非目标

- 多 ICS 源分色/分组、事件跨天合并显示、ICS 源级启停；presets 导入；AM/PM 之外的时钟装饰。

## 验收要点

- 时钟：24h 渲染与现状逐字节一致（回归）；12h 在 1 位数/两位数小时、正午/午夜边界、模式切换（自动清缓存重画）均正确；harness 覆盖 draw_clock 三模式。
- 快照：保存→改版面→应用→保存→与快照时一致；覆盖/删除/导出可用；≤8 上限。
- 日程：ICS fixture 解析（含 RRULE 每周/全天）；纪念日 yearly/lunar 命中；月历点标记；字段取值；断网降级保旧数据。
