# PRD：管理端内容包（admin-content-pack：个人语录库上传 / 健康数值折线）

- 版本：v1.0（2026-11-24 讨论拍板：分两轮 / 新增个人库模式 / 管理端切换城市排第二轮）
- 第十五轮管理端增量之轮 1；轮 2（多城市切换：cities 数组 + active、normalize 派生 location、设备零改动）另行立项。
- 架构锚点：BA/AA/FL v2.1（D-06-07 个人语录库上传新增；D-05-04 备份纳入个人库；D-05-07 健康数值折线；S-01-05 一言获取扩个人源）。

## D0 澄清结论

| 项 | 结论 |
|---|---|
| 需求类型 | 增强（无新业务域；L4 新增 1 个：个人语录库上传） |
| 角色 | 维护者（上传/查看）；家庭用户与浏览访客间接受益（页脚一言） |
| 个人库语义 | 第四来源模式 personal，与官方库/在线/自定义并存互不覆盖；中英页共用（同 custom 语义）；按日确定性轮换 |
| 上传语义 | 整份替换（非追加）；整份校验逐条报错；原子写 + 热替换 |
| 健康折线 | AQI + 温度两条数值线，保留 ok/error 点阵；快照存原值，出图随当前显示单位换算；早期无数值拍断点 |
| 在线自定义接口地址 | 不纳入（docs/quote-library.md 明确需单独设计地址限制/认证/超时） |

## R1 个人语录库上传（D-06-07）

- R1.1 `quote.mode` 枚举扩为四态 `library/online/custom/personal`（QUOTE_MODES）；personal 模式保存不要求文件已存在（空库回退离线兜底，健康卡显示「个人库未上传」）。不 bump schema_version（纯枚举扩展；旧服务导入 personal 配置按 QUOTE_MODE_INVALID 拒绝，属预期）。
- R1.2 上传 `POST /admin/api/quotes-personal`（multipart `file`，会话 + 写权限，沿用 MAX_CONTENT_LENGTH=4MB）。整份校验按 docs/quote-library.md 预留规范：顶层 `schema_version` 必须为整数 1；`quotes` 非空数组 1–100 条；每项 `text` 去首尾空白后 1–32 个 Unicode 字符、`from` ≤16 个 Unicode 字符（缺省按空串）；两字段禁回车换行；字符数按 Unicode 字符计非字节。校验复用 settings 的 TEXT_MAX/FROM_MAX/CUSTOM_MAX 常量。
- R1.3 校验失败返回 `QUOTES_PERSONAL_INVALID`（400），details 逐条列出错误条目索引与字段（整份校验，不静默截断、不部分导入）。
- R1.4 通过后原子写 `data/quotes_personal.json`（tmp + os.replace），热替换内存缓存（_personal_sentences + lock，照搬 _library_sentences 模式）；上传成功不自动切换 mode（避免偷跑配置），管理端提示「已上传 N 条，选择『个人库』并保存后生效」。
- R1.5 `quotes.get_quote()` personal 分支：`now.timetuple().tm_yday % len(pool)` 确定性轮换；池空/文件缺失回退 OFFLINE_QUOTES。`english_quote()` personal 分支：同一个人库（中英共用），空库回退 local_en_quote。
- R1.6 健康语义同 library：有库即「正常」（enabled 仅对 online 有意义）；quotes.health() 在 personal 模式反映个人库条数与上传时间。
- R1.7 备份：zip 白名单 += `quotes_personal.json`（可选成员，缺失跳过）；恢复按 R1.2 同一校验（1–100 条规范），通过后原子写 + 热替换；restore 仍 gc_assets=False。
- R1.8 管理端一言分区：来源 radio 加「个人库」第四项；选中个人库时显示上传控件 + 当前库信息（条数/上传时间，来自 health）；未上传显示空态引导。上传与 mode 保存解耦（上传即生效文件，mode 走分区脏点保存）。
- R1.9 docs/quote-library.md 状态注记更新为「个人库上传已实现」（/docs 路由单一来源，仅改 docs/）。
- R1.10 设备端零改动：一言服务端渲染，env 协议不变；settings_version 因 normalize 变化一次性轮转（设备多拉一次 env，可忽略）。

## R2 健康数值折线（D-05-07）

