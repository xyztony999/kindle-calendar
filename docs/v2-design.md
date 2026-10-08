# v2 设计定稿：电子翻页台历

> 2026-09-12 讨论定稿。核心思路：E-ink 的"动态感"来自**什么在变、多久变一次、变哪一块**，
> 而不是帧率。方案 = fbink 分区刷新 + 触摸翻页 + 云端数据/渲染分离，视觉走印刷杂志风。

## 1. 已拍板的决策

| 决策点 | 结论 |
|--------|------|
| 技术路线 | 分区刷新 + 触摸翻页（设备端引入 fbink + 触摸助手小二进制） |
| 页面集 | 今日大字页（首页）、一周预报页、月历网格页、天气详情页、老黄历页 |
| 视觉风格 | 印刷杂志风：衬线大字、报刊排版、大留白、灰阶抖动场景图 |
| 内容扩展 | 节气/节日/调休、个人 ICS 日历订阅、月相+日出日落、每日一句 |

## 2. 架构

```
 云端 Flask                          Kindle（越狱，沉浸模式）
 ┌────────────────────┐   JSON+PNG   ┌──────────────────────────┐
 │ /api/v1/dashboard  │ ◄─────────── │ dash.sh 主循环            │
 │   聚合: 天气/农历/  │  按需拉取    │   ├ 时钟: fbink 文本打印   │
 │   黄历/ICS/一言/    │              │   │  每分钟, A2, 零网络   │
 │   节假日/天文       │              │   ├ 拉取: JSON + 变化的   │
 │ /r/{page}/{region} │              │   │  分区 PNG, 分区重绘    │
 │   分区图(8位灰度)   │              │   └ 触摸: tapread 助手    │
 │ /dashboard.png     │              │     翻页/刷新/退出        │
 │   (v1 兼容, 保留)   │              │ lib/display.sh: fbink 封装│
 └────────────────────┘              └──────────────────────────┘
```

要点：

- **时钟不依赖网络**：设备端用 fbink 自带字体直接打印 `14:23`（A2 波形，快速清晰无闪），
  云端只负责"内容数据"。fbink 具体 flag 以 `fbink -h` 为准，镜像随 KUAL 扩展分发或
  交叉编译后放入 `kindle/bin/`。
- **服务端按分区出图**，每区一个 PNG（304 缓存），设备端只重绘变化的区域；
  `/dashboard.png` 整页合成图保留，v1 脚本和旧设备不破坏。
- **沉浸模式**：触摸交互要求 framework 停止（否则 framework 抢触摸事件）。
  退出方式：长按右上角 ≥2s 恢复系统 UI；KUAL 菜单 stop 仍然有效。

## 3. 数据协议

### `GET /api/v1/dashboard.json`

```jsonc
{
  "generated_at": "2026-09-12T14:23:00+08:00",
  "date": {
    "iso": "2026-09-12", "weekday": "六",
    "lunar": "八月初二", "ganzhi": "丙午年", "zodiac": "马",
    "solar_term": { "name": "白露", "at": "2026-09-07", "days_since": 5 },
    "festivals": ["教师节"],
    "holiday": { "type": "workday|holiday|swap", "note": "班|休" }
  },
  "weather": { "current": {}, "hourly": [], "daily": [], "aqi": {}, "uv": {} },
  "sun": { "sunrise": "06:12", "sunset": "18:45", "moon_phase": 0.73, "moon_name": "盈凸月" },
  "events": [ { "time": "09:00", "title": "周会", "source": "ics" } ],
  "quote": { "text": "山川湖海，皆是文章。", "from": "" },
  "almanac": { "yi": ["出行", "修置"], "ji": ["动土", "开市"], "wuhou": "雷始收声" },
  "pages": ["today", "week", "month", "detail", "almanac"],
  "regions_version": "b3f1..."   // 内容 hash，设备端据此判断哪些分区图变了
}
```

### 分区图

`GET /r/{page}/{region}.png`（8 位灰度，按屏幕分辨率渲染）
例：`/r/today/weather.png`、`/r/today/scene.png`、`/r/month/grid.png`。
时钟分区不存在——设备端 fbink 直接打印文字。

