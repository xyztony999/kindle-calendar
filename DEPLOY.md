# 自动化部署流水线（GitHub → 阿里云）

推送代码到 GitHub 后全自动部署：**GitHub Actions 构建镜像 → 推送到阿里云 ACR（容器镜像服务）→ SSH 到服务器拉取新镜像并重启容器**。

服务器全程只访问阿里云 ACR（国内链路，速度快），**不需要访问 GitHub / Docker Hub**，规避国内网络问题。

```
 本地 push                 GitHub Actions            阿里云 ECS（宝塔）
┌──────────┐  git push  ┌──────────────┐  推镜像  ┌──────────────────┐
│ 开发机    │ ─────────► │ 构建镜像      │ ──────► │ ACR 仓库（国内）  │
└──────────┘            │ （境外 runner）│         └────────┬─────────┘
                        └──────┬───────┘                  │ 拉取（快）
                          SSH 触发部署                     ▼
                        ┌──────────────────────────────────┐
                        │ docker compose pull && up -d     │
                        └──────────────────────────────────┘
```

## 一次性配置（约 10 分钟）

### 1. 开通阿里云 ACR 并创建镜像仓库

1. 打开 [阿里云容器镜像服务控制台](https://cr.console.aliyun.com)，开通**个人版**（免费）
2. 「实例列表 → 个人实例 → 命名空间」：创建一个命名空间（如 `xyztony`）
3. 「仓库管理 → 创建仓库」：命名空间选刚才的，仓库名 `kindle-calendar`，**私有**，代码源选「本地仓库」
4. 「访问凭证」：设置**固定密码**（记下用户名，通常是阿里云账号全名）

你的完整镜像地址直接在仓库详情页点「公网地址」复制，常见两种格式（新开通的个人版都是第 2 种）：

- 老版：`registry.cn-<地域>.aliyuncs.com/<命名空间>/kindle-calendar`
- 新版个人版实例：`crpi-<实例ID>.<地域>.personal.cr.aliyuncs.com/<命名空间>/kindle-calendar`

拆分方法：去掉 `<命名空间>/kindle-calendar` 之前的部分填 `ACR_REGISTRY`，命名空间填 `ACR_NAMESPACE`。

### 2. 创建部署专用 SSH 密钥

在本地执行：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/kindle_deploy -C "kindle-calendar-deploy"   # 一路回车
cat ~/.ssh/kindle_deploy.pub
```

把公钥追加到**服务器**的 `/root/.ssh/authorized_keys`（宝塔终端执行即可）：

```bash
echo "ssh-ed25519 AAAA... kindle-calendar-deploy" >> /root/.ssh/authorized_keys
```

验证免密登录可用：`ssh -i ~/.ssh/kindle_deploy root@服务器IP`。

> 如果本地已有惯用的服务器密钥（如阿里云 ECS 创建时绑定的密钥对 `.pem`），
> 可以不新建——把现有私钥内容直接填进 `DEPLOY_SSH_KEY` secret 即可。
> 新建专用密钥的好处是权限隔离，部署凭证泄露不影响你日常登录的密钥。

### 3. 配置 GitHub Secrets

GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret，逐个添加：

| Secret | 值 | 说明 |
|--------|-----|------|
| `ACR_REGISTRY` | `crpi-xxxx.cn-beijing.personal.cr.aliyuncs.com` | ACR 注册地址（新版个人版格式；老版形如 `registry.cn-hangzhou.aliyuncs.com`，不含命名空间） |
| `ACR_NAMESPACE` | 命名空间名称 | ACR 命名空间 |
| `ACR_USERNAME` | 阿里云账号 | 「访问凭证」页显示的用户名 |
| `ACR_PASSWORD` | 固定密码 | 第 1 步设置的 |
| `DEPLOY_HOST` | `47.x.x.x` | 服务器公网 IP |
| `DEPLOY_USER` | `root` | SSH 用户 |
| `DEPLOY_SSH_KEY` | 私钥内容 | `cat ~/.ssh/kindle_deploy` 的**全部输出**（含 BEGIN/END 行） |
| `DEPLOY_PORT` | `22` | 可选，改过 SSH 端口才需要 |

> 部署路径固定为 `/www/wwwroot/kindle-calendar`（与 deploy-remote.sh 默认一致），
> 如需更换请改 workflow 里 SSH 脚本的 `cd` 行。

### 4. 初始化服务器（首次执行一次）

流水线部署时 SSH 只做「login + pull + up -d」，不会向服务器上传任何文件，
因此需要一次性把 `docker-compose.acr.yml` 和 `.env` 放到服务器项目目录。

方式一（服务器上已有项目，如迁移时上传过）：只需把新增的
`docker-compose.acr.yml` 和 `.env.example` 上传到项目目录（宝塔文件管理或 scp），
然后创建 `.env`（见下方）。

方式二（全新服务器）：从本地把项目完整同步上去（Windows Git Bash / macOS / Linux 均可）：

```bash
./deploy-remote.sh root@服务器IP

# 服务器仅允许密钥登录时，用 -i 指定密钥（如阿里云 ECS 密钥对）：
./deploy-remote.sh -i ~/.ssh/aliyun.pem root@服务器IP
```

若常用密钥登录，推荐在本地 `~/.ssh/config` 配置别名，之后所有 ssh/scp
都免参数：

```
Host kindle-server
    HostName 服务器IP
    User root
    Port 22
    IdentityFile ~/.ssh/aliyun.pem
```

配好后直接 `./deploy-remote.sh kindle-server` 即可。

它会把项目（含 compose 文件）打包上传、在服务器本地构建镜像并启动，
服务即刻可用——不必等 ACR 与 Secrets 配置完成，也算对服务器环境的整体验证。
首次流水线部署后会自动切换为 ACR 镜像。

然后在服务器上创建配置文件 `.env`：

```bash
cd /www/wwwroot/kindle-calendar
cp .env.example .env
vi .env   # 改城市/坐标/分辨率；ACR_IMAGE 填第 1 步复制的镜像地址
```

同时确认服务器防火墙与阿里云安全组已放行 **8080**（见 README 迁移章节）。

> 注意：`deploy-remote.sh` 走服务器本地构建，需要已配置 Docker 镜像加速；
> 后续走 GitHub Actions 的 CI/CD 部署则不需要镜像加速（服务器只从 ACR 拉取）。

### 5. 触发首次自动部署

把本仓库所有新文件提交推送：

```bash
git add .github docker-compose.acr.yml docker-compose.image.yml deploy-remote.sh .env.example DEPLOY.md
git commit -m "ci: 阿里云 ACR + GitHub Actions 自动部署"
git push
```

推送后到 GitHub 仓库 → Actions 页面观察 `Deploy to Aliyun` 流水线；
也可随时点 `Run workflow` 手动部署。

看到最后一步输出 `==> 部署完成` 即成功。浏览器访问 `http://服务器IP:8080/dashboard.png` 确认。

### 6. 图片素材存储（可选：管理端上传图片积木）

图片积木的素材保存在阿里云 OSS（不经服务器磁盘），未配置时管理端会自动禁用「上传图片」按钮。需要用图片积木时：

1. 开通 [对象存储 OSS](https://oss.console.aliyun.com)，创建一个**私有** Bucket（地域任选，与 ECS 同地域可用内网 Endpoint）
2. RAM 访问控制创建子用户并生成 AccessKey，授权只需该 Bucket 的 `PutObject / GetObject / DeleteObject`（最小权限）
3. 在服务器 `.env` 追加以下变量后重启容器：

   ```bash
   OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com   # Bucket 概览页的 Endpoint
   OSS_BUCKET=你的Bucket名
   OSS_ACCESS_KEY_ID=子用户AccessKeyId
   OSS_ACCESS_KEY_SECRET=子用户AccessKeySecret  # 只写在服务器 .env，不要提交、不要进 GitHub
   OSS_PREFIX=calendar/                        # 可选，对象 key 前缀
   ```

   ```bash
   cd /www/wwwroot/kindle-calendar && docker compose -f docker-compose.acr.yml up -d
   ```

> 各 docker-compose 编排文件已透传上述变量。素材读取失败时设备画面会显示「缺图占位框」而非无提示的白板，`docker logs kindle-calendar` 中有 `OSS 读取失败` / `OSS 未配置` 告警可排查。

### 7. 设备脚本自更新（2026-10 起）

镜像内置 `kindle/dash.sh` 并通过 `/api/v1/script` 下发；env 携带 `DASH_MD5`。设备端每个拉取周期比对校验和，不一致时自动下载→md5 校验→原子替换（备份 `dash.sh.old`）→重启，日志见设备端 `dash.log` / `update.log`。

- **引导**：现役设备上的旧版 dash.sh 没有自更新逻辑，**升级到本机制需要最后一次手动拷贝**新版 dash.sh；此后服务端更新设备脚本全自动。
- 关闭：设备 `config.sh` 加 `DASH_AUTOUPDATE=0`。
- 校验失败保留旧版，下个周期自动重试；`lib/display.sh` 等其他设备文件不在自更新范围。

## 日常使用

- **改代码后**：`git push` 即可，约 2~3 分钟自动上线（构建有缓存会更快）
- **只改配置**（城市/分辨率等）：SSH 到服务器改 `.env`，然后 `docker compose -f docker-compose.acr.yml up -d`
- **管理端口令**：写在服务器 `/www/wwwroot/kindle-calendar/.env` 的 `ADMIN_PASSWORD`（可另加 `SECRET_KEY`）。Actions 只构建镜像并 `pull` / `up -d`，不会覆盖这份 `.env`，也不会把口令打进镜像。改完执行一次 `mkdir -p data && docker compose -f docker-compose.acr.yml up -d`。`data/` 挂进容器，页面和城市设置在重新部署后还在。编排文件本身不随镜像更新，这次需把仓库里新的 `docker-compose.acr.yml` 同步到服务器一次。
- **手动重新部署**：Actions → Deploy to Aliyun → Run workflow
- **查看日志**：宝塔 → Docker → 容器日志，或 `docker logs -f kindle-calendar`

## 回滚

每次部署都会在 ACR 留一个以 commit SHA 命名的镜像标签。回滚到某次提交：

```bash
# 服务器上，把 .env 里的 ACR_IMAGE 改成指定 SHA 的标签
ACR_IMAGE=crpi-xxxx.cn-beijing.personal.cr.aliyuncs.com/你的命名空间/kindle-calendar:<commit-SHA>
vi .env && docker compose -f docker-compose.acr.yml up -d
```

## 两种部署方式对比

| | GitHub Actions（推荐） | deploy-remote.sh |
|---|---|---|
| 触发方式 | push 自动 | 手动执行一条命令 |
| 构建位置 | GitHub 服务器 | 你的阿里云服务器 |
| 需要镜像加速 | 否（服务器只拉 ACR） | 是（服务器要 docker build） |
| 需要配置 | ACR + Secrets（一次性） | 无 |

## 常见问题

| 问题 | 解决方法 |
|------|----------|
| Actions 推镜像报 `denied: requested access` | ACR 用户名/密码错，或仓库未创建；确认用的是「访问凭证」的固定密码而非阿里云登录密码 |
| SSH 步骤连不上 | 确认 `DEPLOY_HOST`/`DEPLOY_PORT` 正确；服务器安全组放行了 Actions 出口回连的 22 端口（默认对本机 22 全放通即可） |
| 服务器上 `docker build` 慢/超时 | 两重优化已内置：① 字体只装基础包 `fonts-noto-cjk`（含思源宋体 Regular/Bold，无需 134MB 的 -extra）；② apt 默认走阿里云**内网**镜像 `mirrors.cloud.aliyuncs.com`，不占公网带宽。非阿里云服务器用 `APT_MIRROR=mirrors.aliyun.com` 覆盖。另注意：字体层有 Docker 缓存，只在改动 Dockerfile 的 apt 行后才会重新下载；GitHub Actions 构建在境外 runner，自动走官方源 |
| 容器反复报 `exec /app/start.sh: no such file or directory` | Windows 换行符（CRLF）问题：脚本 shebang 变成 `#!/bin/sh\r`。已双重防护：`.gitattributes` 强制 `.sh` 用 LF 检出，Dockerfile 构建时自动剥 `\r`；若在其他机器构建仍复现，对该文件执行 `sed -i 's/\r$//' start.sh` |
| WSL 里用 `/mnt/c` 下的密钥报 `bad permissions` | Windows 盘挂载到 WSL 后权限恒为 0777 且 chmod 无效；把密钥复制进 WSL 家目录：`cp /mnt/c/.../key ~/.ssh/ && chmod 600 ~/.ssh/key` |
| `docker compose` 不存在 | 宝塔安装 Docker 时勾选 docker-compose 插件；或使用 `docker-compose`（v1）命令 |
| 服务器是 ARM 实例 | 把 workflow 里 `platforms: linux/amd64` 改为 `linux/arm64` |
| ACR 拉取慢 | `.env` 的 `ACR_IMAGE` 可填控制台同页显示的 **VPC 地址**（同地域服务器内网拉取，不占公网带宽）。SSH 部署脚本会自动读取 `.env` 里的仓库主机并登录，公网/VPC 地址均支持 |
| 管理端「上传图片」按钮置灰 | 服务器未配置 OSS：按上文「图片素材存储」在 `.env` 填 `OSS_*` 后重启容器。编排文件已透传这些变量 |
| 设备上图片积木显示缺图占位框 | OSS 读取失败：`docker logs kindle-calendar` 搜 `OSS 读取失败`；确认 Endpoint 可达（`-internal` 内网地址仅同地域 ECS 可用）、AccessKey 有效、Bucket 未删 |
