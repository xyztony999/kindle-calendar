# PRD：landing-mono-font（首页与阅读页代码字体统一）

- 版本：v1.0（2026-11-12，/pipeline 增量，会话编排轨；master @ 53706f5）
- 契约：无接口变化，纯模板 CSS。

## 1. 问题与拍板

首页 API 清单（`.endpoints code`）与接口阅读页原文视图（`pre`）未声明字体族，落到浏览器默认 fixed 字体（用户环境命中 Courier New 打字机衬线），与全站「正文无衬线 + 标题衬线」体系不协调。

用户拍板（两题全推荐）：会话编排；**两处统一等宽栈**（否决仅修首页 / 改无衬线）。

## 2. 方案

字体栈（两处一致）：
`ui-monospace, "Cascadia Mono", "SF Mono", Consolas, Menlo, "Courier New", monospace`

- index.html `.endpoints code`、reading.html `pre` 各加一行声明（沿用模板各自内联样式的惯例）。
- admin/credits/viewer 无代码元素，不涉及。

## 3. 验收（Gate 2 实测）

- computed font-family 断言：首页 code 与阅读页 pre 均解析到新栈；亮/暗/390px 截图目检（data/ui-redesign/mono-*.png）。
- 195 单测 OK；HTTP 回归 80/80。
- 勘察坑：阅读页 `pre` 在「原始数据」details 折叠块内且仅 `dashboard.env` 视图内嵌 source；Playwright goto 默认 `Accept: */*` 走机器原文，需 `?format=html`。