## 4. 页面与分区布局（以 PW2 758×1024 为基准，其他分辨率等比）

### 今日页 today（首页）

```
 y  56  ── 细规则线 + kicker：SEPTEMBER 2026 · 星期六        [每日]
 y 120      1 4 : 2 3   衬线大字时钟                        [每分钟·A2]
 y 340  ── 细规则线
 y 380      晴 · 26° → 18° · 湿度 45% · 风 12km/h           [随拉取]
 y 620      日出 06:12 ──弧线── 日落 18:45   ◐ 月相          [每日]
 y 760      ░▒▓ 灰阶抖动场景条（随天气的程序化线稿）           [随天气]
 y 950  「今日一言」 山川湖海，皆是文章。                      [每日]
```

### 其余页面

| 页 | 主要分区 | 节奏 |
|----|----------|------|
| week 一周页 | 7 天行（图标+高低温+降水）、温度曲线 | 随拉取 |
| month 月历页 | 月网格（农历/节气角标、调休"班"/假日"休"标记）、个人 ICS 事件点 | 每日 + ICS 变化 |
| detail 详情页 | AQI、紫外线、体感、逐小时温度条 | 随拉取 |
| almanac 老黄历页 | 竖排大字日期、双栏宜忌、节气物候 | 每日 |

页眉统一放当前页指示（·今日· 一周 月历 详情 黄历），翻页只重绘内容区、保留页眉页脚。

## 5. 刷新节奏总表

| 内容 | 节奏 | 波形/方式 |
|------|------|-----------|
| 时钟 | 每 60s | A2 局刷（fbink 文本打印） |
| 天气分区 | 拉取周期（默认 15–30min） | GC16 局刷 |
| 日历/黄历/一言/月相 | 每日 00:05 | 随首次拉取局刷 |
| 翻页/手动刷新 | 即时 | 内容区 GC16 局刷，保留页眉 |
| 清残影 | 每日 03:00 | 全刷 |

WiFi 仍按需开关（沿用 `WIFI_ON_DEMAND`）；JSON 仅几 KB，缓解 Render 冷启动痛点。

## 6. 触摸区映射（沉浸模式，tapread 助手读取 /dev/input/event*）

| 手势 | 动作 |
|------|------|
| 点左/右边缘（x < 80 或 x > 678） | 上一页 / 下一页（today→week→month→detail→almanac 循环） |
| 点右上角 | 手动刷新（开 WiFi 拉取） |
| 长按右上角 ≥ 2s | 退出：恢复 framework，回到书库 |
| 点底部中央 | 夜间反色开关（fbink invert） |

`tapread`：~50 行 C，静态编译；自动探测触摸设备（按 `/proc/bus/input/devices` 中的
名称匹配，路径因机型而异），向 stdout 输出 `x y` 行供 shell `read` 消费。

## 7. 服务端数据源

| 数据 | 来源 | 失败兜底 |
|------|------|----------|
| 天气 | Open-Meteo（现有） | 保留上次数据 + "更新于 hh:mm" 标注 |
| 农历/干支/节气/宜忌/物候 | `lunar-python`（纯本地计算，替代 zhdate） | 无需兜底 |
| 法定节假日/调休 | NateScarlet/holiday-cn 年度 JSON，启动时拉取缓存 | 内置本年度静态数据 |
| 日出日落/月相 | `astral` + 平朔望月周期内联计算 | 无需兜底 |
| 每日一言 | Hitokoto API | 仓库内置离线古诗词 JSON，按日轮换 |
| 个人日程 | 配置中的 ICS 链接（CalDAV/Google/Outlook 私链） | 跳过并标注 |

凭据约束：ICS 私链等含 token 的配置走环境变量（如 `KINDLE_ICS_URLS`，逗号分隔）或
不入库的本地 `config.yaml`；源码与示例文件中不得出现可用凭据字面量。

## 8. 视觉规范（印刷杂志风）

