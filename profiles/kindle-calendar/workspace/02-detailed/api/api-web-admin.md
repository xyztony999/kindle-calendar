# API / 契约设计：web-admin（Web 管理端）

| 属性 | 值 |
|------|-----|
| 模块 | web-admin |
| 版本 | v1.0 |
| 状态 | 待评审 |
| 最后更新 | 2026-10-10 |
| 输入 | prd-web-admin.md v1.0 + 领域模型（本文 1.4） |
| 技术规约 | 无激活技术栈；HTTP/JSON/POSIX env 契约按本模块通用规约（3.1）；栈特定项（Result\<T\>/三级路径/DDL）标注 N/A |
| 功能类型 | 主数据类（单例配置聚合根） |

## 1. 模块设计概述

### 1.1 业务背景及目标

维护者（用户角色）需要不触碰设备与配置文件即可决定台历显示哪些页、为哪座城市、以什么节奏轮播、页脚一言取自何处（业务问题），并知道配置是否已到达设备（业务价值：配置可达、可见、可恢复）。本模块定义三类契约：管理端 HTTP/JSON 接口、配置文件结构、设备 env 契约扩展与 dash.sh 行为变更。

### 1.2 边界说明

| 边界 | 说明 |
|------|------|
| 做 | 管理员登录/会话；配置读写/校验/原子持久化/版本；Geocoding 代理；设备心跳采集与状态；导入导出/恢复默认；env/json 载荷扩展；dash.sh 轮播与页序读取规则 |
| 不做 | 多城市；分区级/像素级布局；设备本地参数（INTERVAL/CLOCK_ENABLED/TOUCH_*/WIFI_*）云端化；配置变更历史；多用户角色；渲染算法 |

### 1.3 设计决策

| # | 决策 | 理由 |
|---|------|------|
| AD-0 | 混合模式声明：**自管单源**——配置仅由管理端写入，无外部系统托管同步，故不设 manage_mode、不设同步日志 | 引擎混合模式面向有外部同步源的主数据；本聚合根唯一写入方是维护者 |
| AD-1 | 单例聚合根 `CalendarSettings`，整体读/整体写（无局部 PATCH） | 字段间有跨项不变量（页序与停留一一对应）；整体原子替换最简单且无半更新 |
| AD-2 | 持久化为 JSON 文件（`SETTINGS_PATH`），tmp+rename 原子写 | 零新增依赖；Docker 挂卷即持久；Render 无盘回退默认值 |
| AD-3 | 配置版本 = 规范化 JSON 内容哈希前 12 位，而非自增号 | 无数据库仍可比对「设备已下发 vs 当前」；导入相同内容版本不变 |
| AD-4 | 云端优先：env 覆盖设备本地；删除 dash.sh `LOCAL_ROTATE_*` 恢复逻辑 | D0 决策；消除两处配置源 |
| AD-5 | env 新增 `ROTATE_ENABLED`/`ROTATE_{PAGE}_S`/`SETTINGS_VERSION`，保留 `ROTATE_TODAY_S`/`ROTATE_OTHER_S` | BR-8 旧脚本兼容 |
| AD-6 | 心跳 = env 拉取，服务端被动记录，进程内保存 | 设备端零改动；重启丢失可接受（状态 unknown） |
| AD-7 | 鉴权：口令 + Flask 签名 Cookie；写接口要求 `X-Requested-With` 头 + `SameSite=Strict` | 单管理员、零依赖；CSRF 双重防护 |
| AD-8 | 预览复用 `/dashboard.png?page=`，不新增渲染端点 | 已有整页合成；草稿预览不在范围（O-2） |
| AD-9 | 配置纳入载荷：`payload.settings_version`、`payload.pages`（已启用页序）、`payload.location`、一言取法；`data_fingerprint` 自动覆盖 | 复用既有指纹 → 分区缓存与设备重拉链路无需新机制 |

### 1.4 领域对象总览（D2-2 结果）

**PRD 范围判定**：模块名已标注 → 跳过战略设计，直接战术设计。