- R2.1 快照存值：`health_history.record()` 在 `{ok, error}` 之外保留源提供的数值字段（可选）：aqi 存 `value`（us_aqi，已有）+ `cn_value`（国标，新增）；weather 存 `value`（当前温度 ℃ 原值，service.sources_health 天气条目新增）。quote/ics 无数值语义，不存。
- R2.2 aqi._status 补存 cn_value（fetch 时已算出 cn_aqi，顺手存入）；weather 条目 value 取 _weather.current 温度（缺失不存值，ok 语义不变）。
- R2.3 `GET /admin/api/sources-history` 响应扩展：points 内各源含可选 value/cn_value；**服务端按当前 settings.units 换算后输出**（复用 units.py 唯一换算入口：AQI 国标取 cn_value、美标取 value；温度 ℉ 换算），附 units 口径标签。历史拍按当前口径重释（与渲染一致）。
- R2.4 管理端设备分区健康卡：点阵之上新增两条原生 SVG 折线（AQI / 温度），7 天窗口、y 轴自适应、x 轴日期刻度；无数值拍（旧快照/源失败）断线不插值；无图表库依赖。点阵与四源状态卡保留不变。
- R2.5 保留策略不变：RETAIN_DAYS=7、MAX_POINTS=672、单 JSON 原子快照、坏文件即弃；旧文件无 value 字段载入兼容（value 可选）。

## 非目标

- 在线自定义语录接口地址（SSRF/认证需单独设计）；个人库多文件/追加/在线同步；个人库删除入口（重传即替换，切 mode 即停用）。
- 健康告警/通知推送；折线导出；更长保留期。
- 设备端任何改动；多城市切换（轮 2）。

## 验收

- 上传合规文件 → 200 + 条数；切 personal 保存 → 中英页脚按日轮换个人句；空库/未上传 → 离线兜底不空白。
- 上传越界文件（101 条 / 33 字 / 换行 / schema_version=2）→ 400 逐条索引报错，原文件不被破坏。
- 备份 zip 含 quotes_personal.json；恢复到新实例后 personal 模式立即取句；恢复非法个人库成员 → 400 不落盘。
- 健康折线：AQI/温度随 units 切换换算正确（℃/℉、美标/国标像素级或数值断言）；旧拍断点；点阵回归不变。
- 单测 + 两 E2E + HTTP 全端点回归（含上传/恢复/历史路径）；管理端 UI 改动同提交更新 ui 脚本。

## D2 领域建模（范围明确，跳过战略设计）

本域：台历配置（基础数据域，薄适配）+ 内容供给·数据聚合（支撑域，消费侧）。

| 对象名 | 分类 | 与上级关系 | 核心业务字段 | 备注 |
|--------|------|-----------|------------|------|
| 台历配置 settings | 聚合根（沿用） | — | quote.mode 扩 personal | 一致性边界：保存即整体生效 |
| 个人语录库文件 | 域内对象·值对象集合 | settings 之外独立文件，mode 引用 | schema_version, quotes[{text,from}] | 整份替换不可变；无个体标识，按日索引取句 |
| 当前健康状态 | 域内对象（内存态，沿用） | 各源 _status | ok/error/at/value/cn_value | aqi 补 cn_value、weather 补 value |
| 健康历史快照 | 子流程（G2 历史对象） | 服务于配置治理观测 | points[{at, sources}] | I/O 见下；7 天保留 |
| 上传请求/校验报错 | 过程数据 P4/P7 | — | file/details | 不持久化 |

子流程 I/O 契约：

| 子流程 | 触发条件 | 输入 | 输出 | 输出写入 |
|--------|---------|------|------|---------|
| 健康历史快照 | 天气刷新节拍（15min）尾部 | sources_health() 全量（含值） | data/health_history.json 追加一拍 | 独立文件，非 settings |

关联领域对象：

| 关联领域对象 | 所属业务域 | 关联字段 | 需获取信息 | 映射模式 |
|------------|--------|---------|----------|---------|
| 一言获取 S-01-05 | 内容供给 | quote.mode=personal | 个人库取句结果 | 遵奉者（同进程直调） |
| 全量备份恢复 D-05-04 | 配置治理 | 白名单成员名 | 文件字节 | 共享内核（白名单常量） |

## PRD 完备性检查 — 通过

功能类型：主数据（配置扩展）+ 工具（上传/观测）
检查项：G1–G5 ✅（目标/范围/角色/对象/关系齐备）；T1 ✅（字段与约束 R1.2/R2.1）；T1a ✅（被引用关系见关联表）；T9 ✅（输入输出规格 R1.2–R1.4/R2.3）；N1 ✅（4MB 上限/100 条/672 拍）；N2 ✅（空库兜底/坏文件即弃/校验不部分导入）；N3 ✅（轮换/换算/校验规则）。
本次变更影响范围：quote.mode 枚举 +1；备份白名单 +1 成员；sources-history 响应 +值字段；无状态机变更。