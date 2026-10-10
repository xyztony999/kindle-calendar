# 交互设计 PageSpec：web-admin（Web 管理端）

| 属性 | 值 |
|------|-----|
| 模块 | web-admin |
| 版本 | v1.0 |
| 状态 | 待评审 |
| 最后更新 | 2026-10-10 |
| 输入 | api-web-admin.md v1.0（唯一信息来源） |
| 技术形态 | Flask 内嵌单 HTML（内联 CSS + 原生 JS，无构建、无 CDN）；组件名为通用语义，非特定 UI 库 |

## 1. 模块元信息

| 项 | 值 |
|----|-----|
| 模块编码 | D-03 / D-04 / D-05（配置）+ P-04（登录） |
| 业务类型 | 配置型主数据（单例记录，整体编辑/保存；无列表页、无详情页） |
| 页面类型 | 单页多区块（hybrid：表单区块 + 只读状态区块 + 图片预览区块） |
| 路由 | `/admin`（唯一路由；视图按状态切换：禁用提示 / 登录 / 设置） |
| 响应式 | ≥768px 双栏（左：页面与轮播、城市、一言；右：设备状态、预览、操作）；<768px 单栏按上述顺序堆叠 |

## 2. Action 定义

| Action | 方法 | URL | 触发 | 对应 API |
|--------|------|-----|------|---------|
| `auth.login` | POST | /admin/api/login | 登录按钮 | A-2 |
| `auth.logout` | POST | /admin/api/logout | 退出按钮 | A-3 |
| `settings.get` | GET | /admin/api/settings | 进入设置视图 / 保存后刷新 | A-4 |
| `settings.save` | POST | /admin/api/settings/save | 保存按钮 | A-5 |
| `settings.reset` | POST | /admin/api/settings/reset | 恢复默认（二次确认后） | A-6 |
| `settings.export` | GET | /admin/api/settings/export | 导出按钮（`<a download>`） | A-7 |
| `settings.import` | POST | /admin/api/settings/import | 导入文件选择后 | A-8 |
| `geocode.search` | GET | /admin/api/geocode?q= | 城市搜索输入（防抖 400ms / 回车 / 搜索按钮） | A-9 |
| `device.status` | GET | /admin/api/device | 进入设置视图 + 每 30s 轮询 + 保存后立即 | A-10 |
| `preview.image` | GET | /dashboard.png?page={page}&v={settings_version} | 设置视图加载 / 保存后 | 复用整页合成 |

所有写 Action 自动附带请求头 `X-Requested-With: kindle-admin` 与 `Content-Type: application/json`（导入为 multipart 时不设 JSON 头）。

## 3. 字典 Key 清单（前端静态映射，来源 api-web-admin.md 3.4 / enum-pool.md §1）

| Key | 取值 → 显示文案 |
|-----|----------------|
| `page_id` | today→今日 / week→一周 / month→月历 / detail→详情 / almanac→黄历 |
| `quote_mode` | online→在线一言（失败回退离线诗词）/ offline→离线诗词 / custom→自定义文案 |
| `delivery_state` | pending→待下发 / delivered→已下发 / unknown→未知（尚无设备拉取） |
| `online_state` | online→在线 / offline→离线 / unknown→未知 |

语义色（由前端按 code 匹配，不输出 hex）：delivered/online→成功色；pending→提示色；offline→警示色；unknown→中性色。

## 4. 视图与区块

### 4.1 视图切换

```
GET /admin
 ├─ 管理端未启用（ADMIN_DISABLED）→ V0 禁用提示视图
 ├─ 未登录                           → V1 登录视图
 └─ 已登录                           → V2 设置视图
```

### 4.2 V0 禁用提示视图

| 元素 | 内容 |
|------|------|
| 标题 | 管理端未启用 |
| 正文 | 请在服务端设置环境变量 `ADMIN_PASSWORD` 后重启服务。 |
| 附注 | Docker：`.env` 增加 `ADMIN_PASSWORD=…`；Render：Environment 面板添加。 |

### 4.3 V1 登录视图

| 字段 | 组件 | 校验 | 说明 |
|------|------|------|------|
| password | password input（自动聚焦，回车提交） | 非空 | 不回显、不记忆 |
| 登录 | primary button | — | 调 `auth.login`；成功 → 切换 V2 并加载 `settings.get` + `device.status` |

错误反馈：`ADMIN_AUTH_INVALID` → 输入框下红字「口令错误」；`ADMIN_AUTH_LOCKED` → 「失败次数过多，请 N 分钟后再试」并禁用按钮倒计时。

