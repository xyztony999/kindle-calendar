# API / 契约设计：en-locale（双语画面与网页语言）

| 属性 | 值 |
|------|-----|
| 模块 | en-locale |
| 版本 | v1.2 |
| 状态 | 稳定 |
| 最后更新 | 2026-10-11 |
| 输入 | prd-en-locale.md v1.2 |
| 技术规约 | 无激活技术栈。沿用现有 GET 与 Flask 内嵌页，不引入企业 POST 三段路径、Result 包装或数据表 |

本版替换作废的 v1.0。v1.0 要求删除 `WeatherCalendar.sh`、不翻译画面和管理端。

## 1. 模块设计概述

### 1.1 业务背景及目标

解决开源之后海外使用者看不懂中文画面和中文网站的问题。家庭用户从书库启动英文画面，维护者在首页和管理端切换语言。价值是同一套台历可以中文或英文阅读，旧的中文设备不用改脚本也保持原样。

### 1.2 边界说明

| 边界 | 说明 |
|------|------|
| 做 | 启动器语言声明、`lang` 查询参数、英文界面词、方案丁的历法对照、英文一言、网页单按钮与 Cookie、跟随系统深色、校验句子随语言变化 |
| 不做 | 新表、新鉴权、改配置 JSON、改轮播云端优先、自动翻译自定义文案、把 KUAL 改成英文、用 CDN、另加主题开关、在对照表之外新造黄历术语 |

### 1.3 设计决策

| # | 决策点 | 选择 | 理由 |
|---|--------|------|------|
| AD-0 | 管理模式 | 不适用 | 工具类，无自管/托管数据，无写入表 |
| AD-1 | 设备语言载体 | 查询参数 `lang`，取值见 enum-pool.md §3 `ui_lang` | 旧设备不带参数时 URL 与中文图都不变 |
| AD-2 | 进程变量名 | `KC_BOOK_LANG` | 不用 `LANG`，避免改设备区域设置 |
| AD-3 | 英文入口 | `WeatherCalendar.sh` 声明英文后 exec 同目录 `天气台历.sh` | 只有一套拉起逻辑。带空格的文件不声明英文 |
| AD-4 | 中文 env | 缺省和 `lang=zh` 都不往 env 资产地址追加 `lang` | 旧 `dash.sh` 拿到的 env 文本形状不变 |
| AD-5 | 网页记忆 | Cookie `kc_lang`，与会话 Cookie 分开 | 切换语言不碰鉴权 |
| AD-6 | 根路径 JSON | 清单句子保持中文 | 机器读的接口说明不是给人看的画面 |
| AD-7 | 缓存 | 指纹与 PNG 缓存键包含语言 | 中英文设备不会共用一张图 |
| AD-8 | 错误码 | 保持现有大写码，只翻译 `message` | 调用方仍按码分支 |
| AD-9 | 字体 | 继续用现有系统字体的拉丁字形 | 不新增字体，不引用 CDN |
| AD-10 | 黄历英文 | 方案丁：节气用通行英译，宜忌用固定对照，物候用意译，节日按有无通行译名取舍 | 用户 2026-10-11 选定。表外宜忌和无通行译名的节日留中文 |
| AD-11 | 农历与干支 | 英文序数加天干地支拼音和英文生肖 | 与方案丁一起锁定。中文画面不变 |
| AD-12 | 英文一言 | 在线取 ZenQuotes 当日一句，失败再用本地公有领域短句；不请求中文一言接口 | 与中文一言同一结构。自定义文案原样。Kindle 画面写作者名；ZenQuotes 要求的链接写在 README |
| AD-13 | 语言按钮 | 只渲染一个链到另一种语言的按钮 | 用户锁定。Cookie 规则不变 |
| AD-14 | 网页深色 | 模板内 `prefers-color-scheme: dark` | 不新增接口，不新增主题设置 |

### 1.4 领域对象总览

| 对象 | 角色 | 说明 |
|------|------|------|
| 界面语言 | 过程数据 | `zh` 或 `en`，不入库 |
| 文案条目 | 过程数据 | 中英成对 |
| 历法原文 | 关联领域对象 | 只读。英文画面按第 4.4.7–4.4.11 节对照 |
| 页面资产集 | 关联领域对象 | v2-pages 已有聚合根。本模块只加语言维度 |

无聚合根，故无混合模式声明表。无子流程。

### 1.5 上下文映射

| 对方 | 关系 | 说明 |
|------|------|------|
| v2-pages 页面资产 | 上游数据、本模块附加语言 | 页面种类和分区名不变 |
| 历法数据 | 上游原文 | 先取中文专名，英文画面再查对照表 |
| web-admin 配置 | 上游错误码 | 存储与口令不变，只换提示句 |
| 旧设备 | 遵奉者 | 不带 `lang` 的请求维持今天的契约 |