- 字体：思源宋体 Noto Serif CJK SC（Docker 内置）；拉丁数字用衬线体。
- 灰阶：严格 8-bit；场景图用 Bayer 8×8 有序抖动，程序化线稿（山/云/日/月剪影），
  不依赖外网图片。
- 排版 token：页边距 ≥ 56px；细规则线 1px/50% 灰；kicker 小字宽字距；
  大数字字高 ~220px；正文灰阶只用 0x00/0x44/0x88/0xFF 四档，减少局刷残影。

## 9. 代码结构（目标）

```
server/
  app.py          # 路由：/api/v1/dashboard.json、/r/...、/dashboard.png(v1)
  data.py         # 聚合编排 + 缓存（沿用 DashboardCache 思路）
  almanac.py      # lunar-python 封装
  astro.py        # 日出日落/月相
  holidays.py     # holiday-cn 缓存
  ics.py          # ICS 拉取解析（仅未来 7 天）
  quotes.py       # 一言 + 离线兜底
  render/
    style.py      # 设计 token、Bayer 抖动、字体
    regions.py    # 每页分区坐标定义（分辨率归一化）
    pages/        # today/week/month/detail/almanac 渲染器
kindle/
  bin/tapread     # 触摸助手（静态编译）
  bin/fbink       # 随扩展分发
  lib/display.sh  # fbink 封装：show_region / print_clock / invert / full_refresh
  dash.sh         # 主循环：时钟 + 拉取调度 + 触摸分发
  kual-extension/ # 菜单不变，增加「触摸模式」开关
```

## 10. 分期落地

- **P1（纯增量，先让图活起来）**：fbink 版 `display.sh` + 今日页分区渲染 + JSON API +
  设备端分钟级时钟。不动触摸。
- **P2（交互）**：tapread 助手 + 沉浸模式 + 翻页 + 5 页面集 + 触摸区映射。
- **P3（内容）**：ICS 订阅、黄历页、月相/日出日落、一言、月历调休标记、节假日数据。

每期独立可用，`/dashboard.png` 全程保留兼容。

## 11. P1 实现记录（2026-09-12）

P1 已完成并本地验证。与第 2~7 章设计的偏差：

| 设计稿 | 实际实现 | 原因 |
|--------|----------|------|
| 设备端 fbink 打印文字时钟 | 服务端渲染**时钟字形 PNG 集**（0-9 + 冒号），设备端 fbink 按坐标 A2 拼装、只重画变化的数字 | Kindle 设备字体不受控，无法保证衬线大字排版；字形下缓存后时钟仍零网络 |
| 设备端解析 JSON | 新增 `GET /api/v1/dashboard.env`（POSIX 可 source 的 key=value） | busybox sh 无 JSON 解析器；JSON 端点保留给测试与调试 |
| 日出日落用 `astral` | **内联 NOAA 算法**（`server/astro.py`），本地与 astral 交叉验证误差 ≤ 2 分钟 | astral 新版 API 破坏性变更（Observer/LocationInfo 分离），少一个依赖更稳 |
| 农历用 `zhdate` | 改用 `lunar-python`（`server/almanac.py`） | 顺带获得宜忌/物候/节气精确日期，黄历页（P2/P3）直接可用 |
| 节假日"内置静态兜底" | 仅内存缓存，拉取失败则不标注（优雅降级） | 避免手写年度数据出错；holiday-cn 源本身稳定 |
| 字体 Noto Serif | Docker 加装 `fonts-noto-cjk-extra` | Debian 下思源宋体的实际包名 |

设备端新增文件：`kindle/bin/README.md`（fbink 获取方式）。`dash.sh` 在
`API_URL` 未配置或无 fbink 时自动回退 v1 整图模式；脚本书与 KUAL「立即刷新」
仍是 v1 整图路径，P2 统一。

验证情况：模块冒烟（农历/节气/宜忌/物候/节假日/月相多日期断点）、NOAA vs
astral 五城市对比、渲染管线出图（图像审查通过：时钟完整居中、引言自适应）、
HTTP 全端点 200（含 ETag 304、非法路径 404）、设备 env source 模拟、
preview.py 端到端。待真机验收项：fbink 实机局刷效果与时钟 A2 残影表现。
