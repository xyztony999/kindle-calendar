# 管理端体验接口增量

v1.0 / 2026-10-16。继承 api-admin-feedback；已有配置、积木、预览、城市接口保持原路径与保存语义。

## 设备确认

POST /api/v1/device/heartbeat 继续要求 X-Kindle-Device: dash。请求体上限 2048 字节，超限413，不记录状态。保留 JSON {interval_s:900,mode:"v2",applied_version:"配置版本"}；新增标准 application/x-www-form-urlencoded interval_s=900&mode=v2&applied_version=版本，作为新 dash.sh 默认格式。值只含整数、v1/v2和版本安全字符，避免旧 wget 再编码破坏语义。

兼容已部署旧 dash.sh：仅在标记设备请求、有限载荷和 JSON/表单类型下，识别原始JSON或以%7B开头的单次URL编码JSON；解码一次后严格解析对象，不任意 force 解析。重复表单字段、非整数周期、范围外周期、非法mode、v1携带非空应用版本仍返回400。空确认保持此前记录；v2当前版本才delivered，v1unknown。成功200 {ok:true}。错误包含稳定错误code与具体原因，日志不记录管理员口令。

新脚本记录上报成功版本与传输错误；wget失败且curl可用时进行一次curl回退，两者均失败不清空旧确认。资产下载和绘制失败日志指明阶段。不要把HTTP请求成功等同于屏幕内容成功。

## 持久化

HeartbeatLog 接收独立文件路径，与 settings.json 同目录 device-status.json。只写最近通信、拉取、应用时间、周期、模式、来源与确认版本；用临时文件+os.replace 原子替换，线程锁保护。启动验证结构和类型后载入，非法/损坏文件忽略并记录警告。快照按保存的时间计算有效期。单worker两线程部署满足共享；未来多worker共享写需另行文件锁或数据库，本轮不声称支持并发多进程写。

GET /admin/api/device 的已有字段保持，不增加公开状态读取接口。状态存储失败不改变配置读写；无存储记录才unknown。部署现有data卷承载该文件。

## 品牌资源

GET /static/brand/logo.svg、favicon.svg、favicon.ico、apple-touch-icon.png 为公开静态资源；favicon.svg 自带 prefers-color-scheme 配色，不依赖页面CSS。模板共用品牌macro及图标引用；Docker COPY server/ 自动覆盖 server/static/brand。GET /favicon.ico 可重定向兼容资源。

## 一言库预留契约

独立库结构：{"schema_version":1,"quotes":[{"text":"此心安处是吾乡。","from":"苏轼《定风波》"}]}。沿用 text 1–32字符、from 0–16字符、禁止换行、最多100项；provider适配后的运行时结果仍为{text,from}。本轮落示例与文档，不添加quote mode、配置schema或导入接口。未来再定义来源选择、导入与远端获取，不将该格式混同整个settings导入。

## 验证计划

设备标识/JSON/表单/旧wget编码/重复字段/错误类型/超限、成功确认与失败保持、重启恢复与腐坏降级；POSIX shell模拟传输回退与下载/绘制失败。界面验证取消恢复跨页引用和新增页、此前草稿保留、搜索乱序与中文合成、静态Logo在Docker与所有页面可用。设备实际确认待真机验证。