说明列只描述业务关系，不写框架或库的调用方式。

## 2. 跨聚合根设计

不适用。本模块没有聚合根。页面资产集仍只在 v2-pages 文档里定义。

## 3. 应用/基础设施层设计

### 3.1 接口规范

现有端点保持 GET。不新增 POST，不用 `Result<T>`，路径不加企业三段前缀。

| 端点 | 语言规则 |
|------|----------|
| `GET /api/v1/dashboard.env` | 设备规则（第 4.2 节） |
| `GET /api/v1/dashboard.json` | 设备规则。结构不变，天气描述随语言 |
| `GET /r/<page>/<region>.png` | 设备规则。已有 `offset` 保留 |
| `GET /r/<page>/clock/<glyph>.png` | 字形与语言无关，忽略 `lang` |
| `GET /dashboard.png` | 设备规则。已有 `page` 保留 |
| `GET /weather` | 设备规则 |
| `GET /` | 先判 JSON。HTML 用网页规则 |
| `GET /admin` | 网页规则。未登录也按同一语言显示登录页 |
| `GET /admin/api/*` | 网页规则决定 `message`。鉴权失败码不变 |

设备规则不读取 Cookie 和 `Accept-Language`。网页规则见 PRD 4.4。

权限守卫：画面与首页仍是公开只读。管理端写接口仍要现有登录和 CSRF。语言 Cookie 不作为登录凭证。

用户类型：家庭用户使用设备端点；维护者使用首页和管理端。

### 3.2 依赖与约束

| 依赖方 | 依赖什么 |
|--------|----------|
| 英文启动器 | 同目录中文启动器、已安装的 `dash.sh` |
| 英文渲染 | 现有 WMO 代码表、US AQI 断点、历法原文 |
| 网页 | 现有模板。城市搜索在英文页面把上游语言设为 en |

| 被依赖方 | 说明 |
|----------|------|
| 旧设备 | 依赖「不带 lang 等于今天的中文」 |
| 管理端前端 | 依赖错误码不改名 |

约束：env 必须仍能被 busybox ash source。`lang` 的值只有 `en` 或在中文响应里不出现。资产 URL 不得含换行。

### 3.3 权限模型

不新增角色。操作矩阵：

| 操作 | 家庭用户 | 维护者 | 未登录浏览器 |
|------|----------|--------|----------------|
| 拉取中文或英文画面 | 可以 | 可以 | 可以（公开只读图） |
| 切换网页语言 | — | 可以 | 可以（首页和管理端登录页） |
| 保存配置 | 不可以 | 登录后可以 | 不可以 |

数据权限：无多租户。语言不按用户隔离。

### 3.4 公共规范

| 枚举 | 来源 | 取值 |
|------|------|------|
| `ui_lang` | enum-pool.md §3 | zh / en |

错误码沿用现有码，不新建一套。给人看的句子见 4.4。配置项：不新增。语言不是 `config.yaml` 或配置 JSON 的字段。

## 4. 详细设计

无聚合根。本节按工具的输入输出写契约，不建表。

### 4.1 领域模型

不适用数据表。标准审计字段、乐观锁、软删除、业务编码、主键均不适用。

不变量：

- INV-1 缺省请求的中文 PNG 字节与本次语言能力加入前的中文渲染一致（同一天气与历法输入下）。
- INV-2 `lang=zh` 与缺省的 PNG 字节相同，env 文本都不追加 `lang`。
- INV-3 `lang=en` 的分区 ETAG 不得等于同一分区的中文 ETAG，除非该分区本来就没有文字（时钟字形）。
- INV-4 `lang=en` 时，农历日期和干支年用第 4.4.7 节的英文；节气名只能来自第 4.4.8 节；宜忌有对照则用第 4.4.9 节，否则保留中文；物候只能来自第 4.4.10 节；节日有通行译名则用第 4.4.11 节，否则保留中文。页脚一言按第 4.4.12 节取在线或本地句子，自定义文案除外。
- INV-5 配置 JSON 不出现语言字段。会话 Cookie 的名字和校验方式不变。

### 4.2 状态模型

不适用。语言没有草稿、审批或生效状态。

### 4.3 子流程

无。

### 4.4 接口设计

#### 4.4.1 启动器与 dash.sh

