# PRD：体感温度、天气突变提醒、数据源健康页与 dash.sh 自更新（weather-sources-selfupdate）

- 版本：v1.0（2026-10-26 Gate 1 确认，用户按推荐执行：1A/2A/3A/4A）
- 前置：8277d50（三轮同批）之上
- 实施顺序：① 体感 → ② 提醒 → ③ 健康页 → ④ 自更新

## R1 体感温度

- R1.1 Open-Meteo current 块新增 `apparent_temperature`；`CurrentWeather.apparent`（末位默认 None，兼容既有构造）。
- R1.2 payload `weather.current.apparent`；新数据积木字段 `weather.apparent`（number，°）。
- R1.3 天气积木 stats 行新开关 `show_feels`（bool，默认关）。

## R2 天气突变提醒

- R2.1 Open-Meteo 请求加 `past_days=1`；`WeatherData.yesterday`（DailyForecast|None）——**按日期校验切分**（daily[0].date == 昨日才切），`daily` 保持「[0]=今天」既有契约；hourly 侧 cutoff 过滤天然安全。
- R2.2 payload 新增 `weather_alerts: [{"kind":"cool","drop":Δ},{"kind":"rain","prob":p}]`：今日最高温较昨日降 ≥5°、今日降水概率 ≥50%；昨日仅用于计算，不进 payload。
- R2.3 渲染：页眉备注行（复用 `show_notes` 开关）追加提醒文案（较昨日降 N°/降水 N%），en 同步；与节日/纪念日共用 notes[:2] 截断。

## R3 数据源健康页

- R3.1 各源结构化状态：weather（service 已有，失败明细已有）；aqi/quote/ics 模块补模块级 `{"ok","at","error"}` 状态与 `health()` 访问器；AQI 失败补 log.warning。
- R3.2 `service.sources_health()` 聚合四源；新 `GET /admin/api/sources`。
- R3.3 管理端侧栏新卡「数据源」：每源一行 = 名称 + 状态徽标（正常/失败/未配置）+ 最近刷新（相对时间）+ 最近错误（截断，title 全文）；随设备卡 30s 轮询与 visibilitychange 刷新。

## R4 dash.sh 自更新

- R4.1 镜像打包：Dockerfile `COPY kindle/dash.sh kindle/`（.dockerignore 放行该文件）；新路由 `GET /api/v1/script` 下发脚本内容（ETag/`X-Script-Md5`=md5，no-store）。
- R4.2 env 新增 `DASH_MD5` 与 `DASH_SCRIPT_URL`。
- R4.3 设备端 `self_update()`（fetch_consume 重载 env 后调用）：`DASH_AUTOUPDATE≠1` 或工具缺失直接跳过；md5 一致跳过；不同则下载 `dash.sh.new` → **md5 校验通过才原子替换**（旧版备份 `dash.sh.old`，失败保留旧版）→ 写 `updated.flag` → `nohup` 重启自身并干净退出（触发既有 trap 清理）。
- R4.4 引导说明：当前设备上的旧版 dash.sh 没有自更新逻辑，**需最后一次手动 scp**；此后自动。
- R4.5 config.sh 可 `DASH_AUTOUPDATE=0` 关闭；DEPLOY.md 补说明。

## 非目标

- 自更新 lib/display.sh 与其他设备端文件（仅 dash.sh）；回滚 UI；健康历史持久化（内存态，重启清零）；提醒规则自定义阈值。

## 验收要点

- 体感字段/开关渲染有变化，默认关不回归；昨日切分后一周页/详情页/积木字段全部仍以今天为 [0]（回归）。
- 降温/降水 alert 在页眉出现且可被 show_notes 关闭；无昨日数据时无提醒且无异常。
- 健康卡四源状态正确（断言 mock 场景 ok/fail）。
- self_update harness：md5 一致零动作；不一致→下载+校验+替换+重启标记；校验失败保留旧版；DASH_AUTOUPDATE=0 跳过。