| 对象 | 分类 | 说明 |
|------|------|------|
| 台历配置 CalendarSettings | **聚合根**（单例） | 一致性边界：页面集 × 轮播 × 一言 × 城市 整体保存；外部（渲染/载荷/env）只经它读取 |
| 页面项 PageSetting | 值对象 | `{page_id, enabled, dwell_s}` 有序列表，位置即页序；无独立身份 |
| 轮播计划 RotationPlan | 值对象 | `{enabled, suppress_s}`（每页停留在 PageSetting 内） |
| 一言来源 QuoteSource | 值对象 | `{mode, custom[]}`，custom 项 `{text, from}` |
| 城市 Location | 值对象 | `{name, latitude, longitude, timezone}` |
| 配置版本 SettingsVersion | 值对象 | 内容哈希，派生 |
| 管理员会话 AdminSession | 过程数据(P6) | 签名 Cookie，框架托管 |
| 登录限速计数 | 过程数据(P7) | 来源地址 → 失败次数/锁定至 |
| 设备心跳 DeviceHeartbeat | 过程数据(P2，进程内) | 最近两次 env 拉取记录；派生在线/下发状态 |
| 地点候选 GeocodeCandidate | 过程数据(P4) | 搜索响应载体，不持久化 |
| 下发状态 DeliveryState | 过程数据(P2) | pending / delivered / unknown，由版本比对派生 |

子流程：无（无审批、无多轮）。关联领域对象：无（天气/渲染等均为本系统支撑域，经进程内调用）。

**聚合根识别（A1–A4）**：A1 一致性边界 ✓（页序与停留成对、custom 与 mode 成对）；A2 全局引用 ✓（载荷/渲染/env 引用）；A3 生命周期入口 ✓（所有子项只随整体保存）；A4 规则驱动 ✓（变更驱动缓存失效与重渲染）→ 4/4 聚合根。

### 1.5 上下文映射

| 对方 | 关系 | 说明 |
|------|------|------|
| 数据聚合 S-01 | 下游（本模块 → 其） | 载荷组装读取配置；城市变更触发天气缓存失效 |
| 页面渲染 S-02 | 下游 | 渲染读取已启用页；预览消费整页合成 |
| 缓存协商 S-03 | 下游 | 配置纳入指纹 |
| 页面导航 C-06（设备端） | 下游（经 env） | 页序与轮播参数 |
| Open-Meteo Geocoding | 上游外部（防腐：仅取六字段，字段名本地化） | 城市搜索 |
| v2.1 旧 dash.sh | 遵奉者 | 既有 env 变量不变 |

## 2. 跨聚合根设计

不适用（单聚合根模块）。

## 3. 应用/基础设施层设计

### 3.1 接口规范

| 项 | 规约 |
|----|------|
| 基础路径 | 管理端 `/admin`（HTML）与 `/admin/api/*`（JSON） |
| HTTP 方法 | 读 GET、写 POST（无 PUT/PATCH/DELETE，便于 CSRF 头统一） |
| 响应格式 | JSON：成功 `{"ok": true, "data": …}`；失败 `{"ok": false, "error": {"code": "…", "message": "…", "details": […]}}`（Result\<T\> 栈规约 N/A，以此为本模块统一包装） |
| 鉴权 | 除 `POST /admin/api/login` 与 `GET /admin` 登录态判定外，`/admin/api/*` 均需会话；未登录 → 401 `ADMIN_AUTH_REQUIRED`；管理端未启用 → 503 `ADMIN_DISABLED` |
| CSRF | 写请求须带 `X-Requested-With: kindle-admin`，缺失 → 403 `ADMIN_CSRF_REJECTED` |
| 校验 | 整体校验，`details` 为 `[{field, code, message}]` 列表 |
| env 契约 | POSIX 可 source，变量名大写下划线，值无换行 |
| 用户类型标注 | 本模块全部接口用户类型 = 维护者；设备消费的 env 为系统契约 |

### 3.2 依赖与约束

- 依赖：`DashboardService`（载荷/渲染/缓存失效）、`requests`（Geocoding）、Flask `session`、`zoneinfo`；
- 约束：零新增 Python 依赖；`settings.json` 读写经单一 `SettingsStore` 入口（线程锁）；配置变更后 `DashboardService` 必须收到通知（进程内回调）。

### 3.3 权限模型

| 角色 | 定义 | 可执行 |
|------|------|--------|
| admin（维护者） | 持有 `ADMIN_PASSWORD` 并登录成功 | 本模块全部接口 |
| anonymous | 未登录 | `GET /admin`（返回登录视图）、`POST /admin/api/login` |
| device | Kindle 客户端 | 既有公开端点（env/json/png），不受本模块鉴权影响 |