### 4.4 V2 设置视图 — 区块清单

| # | 区块 | 位置（双栏） | 类型 | 数据源 |
|---|------|-------------|------|--------|
| B0 | 顶栏 | 通栏 | 标题「Kindle 台历 · 管理端」+ 当前版本短码 + 退出登录；`degraded=true` 时下方黄色横幅「配置文件缺失或损坏，当前为默认值运行；保存后将重新创建」 | settings.get |
| B1 | 设备状态条 | 右栏顶部 | 只读状态卡 | device.status |
| B2 | 页面与轮播 | 左栏 | 可排序表单列表 | settings.pages / rotation |
| B3 | 城市 | 左栏 | 搜索 + 表单 | settings.location / geocode |
| B4 | 一言 | 左栏 | 单选 + 可编辑列表 | settings.quote |
| B5 | 预览 | 右栏 | 图片网格 | preview.image |
| B6 | 操作区 | 右栏底部（<768px 时吸底） | 按钮组 | — |

#### B1 设备状态条

| 字段 | 显示 | 来源 |
|------|------|------|
| 在线 | 徽标：在线/离线/未知（语义色） | online_state |
| 最近拉取 | 相对时间「3 分钟前」+ 悬停绝对时间 | last_seen_at |
| 下发状态 | 徽标：已下发 / 待下发（附「预计最迟 N 分钟后生效」）/ 未知 | delivery_state, eta_minutes |
| 版本 | `设备 a1b2c3 · 当前 d4e5f6`（相同时只显示一个） | delivered_settings_version / current_settings_version |
| 来源 | IP · UA 截断 40 字 | last_ip / last_user_agent |

轮询 30s；页面不可见（`document.hidden`）时暂停。

#### B2 页面与轮播

| 元素 | 组件 | 规格 |
|------|------|------|
| 轮播总开关 | switch「自动轮播」 | 绑定 rotation.enabled；关闭时停留秒数输入变灰但保留值 |
| 页面列表 | 5 行可拖拽列表（HTML5 Drag & Drop + 上/下移按钮作键盘与触屏替代） | 行序 = pages 顺序 |
| 行：拖拽把手 | icon | today 行无把手（固定首位），其它行可拖；拖拽目标不得位于 today 之上 |
| 行：启用 | checkbox | today 行禁用且勾选；其它行自由 |
| 行：页面名 | text | 字典 page_id |
| 行：停留秒数 | number input（min 5, max 3600, step 5） | 绑定 dwell_s；禁用页该输入灰显但保留值 |
| 让位秒数 | number input（min 0, max 3600） | rotation.suppress_s；辅助文案「触摸后暂停轮播的秒数」 |
| 行内提示 | 全部非今日页禁用时，列表下方灰字「仅今日页：不轮播、无翻页」 | — |

前端校验（与 limits 一致）：超范围即时红边并阻止保存。

#### B3 城市

| 元素 | 组件 | 规格 |
|------|------|------|
| 搜索框 | search input + 按钮「搜索」 | 防抖 400ms，1–50 字；加载态 spinner |
| 候选列表 | 下拉列表（≤10 项） | 每项「name · admin1 · country ／ lat, lon ／ timezone」；点击带入下方四字段并关闭列表 |
| 上游失败 | 行内提示「搜索服务暂不可用，请手动填写」 | GEOCODE_UPSTREAM_FAILED |
| name | input（1–20 字） | 必填 |
| latitude | number（-90~90，step 0.0001） | 必填 |
| longitude | number（-180~180，step 0.0001） | 必填 |
| timezone | input + datalist（内置常用 IANA 时区 20 项） | 必填；保存时服务端做最终校验 |
| 变更提示 | 四字段任一与已保存值不同 → 卡片角标「保存后天气将重新拉取」 | — |

#### B4 一言

| 元素 | 组件 | 规格 |
|------|------|------|
| 模式 | radio group（3 项，字典 quote_mode） | 绑定 quote.mode |
| 自定义列表 | 仅 mode=custom 显示；可增删的行列表 | 每行：text input（≤32 字，计数器）+ from input（≤16 字）+ 删除；底部「添加一条」（≤100 条时可用） |
| 预览文案 | 灰字显示「今日将显示：第 (dayOfYear % n) 条」 | 与服务端轮换规则一致 |
| 校验 | mode=custom 且 0 条 → 阻止保存并提示 | INV-3 |

#### B5 预览

