# Gate 2：管理端五条反馈

日期：2026-10-16。Profile：kindle-calendar，无依赖技术栈。Gate 1 已获用户 yes 确认。

## 判定

WARN（用户已接受）：本地代码、契约、界面与模拟设备验证通过；真实 Kindle 的固件网络工具兼容性、Wi-Fi 窗口与墨水屏显示尚未验收。2026-10-16 用户回复“确认”，接受当前本地结果，将真机验收保留为待办。本次本地交付确认完成；未提交、未部署。

## 实现与根因

LogoLoom 优化并导出 design/brand，管理端登录与顶栏使用同一 SVG，currentColor 跟随主题。原 .field 的纵向布局造成样式 radio 与文字分离，现用原生 radio + 双示例卡修正。原退出按钮使用 .link 且位于标题区，现使用 .btn 纳入顶栏并仅登录后可见。

原草稿预览会 POST 未保存布局生成底图，编辑区已经自动刷新。现更名刷新预览，并说明自动更新、未保存和不会下发；保留 700ms 自动防抖和手动重试。

设备 v2 原本每 900s 同步。根因是仅 env 计数、浏览器访问污染、相邻请求间隔估算阈值，以及 GET 配置即认定 delivered。现明确设备标识，按声明周期×2+60 秒判断在线，整图补通信，新增 POST 应用确认，下载/绘制失败不确认。v1 的配置状态 unknown，v2→v1 不沿用历史确认宣称当前布局已应用。进程重启回 unknown，旧脚本需更新才上报可信状态。

## 验证证据

- python -m unittest discover -s tests：58 项通过，无跳过。设备接口覆盖格式错误、管理员鉴权、浏览器/旧脚本排除、拉取待确认、旧/当前版本确认、失败保留、v1/v2切换、在线边界与连续快速请求。
- shell 模拟覆盖资产失败/显示失败不确认、先绘制再确认再关 Wi-Fi、回报失败不阻断与显示失败传播。
- Git POSIX sh -n kindle/dash.sh 通过；脚本 UTF-8 LF，无 CRLF。
- python -m compileall -q server tests 通过；git diff --check 通过。
- 本地独立 Flask 8766 + Chromium：中文/英文、浅色/深色、390px 窄屏、原生 radio 方向键、预览刷新、退出登录全部通过。检查预览阶段零 settings/save/import/reset 请求、零 JS 运行错误，页面无水平溢出。
- 状态卡通过 mock 响应分别验证未知与已应用信息显示；真实服务状态逻辑由接口测试验证。截图 data/admin-zh-dark.png、data/admin-mobile.png；临时验证脚本与环境在被忽略的 data 目录，不增加产品依赖。

## 激活规则扫描与契约核对

按引擎→技术栈→业务链扫描：当前无栈规则或业务挂载规则，仅 engine-rules 与业务知识注入。GR-02/04 编译通过；GR-03 新增 heartbeat 接口完成端到端状态链测试，此接口为事件确认、无 CRUD 删除语义；GR-05/06 已核对请求头、JSON interval_s/mode/applied_version、200/400、GET /admin/api/device 所有展示字段与中英文字典。原 hero/rows 值与 ID 保持，布局预览 API 未改变保存语义。GR-01 无 CRITICAL 违规，未执行提交。

测试覆盖率未测量，58 为通过的测试数量。
