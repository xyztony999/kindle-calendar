# Gate 2：管理端体验与设备确认兼容

2026-10-16。Profile kindle-calendar，无激活技术栈。用户已以 confirm 确认 Gate 1。

## 判定

WARN（用户已接受本地结果）：本地实现与验证通过，真实 Kindle 的 HTTP400是否消失、固件下载器兼容与屏幕确认尚待部署后验收。2026-10-17用户回复“commit & push”，授权本轮与后续数据样式改动一起提交推送；真机验收继续保留待办。

## 结果

- 页面卡标题右侧新增页面，退出列表与暂停秒数之间的夹缝。设置标题下为全宽吸顶操作条，保存/导入/导出/恢复默认在桌面与手机均可用。
- 样式改名“突出首个数据”“逐行数据列表”，真实字段样例与最多3/6项说明。首个字段提示按目录顺序确定，字段值hero/rows与渲染不改。
- 取消/Escape/遮罩恢复进入编辑前整个草稿；新页取消不留空页；完成保留草稿但不全局保存。跨页定义删除可取消，未完成上传不会回写已关闭会话，关闭后恢复焦点。
- 右侧只负责新建。已有定义与删除菜单归左侧我的积木，删除提示受影响页面数；画布×仍只移除一个实例。
- 共享_brand.html覆盖首页/管理/阅读/图片页。SVG favicon明暗适配，兼容ICO与Apple touch资源；Docker既有COPY server/包含静态资源。
- 城市42px单行输入，移除搜索按钮，400ms自动联想、AbortController和序号防乱序、输入法合成、方向键/Enter/Escape与空结果/失败提示。原有手动坐标字段保留。
- 一言库仅预留docs/quote-library.md与JSON示例，静态说明可本地访问，不增加来源或任意URL抓取。
- 设备接口兼容JSON、标准表单、旧wget原始/一次URL编码JSON；2KB上限、重复字段/类型/范围/版本字符严格校验，错误含code与message。新脚本用标准表单，wget不手工加Content-Type，失败可回退curl；阶段诊断日志完善。
- HeartbeatLog原子保存至settings同目录device-status.json。单worker线程锁保护；启动验证恢复，损坏降级未知，写失败仅记警告且不影响画面与配置。重启不重置原通信时间，仍按声明周期判离线。

## 证据与验证

用户日志中确认POST连续HTTP400。旧BusyBox源码的URL_escape与追加form Content-Type与该现象吻合；原接口模拟form类型JSON和编码JSON均400，新接口均200。尚无真机wget版本与服务端400响应体，不能将具体代理/解析拒绝点描述为已真机证实。新脚本同时避免编码JSON和重复Content-Type两类风险。

1. python -m unittest discover -s tests：69项通过，无跳过；随后增强同一重启测试，真实创建新Flask实例再登录读状态的专项1项也通过。
2. python -m compileall -q server tests 通过；POSIX sh -n kindle/dash.sh 通过；UTF-8 LF断言通过；git diff --check通过。
3. tests/ui_admin_refinement.cjs 在隔离Flask 8766+Chromium通过：取消新页/已有布局/此前未保存草稿；两页引用定义删除的取消与完成；取消后延迟上传不加入assets；搜索乱序、IME、键盘选择；中英/明暗/390px/吸顶工具条与恢复焦点，零JS运行错误。保存和上传在浏览器测试中拦截，不写真实设置/OSS；实际保存/上传契约已有接口测试覆盖。
4. tests.test_web_chrome 验证所有页面品牌与静态图标资源200；语录文档、示例与docs源逐字节一致。截图位于被忽略的data/ui-refinement/，测试依赖仅验证环境，未加入产品依赖。

运行浏览器回归需提供隔离服务与Playwright，UI_TEST_BASE默认127.0.0.1:8766，UI_TEST_PASSWORD指定测试口令；PLAYWRIGHT_MODULE/UI_TEST_BROWSER可指向已安装运行时。测试文件注释与环境变量说明见tests/ui_admin_refinement.cjs。

## 规则扫描与契约对齐

激活链仅engine-rules及业务知识注入，无栈/业务挂载规则。GR-01扫描无CRITICAL；GR-02/04编译与shell检查通过；GR-03确认事件覆盖请求→状态→失败保持→重启读取完整链路，无CRUD删除语义；GR-05/06逐项对齐表单/JSON字段、设备请求头、响应错误、状态字段、hero/rows、模板/中英字典与静态地址。不从普通wget/curl或浏览器访问推断设备。

未测覆盖率；69是测试数量。真实Kindle验收和多worker持久化并发不在本地验证结论内；生产既有启动为1worker/2threads。
