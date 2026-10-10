# PRD：Web 管理端（web-admin）

| 属性 | 值 |
|------|-----|
| 模块 | web-admin（基础数据域-显示配置 D-03 / 位置配置 D-04 / 配置运维 D-05 + 平台支撑域-管理端接入 P-04） |
| 版本 | v1.0 |
| 状态 | 待评审 |
| 最后更新 | 2026-10-10 |
| 关联架构 | workspace/00-architecture/（BA v1.2 / AA v1.2 / FL v1.1） |
| 功能类型 | 主数据类（单例配置聚合根，有写操作、数据生命周期无流程流转） |

## 1. 背景与目标

v2.1 已交付五页面集与双导航。但「显示什么、为哪座城市、以什么节奏轮播」全部散落为常量与配置文件：

1. **R1 配置不可达**：城市只能改 `config.yaml`/环境变量后重启服务；页面集与页序在 `regions.py` 硬编码；轮播秒数在 `service.py` 字面量与设备 `config.sh` 两处各一份。
2. **R2 两端配置冲突**：`dash.sh` 以「不等于默认值 120/30 才覆盖」的脆弱逻辑决定本地与云端谁优先，调参需同时烧录设备。
3. **R3 无反馈**：维护者看不到设备是否拉到了新配置、何时生效。

**目标**：
- G1：提供口令保护的 Web 管理端（`/admin`），集中管理页面集与页序、每页轮播停留、一言来源、城市；
- G2：配置云端优先，保存后设备下一次拉取即生效，无需触碰设备；
- G3：管理端可预览各页效果、查看设备在线与配置下发状态、导入导出与恢复默认；
- G4：不破坏 `/dashboard.png` v1 兼容与既有 env 契约变量（仅新增/扩展）。

**不做**：多城市预设切换；分区级开关与像素级布局编辑；设备端本地参数（INTERVAL/时钟开关/触摸模式/WiFi）的云端管理；夜间反色定时；多用户与角色权限；配置变更历史。

## 2. 角色与场景

| 角色 | 场景 |
|------|------|
| 维护者 | 搬家后在手机浏览器打开 `/admin` 搜「杭州」选中保存，15 分钟内 Kindle 天气切换；觉得黄历页没人看，禁用它并把月历提前；把今日页停留改成 5 分钟；给长辈写几句自定义寄语做页脚一言；换服务器前导出配置 |
| 家庭用户 | 无感知；只看到页面集、页序、轮播节奏与一言随之变化 |
| 设备（dash.sh） | 每 INTERVAL 拉 env，读取 PAGES 与 ROTATE_* 新变量；不再用本地值覆盖云端值 |

## 3. 功能需求

### FR-1 管理员登录（P-04-01）

| 项 | 规则 |
|----|------|
| 口令来源 | 环境变量 `ADMIN_PASSWORD`；未设置 → `/admin` 与 `/admin/api/*` 全部返回「管理端未启用，请设置 ADMIN_PASSWORD」（HTML 提示页 / JSON 错误） |
| 会话 | 登录成功签发签名 Cookie（`HttpOnly; SameSite=Strict; Secure`[HTTPS 时]），有效期 7 天；签名密钥取 `SECRET_KEY` 环境变量，缺省时进程启动随机生成（重启需重新登录） |
| 限速 | 同一来源地址连续失败 5 次后锁定 15 分钟 |
| 写接口防护 | 写请求必须携带自定义头 `X-Requested-With: kindle-admin`（配合 SameSite 抵御 CSRF） |
| 退出 | 清除 Cookie |

### FR-2 页面集配置（D-03-01）

- 可配置页：week / month / detail / almanac，各有 `enabled` 与顺序；
- `today` 固定启用且固定为首页（时钟、启动页、轮播一圈起点均依赖它）；
- 保存后 env `PAGES` 仅含已启用页并按配置顺序排列；`/api/v1/dashboard.json` 的 `pages` 同步；
- 禁用页的分区图路由仍可访问（预览与调试用），只是不进入设备清单。

### FR-3 轮播计划配置（D-03-02）

| 字段 | 取值 | 默认 |
|------|------|------|
| `rotation.enabled` | 布尔 | true |
| `pages[*].dwell_s` | 5–3600 整数，每个已启用页一个 | today 120，其余 30 |
| `rotation.suppress_s` | 0–3600 整数 | 120 |

