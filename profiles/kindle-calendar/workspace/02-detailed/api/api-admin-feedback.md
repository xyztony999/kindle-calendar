# 管理端反馈接口增量

v1.0 / 2026-10-16。继承 api-web-admin 的会话、配置与预览契约。

## 现状与根因

dashboard.env GET 是唯一心跳来源。v2 默认 900 秒自动同步，v1 整图模式漏报；浏览器访问混入设备记录；最近两次访问间隔不能代表周期。请求配置成功也不代表图片显示成功。

## 设备契约

设备 env 和 PNG 请求添加 X-Kindle-Device: dash 与 X-Kindle-Interval: 正整数秒。明确标识后才记设备通信；无标识请求继续获取原载荷，但不充当可信设备心跳。旧脚本需更新后获得准确状态。

新增 POST /api/v1/device/heartbeat，JSON：interval_s（60–86400）、mode（v2/v1）、applied_version（v2 成功应用时填原配置 SETTINGS_VERSION；v1 为空）。设备用同轮 Wi-Fi 在显示成功后发送；失败不阻断显示、不清空此前确认。成功返回 200 与 ok:true；格式错误返回 400，且不更新状态。沿用公开设备 API 网络边界，不携带管理口令；此信息只用于状态提示，不能作为安全身份凭据。

GET /admin/api/device 继续要求管理员会话；沿用 online_state、delivery_state、last_seen_at、delivered_settings_version、current_settings_version，增加 last_fetch_at、last_applied_at 与 mode。last_seen_at 为最后通信，last_fetch_at 为配置/图片拉取，last_applied_at 为成功确认。online_state 复用 online/offline/unknown；delivery_state 复用 delivered/pending/unknown，delivered 仅在 v2 成功确认版本等于当前版本时成立。v1 的 delivery_state 为 unknown，历史确认保留但不代表整图模式应用了分区布局，前端明确标注模式。周期取声明值，旧值缺省 900 秒；离线阈值为周期 ×2 +60 秒。进程重启回到 unknown。

## 前端与测试

前端分别展示通信与应用状态，中英文字段同步。不从 online_state=unknown 提前隐藏其他有效状态。

接口测试覆盖校验、浏览器排除、v1/v2、重复快速请求、正常自动周期、超时、待同步/成功确认/失败、进程重启与管理员鉴权。脚本检查使用 POSIX sh 语法与请求失败回退；实际墨水屏效果需设备验收。
