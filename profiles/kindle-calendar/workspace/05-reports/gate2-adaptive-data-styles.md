# Gate 2：数据适用样式与画布实例外观

2026-10-17。Profile kindle-calendar，无激活技术栈。用户已明确选择画布按页面设置，并确认Gate1四样式设计。

## 判定

PASS（本地实现与契约验证）。2026-10-17用户回复“commit & push”，确认本地结果并授权与前轮改动一起提交推送。前轮admin-refinement的真实Kindle确认HTTP400与固件验收待办继续保留，不因本报告自动完成。

## 实现

创建数据积木只填写名称/1–6字段，定义默认rows用于兼容。选中画布custom实例后按后端目录计算适用候选：hero首项数字/时间/日期且1–3项紧凑字段；rows通用1–6项；horizontal紧凑2–3项；grid紧凑2–6项。新实例写推荐值；未知kind保守按text；不从当前字符串长短或空值推断类别。

实例block.style优先，缺省沿用definition.style。实际渲染复制定义覆盖样式，不修改共享定义；同定义跨页甚至同页实例互不影响。历史hero长文允许继承但不作为新显式候选；恢复原样式移除覆盖。选择/删除/关闭会话同步选中状态，键盘Enter/Space选择、radio方向键可操作；取消沿用全草稿事务。

四种样式使用真实payload与正式Pillow渲染。横排等宽，网格固定两列带细边框以区别两项横排。文字按bbox预算换行/缩字/末行省略，原字段不截断。预览走既有layout-preview，字段目录、适用规则与推荐标记由catalog支撑；不显示固定24°假数据。

配置schema3，normalize保留block.style；导入统一ACCEPTED_SCHEMAS=(1,2,3)，旧schema1/2迁移不注入覆盖、原坐标和样式继承保留。新style参与内容版本。旧服务拒绝schema3，避免静默丢失新属性。审核中心仍只允许已审核定义，不因可设置外观绕过审核。本轮无需Kindle新协议。

## 证据

- python -m unittest discover -s tests：78项通过，无跳过。覆盖目录25字段、推荐/数量/类别边界、非法override、旧长文继承、非custom属性拒绝、schema1/2迁移、schema3保存→真实预览→导出→导入、版本随style变化和中心审核约束。
- 网格固定两列/细边框最终调整后，tests.test_data_styles_render专项5项再过。实际Pillow绘制验证中英、缺值、长字符串、极小矩形、每次文本绘制bbox不越界、实例不串改。
- tests/ui_data_styles.cjs通过：创建无样式输入、字段候选过滤、四种真实PNG内容不同、旧hero继承、双页面外观独立、取消/恢复默认、4字段推荐网格、键盘/中英/明暗/390px无水平溢出，零JS错误。实际PNG内容通过同一请求体的API客户端读取；浏览器页面也执行预览请求，规避特定Chromium已释放fetch body导致CDP返回空buffer的验证环境限制。
- 前轮tests/ui_admin_refinement.cjs已适配实例样式入口并再次通过，取消/跨页删除/延迟上传/IME与搜索乱序/吸顶工具条无回归。
- python -m compileall -q server tests与git diff --check通过。后续仅增加选中边框在白色预览上的对比度样式与README说明，不改变功能链。

截图：data/ui-data-styles/canvas-zh-dark.png、canvas-zh-light.png、canvas-mobile.png、canvas-en.png；均是隔离数据示例。测试运行方式沿用tests/ui_admin_refinement.cjs的环境变量。无新增产品运行依赖；未测覆盖率，78为测试数量。

## 规则与对齐

扫描激活链engine-rules与业务知识注入，无技术栈/业务挂载规则。GR-01无CRITICAL；GR-02/04编译和测试通过；GR-03覆盖修改接口完整保存/查询/预览/更新/导出导入链与跨页删除既有回归；GR-05/06逐项核对field.kind、data_styles的数量/allowed_kinds/first_kinds、前后端推荐、custom.block.style、schema版本和中英文案。前轮设备上报变更仍保留，未混同本增量验收结论。
