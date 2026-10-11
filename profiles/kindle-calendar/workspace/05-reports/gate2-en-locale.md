# Gate 2 验证报告 — 代码→交付门控

**模块**：en-locale（双语画面与网页语言）
**检查时间**：2026-10-11
**Profile**：kindle-calendar（business，无激活技术栈）
**设计基线**：api-en-locale.md v1.3（第 4.4.7–4.4.12 节）/ interaction-en-locale.md v1.2 / Gate 1 PASS（用户已确认）
**扫描路径**：`server/`、`tests/test_landing_lang.py`、`tests/test_en_locale.py`、`tests/test_web_admin.py`

## 判定

**WARN**

服务端契约、26 项单测和浏览器检查已通过。本环境没有 Kindle，书库里的中文入口和英文入口没有在真机上再跑。无激活技术栈，Java 后端与前端清单不适用。

2026-10-10 那份 Gate 2 记录的是上一版「历法专名留中文」。本报告替换它，作为这次增量的交付门控。

## 服务端与网页

| 检查 | 结果 |
|------|------|
| 不带 `lang` 与 `lang=zh` 的农历、干支、节气、宜忌、物候、一言仍是中文，且彼此一致 | 通过。九月初二、丙午、寒露、嫁娶、鸿雁来宾 |
| `lang=en` 的农历、干支、节气、宜忌、物候为对照表英文 | 通过。`2nd day, 9th lunar month`、`Bingwu`、Cold Dew、Marry / Worship、Wild geese arrive as guests |
| `lang=en` 页脚与中文页脚不同 | 通过。英文为 `Tyger, tyger, burning bright.` / Blake；中文为当日一言原文。出处只有作者名，没有 ZenQuotes 链接 |
| 英文在线一言 | 通过。请求固定地址 `https://zenquotes.io/api/today`，禁止重定向，超时 8 秒。当日句子缩到 16px 仍超宽，改用第 4.4.12 节的本地短句 |
| 单测 | 通过。`tests.test_en_locale`、`tests.test_landing_lang`、`tests.test_web_admin` 共 26 项 |
| 鉴权、配置 JSON、启动器、轮播 | 未改 |

## 浏览器

在 `http://127.0.0.1:8770` 打开页面：

1. `/?lang=zh` 页头只有一个 English 按钮，链到 `/?lang=en`。没有并排的「中文」按钮。
2. 点 English 后整页变成英文，页头只剩「中文」，链到 `/?lang=zh`。再点回去，页头又只剩 English。
3. Cookie `kc_lang` 会记住。浏览器语言是英文时，Cookie 为 zh 的后续访问仍是中文。
4. `/admin?lang=en` 只有「中文」一个语言链接，正文是 Admin is off。`/?lang=zh` 的管理端未启用页只有 English。管理端未设置口令时状态码仍是 503，这是原有行为。
5. 模拟 `prefers-color-scheme: dark` 后，首页背景为深色 `rgb(28, 25, 21)`，文字为浅色 `rgb(243, 239, 231)`。预览图底色仍是白色，没有把 Kindle 灰度图反相。
6. 英文今日图请求带 `lang=en`，中文今日图不带 `lang`。

## 真机未验证

| 项 | 说明 |
|----|------|
| 书库「天气台历」 | 应仍是中文画面。本环境没有 Kindle |
| 书库「WeatherCalendar」 | 应拉到英文画面：农历序数、Bingwu Horse、方案丁黄历、英文页脚 |
| 带空格的「Weather Calendar」 | 应仍转入中文启动器 |
| 英文页眉与黄历左栏是否挤 | 浏览器请求到的英文数据已换词。墨水屏上的换行要以真机为准 |
| 页脚缩字 | 过宽会改用本地短句。真机分辨率若不是 758 宽，是否仍放得下要在设备上看 |

## 未改动的既有决策

鉴权、配置持久化、GPL-3.0、云端优先轮播、语言入口都没有改。没有新增 Python 依赖，页面没有 CDN，也没有主题开关。

## 需要用户确认

在 Kindle 上分别点开「天气台历」和「WeatherCalendar」，看中文画面是否保持原文，英文画面的农历、干支、黄历和页脚是否与上面的英文数据一致。确认前，真机部分保持 WARN。
