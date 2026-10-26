# Gate 2 报告：weather-sources-selfupdate（体感温度 / 突变提醒 / 数据源健康 / dash.sh 自更新）

- 日期：2026-10-26
- 结论：**PASS（待用户验收）**——112 项单测全过、两条 E2E PASS、健康卡与脚本下发路由真机外实测通过；未提交。

## 交付清单

### R1 体感温度
- Open-Meteo current 增 `apparent_temperature`；`CurrentWeather.apparent`（末位默认 None 兼容旧构造）；payload `weather.current.apparent`；新字段 `weather.apparent`（FIELD_IDS=29）；天气积木 stats 开关 `show_feels`（默认关）。

### R2 天气突变提醒
- 请求加 `past_days=1`，昨日按日期校验切分至 `WeatherData.yesterday`（daily[0]=今天 契约不变；hourly 靠 cutoff 过滤天然安全）。
- payload `weather_alerts`：较昨日最高温降 ≥5°、降水概率 ≥50%；页眉备注行渲染（受 `show_notes` 开关控制，en 同步）；昨日仅用于计算不进 payload。

### R3 数据源健康页
- quotes/aqi/ics 补模块级状态与 `health()`（AQI 失败顺带补日志）；`service.sources_health()` 聚合天气/aqi/一言/ICS；`GET /admin/api/sources`；管理端侧栏「数据源」卡（徽标+相对时间+错误截断），随设备卡 30s 轮询。实测：AQI 模拟失败正确显示"失败"。

### R4 dash.sh 自更新
- Dockerfile `COPY kindle/dash.sh`（.dockerignore `kindle/*` + `!kindle/dash.sh`，静态校验为正确形态）；`GET /api/v1/script`（字节级下发，X-Script-Md5 实测 == 文件 md5）；env `DASH_MD5`/`DASH_SCRIPT_URL`。
- 设备端 `self_update()`（fetch_consume 重载 env 后调用）：md5 一致跳过；下载→校验→备份 dash.sh.old→原子替换→updated.flag→nohup 重启+exit（trap 清理生效）；失败保留旧版下周期重试；`config.sh DASH_AUTOUPDATE=0` 可关。harness 四分支覆盖（含 command -v 找到函数桩、exit 截断）。
- DEPLOY.md 第 7 节：引导说明（**现役设备需最后一次手动 scp 新 dash.sh，此后全自动**）。

## 验证

- 单测 112 OK（新增：alerts 规则/env+script+sources 断言/页眉提醒墨量/feels 开关墨量/ics health 状态/self_update harness 四分支）。
- E2E 两条 PASS；真机外探测：健康卡四源渲染正确、/api/v1/script 字节一致。
- 测试侧修正 3 处（新渲染测试误入 schema 类、日志断言两行）。

## 部署注意

- push 后流水线自动构建（镜像首次内置 dash.sh）。
- **Kindle 需手动拷贝一次本版 dash.sh**（引导）；此后设备脚本更新全自动。
- config.sh 可设 `DASH_AUTOUPDATE=0` 关闭。

## 保留待办

- 真机：体感开关、页眉提醒文案、健康卡、自更新实际触发（下次改 dash.sh 即可观察）。
