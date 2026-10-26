# Gate 2 报告：editor-manage（编辑器内管理面板 + 系统积木自定义扩展）

- 日期：2026-10-24
- 结论：**PASS（待用户验收）**——100 项单测全过、两条 E2E 全绿；未提交。

## 交付清单

### R1 编辑器内管理面板
- 弹窗左栏新增管理抽屉 `#widget-drawer`（覆盖左栏）：「我的积木」列表 + 新建/编辑表单（名称+字段）+ 素材列表与删除 + 每行「＋放置」快捷按钮 + 「返回放置」；编辑器全程不关、草稿/预览不丢。
- 管理逻辑参数化（`managerScope`/`renderManagerList`/`onWidgetAdd`/`onWidgetSave`），主视图卡片（#widget-* 原有 id 不变，E2E 兼容）与抽屉双挂载复用同一套逻辑；任何一处变更 `afterManagerChange` 同步两处+调色板+画布。

### R2 系统积木自定义（2B 全量）
| 项 | 实现 |
|---|---|
| 页眉节日/假期备注开关 | `show_notes`（common.render_header，关闭保留星期） |
| 天气高低温行/图标开关 | `show_range` / `show_icon`（today.render_weather） |
| 一言字号档位 | `size` lg/md/sm（起步 32/27/22；收缩下限按档位 60% = 19/16/15，长句不收敛） |
| 月历周起始日 | `week_start` mon/sun（month.py 表头/周末列/矩阵 + almanac.month_grid_info(firstweekday) 缓存 key 加维度） |
| 通用边框 | `border` bool，除 clock 外 12 个系统积木（paint_system 统一绘制 2px 内缩框） |
| 文字积木对齐+字号 | align UI 补齐；`size` 走专用字段（校验/normalize/paint_text/外观面板单选） |
| z 序控制 | 外观面板「上移/下移一层」（z 序排序交换并重排 1..n，纯前端） |
| Bug：grid.show_lunar 死选项 | month.render_grid 补消费，关闭即不画角标 |
| Bug：月历偏移漏传 options | service._get_month_offset_region 补传块 options，缓存 key 含 options |

前端：choice 值→文案改为映射（lg/md/sm→大/中/小，mon/sun→周一/周日）。

### 验证
- 单测 100 项 OK（新增 12：schema/边框排除 clock/文字 size 校验/页眉节日行/天气 range+icon/一言档位/周起始表头+矩阵/月历角标单关/paint_system 边框/paint_text 档位 + test_layout 文字 size 往返）。
- E2E 两条 PASS（refinement 新增抽屉全流程：打开抽屉→新建→列表与调色板即时出现→放置→层级调整→返回→保存 payload 校验）。
- 过程中发现并修复两处实现缺陷：①边框注入循环误遍历 SYSTEM_OPTIONS（6 个无选项积木漏配）→ 改遍历 SYSTEM_WIDGETS + setdefault；②一言档位长句收敛 → 档位化下限。测试侧修正：quote 档位用例固定短句（在线一言随机长句导致非密闭）。

### 保留待办
- 真机观感：边框/周起始日/一言档位的实际墨迹效果。
- 用户 commit & push 后 CI/CD 自动部署。
