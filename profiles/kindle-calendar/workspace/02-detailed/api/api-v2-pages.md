# API / 契约设计：v2-pages（页面集与显示治理）

| 属性 | 值 |
|------|-----|
| 模块 | v2-pages |
| 版本 | v1.0 |
| 状态 | 待评审 |
| 最后更新 | 2026-10-09 |
| 输入 | prd-v2-pages.md v1.0 + 领域模型（本文 1.4） |
| 技术规约 | 无激活技术栈；HTTP/POSIX shell 契约按本模块通用规约（3.1） |

## 1. 模块设计概述

### 1.1 业务背景及目标

为五页面集、双模式导航、三月预裁翻月与启动清屏定义云端 HTTP 契约与设备端行为契约。本模块「接口」为三类：HTTP 端点（服务端）、env 变量契约（设备拉取清单）、行协议与启动序列（设备端运行时）。

### 1.2 边界说明

| 边界 | 说明 |
|------|------|
| 做 | env/json 载荷扩展、五页分区路由通用化、整图参数化、手势行协议、清屏与轮播契约 |
| 不做 | 数据源接入变更（weather/almanac/astro 等模块内部不变）、ICS（P3）、渲染算法细节（见交互设计） |

### 1.3 设计决策

| # | 决策 | 理由 |
|---|------|------|
| AD-0 | 管理模式声明：**不适用**——本模块为只读展示契约（GET-only，无自管/托管数据写入，无 CRUD 表） | 引擎混合模式针对主数据/业务流程类对象 |
| AD-1 | env 采用「页内分区」命名 `R_{PAGE}_{REGION}_*`，P1 的 `R_HEADER_*` 等旧名保留一个版本作别名 | 旧 dash.sh 不至于静默回退 v1；升级窗口后移除 |
| AD-2 | 手势助手行协议 `D x y` / `U x y`，长按由设备端计时长判定 | 助手零逻辑、可测、shell 可解析 |
| AD-3 | 触摸能力为设备本地事实（tapread 存在与否），不由服务端下发 | 服务端无法感知设备外设 |
| AD-4 | 轮播参数默认值由 env 下发、config.sh 本地覆盖 | 免烧录即可调参，弱网时用本地值 |
| AD-5 | 月历三月资产（prev/cur/next）独立 ETAG、同批预裁 | 翻月零流量（FR-4） |

### 1.4 领域对象总览

| 对象 | 分类 | 说明 |
|------|------|------|
| 页面资产集 PageAssetSet | **聚合根** | 页面→分区资产与指纹的一致性边界；设备端经它取资产 |
| 页面 Page | 实体 | page_id ∈ {today,week,month,detail,almanac}，含分区布局 |
| 分区 Region | 实体 | (page, name) 标识；rect/ETAG/png 资产 |
| 月历矩阵 MonthGrid | 值对象 | 月+每日格（农历角标/节气/节日/班休），预裁三份 |
| 轮播计划 RotationPlan | 值对象 | 页面→停留秒表 |
| 清屏策略 ClearPolicy | 值对象 | 触发时机→全刷动作 |
| 字形几何 GlyphGeometry | 值对象 | digit_w/h、colon_w、gap |
| 导航事件 NavEvent | 过程数据(P3) | D/U 行与坐标 |
| 页面焦点 PageFocus | 过程数据(P3) | 当前页 × 偏移月 × 反色 |
| 轮播计时器 | 过程数据(P3) | rotating / suppressed |

无子流程、无关联领域对象（数据源均在本系统支撑域内）。

### 1.5 上下文映射

| 对方 | 关系 |
|------|------|
| 数据聚合（S-01） | 下游：载荷组装引用其输出 |
| 页面渲染（S-02） | 下游：分区资产由渲染产出 |
| 缓存协商（S-03） | 平级：ETAG/指纹经本模块契约暴露 |
| v1 整图客户端 | 遵奉者：/dashboard.png 契约不变 |

## 2. 跨聚合根设计

不适用（单聚合根模块）。

## 3. 应用/基础设施层设计

### 3.1 接口规范

| 项 | 规约 |
|----|------|
| HTTP | GET-only；响应 PNG（image/png，带 ETag/304）或 text（env）/JSON |
| 坐标单位 | 像素（按部署配置的目标分辨率渲染，env 内同时下发 SCREEN_W/H） |
| 分辨率 | 单部署单分辨率（SCREEN_WIDTH/HEIGHT 环境变量），不按请求参数变化 |
| env 文件 | POSIX 可 source：`KEY=value` 或 `KEY="value"`，无换行值 |
| 手势行协议 | `D <x> <y>`（按下）/ `U <x> <y>`（抬起），坐标为屏幕像素 |

### 3.2 依赖与约束

- 依赖：数据聚合载荷、渲染分区资产、指纹/ETAG；
- 约束：所有端点只读幂等；env 内容必须可被 busybox ash 直接 source。

### 3.3 权限模型