数据权限：单租户单配置，无行级规则。

### 3.4 公共规范

**枚举引用**（来源：`workspace/01-solution/common-spec/enum-pool.md` §1 web-admin）：

| 枚举 | 取值 | 用于 |
|------|------|------|
| `page_id` | today / week / month / detail / almanac | PageSetting.page_id、env PAGES |
| `quote_mode` | online / offline / custom | QuoteSource.mode |
| `delivery_state` | pending / delivered / unknown | 设备状态 |
| `online_state` | online / offline / unknown | 设备状态 |

**错误码**：

| 代码 | HTTP | 含义 |
|------|------|------|
| `ADMIN_DISABLED` | 503 | 未设置 ADMIN_PASSWORD |
| `ADMIN_AUTH_REQUIRED` | 401 | 未登录 |
| `ADMIN_AUTH_INVALID` | 401 | 口令错误 |
| `ADMIN_AUTH_LOCKED` | 429 | 失败次数超限锁定（`details[0].retry_after_s`） |
| `ADMIN_CSRF_REJECTED` | 403 | 缺少防护头 |
| `SETTINGS_VALIDATION_FAILED` | 400 | 配置校验失败（`details` 逐字段） |
| `SETTINGS_IO_FAILED` | 500 | 文件写入失败（配置未改动） |
| `SETTINGS_IMPORT_INVALID` | 400 | 导入文件非 JSON / schema_version 不支持 |
| `GEOCODE_QUERY_INVALID` | 400 | 查询串为空或 > 50 字 |
| `GEOCODE_UPSTREAM_FAILED` | 502 | Geocoding 上游失败/超时 |

**配置项（环境变量）**：

| 变量 | 默认 | 说明 |
|------|------|------|
| `ADMIN_PASSWORD` | 空（管理端禁用） | 管理员口令 |
| `SECRET_KEY` | 进程随机 | 会话签名密钥 |
| `SETTINGS_PATH` | `data/settings.json` | 配置文件路径 |
| `ADMIN_SESSION_DAYS` | 7 | 会话有效期 |
| `ADMIN_LOCK_THRESHOLD` / `ADMIN_LOCK_SECONDS` | 5 / 900 | 登录限速 |

## 4. 聚合根详细设计：台历配置 CalendarSettings

### 4.1 领域模型

**存储**：无数据库；单文件 `settings.json`（schema_version 1）。主键/审计/软删/DDL 等栈特定项 N/A。

```json
{
  "schema_version": 1,
  "pages": [
    {"page_id": "today",   "enabled": true,  "dwell_s": 120},
    {"page_id": "week",    "enabled": true,  "dwell_s": 30},
    {"page_id": "month",   "enabled": true,  "dwell_s": 30},
    {"page_id": "detail",  "enabled": true,  "dwell_s": 30},
    {"page_id": "almanac", "enabled": true,  "dwell_s": 30}
  ],
  "rotation": {"enabled": true, "suppress_s": 120},
  "quote": {"mode": "online", "custom": []},
  "location": {"name": "北京", "latitude": 39.9042, "longitude": 116.4074, "timezone": "Asia/Shanghai"},
  "updated_at": "2026-10-10T15:30:00+08:00"
}
```

**字段表**：

| 对象.字段 | 类型 | 必填 | 约束 | 默认来源 |
|----------|------|------|------|---------|
| schema_version | int | 是 | = 1 | 常量 |
| pages[] | array | 是 | 恰好 5 项，page_id 互异且覆盖全部五页；位置即页序 | `PAGES` 常量顺序 |
| pages[].page_id | enum page_id | 是 | — | — |
| pages[].enabled | bool | 是 | today 必为 true | true |
| pages[].dwell_s | int | 是 | 5–3600 | today 120，其余 30 |
| rotation.enabled | bool | 是 | — | true |
| rotation.suppress_s | int | 是 | 0–3600 | 120 |
| quote.mode | enum quote_mode | 是 | — | online |
| quote.custom[] | array | 是 | 0–100 项；mode=custom 时 ≥ 1 | [] |
| quote.custom[].text | string | 是 | 1–32 字，去首尾空白，无换行 | — |
| quote.custom[].from | string | 否 | 0–16 字 | "" |
| location.name | string | 是 | 1–20 字 | config.location_name |
| location.latitude | number | 是 | -90~90 | config.latitude |
| location.longitude | number | 是 | -180~180 | config.longitude |
| location.timezone | string | 是 | `zoneinfo.ZoneInfo(tz)` 可构造 | config.timezone |
| updated_at | ISO datetime | 服务端写 | — | 保存时刻 |

