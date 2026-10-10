# API / 契约设计：en-locale（双语画面与网页语言）

| 属性 | 值 |
|------|-----|
| 模块 | en-locale |
| 版本 | v1.1 |
| 状态 | 稳定 |
| 最后更新 | 2026-10-10 |
| 输入 | prd-en-locale.md v1.1 |
| 技术规约 | 无激活技术栈。沿用现有 GET 与 Flask 内嵌页，不引入企业 POST 三段路径、Result 包装或数据表 |

本版替换作废的 v1.0。v1.0 要求删除 `WeatherCalendar.sh`、不翻译画面和管理端。

## 1. 模块设计概述

### 1.1 业务背景及目标

解决开源之后海外使用者看不懂中文画面和中文网站的问题。家庭用户从书库启动英文画面，维护者在首页和管理端切换语言。价值是同一套台历可以中文或英文阅读，旧的中文设备不用改脚本也保持原样。

### 1.2 边界说明

| 边界 | 说明 |
|------|------|
| 做 | 启动器语言声明、`lang` 查询参数、英文界面词渲染、历法降级、网页 Cookie、校验句子随语言变化 |
| 不做 | 新表、新鉴权、改配置 JSON、改轮播云端优先、翻译一言和历法专名、把 KUAL 改成英文、用 CDN |

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

### 1.4 领域对象总览

| 对象 | 角色 | 说明 |
|------|------|------|
| 界面语言 | 过程数据 | `zh` 或 `en`，不入库 |
| 文案条目 | 过程数据 | 中英成对 |
| 历法原文 | 关联领域对象 | 只读，专名不翻译 |
| 页面资产集 | 关联领域对象 | v2-pages 已有聚合根。本模块只加语言维度 |

无聚合根，故无混合模式声明表。无子流程。

### 1.5 上下文映射

| 对方 | 关系 | 说明 |
|------|------|------|
| v2-pages 页面资产 | 上游数据、本模块附加语言 | 页面种类和分区名不变 |
| 历法数据 | 上游原文 | 专名原样使用 |
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
- INV-4 宜忌条目、节气名、干支、节日名在英文图中仍是中文原文。
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

页眉大字日期在英文下改为 `10 Oct` 这种形式。农历行是 `Lunar` 加中文农历。节气行是 `Solar term {中文名} · Day {n} · Next {中文名}`。物候行是 `Phenology` 加中文物候。宜忌栏题用 Suitable / Avoid，条目不译。

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

`dashboard.json` 与 `/weather` 里的 `description` 在 `lang=en` 时用上表，缺省时仍是现在的中文。`yi`、`ji`、农历、节气字段两种语言都保持中文。

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

`GET /` 与 `GET /admin` 按 PRD 4.4 选择文案。`Set-Cookie` 只在查询参数明确给出 `zh` 或 `en` 时更新。

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
| v1.1 | 2026-10-10 | structural | 1–4 | 推翻 v1.0 的窄范围，改为画面语言 + 网页 Cookie |
| v1.1 | 2026-10-10 | interface_changed | 4.2、4.4 | 现有 GET 增加可选 `lang`；缺省保持中文契约 |
| v1.1 | 2026-10-10 | rule_added | 4.3–4.6 | 界面词、WMO 英文、AQI 英文、历法降级、校验句 |
| v1.1 | 2026-10-10 | enum_added | 3.4 | `ui_lang` 写入 enum-pool.md §3 |
| v1.0 | 2026-10-10 | initial | — | 已作废。只覆盖落地页，且要求删除无空格启动器 |

相对 v2-pages / web-admin：不删除它们的端点，不改 `page_id`、轮播字段和登录流程。只在读图和错误句子上增加语言。
