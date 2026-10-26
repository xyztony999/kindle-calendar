# API：editor-manage（编辑器内管理面板 / 系统积木选项扩展）

- 版本：v1.0（2026-10-24）
- 原则：无新 HTTP 接口；全部经由既有 schema 驱动链路（SYSTEM_OPTIONS → 校验 → normalize → 渲染 → widget-catalog → 前端控件）。

## 1. SYSTEM_OPTIONS schema 变更（server/layout.py）

新增条目（默认值=现状）：

| widget | key | 类型 | 默认 | 枚举 | 说明 |
|---|---|---|---|---|---|
| header | `show_notes` | bool | True | — | 节日/假期备注行 |
| weather | `show_range` | bool | True | — | 今日高低温行 |
| weather | `show_icon` | bool | True | — | 天气图标 |
| quote | `size` | choice | "md" | lg/md/sm | 起步字号 32/27/22；收缩下限按档位 60%（19/16/15），避免长句把档位收敛成同一字号 |
| grid | `week_start` | choice | "mon" | mon/sun | 周起始日 |
| header, weather, sun, scene, quote, list, chart, title, grid, hourly, indices, main（除 clock） | `border` | bool | False | — | 细边框；clock 因设备端字形拼装明确排除 |

- `QUOTE_SIZE_START = {"lg":32,"md":27,"sm":22}`（渲染侧映射）。
- 前端 choice 值→文案映射：lg/md/sm→大/中/小（既有词条），mon/sun→周一/周日（新词条 `week_mon/week_sun`）。

## 2. 文字积木专用字段（非 options 通道，与 align 同级）

- `block.size ∈ ("lg","md","sm")`，默认 "md"（=现状 `max(18, rect.h//3)` 起步）。
- lg→起步×1.35，sm→起步×0.7；`_fit_font` 自适应收缩下限 15 不变。
- 校验（layout.py）：`size` 仅 text 积木允许，取值枚举；normalize 白名单（settings.py `_normalize_block`）加 `size`。
- 渲染（placed.py `paint_text`）签名增加 size 参数；dispatch 传 `block.get("size")`。
- `align` 链路不变，仅补前端控件。

## 3. 渲染行为变更

- `render_header`：`show_notes=False` 隐藏节日/假期备注（星期保留）。
- `render_weather`：`show_range=False` 隐藏高低温行；`show_icon=False` 隐藏图标（文字描述保留）。
- `render_quote`：增加 options 参数；size 档位改起步字号。placed.py 分发补传 options。
- `render_grid`（month.py）：补 `show_lunar` 消费（修复死选项）；`week_start=sun` 时表头/周末列/矩阵重排；依赖 `almanac.month_grid_info(year, month, firstweekday)` 且缓存 key 增加起始日。
- `paint_system`（placed.py）：`options.border=True` 时按目标矩形画 1px 内缩边框（INK，宽 2），对全部走 paint_system 的系统积木生效（clock 除外）。
- `paint_text`：见上。
- service.py `_get_month_offset_region`：月历 ±N 月渲染补传块 options（修复漏传，连带 show_badges/border/week_start 生效）。

## 4. 管理端前端（无后端接口变化）

- 版面编辑器左栏新增管理抽屉（#wm-* 元素），与主视图卡片复用同一套参数化管理逻辑（容器化 scope）。
- 抽屉行含「放置」按钮（等同调色板点击 place）。
- 外观面板：text 积木显示对齐（左/中/右）与字号（大/中/小）单选；任意积木显示「上移/下移一层」（z 与相邻块交换，0–99 钳制）。
- choice 选项文案改为值→词条映射（支持 mon/sun 等新枚举）。

## 5. 不变项

- settings/save、widget-catalog、layout-preview 契约不变（schema 自动驱动）。
- 设备端 env/分区契约不变（时钟仍走字形，无 12/24h、无秒）。
