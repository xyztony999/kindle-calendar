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

## §4 web-chrome（网页明暗）

| 枚举名 | 取值 | 说明 | 引用方 |
|--------|------|------|--------|
| `ui_theme` | light / dark | 使用者点过明暗按钮之后记住的外观。只有这两个值会写入 Cookie `kc_theme`。没有这枚 Cookie，或值不是这两个，页面跟随系统，不另设第三态 | api-web-chrome.md 3.4 / interaction-web-chrome.md |

## §5 adaptive-data-styles（数据积木外观，2026-10-17设计）

data_style code+label：hero=突出首项，rows=逐行列表，horizontal=横向指标，grid=网格卡片。适用规则见api-adaptive-data-styles.md，不用于系统widget类型枚举。历史定义默认仍hero/rows；新覆盖使用四值。

field_kind code+label：number=数字，time=时间，date=日期，short_text=短分类，text=文本。紧凑类别为前四项；缺失值不改变类别。引用：catalog与样式适用校验。

## 更新记录

| 版本 | 日期 | 更新说明 |
|------|------|---------|
| v1.2 | 2026-10-15 | 新增 §4 `ui_theme`（light / dark）。跟随系统是缺省，不入库、不入枚举值 |
| v1.1 | 2026-10-10 | 新增 §3 `ui_lang`（zh / en），供设备画面与网页共用 |
| v1.0 | 2026-10-10 | 初始填充：web-admin 四枚举；回填 v2-pages 两枚举（page_id 与 web-admin 共用） |
