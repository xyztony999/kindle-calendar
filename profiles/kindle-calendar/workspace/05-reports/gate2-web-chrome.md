# Gate 2 验证报告 — 代码→交付门控

**模块**：web-chrome（网页外观：登录卡、顶栏按钮、图片承载页、深浅色）
**检查时间**：2026-10-15
**Profile**：kindle-calendar（business，无激活技术栈）
**设计基线**：prd-web-chrome.md v1.0 / api-web-chrome.md v1.0 / interaction-web-chrome.md v1.0 / Gate 1 PASS（用户已确认六条）
**扫描路径**：`server/locale.py`、`server/reading.py`、`server/viewer.py`、`server/app.py`、`server/admin.py`、`server/landing.py`、`server/templates/admin.html`、`reading.html`、`viewer.html`、`index.html`、`tests/test_web_chrome.py`

## 判定

**PASS**

无激活技术栈。Java 后端 34 项与企业前端列表、表单、分步单据检查不适用。没有新路径、新表、新依赖。适用的契约已经用测试和浏览器核对过。

本判定不代替用户确认。确认前不提交。

## 行为

| 页面 | 结果 |
|------|------|
| 管理端三种版面的顶栏 | 左侧站点名，右侧明暗、English 或中文、返回首页。胶囊按钮。登录卡居中，卡片里没有第二条返回链接 |
| 阅读页顶栏 | 左侧站点名，右侧明暗、语言、原始数据、返回首页 |
| 首页顶栏 | 明暗在语言按钮左侧，GitHub 和管理端仍在后面 |
| 明暗 | 没选过跟随系统。点一下只在深色和浅色之间换。Cookie `kc_theme` 只有 light / dark，路径 `/`，一年。刷新后仍在，四类页面一致 |
| 三个图地址，浏览器要网页 | 嵌图页，有返回首页和查看原图。查看原图是 `format=png`，新标签 |
| 三个图地址，`Accept: */*`、图片类型、`format=png` | 仍是 `image/png`，正文与 ETag 与不带 format 的机器请求相同，并带 `Vary: Accept` |
| 深色管理端 | 数字框背景 `#2a2622`、字 `#f4f1ea`、边框 `#8a8175`。禁用的黄历行不透明度 0.75，背景仍是深色。预览图没有被换成 HTML |

不看 User-Agent。打开图片页不记心跳。语言仍是一个按钮。

## 测试

`tests.test_web_chrome`、`tests.test_api_view`、`tests.test_landing_lang`、`tests.test_web_admin`：34 项通过。

同一次更早的全量里，`tests.test_en_locale` 也通过。没有改它的断言。

## 浏览器与实请求

在 `http://127.0.0.1:8766` 打开页面，并用 `Accept: */*` 请求同一服务：

1. 管理端登录页是深色卡片（当时系统为深色）。顶栏右侧是月亮/太阳、English、返回首页。口令框是深底，卡片里没有第二条返回链接。
2. 登录后设置页：数字框、文本框为深底浅字。取消黄历后，该行不透明度 0.75，数字框仍是深底。预览图是灰度图，不是一页 HTML。
3. 点明暗变成浅色，刷新后仍是浅色，图标为月亮、提示「切换到深色」。阅读页、整页图、分区图、时钟字形、首页都保持浅色。
4. 阅读页顶栏顺序是明暗、English、原始数据、返回首页。
5. 浏览器打开 `/dashboard.png?page=today`、`/r/today/header.png`、`/r/today/clock/0.png`，都是嵌图页，带返回首页和「查看原图」。图没有反相。
6. 同一三个地址在 `Accept: */*` 下是 PNG 魔数，要网页时是 HTML。

## 未改动

没有改 PNG 字节和 ETag 的计算，没有改机器 JSON 和 env，没有改 `/admin/api/*` 的字段，没有用 User-Agent。没有新增 Python 依赖。没有提交。

## 需要用户确认

确认本判定后，这次网页外观即可视为交付。Kindle 仍用 wget/curl，不声明网页，拿到的仍是原来的 PNG。
