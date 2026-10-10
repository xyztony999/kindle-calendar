# Gate 2 验证报告 — 代码→交付门控

**模块**：web-admin（Web 管理端）
**检查时间**：2026-10-10
**Profile**：kindle-calendar（无激活技术栈 → 栈特定 BE-xx/FE-xx 清单不适用，按引擎机制层 + 本模块契约执行）
**扫描路径**：`server/`、`kindle/dash.sh`、`kindle/config.sh.example`、`tests/test_web_admin.py`
**设计基线**：api-web-admin.md v1.0 / PageSpec v1.0 / Gate 1 PASS（沿用，未重跑）

## 1. 代码扫描（适用项）

| 检查 | 结果 | 证据 |
|------|------|------|
| 编译必过 | PASS | 项目虚拟环境导入 `server.app` 并跑通 `tests/test_web_admin.py`（9 项） |
| shell 语法 | PASS | WSL `bash -n kindle/dash.sh` 通过 |
| 零新增依赖 | PASS | 未改 `requirements.txt`；会话签名、Geocoding 分别用 Flask 与既有 `requests` |
| 口令不入库 | PASS | `ADMIN_PASSWORD` 只从环境变量读取；仓库无口令字面量。单测夹具为明显的测试字符串 |
| 出网安全基线 | PASS | Geocoding 固定 https 主机、`allow_redirects=False`、超时 6s；一言/天气沿用既有白名单 |
| 栈特定 BE/FE 规则 | N/A | 无激活栈；形态为 Flask 内嵌单页 + POSIX env |

## 2. 契约对齐

| 编号 | 检查项 | 结果 |
|------|--------|------|
| AL-001 | A-1~A-10、E-1/E-2 与实现路径 | PASS。登录/保存/导出/导入/城市搜索/设备状态/env/json 均按文档状态码与错误码返回 |
| AL-002 | PageSpec Action URL 与实现 | PASS。页面内写请求带 `X-Requested-With: kindle-admin`；导入为 multipart |
| AL-003 | 表单字段 ↔ 4.1 | PASS。pages / rotation / quote / location；today 固定首位且不可取消 |
| AL-004 | 枚举 | PASS。page_id、quote_mode、delivery_state、online_state 与 enum-pool §1 一致 |
| AL-005 | 错误码前端可识别 | PASS。口令错误、锁定倒计时、校验逐字段、导入失败、搜索失败均有页面反馈 |
| 旧 env 语义 | PASS | 未保存配置时 `PAGES="today week month detail almanac"`、`ROTATE_TODAY_S=120`、`ROTATE_OTHER_S=30`、`ROTATE_SUPPRESS_S=120` 仍在；另增 `ROTATE_ENABLED`、`ROTATE_{PAGE}_S`、`SETTINGS_VERSION` |
| `/dashboard.png` 无参数 | PASS | 返回 `image/png`，浏览器放大今日页可阅读（时钟、天气、一言、五页指示） |

## 3. 测试与手工验证

无既有测试框架。新增标准库 `unittest`（不增加依赖），并用本机临时服务做了 HTTP 与浏览器走查。

| 层 | 方式 | 结果 |
|----|------|------|
| 配置与接口 | `tests/test_web_admin.py`：版本哈希不含 `updated_at`、校验收集、登录 CSRF/5 次锁定、禁用口令 503、保存后 env 页序与停留、导入失败不改配置、恢复默认、损坏文件降级、Geocoding 字段、dash.sh 无 `LOCAL_ROTATE` | PASS（9/9） |
| 实服务 HTTP | 临时端口：错误口令 401、正确口令 200、保存后 `ROTATE_WEEK_S` 变化、`/dashboard.png` PNG 魔数、导出 `Content-Disposition`、env 拉取后设备 `delivered`、退出后 401、multipart 导入 | PASS |
| 浏览器 | 登录进入设置页；改一周停留为 50 秒并保存（落盘）；未保存时出现「预览反映已保存配置」；搜索「杭州」选出浙江候选并填入经纬度/时区；点击今日预览打开放大层，Esc 关闭。预览图为已保存配置，不是未保存的杭州草稿 | PASS |
| 真机 Kindle | 页序、每页停留、`config.sh` 不再覆盖云端、下发状态从 pending 到 delivered | **未验证** |

## 4. 交付物

- `server/settings.py`：校验、默认值、原子写、内容版本、进程内心跳
- `server/admin.py` + `server/templates/admin.html`：A-1~A-10
- `server/data.py`、`quotes.py`、`service.py`、`app.py`：载荷/env/心跳/`apply_settings`
- `kindle/dash.sh`：按页停留、一圈终点为 `PAGES` 末项、删除 `LOCAL_ROTATE_*`、当前页被禁用时回 today
- `kindle/config.sh.example`：轮播参数注明仅 env 失败时兜底

## 总结

**判定**：**WARN**

- CRITICAL 违规：0
- WARN：1（验收标准 2、3、7 的真机部分未在本环境执行）
- INFO：0
- 真机验收：未执行，需用户在 Kindle 上确认后视为交付完成

服务端与脚本契约已实现并通过本机验证。请确认后是否接受本 WARN 并关闭 web-admin 代码阶段；确认前不要把本次改动视为已在设备上验收。