| 文件 | 契约 |
|------|------|
| `kindle/documents/天气台历.sh` | 先记住调用前的 `KC_BOOK_LANG`。source `config.sh` 之后恢复该值。只有值正好是 `en` 才保留，其它值清掉。然后启动 `dash.sh`，环境变量随进程继承。整图回退时，仅保留值为 `en` 才给 `SERVER_URL` 追加 `lang=en` |
| `kindle/documents/WeatherCalendar.sh` | 导出 `KC_BOOK_LANG=en`，再 `exec` 同目录 `天气台历.sh`。文件保留，不再复制一整份拉取循环 |
| `kindle/documents/Weather Calendar.sh` | 保持现在的 `exec` 到 `天气台历.sh`，不导出 `KC_BOOK_LANG` |
| `kindle/dash.sh` | `KC_BOOK_LANG` 为 `en` 时，若 `API_URL` 与 v1 `SERVER_URL` 还没有 `lang=`，则追加 `lang=en`。其它情况不追加 |

`config.sh` 不新增语言键。KUAL 与 `refresh-once.sh` 不改，因此不声明语言，得到中文。

#### 4.4.2 env

`lang=en` 时，在现有 env 正文中增加一行：

```
lang=en
```

同时每个会再次请求的分区 URL 和整图 URL 带 `lang=en`。`REGIONS_VERSION` 必须把语言算进去。缺省与 `lang=zh` 的 env 正文不出现 `lang` 行，资产 URL 与现在相同。

#### 4.4.3 英文界面词

| 中文 | 英文 |
|------|------|
| 今日 | Today |
| 一周 | Week |
| 月历 | Month |
| 详情 | Detail |
| 黄历 | Almanac |
| 星期一至日 | Mon Tue Wed Thu Fri Sat Sun |
| 湿度 | Humidity |
| 风速 | Wind |
| 降水 | Rain |
| 休 | Off |
| 班 | Work |
| 宜 | Suitable |
| 忌 | Avoid |
| 节气 | Solar term |
| 已过 N 天 | Day N |
| 下一节气 | Next |
| 暂无数据 | No data |
| 未知（天气） | Unknown |

页眉大字日期在英文下改为 `11 Oct` 这种形式。农历行、干支、节气、物候、宜忌和节日见第 4.4.7–4.4.11 节。黄历栏题仍是 Suitable / Avoid。

#### 4.4.4 天气描述

与 `server/weather.py` 现有代码一一对应，英文采用 Open-Meteo 对同一 WMO 代码公布的短语，不另写近义词。

| 代码 | 英文 |
|------|------|
| 0 | Clear sky |
| 1 | Mainly clear |
| 2 | Partly cloudy |
| 3 | Overcast |
| 45 | Fog |
| 48 | Depositing rime fog |
| 51 | Light drizzle |
| 53 | Moderate drizzle |
| 55 | Dense drizzle |
| 56 | Light freezing drizzle |
| 57 | Dense freezing drizzle |
| 61 | Slight rain |
| 63 | Moderate rain |
| 65 | Heavy rain |
| 66 | Light freezing rain |
| 67 | Heavy freezing rain |
| 71 | Slight snow |
| 73 | Moderate snow |
| 75 | Heavy snow |
| 77 | Snow grains |
| 80 | Slight rain showers |
| 81 | Moderate rain showers |
| 82 | Violent rain showers |
| 85 | Slight snow showers |
| 86 | Heavy snow showers |
| 95 | Thunderstorm |
| 96 | Thunderstorm with slight hail |
| 99 | Thunderstorm with heavy hail |
| 其它 | Unknown |

`dashboard.json` 与 `/weather` 里的 `description` 在 `lang=en` 时用上表，缺省时仍是现在的中文。`lang=en` 时，`yi`、`ji`、农历、干支、节气、物候、节日和 `quote` 使用第 4.4.7–4.4.12 节的英文；缺对照的宜忌和没有通行译名的节日仍是中文。缺省与 `lang=zh` 这些字段保持现在的中文。

#### 4.4.5 空气质量

断点仍是 `server/aqi.py` 的 50 / 100 / 150 / 200 / 300。英文名：

| 现中文 | 英文 |
|--------|------|
| 优 | Good |
| 良 | Moderate |
| 轻度敏感 | USG |
| 中度 | Unhealthy |
| 重度 | Very Unhealthy |
| 严重 | Hazardous |

USG 是 US EPA「Unhealthy for Sensitive Groups」的既有缩写，用来放进现有 AQI 卡。不增加第七级。

#### 4.4.6 网页与校验句

`GET /` 与 `GET /admin` 按 PRD 4.4 选择文案。`Set-Cookie` 只在查询参数明确给出 `zh` 或 `en` 时更新。两页模板各只输出一个语言链接：当前为 zh 时链接文字 English、目标 `lang=en`；当前为 en 时链接文字中文、目标 `lang=zh`。样式表在文件内用 `prefers-color-scheme: dark` 覆盖颜色变量，浅色变量保持现有纸感。不新增主题接口。

