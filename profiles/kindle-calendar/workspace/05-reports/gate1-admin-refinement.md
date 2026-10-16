# Gate 1：管理端体验与确认兼容

2026-10-16 / 设计检查 PASS / 用户以confirm确认，已进入实施。设计阶段记录保留如下。

证据：用户画面内刷新日志HTTP400；Flask模拟JSON返回200，表单类型JSON与URL编码JSON返回400。BusyBox旧版源代码与现象吻合，但未拿到实际wget版本。城市已有400ms联想；hero/rows真实渲染、全局操作位置、共享草稿取消与跨页删除影响已核对。

G1-01：沿用Flask+原生网页+设备拉取，架构三文档附增量说明；只新增状态持久化与共享品牌资源。
G1-02：PRD覆盖设备确认和八条浏览器反馈、异常与兼容。
G1-03：确认接口JSON/表单/旧编码/上限/错误明确，品牌资源与一言预留边界明确。
G1-04：主页面、弹窗、取消、样式、积木管理、联想搜索均定义。
G1-05：接口和交互字段沿用现有值，状态时间与确认规则保持。
G1-06：完成→未保存、取消→进入前草稿、失败→保持旧确认、重启→恢复时间均定义。
G1-07：复用hero/rows、online/offline/unknown、delivered/pending/unknown、v1/v2；仅换显示文案。
G1-08：沿用现有设备命名空间，无新增管理写路径。
G1-09：新增设计文档带版本日期和更新说明。
G1-10：INDEX已登记design完成、code待执行。

参考源码：https://raw.githubusercontent.com/mirror/busybox/1_17_1/networking/wget.c （URL_escape及POST头写入）。

真机400兼容验证与实际持久化挂卷恢复将在Gate2单独记录，不能以本地模拟代替。
