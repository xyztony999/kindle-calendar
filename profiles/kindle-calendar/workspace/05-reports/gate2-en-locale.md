# Gate 2 验证报告 — 代码→交付门控

**模块**：en-locale（双语画面与网页语言）
**检查时间**：2026-10-10
**Profile**：kindle-calendar（business，无激活技术栈）
**设计基线**：api-en-locale.md v1.1 / interaction-en-locale.md v1.1 / Gate 1 PASS（用户已确认）
**扫描路径**：`server/`、`kindle/documents/`、`kindle/dash.sh`、`tests/test_landing_lang.py`、`tests/test_en_locale.py`

## 判定

**WARN**

服务端契约、单测和浏览器切换已通过。Kindle 真机没有在本环境启动，英文入口是否在书库里拉起英文画面，需要用户在设备上确认。无激活技术栈，Java 后端与 Scm 前端清单不适用。

较早那份「只翻译落地页」的 Gate 2 已由本报告替换。

## 服务端与网页

| 检查 | 结果 |
|------|------|
| 不带 `lang` 与 `lang=zh` 的今日整图哈希相同 | 通过 |
| `lang=en` 的今日整图、黄历整图与中文图不同 | 通过 |
| 设备图不看 `Accept-Language` | 通过 |
| 中文 env 不出现 `lang=`；英文 env 有 `lang=en`，分区地址带 `lang=en`，`REGIONS_VERSION` 不同 | 通过 |
| 英文 JSON 天气描述为 Clear sky；宜忌与一言正文仍是中文 | 通过 |
| `/?format=json` 接口清单仍是中文 | 通过 |
| 管理端错误码仍是 `ADMIN_DISABLED`；无 Cookie 时句子为中文，Cookie `kc_lang=en` 时为英文 | 通过 |
| 单测 `tests.test_landing_lang`、`tests.test_en_locale`、`tests.test_web_admin` | 23 项通过 |

## 浏览器

在 `http://127.0.0.1:8080` 实际打开页面：

1. 浏览器语言为英文时，首页直接是英文（Today / Week / Admin）。
2. 点「中文」后变成中文首页。再打开不带参数的 `/`，仍是中文，说明 Cookie 压过了浏览器语言。
3. 中文首页的预览地址是 `/dashboard.png?page=today`，没有 `lang=en`。
4. 打开 `/admin`，页面是中文，并显示「管理端未启用」（本机服务没有 `ADMIN_PASSWORD`）。
5. 点 English 后，同一页变成 Admin is off。再回首页，Cookie 已是英文，首页跟着变成英文。
6. 打开 `dashboard.png?lang=en`：页眉为 `10 Oct`、`Sat`、`国庆节 Work`，页名为 Today/Week/Month/Detail/Almanac，天气为 Clear sky，农历行是 `Lunar` 加中文，生肖为 Horse，一言仍是中文。
7. 打开黄历 `page=almanac&lang=en`：栏题 Suitable / Avoid，条目仍是中文；`Solar term 寒露 · Day 2 · Next 霜降`；`Phenology` 后是中文物候。

## 真机未验证

| 项 | 说明 |
|----|------|
| 书库「天气台历」 | 应仍是中文画面。本环境没有 Kindle |
| 书库「WeatherCalendar」 | 应声明英文并进入同一套 `dash.sh`，五页界面词为英文 |
| 带空格的「Weather Calendar」 | 应仍转入中文启动器 |
| 旧设备不带 `lang` | 云端已保证中文图和 env 地址不变，但旧脚本本身没有在真机上再跑 |
| 英文页眉拥挤程度 | 浏览器里的英文今日图能放下页名；墨水屏局刷后的实际换行要以真机为准 |
| 黄历左侧「Horse」竖排 | 浏览器图里生肖英文是逐字竖排。真机上是否接受，请看一眼 |

## 未改动的既有决策

鉴权（口令、会话、限速）、配置 JSON 结构、GPL-3.0、云端优先轮播都没有改。语言 Cookie 是 `kc_lang`，与登录会话分开。没有新增 Python 依赖，页面没有 CDN。

## 需要用户确认

在 Kindle 上分别点开「天气台历」和「WeatherCalendar」，确认中文画面不变、英文画面的界面词和黄历降级与上面的浏览器图一致。确认前，真机部分保持 WARN。