预览：当前语言为 en 时，预览 URL 为 `/dashboard.png?page={page_id}&lang=en`。中文不追加 `lang`。

管理端响应体仍是现在的 JSON 形状：`error.code`、`error.message`、`error.details[].field/code/message`。下面每个中文句子都要有英文对照，码不变。

| 码 | 中文（现文案） | 英文 |
|----|----------------|------|
| ADMIN_DISABLED | 管理端未启用，请设置 ADMIN_PASSWORD | Admin is off. Set ADMIN_PASSWORD |
| ADMIN_AUTH_REQUIRED | 请先登录 | Sign in first |
| ADMIN_AUTH_INVALID | 口令错误 | Wrong password |
| ADMIN_CSRF_REJECTED | 缺少防护头 | Missing protection header |
| ADMIN_AUTH_LOCKED | 失败次数过多，请稍后再试 | Too many attempts. Try again later |
| SETTINGS_VALIDATION_FAILED | 配置校验失败 | Settings are invalid |
| SETTINGS_VALIDATION_FAILED | 配置超过 32KB | Settings are larger than 32KB |
| SETTINGS_IO_FAILED | 配置写入失败，未改动 | Could not save settings. Nothing was changed |
| SETTINGS_IMPORT_INVALID | 导入文件过大或不是受支持的配置 | Import file is too large or not a supported settings file |
| SETTINGS_IMPORT_INVALID | 导入文件不是有效的 JSON | Import file is not valid JSON |
| SETTINGS_IMPORT_INVALID | 导入文件的 schema_version 不受支持 | Import file schema_version is not supported |
| PAGES_SET_INVALID | 配置必须是对象 | Settings must be an object |
| PAGES_SET_INVALID | 请求体须为 JSON 对象 | Body must be a JSON object |
| PAGES_SET_INVALID | 页面须恰好 5 项且覆盖全部页面 | There must be exactly 5 pages covering every page |
| PAGES_SET_INVALID | 页面项格式不正确 | A page entry is invalid |
| PAGES_SET_INVALID | 启用标记须为布尔值 | Enabled must be true or false |
| PAGES_SET_INVALID | 页面须互不重复且覆盖今日、一周、月历、详情、黄历 | Pages must be unique and cover Today, Week, Month, Detail, and Almanac |
| TODAY_MUST_BE_FIRST_ENABLED | 今日页必须固定在首位且保持启用 | Today must stay first and enabled |
| DWELL_OUT_OF_RANGE | 停留秒数须为 {min}–{max} 的整数 | Dwell must be an integer from {min} to {max} |
| ROTATION_INVALID | 轮播开关须为布尔值 | Carousel switch must be true or false |
| SUPPRESS_OUT_OF_RANGE | 让位秒数须为 0–{max} 的整数 | Pause must be an integer from 0 to {max} |
| QUOTE_MODE_INVALID | 一言来源无效 | Quote source is invalid |
| QUOTE_CUSTOM_INVALID | 自定义文案须为列表 | Custom quotes must be a list |
| QUOTE_CUSTOM_INVALID | 自定义文案最多 {max} 条 | At most {max} custom quotes |
| QUOTE_CUSTOM_INVALID | 自定义模式至少需要一条文案 | Custom mode needs at least one quote |
| QUOTE_CUSTOM_INVALID | 文案项格式不正确 | A quote entry is invalid |
| QUOTE_CUSTOM_INVALID | 文案须为 1–{max} 字且不含换行 | Quote text must be 1–{max} characters and have no line break |
| QUOTE_CUSTOM_INVALID | 出处最多 {max} 字且不含换行 | Source must be at most {max} characters and have no line break |
| QUOTE_CUSTOM_INVALID | 配置体积超过 32KB | Settings are larger than 32KB |
| LOCATION_NAME_INVALID | 城市信息不完整 | City details are incomplete |
| LOCATION_NAME_INVALID | 城市名须为 1–{max} 字 | City name must be 1–{max} characters |
| LOCATION_COORD_INVALID | 纬度超出范围 / 纬度须在 -90 到 90 之间 | Latitude must be from -90 to 90 |
| LOCATION_COORD_INVALID | 经度超出范围 / 经度须在 -180 到 180 之间 | Longitude must be from -180 to 180 |
| LOCATION_TZ_INVALID | 时区无法识别 | Time zone is not recognized |
| GEOCODE_QUERY_INVALID | 查询须为 1–50 字 | Search text must be 1–50 characters |
| GEOCODE_UPSTREAM_FAILED | 搜索服务暂不可用，请手动填写 | Search is unavailable. Enter the city manually |

