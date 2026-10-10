# Kindle 电子天气台历

[English](README.en.md)

把闲置 Kindle 变成低功耗、常亮的电子翻页天气台历。**服务部署在云端**，Kindle 通过 WiFi 自行拉取分区 PNG，**无需 PC 常开**。浏览器里的 [Web 管理端](#web-管理端) 可以改页面、城市、轮播和页脚一言，设备下次拉取即生效。

五个页面循环：**今日**（日期、分钟级时钟、当前天气、日出日落与空气质量、场景图）→ **一周** → **月历**（班休标注，可跨月）→ **详情**（逐时温度与生活指数）→ **黄历**。页脚是每日一言。无触摸时按停留时间自动轮播；装了触摸助手后可以点按或滑动翻页。

## 工作原理

```
  云端（Render / Docker）                 Kindle（越狱 + WiFi + fbink）
 ┌──────────────────────┐  env + PNG    ┌────────────────────────────┐
 │ Flask 服务            │ ◄──────────── │ dash.sh 主循环              │
 │ ├ /api/v1/dashboard  │  按需拉取     │ ├ 时钟：本地字形，每分钟 A2  │
 │ │  天气/农历/节气/    │               │ │  局刷，零网络              │
 │ │  AQI/一言/节假日    │               │ ├ 分区图：ETAG 变化才拉取   │
 │ ├ /r/<page>/*.png    │               │ │  GC16 局刷                │
 │ ├ /admin             │               │ └ 凌晨 03:00 与每轮播一圈   │
 │ └ /dashboard.png     │               │    全刷清残影               │
 │   (v1 整图兼容)       │               │ (无 fbink 时回退 eips 整图) │
 └──────────────────────┘               └────────────────────────────┘
```

云端把天气、历法和节假日渲染成灰度分区图，并在 `/api/v1/dashboard.env` 里下发页面顺序、坐标、ETAG 和轮播秒数。Kindle 只在内容变化时拉取对应分区。

## Web 管理端

浏览器打开 `https://你的服务/admin`。可配置：

- 一周 / 月历 / 详情 / 黄历的启用与顺序（今日页固定为首页）
- 轮播总开关、每个已启用页面的停留秒数、触摸后暂停轮播的秒数
- 城市：按名称搜索（Open-Meteo），自动填入经纬度与时区；也可手填
- 页脚一言：在线一言、离线诗词，或自定义文案列表
- 各页预览、配置导入 / 导出、恢复默认、设备最近一次拉取是否已拿到新配置

登录口令来自环境变量 `ADMIN_PASSWORD`。未设置时 `/admin` 只显示「管理端未启用」。`SECRET_KEY` 用于会话签名，建议固定一个随机值，否则每次重建容器都要重新登录。设置保存在 `data/settings.json`；Docker 需挂载 `./data:/app/data`，否则容器重建后设置丢失。这两项只写在服务器的 `.env` 里，不要放进镜像或 GitHub。详见 [DEPLOY.md](DEPLOY.md)。

保存后 Kindle 在下一次拉取时生效（默认最长约 15 分钟，也可在设备上点右上角立即刷新）。拉取成功后以云端值为准，设备 `config.sh` 里的轮播秒数只在拉取失败时兜底。要让「按页停留」和「轮播终点随页序变化」生效，设备上的 `dash.sh` 也需要是当前版本。

## 推荐方案：云端部署 + Kindle 自主拉取

### 1. 部署到 Render（免费）

1. 将本项目推送到 GitHub
2. 登录 [Render](https://render.com) → New → Blueprint → 导入仓库
3. 在环境变量中修改城市、坐标，并设置管理端口令：

| 变量 | 示例（PW2） | 说明 |
|------|-------------|------|
| `LOCATION_NAME` | 北京 | 未在管理端保存城市时的默认值 |
| `LATITUDE` | 39.9042 | 同上 |
| `LONGITUDE` | 116.4074 | 同上 |
| `TIMEZONE` | Asia/Shanghai | 同上 |
| `SCREEN_WIDTH` | 758 | 必须与 Kindle 分辨率一致 |
| `SCREEN_HEIGHT` | 1024 | 同上 |
| `ADMIN_PASSWORD` | （自定） | 管理端登录口令；留空则管理端禁用 |
| `SECRET_KEY` | `openssl rand -hex 32` | 会话签名 |

4. 部署完成后得到地址，如 `https://kindle-calendar-xxxx.onrender.com/dashboard.png`，管理端为同主机的 `/admin`

> Render 免费版闲置约 15 分钟后会休眠，且没有持久磁盘：服务重启后管理端设置会回到环境变量默认值。若要设置长期保留，用下面的 Docker 并挂载 `data/`。

### 2. Docker 自托管

**通用（本地 / VPS）：**

```bash
docker compose up -d
# 画面 http://服务器IP:8080/dashboard.png
# 管理端 http://服务器IP:8080/admin
```

同目录可放 `.env`（模板见 `.env.example`）覆盖城市、分辨率、`ADMIN_PASSWORD` 和 `SECRET_KEY`。

**VPS 一键部署：**

```bash
bash deploy.sh
```

`deploy.sh` 会构建镜像并通过 `docker-compose.image.yml` 启动容器。

**宝塔面板 Docker 编排：**

1. 将项目放到 `/www/wwwroot/kindle-calendar`
2. 宝塔 → Docker → 编排 → 新建，Compose 文件选 `docker-compose.baota.yml`
3. 用同目录 `.env` 填写城市、分辨率和管理端口令
4. 部署后访问 `http://服务器IP:8080/dashboard.png`

> 宝塔「编排」界面构建有时不稳定，若失败请在宝塔终端执行 `bash deploy.sh`。

**CI/CD 自动部署（长期使用推荐）：**

推送 `master` 后 GitHub Actions 构建镜像 → 推送到阿里云 ACR → SSH 到服务器拉取重启。服务器不访问 GitHub / Docker Hub。一次性配置、口令与 `data/` 挂载见 [DEPLOY.md](DEPLOY.md)。不想配 CI 时也可用 `./deploy-remote.sh root@服务器IP`。

### 3. Kindle 端配置

**上传文件：**

```bash
cp kindle/config.sh.example kindle/config.sh
# 编辑 API_URL="https://你的服务/api/v1/dashboard.env"

scp kindle/config.sh kindle/dash.sh root@<Kindle的IP>:/mnt/us/kindle-calendar/
scp -r kindle/lib kindle/bin root@<Kindle的IP>:/mnt/us/kindle-calendar/
ssh root@<Kindle的IP> "chmod +x /mnt/us/kindle-calendar/*.sh /mnt/us/kindle-calendar/lib/*.sh"
```

**v2 分区模式需要 [fbink](https://github.com/NiLuJe/FBInk)**（方法见 `kindle/bin/README.md`，放到 `/mnt/us/kindle-calendar/bin/fbink`）。没有 fbink 时 `dash.sh` 自动回退为定时拉取整张 `/dashboard.png`。

**Kindle 端配置项**（`config.sh`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_URL` | — | 云端 env 端点，分区模式入口 |
| `CLOCK_ENABLED` | 1 | 分钟级时钟（本地跳字，不耗网络） |
| `ROTATE_ENABLED` | 1 | 自动轮播。env 拉取成功后以云端为准 |
| `ROTATE_TODAY_S` / `ROTATE_OTHER_S` | 120 / 30 | 仅 env 拉取失败时的停留兜底 |
| `ROTATE_SUPPRESS_S` | 120 | 仅 env 拉取失败时的触摸让位兜底 |
| `TOUCH_MODE` | force | `force` 有 tapread 即进沉浸；`auto` 先验证触摸；`off` 纯轮播 |
| `SERVER_URL` | — | v1 整图地址（回退模式） |
| `INTERVAL` | 900 | 拉取间隔（秒），建议 ≥ 900；时钟不受此限 |
| `FULL_REFRESH_EVERY` | 6 | 仅 v1：每 N 次局部刷新后全刷 |
| `WIFI_ON_DEMAND` | false | false 保持 WiFi；true 拉完关 WiFi |
| `BOOK_FULLSCREEN` | false | 脚本书：false 按 Home 回书库；true 全屏沉浸 |
| `WIFI_WAIT` | 15 | 开 WiFi 后等待秒数 |

**触摸（可选）**：按 `kindle/bin/README.md` 准备 `tapread`，放到 `bin/` 后自动启用。左右边缘或水平滑动翻页；月历页滑动翻月；右上角单击立即刷新，长按约 2 秒退出沉浸；底部中央切换夜间反色。启动时先全刷清屏。

**方式 A：后台守护（`dash.sh`）**

```bash
ssh root@<Kindle的IP> "nohup /mnt/us/kindle-calendar/dash.sh &"
```

**方式 B：脚本书**

1. 复制 `kindle/documents/天气台历.sh` 到 Kindle 的 `documents/`
2. 确保已上传 `/mnt/us/kindle-calendar/lib/display.sh`
3. 在书库中点「天气台历」看中文画面。同目录的 `WeatherCalendar.sh` 是英文画面。带空格的 `Weather Calendar.sh` 仍进入中文。

默认 `BOOK_FULLSCREEN=false` 时按 Home 返回书库。设为 `true` 后只能重启退出。

**方式 C：KUAL 菜单**

将 `kindle/kual-extension/` 复制到 Kindle 的 `extensions/kindle-calendar/`，可启动、停止、立即刷新、查看日志。

Kindle 需预先配好 WiFi。

## 前置条件

| 项目 | 说明 |
|------|------|
| Kindle 型号 | Paperwhite 2/3/5、Kindle 11 等，需越狱 |
| 固件 | 按型号参考 [KindleModding](https://kindlemodding.org/) |
| 越狱后 | **KUAL** + **USBNetwork**（SSH） |
| 电脑 | 只在开发和预览时需要 |

### 越狱（简要）

1. 开启飞行模式，避免自动升级固件
2. 设置 → 设备选项 → 设备信息，查看固件版本
3. 按版本选择方法：
   - 5.16.3 – 5.18.0 → [WinterBreak](https://kindlemodding.org/jailbreaking/WinterBreak/)
   - 5.18.1 – 5.18.5 → [AdBreak](https://kindlemodding.org/jailbreaking/AdBreak/)
   - 5.16.4 – 5.18.6（PW5/KT5/KOA3）→ [Nosebleed](https://kindlemodding.org/jailbreaking/Nosebleed/)
4. 安装 Block OTA Updates，再安装 **MRPI** + **KUAL** + **USBNetwork**

越狱有风险，请先备份并阅读官方文档。

## 本地开发

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
```

复制 `config.example.yaml` 为 `config.yaml`，填写城市与分辨率。越狱后可在设备上执行 `eips -i` 核对 `xres` / `yres`。

| 型号 | 分辨率 |
|------|--------|
| Kindle 4 | 600 × 800 |
| Paperwhite 2 | 758 × 1024 |
| Paperwhite 3 / 7 代 | 1072 × 1448 |
| Paperwhite 5 / Kindle 11 | 1236 × 1648 |

```bash
python scripts/preview.py    # 生成 preview.png
# 管理端（PowerShell 示例）
$env:ADMIN_PASSWORD = "本地口令"
python -m server.app         # http://localhost:8080/dashboard.png 与 /admin
```

云端部署用环境变量覆盖 `config.yaml`，无需把该文件放进镜像。

## API

| 路径 | 说明 |
|------|------|
| `GET /api/v1/dashboard.json` | 台历数据（天气、农历、节气、黄历、空气质量、一言、节假日、已启用页序） |
| `GET /api/v1/dashboard.env` | 设备用 POSIX env：分区坐标 / URL / ETAG、页序、每页轮播秒数 |
| `GET /r/<page>/<region>.png` | 分区灰度图。`page` 为 today / week / month / detail / almanac |
| `GET /r/today/clock/<g>.png` | 时钟字形（0–9 与 `:`） |
| `GET /dashboard.png?page=` | 整页合成图，默认 today |
| `GET /admin` | Web 管理端 |
| `GET /weather` | 当前天气 JSON |
| `GET /health` | 健康检查 |

## 屏幕与用电

- 拉取间隔建议 ≥ 15 分钟（`INTERVAL=900`）。时钟每分钟局部刷新，不走网络
- 每天凌晨 03:00 全刷一次；轮播每走完一圈回到今日页时再全刷一次，减轻残影
- 不建议长期插电，定期充放电
- 保持阻止 OTA，避免固件升级破坏越狱

## 故障排查

| 问题 | 处理 |
|------|------|
| 白屏 / 花屏 | PNG 分辨率须与 `eips -i` 一致，且为 8 位灰度 |
| 拉不到图 | 核对 `config.sh` 的 URL、WiFi，以及 `/mnt/us/kindle-calendar/dash.log` |
| 首次拉取很慢 | Render 免费版冷启动约 30 秒 |
| 中文乱码 | Docker 镜像已含 Noto 字体；本地在 `config.yaml` 设置 `font_path` |
| `/admin` 显示未启用 | 设置 `ADMIN_PASSWORD` 后重建容器 |
| 管理端设置重启后丢失 | 确认挂载了 `./data:/app/data`。Render 免费版无持久盘，重启会回到环境变量默认值 |
| 改了轮播但设备不变 | 更新设备上的 `dash.sh`，并点右上角刷新或等待一个 `INTERVAL` |
| 脚本书无法退出 | `BOOK_FULLSCREEN=false` 时按 Home。沉浸模式可长按右上角约 2 秒 |
| 重复打开多个实例 | 脚本书会停掉旧进程；后台模式不要多次启动 `dash.sh` |
| `eips: not found` | 确认已越狱，路径为 `/usr/sbin/eips` |
| SSH 连不上 | 确认 USBNetwork 已开，IP 正确 |

## 项目结构

```
kindle-calendar/
├── Dockerfile
├── docker-compose.yml          # 通用编排（含 data 卷与管理端变量）
├── docker-compose.acr.yml      # GitHub Actions → 阿里云 ACR
├── docker-compose.baota.yml    # 宝塔编排
├── docker-compose.image.yml    # 只启动已构建镜像
├── deploy.sh / deploy-remote.sh
├── DEPLOY.md                   # CI/CD 与服务器 .env
├── render.yaml
├── config.example.yaml
├── server/
│   ├── app.py                  # 路由
│   ├── admin.py                # 管理端 API
│   ├── settings.py             # 配置校验与 settings.json
│   ├── templates/admin.html    # 管理端页面
│   ├── service.py              # 缓存、分区渲染、env
│   ├── data.py / weather.py / aqi.py
│   ├── almanac.py / astro.py / holidays.py / quotes.py
│   └── render/                 # 五页分区渲染
├── kindle/
│   ├── dash.sh
│   ├── config.sh.example
│   ├── lib/display.sh
│   ├── bin/                    # fbink、tapread（见 bin/README.md）
│   ├── documents/天气台历.sh
│   └── kual-extension/
├── tests/test_web_admin.py
└── scripts/preview.py
```

## 现状与后续

- 已完成：分区刷新、分钟级时钟、五页、触摸与轮播、月历跨月、启动清屏、空气质量、Web 管理端
- 未做：日历订阅（ICS）、多城市切换、在管理端里改设备拉取间隔

设计过程记录在 `profiles/kindle-calendar/workspace/`。

## 许可

本项目以 [GNU General Public License v3.0](LICENSE) 发布。你可以自由使用、修改和再发行，但再发行时必须提供完整源码，并且修改版也必须使用 GPL-3.0。版权 © 2026 Xinyi Zhang。