**不变量**：

- INV-1 `pages[0].page_id == "today"` 且 `enabled == true`；
- INV-2 `pages` 的 page_id 集合 == {today, week, month, detail, almanac}；
- INV-3 `quote.mode == custom ⇒ len(quote.custom) ≥ 1`；
- INV-4 `settings_version = sha256(canonical_json(settings 去 updated_at))[:12]`；相同内容必同版本；
- INV-5 保存要么全部成功（文件替换 + 版本更新 + 通知下游），要么文件不变；
- INV-6 env 中 `PAGES` 恰为 enabled 页按 pages 顺序；`ROTATE_{PAGE}_S` 仅对 enabled 页下发。

**领域服务**：

| 服务 | 职责 |
|------|------|
| `SettingsStore.load()` | 读文件；缺失/损坏 → 返回部署默认值并置 `degraded=true` |
| `SettingsStore.save(settings)` | 校验 → 规范化 → tmp 写 → rename → 计算版本 → 触发 `on_change(old, new)` |
| `SettingsValidator.validate(dict) -> details[]` | 全部字段校验，收集而非短路 |
| `defaults_from_config(config)` | 由 `load_config()` 结果推导默认配置 |
| `DashboardService.apply_settings(new, location_changed)` | 更新 config 中城市四项；若 location_changed → 清空天气缓存并同步重拉（超时 8s，失败保留旧数据）；无条件清空 `_regions`/`_month_offset_cache` |

**业务常量**：

| 常量 | 值 |
|------|-----|
| DWELL_MIN / DWELL_MAX | 5 / 3600 |
| SUPPRESS_MAX | 3600 |
| CUSTOM_MAX / TEXT_MAX / FROM_MAX | 100 / 32 / 16 |
| GEOCODE_TIMEOUT_S / GEOCODE_COUNT | 6 / 10 |
| HEARTBEAT_ONLINE_FACTOR | 2（× 拉取间隔估计） |
| DEFAULT_INTERVAL_S | 900 |

标签池：本聚合根无标签池。

### 4.2 状态模型

配置本身无流程状态机（主数据类）。派生的**下发状态**：

```
unknown ──(收到任一心跳)──▶ delivered(心跳版本 == 当前) / pending(≠)
pending ──(心跳版本 == 当前)──▶ delivered
delivered ──(保存产生新版本)──▶ pending
任意 ──(进程重启)──▶ unknown
```

状态历史：不需要（无审计要求）。驳回/撤回：不适用。

### 4.3 子流程设计

无子流程。

### 4.4 接口设计

#### 4.4.1 接口清单

**管理接口（维护者）**

| # | 端点 | 方法 | 鉴权 | 说明 |
|---|------|------|------|------|
| A-1 | `/admin` | GET | 否（视图按登录态切换） | 管理端 HTML（登录视图 / 设置视图 / 禁用提示） |
| A-2 | `/admin/api/login` | POST | 否 | 口令登录 |
| A-3 | `/admin/api/logout` | POST | 是 | 退出 |
| A-4 | `/admin/api/settings` | GET | 是 | 读取当前配置 + 版本 + degraded + 默认值 |
| A-5 | `/admin/api/settings/save` | POST | 是 | 整体保存 |
| A-6 | `/admin/api/settings/reset` | POST | 是 | 恢复默认（等同保存默认值） |
| A-7 | `/admin/api/settings/export` | GET | 是 | 下载 JSON |
| A-8 | `/admin/api/settings/import` | POST | 是 | 上传 JSON（multipart 或 raw JSON）并保存 |
| A-9 | `/admin/api/geocode` | GET | 是 | 城市搜索代理 |
| A-10 | `/admin/api/device` | GET | 是 | 设备心跳与下发状态 |

**系统契约（设备消费）**

| # | 契约 | 变更 |
|---|------|------|
| E-1 | `GET /api/v1/dashboard.env` | 扩展：PAGES 按配置、ROTATE_ENABLED、ROTATE_{PAGE}_S、ROTATE_SUPPRESS_S、SETTINGS_VERSION；响应时记录心跳 |
| E-2 | `GET /api/v1/dashboard.json` | 扩展：`pages` 为已启用页序、新增 `settings_version` |
| E-3 | dash.sh 行为契约 | 轮播按页读取、一圈终点为 PAGES 末项、删除本地覆盖 |
| F-1 | `settings.json` 文件契约 | 新增（4.1 结构） |