页面里不经过接口的句子同样要进文案表，至少包括：请填写口令、登录已过期请重新登录、请填写时区、未保存、管理端未启用、页面与轮播、城市、一言、设备状态、预览、保存、恢复默认、导出、导入、搜索、自动轮播、仅今日页、保存后天气将重新拉取、预览反映已保存配置。英文用直白句子，不新造产品名。产品名可保持 Kindle Calendar。

数字范围用现有常量填进句子，不改范围本身。

#### 4.4.7 农历日期与干支年

只在 `lang=en` 时使用。中文画面仍用现在的中文农历和干支。

农历月名来自历法库的 `getMonthInChinese()`。英文是序数，闰月在序数前加 leap。

| 中文月名 | 英文 |
|----------|------|
| 正 | 1st |
| 二 | 2nd |
| 三 | 3rd |
| 四 | 4th |
| 五 | 5th |
| 六 | 6th |
| 七 | 7th |
| 八 | 8th |
| 九 | 9th |
| 十 | 10th |
| 冬 | 11th |
| 腊 | 12th |

农历日名来自 `getDayInChinese()`，对应 1st–30th：初一到初十为 1st–10th，十一到十九为 11th–19th，二十为 20th，廿一到廿九为 21st–29th，三十为 30th。

整句：`{日序} day, {月序} lunar month`。闰月：`{日序} day, leap {月序} lunar month`。九月初二是 `2nd day, 9th lunar month`。

月历格子较窄：初一只写 `{月序} month`，闰月写 `leap {月序}`；其它日只写日序，例如 `2nd`。

干支年只翻译年柱。天干地支用无声调拼音连写，生肖用已有英文动物名。丙午马年是 `Bingwu Horse`。页眉把两段连成 `2nd day, 9th lunar month · Bingwu Horse`。

| 天干 | 拼音 | 地支 | 拼音 |
|------|------|------|------|
| 甲 | Jia | 子 | Zi |
| 乙 | Yi | 丑 | Chou |
| 丙 | Bing | 寅 | Yin |
| 丁 | Ding | 卯 | Mao |
| 戊 | Wu | 辰 | Chen |
| 己 | Ji | 巳 | Si |
| 庚 | Geng | 午 | Wu |
| 辛 | Xin | 未 | Wei |
| 壬 | Ren | 申 | Shen |
| 癸 | Gui | 酉 | You |
| | | 戌 | Xu |
| | | 亥 | Hai |

戊和午的拼音都是 Wu，靠前后位置区分，不另造拼法。六十甲子不单独列表，由这两列拼出。

#### 4.4.8 节气

24 个节气用同一套通行英文名，依据是英文维基百科 “Solar term” 条目的英文通名。不混用香港天文台的另一套（例如霜降那里作 Frost，本表作 Frost's Descent）。要换来源时整表一起换。

| 中文 | 英文 |
|------|------|
| 立春 | Start of Spring |
| 雨水 | Rain Water |
| 惊蛰 | Awakening of Insects |
| 春分 | Spring Equinox |
| 清明 | Pure Brightness |
| 谷雨 | Grain Rain |
| 立夏 | Start of Summer |
| 小满 | Grain Buds |
| 芒种 | Grain in Ear |
| 夏至 | Summer Solstice |
| 小暑 | Minor Heat |
| 大暑 | Major Heat |
| 立秋 | Start of Autumn |
| 处暑 | End of Heat |
| 白露 | White Dew |
| 秋分 | Autumn Equinox |
| 寒露 | Cold Dew |
| 霜降 | Frost's Descent |
| 立冬 | Start of Winter |
| 小雪 | Minor Snow |
| 大雪 | Major Snow |
| 冬至 | Winter Solstice |
| 小寒 | Minor Cold |
| 大寒 | Major Cold |

节气行：`Solar term {英文名} · Day {n} · Next {下一节气英文名}`。月历格里只放节气英文名。

#### 4.4.9 宜忌对照

对照覆盖历法库在 2024–2028 年会返回的全部宜忌条目，去掉从不显示的「无」。英文是字面短词，供黄历栏使用，不是另一套黄历术语。表里没有的条目留中文，不临场编。一栏最多仍显示 6 条。