不适用（无多用户鉴权；局域网/公网只读部署，凭据约束沿用项目安全基线：无凭据字面量）。

### 3.4 公共规范

| 枚举 | 取值 |
|------|------|
| page | today / week / month / detail / almanac |
| month asset | prev / cur / next（R_MONTH_GRID_{PREV,CUR,NEXT}） |
| 波形 | A2（时钟）/ GC16（内容）/ FULL（清屏/反色/残影治理） |

## 4. 聚合根详细设计：页面资产集

### 4.1 领域模型

资产结构（逻辑视图，无数据库）：

```
PageAssetSet
├── Page(today)  ── Region: header, weather, sun, scene, quote + GlyphGeometry(clock)
├── Page(week)   ── Region: header, list, chart
├── Page(month)  ── Region: header, title, grid×{prev,cur,next}
├── Page(detail) ── Region: header, hourly, indices
└── Page(almanac)── Region: header, main
```

不变量：
- INV-1 任一分区资产的 ETAG = 其 PNG 内容哈希前 32 位；
- INV-2 env 中下发的每个 `R_*_ETAG` 与 `/r/...` 响应 ETag 一致；
- INV-3 同一 REGIONS_VERSION 下，同 (page,region) 多次请求返回字节相同；
- INV-4 月历三份矩阵的月份 = 当月-1 / 当月 / 当月+1；
- INV-5 跨天或指纹变化后，REGIONS_VERSION 必然变化。

### 4.2 状态模型（页面焦点，设备端）

```
PageFocus = 当前页(5值循环) × 偏移月{-1,0,+1} × 反色{0,1}
轮播态 = rotating ⇄ suppressed(触摸后 ROTATE_SUPPRESS_S 内)
```

| 事件 | 迁移 |
|------|------|
| 点左/右边缘 | 当前页 ←/→（偏移月复位为 0），suppressed |
| 点左下/右下角（month 页） | 偏移月 ∓1（循环 [-1,+1]，越界不动），suppressed |
| 跨天 | 偏移月→0，全量刷新 |
| 轮播到期（rotating） | 当前页→下一页，偏移月复位 |
| 点底部中央 | 反色取反 + 全刷清屏重绘 |
| 长按右上角 ≥2s | 退出进程（恢复系统 UI） |

### 4.3 接口设计

#### 4.3.1 接口清单

| # | 端点/契约 | 方法 | 变更 |
|---|----------|------|------|
| I-1 | `/api/v1/dashboard.env` | GET | 扩展（多页分区+轮播参数+旧名别名） |
| I-2 | `/api/v1/dashboard.json` | GET | 扩展（pages/layout 多页） |
| I-3 | `/r/<page>/<region>.png` | GET | 通用化（page 白名单五页） |
| I-4 | `/r/today/clock/<glyph>.png` | GET | 不变 |
| I-5 | `/dashboard.png?page=<page>` | GET | 参数化（默认 today） |
| I-6 | tapread 行协议 | 本地 | 新增 |
| I-7 | 启动序列契约 | 本地 | 新增（清屏优先） |
| I-8 | display.sh 函数契约 | 本地 | 扩展（clear_screen/show_region/full_redraw） |

#### 4.3.2 接口详情

**I-1 `GET /api/v1/dashboard.env`**（关键新增变量；`…` 为既有变量）

```
PAGES="today week month detail almanac"
SCREEN_W=758  SCREEN_H=1024
# 逐页逐分区（示例 month 页）：
R_MONTH_TITLE_X=56   R_MONTH_TITLE_Y=…  R_MONTH_TITLE_W=…  R_MONTH_TITLE_H=…
R_MONTH_TITLE_URL="https://host/r/month/title.png"
R_MONTH_TITLE_ETAG="…"
R_MONTH_GRID_PREV_URL="…/r/month/grid-prev.png"  R_MONTH_GRID_PREV_ETAG="…"
R_MONTH_GRID_CUR_URL="…/r/month/grid.png"        R_MONTH_GRID_CUR_ETAG="…"
R_MONTH_GRID_NEXT_URL="…/r/month/grid-next.png"  R_MONTH_GRID_NEXT_ETAG="…"
# 其余页同构：R_TODAY_*、R_WEEK_*、R_DETAIL_*、R_ALMANAC_*
# 时钟（不变）：CLOCK_X/Y/DIGIT_W/DIGIT_H/COLON_W/GAP、CLOCK_GLYPH_URL_PREFIX
# 轮播默认值（config.sh 本地可覆盖）：
ROTATE_TODAY_S=120   ROTATE_OTHER_S=30
# 兼容别名（保留一个版本）：R_HEADER_*≡R_TODAY_HEADER_* 等 P1 名称
```

校验规则：值中不得出现换行/引号转义；URL 为本服务绝对地址。

**I-3 `GET /r/<page>/<region>.png`**

- page ∈ {today,week,month,detail,almanac}，region 白名单见 4.1（month 额外含 grid-prev/grid-next 别名 region）；
- 非法 404；命中返回 8 位灰度 PNG + ETag（INV-1）+ `Cache-Control: public, max-age=300`；If-None-Match 命中 304。