动作接口（前端 Action 映射）见交互设计文档 §2；无独立端点。

#### 4.4.2 接口详情

**A-2 `POST /admin/api/login`**

| 请求 | 类型 | 必填 | 说明 |
|------|------|------|------|
| password | string | 是 | 明文口令（HTTPS 传输） |

响应 `data`: `{"expires_at": ISO}`。规则：常量时间比较；失败计数按来源地址；超阈值 → 429 `ADMIN_AUTH_LOCKED`；成功清零计数并 `session.permanent=True`。

**A-4 `GET /admin/api/settings`**

响应 `data`:

| 字段 | 类型 | 说明 |
|------|------|------|
| settings | object | 4.1 结构 |
| settings_version | string(12) | 当前版本 |
| degraded | bool | 文件缺失/损坏，当前为默认值运行 |
| defaults | object | 部署默认值（供「恢复默认」前端对比提示） |
| limits | object | `{dwell_min, dwell_max, suppress_max, custom_max, text_max, from_max}` 供前端校验 |

**A-5 `POST /admin/api/settings/save`**

请求体：完整 `settings`（不含 `updated_at`、`schema_version` 可省略）。

校验规则（全部收集后返回）：

| 字段 | 规则 | 错误 code |
|------|------|-----------|
| pages | 5 项、page_id 互异且全覆盖 | `PAGES_SET_INVALID` |
| pages[0] | today 且 enabled | `TODAY_MUST_BE_FIRST_ENABLED` |
| pages[].dwell_s | 整数 5–3600 | `DWELL_OUT_OF_RANGE` |
| rotation.suppress_s | 整数 0–3600 | `SUPPRESS_OUT_OF_RANGE` |
| quote.mode | 枚举 | `QUOTE_MODE_INVALID` |
| quote.custom | ≤100；mode=custom 时 ≥1；text 1–32 无换行；from ≤16 | `QUOTE_CUSTOM_INVALID` |
| location.name | 1–20 字 | `LOCATION_NAME_INVALID` |
| location.latitude/longitude | 数值范围 | `LOCATION_COORD_INVALID` |
| location.timezone | zoneinfo 可识别 | `LOCATION_TZ_INVALID` |

处理步骤：校验 → 规范化（去空白、整数化）→ 写 tmp → rename → 计算版本 → `apply_settings` → 响应。

响应 `data`: `{"settings": …, "settings_version": "…", "location_changed": bool, "weather_refreshed": bool}`。

**A-6 `POST /admin/api/settings/reset`**：无请求体；以 `defaults_from_config` 走 A-5 同一路径。

**A-7 `GET /admin/api/settings/export`**：`Content-Disposition: attachment; filename="kindle-calendar-settings-YYYYMMDD.json"`；内容 = 4.1 结构（含 schema_version）。

**A-8 `POST /admin/api/settings/import`**：请求 raw JSON 或 multipart `file`；解析失败/`schema_version≠1` → 400 `SETTINGS_IMPORT_INVALID`；否则走 A-5。

**A-9 `GET /admin/api/geocode?q=`**

| 请求 | 规则 |
|------|------|
| q | 1–50 字，trim 后非空 |

上游：`https://geocoding-api.open-meteo.com/v1/search?name={q}&count=10&language=zh&format=json`，超时 6s，仅 https 固定主机，禁止重定向。响应 `data.candidates[]`：

| 字段 | 来源 |
|------|------|
| name | results[].name |
| admin1 | results[].admin1（可空） |
| country | results[].country |
| latitude / longitude | 保留 4 位小数 |
| timezone | results[].timezone |

**A-10 `GET /admin/api/device`**

响应 `data`:

| 字段 | 类型 | 说明 |
|------|------|------|
| online_state | enum online_state | 见 FR-9 |
| delivery_state | enum delivery_state | 版本比对 |
| last_seen_at | ISO / null | 最近心跳 |
| last_ip | string / null | 来源地址 |
| last_user_agent | string / null | 截断 80 字 |
| delivered_settings_version | string / null | 心跳携带 |
| current_settings_version | string | 当前 |
| interval_estimate_s | int | 两次心跳间隔；缺省 900 |
| eta_minutes | int | `ceil(max(0, last_seen + interval − now) / 60)`；pending 时有意义 |