| 中文 | 英文 |
|------|------|
| 上梁 | Raise the beam |
| 乘船 | Board a boat |
| 习艺 | Learn a craft |
| 交易 | Trade |
| 伐木 | Fell timber |
| 会亲友 | Visit family |
| 作梁 | Make a beam |
| 作灶 | Build a stove |
| 修坟 | Repair a grave |
| 修造 | Build or repair |
| 修门 | Repair a door |
| 修饰垣墙 | Mend walls |
| 入学 | Start school |
| 入宅 | Move in |
| 入殓 | Encoffin |
| 冠笄 | Coming of age |
| 出火 | Move the hearth |
| 出行 | Travel |
| 出货财 | Send goods out |
| 分居 | Live apart |
| 割蜜 | Collect honey |
| 动土 | Break ground |
| 取渔 | Fish |
| 合寿木 | Assemble a coffin |
| 合帐 | Make bed curtains |
| 合脊 | Join the roof ridge |
| 启钻 | Open a tomb |
| 坏垣 | Break a wall |
| 塑绘 | Paint and model |
| 塞穴 | Plug holes |
| 嫁娶 | Marry |
| 安床 | Set the bed |
| 安机械 | Install machinery |
| 安碓磑 | Set a grain mill |
| 安葬 | Hold a burial |
| 安门 | Set a door |
| 安香 | Install incense |
| 定磉 | Set the plinth |
| 平治道涂 | Level the road |
| 开仓 | Open the granary |
| 开光 | Consecrate |
| 开厕 | Build a latrine |
| 开市 | Open shop |
| 开柱眼 | Cut mortises |
| 开池 | Dig a pond |
| 开渠 | Dig a ditch |
| 开生坟 | Dig a new grave |
| 归宁 | Visit parents |
| 归岫 | Return to the hills |
| 成服 | Start mourning dress |
| 扫舍 | Sweep the house |
| 拆卸 | Dismantle |
| 挂匾 | Hang a sign |
| 捕捉 | Trap game |
| 掘井 | Dig a well |
| 探病 | Visit the sick |
| 放水 | Release water |
| 教牛马 | Train livestock |
| 整手足甲 | Trim nails |
| 斋醮 | Hold a rite |
| 断蚁 | Stop ants |
| 普渡 | Hold a deliverance rite |
| 架马 | Set a frame |
| 栽种 | Plant |
| 求医 | See a doctor |
| 求嗣 | Pray for a child |
| 沐浴 | Bathe |
| 治病 | Treat illness |
| 牧养 | Raise animals |
| 理发 | Cut hair |
| 畋猎 | Hunt |
| 盖屋 | Raise a roof |
| 破土 | Break burial ground |
| 破屋 | Demolish a house |
| 祈福 | Pray for blessings |
| 祭祀 | Worship |
| 移徙 | Move house |
| 移柩 | Move the coffin |
| 立券 | Sign a contract |
| 立碑 | Set a stele |
| 竖柱 | Raise pillars |
| 筑堤 | Build a dyke |
| 纳婿 | Take a son-in-law |
| 纳畜 | Take in livestock |
| 纳财 | Take in wealth |
| 纳采 | Send betrothal gifts |
| 经络 | Treat meridians |
| 结网 | Make nets |
| 置产 | Acquire property |
| 行丧 | Hold a funeral |
| 补垣 | Mend a wall |
| 裁衣 | Cut out clothes |
| 解除 | Lift a taboo |
| 订盟 | Pledge marriage |
| 词讼 | Go to law |
| 诸事不宜 | Nothing is suitable |
| 谢土 | Thank the soil |
| 赴任 | Take up a post |
| 起基 | Lay the foundation |
| 进人口 | Add to the household |
| 造仓 | Build a storehouse |
| 造庙 | Build a shrine |
| 造桥 | Build a bridge |
| 造畜稠 | Build a pen |
| 造船 | Build a boat |
| 造车器 | Make vehicles |
| 酬神 | Thank the gods |
| 针灸 | Acupuncture |
| 问名 | Ask the name |
| 除服 | End mourning |
| 雇佣 | Hire help |
| 雕刻 | Carve |
| 馀事勿取 | Do nothing else |

#### 4.4.10 物候意译

72 候用历法库 `getWuHou()` 的原文。英文是简短意译，保留原文里的形象，不改写成现代物候学名称。没有单独的国家标准英译。表外物候留中文。