| 元素 | 规格 |
|------|------|
| 网格 | 仅已启用页，按页序排列；每格缩略图宽 ≤240px（等比），标题为页名 |
| 图片 URL | `/dashboard.png?page={id}&v={settings_version}`，懒加载，加载失败显示占位「渲染中…」并 5s 后重试一次 |
| 放大 | 点击 → 原尺寸浮层（Esc/点击遮罩关闭） |
| 草稿提示 | 表单 dirty 时网格上方灰字「预览反映已保存配置，保存后更新」 |

#### B6 操作区

| 按钮 | 类型 | 行为 |
|------|------|------|
| 保存 | primary | 前端校验 → `settings.save` → 成功：toast「已保存，设备最迟 N 分钟后生效」、刷新 B1/B5、dirty 复位；失败：按 `details[].field` 定位到对应控件红边 + 顶部错误汇总 |
| 恢复默认 | danger-outline | confirm 对话框（列出默认城市与「五页全启用 120/30」）→ `settings.reset` → 同保存成功流程 |
| 导出 | default | `<a href="/admin/api/settings/export" download>` |
| 导入 | default | 隐藏 file input（accept .json）→ `settings.import` → 成功同保存；失败 toast 错误并保持表单不变 |
| 退出登录 | link（B0） | `auth.logout` → V1 |

## 5. 交互流程

```
进入 /admin
  → settings.get ─┬─ 渲染 B2/B3/B4（表单初值 = settings）
                  └─ 渲染 B5（已启用页缩略）
  → device.status → 渲染 B1，启动 30s 轮询
编辑任意字段 → dirty=true（顶栏「未保存」标记；beforeunload 提示）
点击保存 → 前端校验（limits）→ POST save
  ├─ 200 → 更新 settings_version → B1 立即刷新（预期 pending）→ B5 以新 v 重载 → toast
  └─ 400 → details 逐字段标红 → 不改动本地表单
城市变更保存 → 响应 weather_refreshed=false 时 toast 追加「天气暂未更新，将稍后重试」
设备拉取（外部）→ 下次轮询 B1 变 delivered
```

## 6. 状态与反馈规范

| 状态 | 表现 |
|------|------|
| 加载中 | 区块骨架灰条；按钮 loading 禁点 |
| 未保存 | 顶栏「● 未保存」；离开页面 beforeunload 确认 |
| 保存成功 | 绿色 toast 3s |
| 校验失败 | 控件红边 + 控件下方错误文案 + 顶部汇总（可点击跳转） |
| 会话过期（401） | 任一 Action 401 → 切 V1，保留表单草稿于内存，重新登录后恢复 |
| 管理端禁用（503） | 切 V0 |
| 设备未知 | B1 全部字段「—」，下发状态「未知」 |
| 降级运行 | B0 黄色横幅 |

## 7. 路由定义

| 路径 | 视图 | 说明 |
|------|------|------|
| `/admin` | V0 / V1 / V2 | 服务端按登录态渲染初始视图；前端无 hash 路由 |

## 8. 质量校验

| # | 检查项 | 结果 |
|---|--------|------|
| Q-1 | 所有 Action 在 api-web-admin.md 4.4.1 有对应端点（A-2~A-10 + 预览复用） | ✅ |
| Q-2 | 表单字段全部来源于 4.1 字段表，无臆造字段 | ✅ pages/rotation/quote/location 四组 |
| Q-3 | 前端校验范围与 limits/业务常量一致（5–3600 / 0–3600 / 100 / 32 / 16 / 1–20） | ✅ |
| Q-4 | 字典 Key 与 enum-pool §1 四枚举一致 | ✅ |
| Q-5 | 错误码全部有前端表现（AUTH_INVALID/LOCKED/CSRF/VALIDATION/IO/IMPORT/GEOCODE_*） | ✅ §4.3/§4.4/§6 |
| Q-6 | INV-1（today 首位启用）在 UI 结构上不可违反（无把手、禁用勾选、拖拽禁止越过） | ✅ |
| Q-7 | 预览仅反映已保存配置（BR-7） | ✅ dirty 提示 |
| Q-8 | 响应式与无构建约束声明 | ✅ 文档头 / §1 |
| Q-9 | 文档头属性表、版本 v{X.Y}、更新记录 | ✅ |

## 更新记录

| 版本 | 日期 | 更新说明 |
|------|------|---------|
| v1.0 | 2026-10-10 | initial：三视图、六区块字段级规格、10 个 Action、字典映射、交互流程与状态反馈、九项质量校验 |
