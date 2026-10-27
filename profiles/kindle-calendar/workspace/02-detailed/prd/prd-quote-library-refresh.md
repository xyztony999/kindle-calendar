# PRD：语料库刷新机制（quote-library-refresh）

- 版本：v1.0（2026-10-27 Gate 1 确认，用户按推荐执行：7 天自动 / 数据源卡行内按钮 / 失败健康行+toast / 脚本薄封装）
- 前置：quote-library（未提交，同批）

## R1 刷新核心（server/quotes.py）

- R1.1 `refresh_library(force=False)`：12 分类逐文件加固拉取（复用 `ics._fetch_ics`：公网 IP 校验直连+SNI+2MB 限长；源顺序 fastly→cdn→raw）→ 4–28 字/去重/from≤24 过滤 → 排序。
- R1.2 持久化：**原子写 `data/quotes_library.json`**（tmp+os.replace）+ `data/quotes_meta.json`（updated/来源/条数/last_error/fetched_at，照 HeartbeatLog 模板）；**镜像内置 `server/quotes_library.json` 降级为首启兜底**（data/ 有库优先用）。
- R1.3 热替换：锁内更新 `_library_sentences` 与 `_status`（含语料 updated/条数），当日选句立刻生效；失败保旧数据+错误入 `_status`。
- R1.4 自动刷新：`refresh_if_stale()` TTL 7 天（常量），挂 `_refresh_ics` 线程尾部（请求触发语义，与天气/ICS 一致）。

## R2 管理端

- R2.1 `POST /admin/api/quotes-refresh`（require_write）：拉起 daemon 线程立即返回 ack；重复触发返回"已在刷新中"。
- R2.2 数据源卡「一言」行：状态徽标旁「刷新语料库」按钮（disabled 忙碌态+防重入），30s 健康轮询显示结果；一言行新增语料更新时间（relTime）+ 条数；失败显示错误摘要（toast 即时反馈 + 健康行）。
- R2.3 locale 双语：刷新按钮/刷新中/成功失败 toast。

## R3 脚本

- `scripts/update_quotes.py` 改薄封装：调 `quotes.refresh_library(force=True)`，消除双份维护。

## 非目标

- 语料增量更新/分类级更新；多语料源管理；刷新周期可配置（常量 7 天）。

## 验收

- 手动刷新：按钮→后台执行→健康行 updated/条数更新→当日选句来自新库；失败：保旧+错误显示。
- 自动：TTL 内跳过、过期触发（mock 时间）；meta 损坏忽略重建。
- 镜像内置兜底：data/ 无库时可用；升级镜像不丢 data/ 库。
