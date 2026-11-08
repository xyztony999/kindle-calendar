# Gate 2 报告：block-options-2 轮 1（编辑体验与全局单位）

- 日期：2026-11-08
- 范围：#0 勾选框排版、#3 -0°、#2/#8/#7 全局显示单位（℃/℉、风速、中国 AQI）、#1 页眉日期格式、#10 月历今日标记
- 结论：**PASS**（待用户验收；未提交）

## 交付清单

| 文件 | 变更 |
|---|---|
| server/units.py（新） | 温度/风速/AQI 唯一换算入口：half-up 取整（根治 -0°）、℉ 与温差换算、km/h·m/s·蒲福风级、AQI 按标准取值与六段定位 |
| server/datefmt.py（新） | 页眉四种预设 + 花括号模板渲染与校验（未知占位符 / 未闭合花括号） |
| server/aqi.py | 同请求加拉六项污染物；HJ 633 IAQI 计算与国标等级；**修复未定义 `log`** |
| server/settings.py / data.py | 新顶层键 `units`（缺键默认、非法 400）；payload 附 `units` 与国标/PM 字段 |
| server/layout.py / admin.py | header.date_format/date_template、grid.today_mark；新 text 选项类型；catalog 下发 choice_labels/visible_when/占位符；字段分组目录 |
| server/render/pages/*.py、fields.py | 全部温度/风速/AQI 显示改走 units；页眉日期格式（缩字 + 截断兜底）；今日标记三样式；指数卡长数值缩字 |
| server/templates/admin.html | 恢复 opt-* 行式样式；文本选项（提交时写入、就地校验）；字段按类分组；城市分区「显示单位」组；分区脏点纳入 units |
| server/locale.py | zh/en 新词条 12 组 |
| tests/test_block_options_2.py（新） | 34 项 |
| tests/test_system_options.py | schema 扩展后的期望值同步（text 类型、新默认键、choice_labels 完整性） |
| tests/ui_admin_refinement.cjs | 新断言：开关逐行、模板显隐与报错、字段分组、显示单位保存 |

## 验证

| 项 | 结果 |
|---|---|
| 单测全量 | **169 项 OK**（原 135 + 新 34） |
| E2E refinement / data_styles | **PASS / PASS**（从干净的测试配置起跑） |
| 全端点 HTTP 回归 | **77/77**：默认单位全量出图 → 切 ℉/风力等级/国标 + 自定义页眉模板 + 实心标记后再全量出图；非法单位 400；dashboard.json 仍为原始 ℃ |
| 断言灵敏度 | 逐行断言：注入「样式丢失」CSS 后条件为 false；圈/方框角点、-0 像素等价、页签留白带、指数卡溢出——均先确认旧行为会失败 |
| 出图目检 | -0.4℃→「0°」；℉ 31°/27°/43°；4 级风；国标「107 轻度污染」刻度落第三段；四种日期预设；三种今日标记居中 |
| 管理端截图 | 外观面板逐行（亮/暗）、模板就地报错、画布页眉「2026年11月8日 周日」缩字避让页签、字段分组（宽表单多列 / 窄抽屉两列）、显示单位组（含 390px） |

## 偏差与顺带修复

见契约 §10。要点：模板上限 16→24 字（验证中发现输入框静默截断导致出图残缺）；国标英文改短写；指数卡长数值缩字（同时修复美标英文既有溢出）；**aqi.py 未定义 `log` 的既有 bug**（AQI 抖动时周期刷新连同新天气一起丢弃）。

## 风险与待跟进

- 部署后所有配置的 settings_version 变化一次（normalize 新增 `units` 键），设备多拉一次 env，无其它影响。
- 温度取整口径 half-even → half-up：x.5 度显示可能比旧版高 1°。
- 轮 2（数据扩展/指数卡自选/逐时图表/一周积木）待开工。
