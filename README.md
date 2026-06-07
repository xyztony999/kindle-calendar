# Kindle 电子天气台历

把闲置 Kindle 变成低功耗、常亮的电子天气台历。**服务部署在云端**，Kindle 通过 WiFi 自行拉取 PNG，**无需 PC 常开**。

```
┌─────────────────────────────────────────────┐
│  2026年06月07日  农历四月廿二 乙巳年（蛇年） │
│  星期六  北京                               │
├─────────────────────────────────────────────┤
│  28°                                        │
│  晴                                          │
│  湿度 45%    风速 12 km/h                   │
├─────────────────────────────────────────────┤
│  06-07  06-08  06-09  …                    │
│  晴     多云    小雨   …                    │
├─────────────────────────────────────────────┤
│  2026年 6月                                 │
│  一  二  三  四  五  六  日                 │
│       1   2   3   4   5   6                 │
│   7   8   9  …                              │
└─────────────────────────────────────────────┘
```

## 工作原理

```
  云端（Render / Docker）              Kindle（越狱 + WiFi）
 ┌──────────────┐    HTTPS GET    ┌──────────────────────┐
 │ Flask 服务    │ ◄────────────── │ dash.sh 定时拉取     │
 │ Open-Meteo   │  /dashboard.png │ 或「脚本书」点书名   │
 │ Pillow 渲染   │                 │ eips 显示 PNG       │
 └──────────────┘                 └──────────────────────┘
        ▲
   部署一次，24h 在线
   PC 仅用于开发预览
```

## 推荐方案：云端部署 + Kindle 自主拉取

### 1. 部署到 Render（免费）