- env 新增 `ROTATE_ENABLED`、每页 `ROTATE_{PAGE}_S`，保留 `ROTATE_TODAY_S`/`ROTATE_OTHER_S`（后者 = 非今日页中首个已启用页的停留值，旧脚本兼容）与 `ROTATE_SUPPRESS_S`；
- 设备端：`rotate_arm` 改为按当前页读取 `ROTATE_{PAGE}_S`，缺失回退 `ROTATE_OTHER_S`；轮播「一圈终点」改为 `PAGES` 最后一项（不再硬编码 almanac）；删除 `LOCAL_ROTATE_*` 覆盖逻辑，`config.sh` 的 ROTATE_* 仅在 env 拉取失败时作离线兜底。

### FR-4 一言来源配置（D-03-03）

| 字段 | 取值 |
|------|------|
| `quote.mode` | `online`（一言 API，失败回退离线）/ `offline`（内置诗词按日轮换）/ `custom`（自定义列表按日轮换） |
| `quote.custom[]` | `{text ≤32 字, from ≤16 字}`，1–100 条；`mode=custom` 时至少 1 条 |

### FR-5 城市配置（D-04-01 / D-04-02）

- 搜索：`GET /admin/api/geocode?q=` 代理 Open-Meteo Geocoding（`language=zh&count=10`），返回候选 `{name, admin1, country, latitude, longitude, timezone}`；上游失败返回错误码并提示手动填写；
- 设定：`location.name`（1–20 字）、`latitude`（-90~90）、`longitude`（-180~180）、`timezone`（IANA 名称，须被 `zoneinfo` 识别）；
- 保存后：天气 SWR 缓存立即失效并同步重拉一次（失败则保留旧数据并提示）；载荷指纹变化 → 全部分区重渲染 → 设备下次拉取整页更新。

### FR-6 配置预览（D-05-01）

- 管理端对每个已启用页展示 `/dashboard.png?page={page}&v={settings_version}` 缩略图（宽 ≤ 240px，点击放大原图）；
- 预览反映**已保存**配置；未保存草稿不预览（页面提示「保存后预览更新」）。

### FR-7 配置生效（D-05-02）

- 配置整体为一份 JSON（`settings.json`，路径 `SETTINGS_PATH` 环境变量，默认 `data/settings.json`），每次保存**整体校验 → 临时文件 → 原子替换**；
- 保存成功生成 `settings_version`（内容哈希前 12 位）；env 下发 `SETTINGS_VERSION`，json 载荷含 `settings_version`；
- 生效原则**云端优先**：env 中出现的参数覆盖设备本地同名参数；
- 管理端显示：当前版本、设备已下发版本（来自心跳）、状态 `pending`（不一致）/ `delivered`（一致）/ `unknown`（无心跳），以及「预计最迟 N 分钟后生效」（N = 设备拉取间隔估计，取两次心跳间隔，缺省 15）；
- 启动时若 `settings.json` 不存在或损坏 → 以部署默认值运行并在管理端顶部提示（Render 免费版重启丢盘场景）。

### FR-8 导入导出与恢复默认（D-05-03 / D-05-04）

- 导出：`GET /admin/api/settings/export` 下载 `kindle-calendar-settings-{date}.json`（含 `schema_version`）；
- 导入：上传 JSON → 结构与取值校验 → 通过则整体覆盖并生效；失败逐项返回错误，不改动现有配置；
- 恢复默认：二次确认后写入部署默认值（由环境变量/`config.yaml` 推导：城市四项 + 五页全启用默认顺序 + 轮播 120/30/120 + 一言 online）。

### FR-9 设备状态（D-05-05 / P-04-02）

- 服务端在 `/api/v1/dashboard.env` 每次响应时记录：时间戳、来源地址（经 ProxyFix 的真实 IP）、User-Agent、本次下发的 `SETTINGS_VERSION` 与 `REGIONS_VERSION`；进程内保存最近 1 条及上一条（用于估算拉取间隔）；
- 在线判定：距最近心跳 < 2 × 拉取间隔估计（缺省 1800s）→ `online`，否则 `offline`；无记录 → `unknown`；
- 管理端每 30s 轮询一次状态。

### FR-10 管理端页面（前端形态）

- Flask 内嵌：`GET /admin` 返回单 HTML（模板内联 CSS/原生 JS，无构建链、无外部 CDN 依赖）；
- 单页分区块：设备状态条、页面与轮播、城市、一言、预览、操作区（保存/恢复默认/导出/导入）；
- 响应式：≥ 768px 双栏，< 768px 单栏（手机可用）。

