# Gate 2 报告：quote-resilience（一言在线获取韧性）

- 日期：2026-10-26
- 结论：**PASS（待用户验收）**——117 项单测全过、E2E PASS；未提交。

## 诊断结论（Gate 1 已确认）

- 请求合规官方文档（端点/参数/无 UA 要求逐项核对）；根因为阿里云北京 ECS → hitokoto 的 Cloudflare（免费版无中国节点，入洛杉矶 POP）跨洋链路晚高峰 ~80% 丢包，随机击穿 TLS/TTFB 撞穿 8s 读超时；一条 A 记录对本机 SYN 黑洞；international 子域同 IP 换域无效。容器与宿主一致。

## 交付

- `server/quotes.py`：在线拉取（hitokoto + zenquotes）超时拆分 (connect 5, read 12)；失败（超时/连接/HTTP/空响应）重试 1 次间隔 1s（日频请求不触碰官方 2 QPS）；**上次成功内容粘性缓存 ≤7 天**（中英独立），失败时设备显示上次在线内容而非跳离线库；健康卡照实显示失败与错误。
- 修复验证中发现的产品 bug：`_days_old` 对带时区 now 抛 TypeError（成功次日再失败会让 payload 构建崩溃）——已归一化处理并有带时区用例覆盖。
- 测试：`tests/test_quotes.py` 5 项（成功记录/失败重试+粘性+健康如实/第二次重试成功/超龄回退/英文粘性）；`test_en_locale.py` 超时断言改用 `ONLINE_TIMEOUT` 常量。

## 部署注意

- 纯服务端改动，push 后流水线自动上线；无需设备/运维操作。
- 根治方向（本地语料库 quote-library 或代理出口）仍为后续可选项。

## 保留待办

- 真机观察：链路劣化期健康卡显示失败、画面一言维持上次在线内容。