1. 将本项目推送到 GitHub
2. 登录 [Render](https://render.com) → New → Blueprint → 导入仓库
3. 在环境变量中修改城市与坐标：

| 变量 | 示例（PW2） |
|------|-------------|
| `LOCATION_NAME` | 北京 |
| `LATITUDE` | 39.9042 |
| `LONGITUDE` | 116.4074 |
| `TIMEZONE` | Asia/Shanghai |
| `SCREEN_WIDTH` | 758 |
| `SCREEN_HEIGHT` | 1024 |

4. 部署完成后得到地址，如 `https://kindle-calendar-xxxx.onrender.com/dashboard.png`

> Render 免费版闲置 15 分钟后会休眠，Kindle 首次拉取可能需等 ~30 秒唤醒。若介意延迟，可用 Docker 部署到 VPS 或家里树莓派。

### 2. Docker 自托管

**通用（本地 / VPS）：**

```bash
docker compose up -d
# 访问 http://你的服务器IP:8080/dashboard.png
```

**VPS 一键部署（推荐）：**

```bash
# 上传整个项目到服务器后执行
bash deploy.sh
```

`deploy.sh` 会构建镜像并通过 `docker-compose.image.yml` 启动容器，适合 SSH / 宝塔终端直接运行。

**宝塔面板 Docker 编排：**

1. 将项目放到 `/www/wwwroot/kindle-calendar`（路径可改，需同步修改 compose 文件）
2. 宝塔 → Docker → 编排 → 新建，Compose 文件选 `docker-compose.baota.yml`
3. 在编排环境变量中修改城市、坐标与屏幕分辨率
4. 部署后访问 `http://服务器IP:8080/dashboard.png`

> 宝塔「编排」界面构建有时不稳定，若失败请在宝塔终端执行 `bash deploy.sh`。

### 3. Kindle 端配置

**上传文件：**

```bash
# 复制配置模板，填入云端 URL
cp kindle/config.sh.example kindle/config.sh
# 编辑 SERVER_URL="https://kindle-calendar-xxxx.onrender.com/dashboard.png"

scp kindle/config.sh kindle/dash.sh kindle/lib/display.sh root@<Kindle的IP>:/mnt/us/kindle-calendar/
ssh root@<Kindle的IP> "chmod +x /mnt/us/kindle-calendar/*.sh /mnt/us/kindle-calendar/lib/*.sh"
```

**Kindle 端配置项**（`config.sh`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SERVER_URL` | — | 云端 `/dashboard.png` 地址 |
| `INTERVAL` | 900 | 刷新间隔（秒），建议 ≥ 900 |
| `FULL_REFRESH_EVERY` | 6 | 每 N 次局部刷新后全刷，减少残影 |
| `WIFI_ON_DEMAND` | false | false=保持 WiFi；true=拉完关 WiFi 省电 |
| `BOOK_FULLSCREEN` | false | 脚本书模式：false=按 Home 回书库；true=全屏沉浸 |
| `WIFI_WAIT` | 15 | 开 WiFi 后等待连接秒数 |

**方式 A：后台守护（`dash.sh`）**

```bash
ssh root@<Kindle的IP> "nohup /mnt/us/kindle-calendar/dash.sh &"
```

每 15 分钟自动拉取 PNG 并刷新，无需 PC 参与。

**方式 B：脚本书（推荐日常使用）**

1. 复制 `kindle/documents/天气台历.sh` 到 Kindle 的 `documents/` 目录
2. 确保 `/mnt/us/kindle-calendar/lib/display.sh` 已上传
3. 在书库中点击「天气台历」即可打开

默认 `BOOK_FULLSCREEN=false`：保留系统界面，**按 Home 键可返回书库**；设为 `true` 则关闭 framework 全屏沉浸（只能重启退出）。

**方式 C：KUAL 菜单**

将 `kindle/kual-extension/` 复制到 Kindle 的 `extensions/kindle-calendar/`，KUAL 中可启动/停止/立即刷新/查看日志。

Kindle 需**预先配好 WiFi**（至少越狱后 SSH 连一次，或在设置里保存过网络密码）。

## 前置条件

| 项目 | 说明 |
|------|------|
| Kindle 型号 | Paperwhite 2/3/5、Kindle 11 等均可，需**越狱** |
| 固件版本 | 取决于型号，参考 [KindleModding](https://kindlemodding.org/) 选择对应越狱方法 |
| 越狱后插件 | **KUAL** + **USBNetwork**（SSH 访问） |
| 电脑 | 仅开发预览时需要；正式使用部署云端即可 |

### 越狱指南（简要）

1. **开启飞行模式**，防止自动升级固件
2. 查看固件版本：设置 → 设备选项 → 设备信息
3. 按版本选择越狱方法：
   - 5.16.3 – 5.18.0 → [WinterBreak](https://kindlemodding.org/jailbreaking/WinterBreak/)
   - 5.18.1 – 5.18.5 → [AdBreak](https://kindlemodding.org/jailbreaking/AdBreak/)
   - 5.16.4 – 5.18.6（PW5/KT5/KOA3）→ [Nosebleed](https://kindlemodding.org/jailbreaking/Nosebleed/)
4. 安装 [Block OTA Updates](https://kindlemodding.org/) 阻止固件更新
5. 安装 **MRPI** + **KUAL** + **USBNetwork**

> 越狱有风险，请备份数据并仔细阅读官方文档。

## 快速开始（本地开发）

### 1. 安装依赖

```bash
cd kindle-calendar
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置

编辑 `config.yaml`：

```yaml
location_name: "上海"
latitude: 31.2304
longitude: 121.4737
timezone: "Asia/Shanghai"

screen:
  width: 1072    # 见下方分辨率表
  height: 1448
```

**常用分辨率**（越狱后 SSH 执行 `eips -i` 查看 `xres` / `yres` 确认）：

| 型号 | 分辨率 |
|------|--------|
| Kindle 4 | 600 × 800 |
| Paperwhite 2 | 758 × 1024 |
| Paperwhite 3 / 7代 | 1072 × 1448 |
| Paperwhite 5 / Kindle 11 | 1236 × 1648 |

经纬度可在 [Open-Meteo](https://open-meteo.com) 查询。

### 3. 本地预览

```bash
python scripts/preview.py          # 生成 preview.png
python -m server.app               # http://localhost:8080/dashboard.png
```

确认布局无误后再部署到云端与 Kindle。

## API 端点

| 路径 | 说明 |
|------|------|
| `GET /dashboard.png` | Kindle 拉取的 8 位灰度 PNG |
| `GET /weather` | 当前天气 JSON |
| `GET /health` | 健康检查 |

## 屏幕保护建议

- 刷新间隔建议 **≥ 15 分钟**（`dash.sh` / `config.sh` 中 `INTERVAL=900`）
- 每 6 次局部刷新后做一次全刷（`-f`），减少残影
- 不建议 24 小时插电，定期充放电延长电池寿命
- 保持飞行模式 + 阻止 OTA，防止固件升级导致越狱失效

## 故障排查

| 问题 | 解决方法 |
|------|----------|
| 白屏 / 花屏 | 检查 PNG 分辨率是否与 `eips -i` 一致，必须是 8 位灰度 |
| 无法拉取图像 | 检查 `config.sh` 中 URL 是否正确；Kindle 是否已配好 WiFi；查看 `/mnt/us/kindle-calendar/dash.log` |
| 首次拉取很慢 | Render 免费版冷启动约 30s，属正常现象 |
| 中文乱码 | 云端 Docker 已内置 Noto 字体；本地需在 `config.yaml` 指定 `font_path` |
| 脚本书无法退出 | 确认 `BOOK_FULLSCREEN=false`；按 Home 键返回书库 |
| 重复打开多个实例 | 脚本书会自动终止旧进程；后台模式检查是否多次运行 `dash.sh` |
| `eips: not found` | 确认已越狱，路径应为 `/usr/sbin/eips` |
| SSH 连不上 | 检查 USBNetwork 是否启用，Kindle IP 是否正确 |

## 项目结构

```
kindle-calendar/
├── Dockerfile                  # 云端部署
├── docker-compose.yml          # 通用 Docker 编排
├── docker-compose.baota.yml    # 宝塔面板专用编排
├── docker-compose.image.yml    # 仅启动已构建镜像
├── deploy.sh                   # VPS 一键构建部署
├── render.yaml                 # Render 一键部署
├── config.yaml                 # 本地开发配置
├── server/                     # Flask 渲染服务
├── kindle/
│   ├── dash.sh                 # 后台守护拉取
│   ├── config.sh.example       # Kindle 端配置模板
│   ├── lib/display.sh          # 公共显示 / WiFi 函数
│   ├── documents/天气台历.sh   # 脚本书入口
│   └── kual-extension/         # KUAL 菜单扩展
└── scripts/preview.py
```

## 扩展

- 添加 RSS 新闻、待办事项 → 修改 `renderer.py`
- 接入 Home Assistant → 用 Playwright 截图 HA 面板替代本渲染器
- 使用 [Online Screensaver](https://www.mobileread.com/forums/showthread.php?t=236104) KUAL 插件替代 `dash.sh`

## 许可

MIT