## 4. 业务规则

| 编号 | 规则 |
|------|------|
| BR-1 | today 固定启用、固定首位；其余四页至少可全部禁用（仅今日页也合法） |
| BR-2 | 配置整体原子保存：任一字段校验失败则整份拒绝，不产生半更新 |
| BR-3 | 云端优先：env 下发的 PAGES/ROTATE_* 覆盖设备本地；本地值只在 env 拉取失败时兜底 |
| BR-4 | 城市变更必须使天气缓存失效并纳入指纹，确保设备整页重拉 |
| BR-5 | 未设置 ADMIN_PASSWORD 时管理端整体不可用（安全默认，而非无鉴权开放） |
| BR-6 | 导入失败不得改动现有配置；导入成功等同一次保存（版本更新、心跳比对重置为 pending） |
| BR-7 | 预览只反映已保存配置 |
| BR-8 | 既有 env 变量名与语义不变，仅新增变量；旧 dash.sh（v2.1）读取新 env 仍可运行（ROTATE_TODAY_S/OTHER_S 保留） |
| BR-9 | 心跳数据仅进程内，不持久化、不含敏感信息（不记录完整 UA 以外的任何设备数据） |

## 5. 非功能需求

| 编号 | 需求 |
|------|------|
| NFR-1 | 保存接口 P95 ≤ 300ms（不含城市变更触发的天气重拉；重拉异步化或 ≤ 8s 超时） |
| NFR-2 | 管理页首屏（含 5 张预览缩略）在家庭宽带 ≤ 3s；缩略图复用 `/dashboard.png` 缓存（max-age=60） |
| NFR-3 | 零新增 Python 依赖（Flask 自带 session 签名；Geocoding 用现有 requests） |
| NFR-4 | `settings.json` ≤ 32KB；写入原子（tmp + rename） |
| NFR-5 | 管理端禁止凭据字面量进入仓库；口令仅从环境变量读取 |
| NFR-6 | 设备端改动限于 `dash.sh` 轮播/页序读取逻辑，`display.sh`、tapread 不动 |

## 6. 验收标准

1. 未设 `ADMIN_PASSWORD` 访问 `/admin` 得到禁用提示；设置后错误口令 5 次被锁 15 分钟，正确口令进入管理页；
2. 禁用 almanac 并把 month 拖到 week 前保存 → env `PAGES="today month week detail"`；Kindle 手动刷新后翻页顺序一致，轮播一圈在 detail 结束回 today；
3. 今日页停留改 300s、其他页改 20s → env 出现 `ROTATE_TODAY_S=300 ROTATE_MONTH_S=20 …`，设备停留时长随之变化，且 `config.sh` 中旧值不再覆盖；
4. 搜索「杭州」选中保存 → `/weather` 经纬度改变，`/health` 显示天气已刷新，设备下次拉取后页眉城市与天气更新；
5. 一言改为自定义两条 → 页脚一言按日在两条间轮换；改回 online 后恢复 API 内容；
6. 预览区 5 张缩略随保存更新；禁用页不显示缩略；
7. 设备拉取后管理端状态由 pending 变 delivered，显示最近拉取时间与在线；
8. 导出 → 修改城市 → 导入旧文件 → 配置回到导出时状态；上传缺字段文件 → 报错且配置不变；恢复默认 → 与 `config.yaml` 推导值一致；
9. `/dashboard.png`（无参数）与 v2.1 旧 `dash.sh` 行为不变。

## 7. 开放问题

| # | 问题 | 当前决策 | 可推翻 |
|---|------|---------|--------|
| O-1 | today 是否允许禁用/移位 | 否（时钟与启动序列依赖） | 是，若需要则 dash.sh 启动页改为 PAGES 首项且时钟仅在 today 绘制 |
| O-2 | 预览是否支持未保存草稿 | 否（避免 POST 渲染端点与缓存复杂度） | 是，后续可加 `POST /admin/api/preview` |
| O-3 | Render 免费版持久化 | 接受重启回默认并提示；建议自托管 Docker 挂卷 `./data:/app/data` | — |

## 更新记录

| 版本 | 日期 | 更新说明 |
|------|------|---------|
| v1.0 | 2026-10-10 | 初始生成：R1–R3 问题、G1–G4 目标、FR-1~FR-10、BR-1~BR-9、NFR-1~NFR-6、九条验收、三项开放问题（D0 已锁定决策） |
