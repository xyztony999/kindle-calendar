# Gate 2 验证报告 — 代码→交付门控

**模块**：api-view（接口阅读页）
**检查时间**：2026-10-11
**Profile**：kindle-calendar（business，无激活技术栈）
**设计基线**：prd-api-view.md v1.0 / api-api-view.md v1.0 / interaction-api-view.md v1.0 / Gate 1 PASS（用户已确认四条）
**扫描路径**：`server/app.py`、`server/reading.py`、`server/templates/reading.html`、`tests/test_api_view.py`

## 判定

**PASS**

无激活技术栈。Java 后端 34 项与企业前端列表、表单、分步单据检查不适用。本模块没有新表、新角色、新路径。适用的契约已经用测试和浏览器核对过。

本判定不代替用户确认。确认前不提交。

## 行为

四个地址按已确认的规则分流：

| 请求 | 结果 |
|------|------|
| 浏览器 `Accept: text/html` | 阅读页 |
| 不带 Accept、`*/*`、`application/json` | 原来的 JSON 或 env 文本 |
| `format=json`，即使浏览器声明要网页 | 机器原文。env 仍是 `text/plain`，不是 JSON |
| `format=html` | 阅读页 |
| 带 `Accept: text/html` 打开 PNG | 仍是 `image/png` |
| 带 `Accept: text/html` 打开 `/admin/api/settings` | 仍是 JSON |

阅读页语言跟随网页（地址、Cookie、浏览器语言）。机器原文只看地址里的 `lang`，不看 Cookie。英文 Cookie 下的 `/weather` JSON 仍是中文描述。打开设备清单阅读页记一次心跳；数据组装失败时不记。成功响应带 `Vary: Accept`。

## 测试

`tests.test_api_view`：10 项通过。

同一次还跑过 `tests.test_landing_lang`、`tests.test_web_admin`，通过。`tests.test_en_locale` 里有一项按日期取英文一言，当天句子与测试里写死的出处不一致。那是双语模块自己的测试，不是这次阅读页改动，没有改那个测试。

## 浏览器与实请求

在 `http://127.0.0.1:8765` 打开页面，并用不声明网页的客户端请求同一服务：

1. 浏览器打开 `/health`，看到「Service status」阅读页，而不是 JSON。当时天气尚未刷新，页面写明 Weather is unavailable，HTTP 仍是 200。
2. 浏览器打开 `/api/v1/dashboard.json`，看到北京、宜忌、节气、当前天气。点 English 后地址变为 `?lang=en`，标题和天气描述变成英文（Clear sky、Cold Dew），宜忌用载荷里的英文。
3. 点 Hour by hour，进入 `/weather` 阅读页，有逐日表和逐时表。
4. 打开 `/api/v1/dashboard.env`，看到屏幕、页序、轮播和「Opening this page counts as a fetch」。展开原文以 `DASH_DATE=` 开头，不是 HTML。
5. 浏览器再打开 `/api/v1/dashboard.env?format=json`，正文是 env 文本，不是阅读页。
6. 不声明网页的请求：`/health`、`/api/v1/dashboard.json`、`/weather` 为 `application/json`；`/api/v1/dashboard.env` 为 `text/plain`；PNG 仍是 `image/png`。

## 未改动

没有改 PNG 的字节和 ETag，没有改管理端接口，没有改首页链接和首页文案，没有用 User-Agent 判断浏览器。没有新增 Python 依赖。没有提交。

## 需要用户确认

确认本判定后，这次阅读页即可视为交付。不需要再改 Kindle 脚本：设备不声明网页，拿到的仍是原来的 env 和 JSON。
