# Gate 2 报告：quote-library-refresh（语料库刷新机制）

- 日期：2026-10-27
- 结论：**PASS（待用户验收）**——124 项单测全过、E2E PASS、并发守卫冒烟通过、自动通道真实网络跑通一次；未提交。

## 交付清单

- **refresh_library(force)**：12 分类逐文件加固拉取（复用 ics._fetch_ics，fastly→cdn→raw）→ 过滤去重排序 → **原子写 data/quotes_library.json + data/quotes_meta.json**（tmp+os.replace）→ 锁内热替换 `_library_sentences`（当日选句即刻生效）+ `_library_meta`；失败保旧+错误入状态；**语料 <100 条视为源异常拒写**；忙守卫内置（Event is_set/set/clear，调用方免锁）。
- **加载优先级**：data/ 刷新版 > 镜像内置（首启兜底）；meta 损坏忽略重建。
- **自动刷新**：`refresh_if_stale()` 挂 `_refresh_ics` 线程尾部，TTL 7 天（`QUOTES_LIBRARY_TTL_S` 可覆盖），失败保旧静默。
- **手动刷新**：`POST /admin/api/quotes-refresh`（require_write）→ 后台 daemon 线程立即 ack（is_set 防重入返回 running）；数据源卡「一言」行「刷新语料库」按钮（禁用忙碌态+30s 轮询完成 toast「语料库已更新（N 条）」）。
- **健康显示**：quote 条目新增 library_updated/条数/refreshing；library 模式徽标有库显示「正常」（修正"未配置"误导）；失败显示错误摘要。
- **脚本薄封装**：`scripts/update_quotes.py` → `refresh_library(force=True)`。

## 验证

- 124 项单测 OK（新增刷新 4 项：构建写入热替换/失败保旧/TTL skip/内置兜底）。
- E2E PASS；并发冒烟：第二调用返回"已在刷新中"、异常后 Event 正确清理。
- **自动通道真实验证**：verify 服务启动触发 refresh_if_stale，真实网络拉取成功落盘 data/（7,684 条），徽标由"刷新中"转"正常"。

## 过程修复

- **P0（验证抓出）**：`threading.Event` 被当锁用（acquire/release 不存在）——手动/自动刷新运行时必崩；改为 Event 三件套。**连带设计错误**：端点预锁 + 函数内锁会致手动刷新永远返回"已在刷新中"——锁职责收归 refresh_library 单点。
- 徽标语义：library 模式有库即"正常"。

## 部署注意

- data/ 目录挂载已存在，无 compose 变更；push 后自动上线。
- 首次上线后首个设备请求周期即触发自动刷新（TTL 从零起算），data/ 出现刷新库；之后每 7 天。

## 保留待办

- 真机/管理端观察刷新按钮全流程（真实网络已验证服务端侧）。
