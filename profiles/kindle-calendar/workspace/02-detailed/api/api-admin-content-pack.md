# API：admin-content-pack（个人语录库上传 / 健康数值折线）

- 版本：v1.0（2026-11-24）
- PRD：prd-admin-content-pack.md；架构锚点 BA/AA/FL v2.1（D-06-07 新增、D-05-04/D-05-07 扩展、S-01-05 扩个人源）。
- 功能类型：工具类（上传/观测接口）+ 主数据类增强（settings 枚举扩展）。单聚合根（台历配置），无跨聚合根设计；存储为 JSON 文件，无 SQL/DDL。

## §1 概述与边界

- 做：个人语录 JSON 上传校验替换、personal 取句分支、备份白名单扩展、健康快照存值与折线数据接口。
- 不做：在线自定义语录接口地址、个人库删除/追加、健康告警、设备端改动、多城市（轮 2）。
- 设计决策：① personal 为第四来源模式而非覆盖官方库文件（避免与 7 天 TTL 刷新互相覆盖）；② 上传与 mode 保存解耦（不偷跑配置，沿用分区脏点模型）；③ 快照存原值、出图按当前 units 换算（units.py 唯一换算入口，与渲染口径一致）；④ 中英页共用个人库（同 custom 语义）。

## §2 settings 变更（schema 3 不变）

```jsonc
"quote": {"mode": "library|online|custom|personal", "custom": [...], "library_types": ["i","d"]}
```

- `QUOTE_MODES` += `"personal"`（offline 仍为兼容别名，normalize 迁移 library）。
- validate：mode=personal 合法；**不要求个人库文件已存在**（空库回退离线兜底）；custom 非空约束仅对 mode=custom 生效（现状不变）。
- normalize：quote 键重建沿用现状；无新顶层键。settings_version 因枚举扩展一次性轮转（设备多拉一次 env，可忽略）。
- 枚举引用：enum-pool.md §1 `quote_mode`（v1.3 已更正四态）。

## §3 个人语录库文件与上传接口

### 文件格式（docs/quote-library.md 预留规范落地）

```json
{"schema_version": 1, "quotes": [{"text": "此心安处是吾乡。", "from": "苏轼《定风波》"}]}
```

存储路径 `data/quotes_personal.json`（与 settings.json 同目录，data 挂卷持久化）。

### POST /admin/api/quotes-personal

- 守卫：require_write（会话 + 写权限，同 backup/restore）；multipart 字段 `file`；全局 MAX_CONTENT_LENGTH=4MB 沿用。
- 校验规则（整份校验，全部错误一次性返回）：

| # | 规则 | 错误码 |
|---|------|--------|
| V1 | JSON 可解析且为对象 | QUOTES_PERSONAL_INVALID |
| V2 | schema_version 为整数 1 | QUOTES_PERSONAL_INVALID |
| V3 | quotes 为非空数组，1–100 条（CUSTOM_MAX） | QUOTES_PERSONAL_INVALID |
| V4 | 每项为对象；text 去首尾空白后 1–32 Unicode 字符（TEXT_MAX） | QUOTES_PERSONAL_INVALID |
| V5 | from 缺省按空串；去首尾空白后 ≤16 Unicode 字符（FROM_MAX） | QUOTES_PERSONAL_INVALID |
| V6 | text/from 禁含 \r \n（HTML 不解析：渲染层 PIL 纯文本绘制，天然不执行） | QUOTES_PERSONAL_INVALID |

- 失败响应 400：`{"ok": false, "error": {"code": "QUOTES_PERSONAL_INVALID", "message": "…", "details": [{"index": 3, "field": "text", "code": "…", "message": "文案须为 1–32 字且不含换行"}]}}`（details 形态沿用 settings validate 的 _detail 惯例；顶层错误 index 缺省为 null）。**不部分导入、不静默截断、原文件不被破坏**。
- 成功响应 200：`{"ok": true, "data": {"count": N, "uploaded_at": "<iso>"}}`。
- 落盘：tmp + os.replace 原子写；写成功后热替换 `_personal_sentences`（threading.Lock 保护，照搬 `_library_sentences` 模式）；**不修改 settings、不自动切换 mode**。
- 并发：上传串行化（单锁）；与取句读共享同一锁。

### 载入与热替换

- `_load_personal()`：懒加载 data/quotes_personal.json；坏文件/缺失 → 空池（warning 日志）；上传/恢复成功后置 `_personal_sentences = None` 或直接替换（同 library 恢复手法）。

## §4 取句行为（quotes.py）

- `get_quote()`：mode=personal → `pool[_yday % len(pool)]`（确定性按日轮换）；池空 → OFFLINE_QUOTES 兜底（同 library 空池语义）。
- `english_quote()`：mode=personal → 同一个人库轮换；池空 → local_en_quote 兜底。
- `health()`：personal 模式 `enabled=False`（同 library，有库即正常）；新增 `personal_count` / `personal_updated`（文件 mtime 或上传时记录的 meta）；library_* 字段保留。
- `_status["enabled"]` 语义不变（仅 online 为 True）。