| 中文 | 英文 |
|------|------|
| 东风解冻 | East wind thaws the ice |
| 蛰虫始振 | Hibernating insects stir |
| 鱼陟负冰 | Fish rise under the ice |
| 獭祭鱼 | Otters set out fish |
| 候雁北 | Wild geese fly north |
| 草木萌动 | Plants begin to sprout |
| 桃始华 | Peach trees bloom |
| 仓庚鸣 | Orioles sing |
| 鹰化为鸠 | Hawks become doves |
| 玄鸟至 | Swallows arrive |
| 雷乃发声 | Thunder sounds |
| 始电 | Lightning begins |
| 桐始华 | Paulownia blooms |
| 田鼠化为鴽 | Moles become quails |
| 虹始见 | Rainbows appear |
| 萍始生 | Duckweed appears |
| 鸣鸠拂其羽 | Doves preen their feathers |
| 戴胜降于桑 | Hoopoes settle on mulberries |
| 蝼蝈鸣 | Frogs begin to croak |
| 蚯蚓出 | Earthworms come out |
| 王瓜生 | Snake gourds sprout |
| 苦菜秀 | Bitter herbs flower |
| 靡草死 | Tender grasses die back |
| 麦秋至 | Wheat ripens |
| 螳螂生 | Mantises hatch |
| 鵙始鸣 | Shrikes begin to call |
| 反舌无声 | Mimic birds fall silent |
| 鹿角解 | Deer shed their antlers |
| 蜩始鸣 | Cicadas begin to sing |
| 半夏生 | Pinellia sprouts |
| 温风至 | Warm winds arrive |
| 蟋蟀居壁 | Crickets keep to the walls |
| 鹰始挚 | Hawks begin to hunt |
| 腐草为萤 | Rotting grass becomes fireflies |
| 土润溽暑 | Soil turns damp and hot |
| 大雨行时 | Heavy rains set in |
| 凉风至 | Cool winds arrive |
| 白露降 | White dew settles |
| 寒蝉鸣 | Cicadas call in the cool |
| 鹰乃祭鸟 | Hawks set out birds |
| 天地始肃 | Heaven and earth grow stern |
| 禾乃登 | Grain comes in |
| 鸿雁来 | Wild geese arrive |
| 玄鸟归 | Swallows depart |
| 群鸟养羞 | Birds store up food |
| 雷始收声 | Thunder dies away |
| 蛰虫坯户 | Insects seal their burrows |
| 水始涸 | Waters begin to dry |
| 鸿雁来宾 | Wild geese arrive as guests |
| 雀入大水为蛤 | Sparrows enter the water as clams |
| 菊有黄花 | Chrysanthemums turn yellow |
| 豺乃祭兽 | Wolves set out their prey |
| 草木黄落 | Plants yellow and fall |
| 蛰虫咸俯 | Insects all lie low |
| 水始冰 | Water begins to freeze |
| 地始冻 | The ground begins to freeze |
| 雉入大水为蜃 | Pheasants enter the water as clams |
| 虹藏不见 | Rainbows stay hidden |
| 天气上升地气下降 | Sky qi rises and earth qi sinks |
| 闭塞而成冬 | The season closes into winter |
| 鹖鴠不鸣 | Crossbills stay silent |
| 虎始交 | Tigers begin to mate |
| 荔挺出 | Lycoris begins to sprout |
| 蚯蚓结 | Earthworms curl up |
| 麋角解 | Elk shed their antlers |
| 水泉动 | Springs begin to stir |
| 雁北乡 | Geese turn toward home |
| 鹊始巢 | Magpies start a nest |
| 雉始雊 | Pheasants begin to call |
| 鸡始乳 | Hens begin to lay |
| 征鸟厉疾 | Birds of prey fly hard and fast |
| 水泽腹坚 | Ice thickens through the marshes |

物候行：`Phenology {英文}`。

#### 4.4.11 节日名

历法库节日和节假日数据里的名称都走这一张表。有通行英文名的用英文。没有通行英文名的不编，画面留中文。节假日数据里的「元旦」「清明节」与历法库的「元旦节」不是同一个字符串，都要列入。

万圣节前夜在历法库里落在 10 月 31 日，画面用 Halloween。万圣节落在 11 月 1 日，画面用 All Saints' Day。

| 中文 | 英文 | 取舍 |
|------|------|------|
| 元旦 | New Year's Day | 用英文 |
| 元旦节 | New Year's Day | 用英文 |
| 腊八节 | Laba Festival | 用英文 |
| 情人节 | Valentine's Day | 用英文 |
| 除夕 | Chinese New Year's Eve | 用英文 |
| 春节 | Spring Festival | 用英文 |
| 元宵节 | Lantern Festival | 用英文 |
| 妇女节 | Women's Day | 用英文。全称是 International Women's Day |
| 植树节 | Arbor Day | 用英文 |
| 消费者权益日 | Consumer Rights Day | 用英文。全称是 World Consumer Rights Day |
| 龙头节 | 留中文 | 英译不统一，不新造 |
| 全国中小学生安全教育日 | 留中文 | 无通行短译名 |
| 愚人节 | April Fools' Day | 用英文 |
| 劳动节 | Labour Day | 用英文 |
| 青年节 | Youth Day | 用英文 |
| 母亲节 | Mother's Day | 用英文 |
| 全国助残日 | 留中文 | 无通行短译名 |
| 儿童节 | Children's Day | 用英文 |
| 端午节 | Dragon Boat Festival | 用英文 |
| 父亲节 | Father's Day | 用英文 |
| 建党节 | CPC Founding Day | 用英文 |
| 建军节 | Army Day | 用英文 |
| 七夕节 | Qixi Festival | 用英文 |
| 教师节 | Teachers' Day | 用英文 |
| 全民国防教育日 | 留中文 | 无通行短译名 |
| 中秋节 | Mid-Autumn Festival | 用英文 |
| 国庆节 | National Day | 用英文 |
| 世界住房日 | World Habitat Day | 用英文。联合国惯用名 |
| 重阳节 | Double Ninth Festival | 用英文 |
| 万圣节前夜 | Halloween | 用英文。日期是 10 月 31 日 |
| 万圣节 | All Saints' Day | 用英文。日期是 11 月 1 日 |
| 感恩节 | Thanksgiving | 用英文 |
| 平安夜 | Christmas Eve | 用英文 |
| 圣诞节 | Christmas | 用英文 |
| 清明节 | Qingming Festival | 用英文。节假日数据用这个名字；节气「清明」仍走第 4.4.8 节 |