**I-5 `GET /dashboard.png?page=`**

- page 缺省 today；非法值回退 today 并记日志（v1 客户端不带参数，行为不变）。

**I-6 tapread 行协议**

- 输出（stdout，行缓冲）：`D 123 456` / `U 118 461`；
- 点击判定：D→U 间隔 < 1s 且位移 < 30px；长按判定：间隔 ≥ 2s；1~2s 间隔忽略（防误触缓冲）；
- 设备不可知热区由 dash.sh 判定（见 D4 交互设计热区表）。

**I-7 启动序列契约**

```
启动 → [清屏：fbink 全刷整屏（反色状态对应底色）]
     → 按 PageFocus 绘制当前页全部分区（GC16）
     → 绘制时钟（A2）
     → 进入主循环
```

规则：清屏不可跳过（BR-3）；无缓存资产时先拉取再按此序列。

**I-8 display.sh 函数契约**

| 函数 | 签约 |
|------|------|
| `clear_screen` | 全刷整屏，成功返回 0 |
| `fbink_img <png> <x> <y> <wfm> [flash]` | 不变 |
| `draw_page_regions <page>` | 按 env 坐标绘制该页全部分区 |
| `full_redraw` | 清屏 + 当前页全量 + 时钟 |

### 4.4 领域事件与集成

无 MQ/回调；唯一「事件」为跨天/指纹变化触发的资产重建（进程内）。

## 5. 模块清单汇总

### 5.1 端点清单

| 端点 | 用途 | 消费方 |
|------|------|--------|
| /api/v1/dashboard.env | 设备拉取清单 | dash.sh v2.1 |
| /api/v1/dashboard.json | 调试/外部集成 | 维护者 |
| /r/<page>/<region>.png | 分区资产 | dash.sh / 浏览器 |
| /r/today/clock/<g>.png | 时钟字形 | dash.sh |
| /dashboard.png?page= | 整图 | v1 客户端 / 预览 |
| /health /weather | 观测 | 维护者 |

### 5.2 SQL 清单

不适用（无数据库）。

## 6. 更新记录

| 版本 | 日期 | 更新说明 |
|------|------|---------|
| v1.0 | 2026-10-09 | initial：五页契约、env 扩展与 P1 别名、tapread 行协议、启动清屏契约、页面焦点状态机 |
| v1.1 | 2026-10-09 | 实现对齐：月历三资产统一 PREV/CUR/NEXT 后缀（与 I-1 示例一致）；实现偏差记录见 prd-v2-pages.md 附录 |

## 附录：实现偏差记录（代码阶段，2026-10-09/10 真机迭代）

| 设计 | 实现 | 原因 |
|------|------|------|
| 交互规范 §5「无网络 → 页眉追加更新于 hh:mm 角标」 | 未实现，仅日志 | 设备端无文本渲染能力；离线时恰好无法拉取新页眉资产，角标依赖网络自相矛盾 |
| tapread 长按由设备端 D/U 时间差判定 | 按 dash.sh 主循环 1s tick 采样计时 | shell 行协议无时间戳，精度 ±1s，2s 阈值下可接受 |
| env 轮播参数服务端下发默认值 + config.sh 本地覆盖 | config.sh 在 env 同步后恢复本地值（LOCAL_* 捕获） | env 每次 source 会覆盖本地配置 |
| 翻月仅底部角区点击 | 增加**滑动手势**（水平 >50px：月历页=翻月，其余页=翻页），角区扩大到 110px | 真机反馈角落热区不好点 |
| 残影治理仅凌晨 03:00 全刷 | 增加**每轮播一圈回今日页全刷清一次** + 今日页 clockblank 白底分区（盖住时钟字形缝隙） | 真机反馈轮播残影逐圈累积、只能反色手清 |
| 触摸检测到 tapread 即进沉浸 | TOUCH_MODE=auto：90s 验证窗口收到真实事件才沉浸；沉浸后 300s 无事件看门狗自动恢复 | tapread 曾因 SIGILL 全程未运行，导致用户被锁死在沉浸（只能电源键重启） |
| tapread 常规 libc 构建 | freestanding 裸 syscall（-nostdlib，零除法，NEON/VFP=0） | PW2 上静态 glibc 的 NEON/除法路径触发 Illegal instruction；glibc 对 3.0 内核亦有兼容风险 |
| 退出沉浸直接恢复 framework | 恢复后 lipc 拉回主页 booklet | framework 会尝试续启被停掉的脚本书并弹「无法启动选定程序」 |
| 时钟冒号字形本地存 `:.png` | 改存 `colon.png` | /mnt/us 文件系统不允许文件名含冒号（EINVAL） |
| 翻页按 ETAG 增量绘制 | 翻页一律 force 全量重绘（仅拉取周期用增量） | 回到内容未变的页时全部跳过重绘，本地时钟却重绘，形成叠加 |
