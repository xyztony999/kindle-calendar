# enum-pool（业务枚举池）

> 由 /design D3 按模块填充。API 文档引用枚举时标注「enum-pool.md §章节」。

## §1 web-admin（Web 管理端）

| 枚举名 | 取值 | 说明 | 引用方 |
|--------|------|------|--------|
| `page_id` | today / week / month / detail / almanac | 台历页面标识（与 `server/render/regions.py` PAGES 一致） | api-web-admin.md 4.1 / api-v2-pages.md 3.4（同义） |
| `quote_mode` | online / offline / custom | 页脚一言来源模式 | api-web-admin.md 4.1 |
| `delivery_state` | pending / delivered / unknown | 配置下发状态（版本比对派生） | api-web-admin.md 4.2 / A-10 |
| `online_state` | online / offline / unknown | 设备在线判定（心跳时效派生） | api-web-admin.md A-10 |

## §2 v2-pages（页面集与显示治理，回填）

| 枚举名 | 取值 | 说明 | 引用方 |
|--------|------|------|--------|
| `month_asset` | prev / cur / next | 月历三月预裁资产键 | api-v2-pages.md 3.4 |
| `waveform` | A2 / GC16 / FULL | 墨水屏刷新波形 | api-v2-pages.md 3.4 |

## §3 en-locale（双语呈现）

| 枚举名 | 取值 | 说明 | 引用方 |
|--------|------|------|--------|
| `ui_lang` | zh / en | 界面语言。zh 为默认。设备请求缺省或无法识别时按 zh，且中文响应与现在一致。网页另有浏览器语言与 Cookie，仍只落在这两个值 | api-en-locale.md 3.4 / interaction-en-locale.md |

## 更新记录

| 版本 | 日期 | 更新说明 |
|------|------|---------|
| v1.1 | 2026-10-10 | 新增 §3 `ui_lang`（zh / en），供设备画面与网页共用 |
| v1.0 | 2026-10-10 | 初始填充：web-admin 四枚举；回填 v2-pages 两枚举（page_id 与 web-admin 共用） |