页眉节日行在英文下是 `{英文或原文} Off` 或 `{英文或原文} Work`。没有班休标记时只显示名称。

#### 4.4.12 英文一言

`lang=en` 且来源是在线时，不请求中文一言接口。改为请求固定地址 `https://zenquotes.io/api/today`（只允许 https、主机 `zenquotes.io`、禁止重定向、超时 8 秒）。用返回的 `q` 作正文、`a` 作出处。按台历时区的日期缓存，同一天不重复请求。不用 `random`，避免同日之内换句。

句子放进现有页脚，字号可以缩到 16px。缩到最小仍超出页脚宽度，或接口失败、超时、空正文，则改用下面的本地句子，按年内第几天轮换。这些句子是公有领域短句。

| 正文 | 出处 |
|------|------|
| To be, or not to be. | Shakespeare |
| All the world's a stage. | Shakespeare |
| Parting is such sweet sorrow. | Shakespeare |
| I wandered lonely as a cloud. | Wordsworth |
| The child is father of the man. | Wordsworth |
| If Winter comes, can Spring be far behind? | Shelley |
| A thing of beauty is a joy for ever. | Keats |
| Beauty is truth, truth beauty. | Keats |
| Tyger, tyger, burning bright. | Blake |
| Hope is the thing with feathers. | Dickinson |
| I celebrate myself. | Whitman |
| I am the master of my fate. | Henley |

来源是离线时，英文画面直接用这张表，不请求接口。自定义来源仍显示用户保存的正文和出处。中文画面的在线、离线和自定义行为不变。

ZenQuotes 免费接口要求链回其网站。Kindle 画面只能印作者名，放不下可点击链接，所以链接写在 README，不写进页脚图。

### 4.5 领域事件与集成

无领域事件，无消息队列。城市搜索仍是现有地理编码调用，只是英文页面多传一个语言偏好。历法与天气代码表都在本进程内。

仓储契约：无。不新增文件格式。配置文件读写与现在相同。

## 5. 模块清单汇总

无新表，无 DDL，无对外 CRUD 服务。对外行为就是第 4 节对现有 GET 的语言维度，以及启动器声明。

SQL 清单：无。

## 6. 更新记录

变更类型词汇：`initial` 首次生成；`structural` 章节重组；`interface_changed` 接口行为变化；`rule_added` 新增规则；`enum_added` 新增枚举。

| 版本 | 日期 | 变更类型 | 章节 | 说明 |
|------|------|----------|------|------|
| v1.2 | 2026-10-11 | rule_added | 4.4.7–4.4.12 | 方案丁对照表、农历干支、英文一言、单按钮与系统深色 |
| v1.3 | 2026-10-11 | rule_changed | 4.4.12 | 英文一言改为 ZenQuotes 当日一句，失败再用本地公有领域短句 |
| v1.2 | 2026-10-11 | interface_changed | 4.1、4.4.4 | `lang=en` 的历法字段和 quote 改为英文；缺省中文不变 |
| v1.1 | 2026-10-10 | structural | 1–4 | 推翻 v1.0 的窄范围，改为画面语言 + 网页 Cookie |
| v1.1 | 2026-10-10 | interface_changed | 4.2、4.4 | 现有 GET 增加可选 `lang`；缺省保持中文契约 |
| v1.1 | 2026-10-10 | rule_added | 4.3–4.6 | 界面词、WMO 英文、AQI 英文、历法降级、校验句 |
| v1.1 | 2026-10-10 | enum_added | 3.4 | `ui_lang` 写入 enum-pool.md §3 |
| v1.0 | 2026-10-10 | initial | — | 已作废。只覆盖落地页，且要求删除无空格启动器 |

相对 v2-pages / web-admin：不删除它们的端点，不改 `page_id`、轮播字段和登录流程。只在读图和错误句子上增加语言。
