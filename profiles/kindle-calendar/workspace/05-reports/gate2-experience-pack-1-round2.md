# Gate 2 报告：experience-pack-1 轮 2（全量备份/健康历史折线/docs 单一来源）

- 日期：2026-10-29
- 结论：**PASS（待用户验收）**——134 项单测全过、E2E PASS、备份/历史/docs 三端点实测（含路径穿越防护）；未提交。

## 交付清单

### A 一键全量备份/恢复
- `GET /admin/api/backup`：内存 zip（settings.json + quotes_library.json + quotes_meta.json，语料缺失跳过），下载文件名带日期。
- `POST /admin/api/backup/restore`：zip 完整性+成员白名单（仅三成员，含 settings.json 必需）→ settings 走现有校验链且 **gc_assets=False**（防恢复瞬间把 presets 引用外的素材连 OSS 一起删）→ 语料成员校验（JSON+≥100 条）后原子落盘 data/ 并热替换（`_library_sentences=None` 重读）。
- 素材不嵌二进制：settings 仅存 id/key/content_type，key 原样恢复即可从 OSS 拉取（跨实例恢复需同 bucket/前缀，恢复 toast 提示"图片素材存于 OSS，按 key 识别"）。
- 管理端工具条：导出旁「全量备份」「恢复备份」按钮（确认弹窗+禁用态+错误 toast）。

### B 健康历史 + 折线
- 新 `server/health_history.py`：单 JSON 快照 `data/health_history.json`（坏文件即弃、tmp+os.replace 原子写，与 HeartbeatLog 同构），保留 7 天+点数双上限；随天气刷新节拍（15 分钟）采样全量四源。
- `GET /admin/api/sources/history`：按源分组时间序列；管理端数据源卡内**原生 SVG 点阵**（最近 48 拍=12 小时，绿=正常/红=失败/灰=无数据，悬停显示时间与错误），零依赖。
- AQI 成功时状态多存 `value`（数值展示备用）。

### G docs 单一来源
- 新 `/docs/<name>` 路由（send_from_directory ROOT/docs，限 md/json，路径穿越实测 404）；Dockerfile `COPY docs/`；admin 文档链接改 `/docs/…`；**删除 server/static/docs/ 双份**；test_web_chrome 断言同步。

## 验证

- 134 项单测 OK（新增 BackupRestoreTests 3 项：round-trip/坏 zip 400/历史端点；web_chrome docs 断言改路由）。
- E2E 两条 PASS；探测：备份 zip 三成员正确、恢复 round-trip 数据回读一致、`/docs/*` 200 且穿越 404、数据源卡 4 行 SVG 渲染。
- 测试侧仅 1 处修复（漏 import io）。

## 部署注意

- **Dockerfile 新增 COPY docs/**——镜像内容变化，push 后自动构建即可；无环境变量/设备端变更。

## 保留待办

- 真机/管理端观察：备份下载-恢复全流程（本地已实测）、健康点阵积累 12 小时后的观感。