**E-1 `GET /api/v1/dashboard.env`**（新增/变更变量；其余不变）

```
PAGES="today month week detail"          # 已启用页按配置顺序，today 恒首
SETTINGS_VERSION="a1b2c3d4e5f6"
ROTATE_ENABLED=1
ROTATE_TODAY_S=120                        # 保留
ROTATE_MONTH_S=30  ROTATE_WEEK_S=30  ROTATE_DETAIL_S=30   # 仅 enabled 页
ROTATE_OTHER_S=30                         # 保留：= 首个非 today 启用页的 dwell_s；无其他页时 30
ROTATE_SUPPRESS_S=120                     # 来自配置
```

服务端副作用：记录心跳 `{ts, ip(ProxyFix 后 remote_addr), ua[:80], settings_version, regions_version}`。

**E-2 `GET /api/v1/dashboard.json`**：`pages` 改为已启用页序；新增 `settings_version`；`location` 来自配置；`quote` 按 quote.mode 取值。

**E-3 dash.sh 行为契约**

| 变更点 | 规则 |
|--------|------|
| 轮播计时 | `rotate_arm`：`eval s=\$ROTATE_${CUR_PAGE^^}_S`（ash 用 tr 转大写）；空 → `ROTATE_OTHER_S`；仍空 → 30 |
| 轮播总开关 | `ROTATE_ENABLED` 以 env 为准；config.sh 值仅 env 缺失时生效 |
| 一圈终点 | 当前页 == `PAGES` 最后一项 → 清屏回 today（替代硬编码 almanac） |
| 本地覆盖 | 删除 `LOCAL_ROTATE_*` 捕获与恢复三行 |
| 页面焦点 | 若当前页不在新 `PAGES` 中（被禁用）→ 切回 today 并重绘 |

### 4.5 领域事件与集成

| 事件（进程内） | 触发 | 消费 |
|---------------|------|------|
| `settings_changed(old, new)` | A-5/A-6/A-8 成功 | `DashboardService.apply_settings`：更新城市、按需失效天气、清分区缓存 |
| `device_heartbeat` | E-1 响应 | 心跳寄存器（最近两条） |

无 MQ、无工作流回调。仓储契约：`SettingsStore`（load/save/version）。关联域调用：Open-Meteo Geocoding（出站，ACL 字段白名单）。

## 5. 模块清单汇总

### 5.1 端点清单

| 端点 | 方法 | 用途 | 消费方 |
|------|------|------|--------|
| /admin | GET | 管理端页面 | 维护者浏览器 |
| /admin/api/login, /logout | POST | 会话 | 管理端前端 |
| /admin/api/settings | GET | 读配置 | 管理端前端 |
| /admin/api/settings/save, /reset, /import | POST | 写配置 | 管理端前端 |
| /admin/api/settings/export | GET | 导出 | 维护者 |
| /admin/api/geocode | GET | 城市搜索 | 管理端前端 |
| /admin/api/device | GET | 设备状态 | 管理端前端 |
| /api/v1/dashboard.env（扩展） | GET | 设备清单 + 心跳 | dash.sh |
| /api/v1/dashboard.json（扩展） | GET | 调试 | 维护者 |
| /dashboard.png?page=&v=（复用） | GET | 预览 | 管理端前端 |

### 5.2 文件与环境变量清单

| 项 | 说明 |
|----|------|
| `data/settings.json` | 配置文件（Docker 建议挂卷 `./data:/app/data`） |
| `ADMIN_PASSWORD`, `SECRET_KEY`, `SETTINGS_PATH`, `ADMIN_SESSION_DAYS`, `ADMIN_LOCK_THRESHOLD`, `ADMIN_LOCK_SECONDS` | 见 3.4 |

### 5.3 SQL 清单 / DDL

不适用（无数据库）。

## 6. 更新记录

| 版本 | 日期 | 变更类型 | 目标节 | 更新说明 |
|------|------|---------|--------|---------|
| v1.0 | 2026-10-10 | initial | — | 单例配置聚合根、A-1~A-10 管理接口、E-1~E-3 设备契约扩展、F-1 文件契约、INV-1~6、错误码与枚举引用 |