## §5 备份/恢复变更（admin.py）

- backup_download：成员循环 += `quotes_personal.json`（可选，OSError 跳过）。
- backup_restore：`allowed` += `quotes_personal.json`；存在时按 §3 V1–V6 同一校验（复用同一校验函数），失败 400 BACKUP_INVALID 不落盘；成功原子写 + 热替换；`restored_personal` 布尔入响应 data。
- restore 仍 `gc_assets=False`（素材 OSS 键复用，防 GC 连带删除）。

## §6 健康数值快照与折线数据

### 快照存值（record 侧）

- aqi.health()：`_status` 补 `cn_value`（fetch 时已算出的 cn_aqi；失败/缺失为 None）。`value`=us_aqi 现状已有。
- service.sources_health()：weather 条目补 `value`=`_weather.current.temperature`（℃ 原值；无天气不存值）。quote/ics 无数值语义。
- health_history.record()：snapshot 每源在 `{ok, error}` 外保留可选 `value` / `cn_value`（仅 int/float 且非 bool 才存）；旧文件无值字段载入兼容；RETAIN_DAYS/MAX_POINTS/原子写/坏文件即弃全不变。

### GET /admin/api/sources/history（响应扩展）

- series() 的 `**state` 透传自动带出 value/cn_value，无需改 series 结构。
- **service.sources_history() 增加换算**：读当前 settings.units，逐拍逐源换算后输出——
  - aqi：构造迷你 payload `{"aqi": {"us_aqi": value, "cn_aqi": cn_value}, "units": units}` 走 `units.aqi_view()` 取数值（国标缺失自动回退美标，与渲染一致）；
  - weather：`units.temp_number(value, {"units": units})`；
  - 换算结果写回该拍该源的 `value`（原值不再外露），无值拍保持无值。
- 响应：`{"ok": true, "data": {"sources": {"weather": [{"at", "ok", "error", "value"?}…], "aqi": […], "quote": […], "ics": […]}, "units": {"temp": "c|f", "aqi": "us|cn"}}}`。
- 历史拍按**当前**口径重释（与全站渲染一致；units 切换后折线整体换算）。

## §7 管理端前端契约（交互细节见 interaction-admin-content-pack.md）

- 一言分区：来源 radio 第四项「个人库」；选中时显示上传控件（file input + 上传按钮）与库信息（personal_count/personal_updated，来自 /admin/api/sources 的 quote 源）；未上传空态引导；上传成功 toast 提示「已上传 N 条，保存后生效」，不自动改 radio 之外的配置。
- 设备分区健康卡：/admin/api/sources/history 驱动，点阵之上新增 AQI/温度两条原生 SVG 折线（7 天、y 自适应、无值断线）；units 标签随响应 units。
- i18n：zh/en 词条同提交补齐（沿用 locale 机制）。

## §8 兼容与部署影响

- 设备端零改动（env 协议不变；一言服务端渲染）。
- 旧配置（无 personal）行为不变；旧备份（无个人库成员）恢复兼容；新备份恢复到旧服务：旧服务白名单拒绝含 quotes_personal.json 的 zip（预期，同 schema3 先例）。
- 无新依赖、无新环境变量、无 compose 变更。

## §9 变更摘要（结构化）

| 变更类型 | 目标 | 说明 |
|---------|------|------|
| enum_value_added | §2 quote_mode | +personal（enum-pool §1 v1.3） |
| interface_added | §3 POST /admin/api/quotes-personal | 上传校验替换 |
| interface_changed | §5 GET /admin/api/backup、POST /admin/api/backup/restore | 白名单 +quotes_personal.json |
| interface_changed | §6 GET /admin/api/sources/history | 逐拍数值 + units 换算 + units 标签 |
| field_added | §6 aqi._status.cn_value、weather 健康条目 value、快照 value/cn_value | 数值折线数据源 |
| rule_added | §3 V1–V6、§4 personal 轮换/兜底 | 预留规范落地 |

## §10 更新记录

| 版本 | 日期 | 更新说明 |
|------|------|---------|
| v1.0 | 2026-11-24 | 初版：个人语录库上传 + 健康数值折线（轮 1）；多城市排轮 2 |

---

### 机械自检（M1–M5）

- M1 章节结构： house 紧凑体例（同 api-experience-pack-1），模板映射 1→§1、3→§3/§5/§6/§8、4→§2/§4、5→§8（无 SQL）、6→§9/§10；2 跨聚合根不适用（单聚合根）。✅
- M2 路径格式：沿用项目既定 `/admin/api/<resource>` 管理端约定（与全部既有端点一致，偏离通用三段式属 house 惯例）。✅
- M3 枚举引用：quote_mode 见 enum-pool.md §1（v1.3 四态，无重复）。✅
- M4 占位符：无 {按需填写}/TODO。✅
- M5 变更记录：§9/§10 齐备。✅