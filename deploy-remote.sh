#!/bin/bash
# 一键部署（无需 CI）：本地打包代码 → 上传服务器 → 远程构建并启动
# 适合首次初始化服务器，或不想配置 GitHub Actions 时使用
#
# 用法:   ./deploy-remote.sh [user@host] [目标目录]
# 密钥:   ./deploy-remote.sh -i ~/.ssh/你的密钥 [user@host] [目标目录]
#         或环境变量: DEPLOY_KEY=~/.ssh/你的密钥 ./deploy-remote.sh root@1.2.3.4
# 推荐:   在 ~/.ssh/config 配好 Host 别名后，直接 ./deploy-remote.sh 别名
#
# 说明:
#   - 服务器上的 .env 不会被覆盖（显示配置持久保留）
#   - 需要服务器已配置 Docker 镜像加速（见 DEPLOY.md）
set -euo pipefail

KEY=""
if [ "${1:-}" = "-i" ]; then
  [ $# -ge 2 ] || { echo "错误: -i 后面要跟密钥路径" >&2; exit 1; }
  KEY="$2"; shift 2
fi
KEY="${KEY:-${DEPLOY_KEY:-}}"

TARGET="${1:-${DEPLOY_TARGET:-}}"
REMOTE_DIR="${2:-${DEPLOY_DIR:-/www/wwwroot/kindle-calendar}}"

if [ -z "$TARGET" ]; then
  echo "用法: ./deploy-remote.sh [-i 密钥路径] [user@host] [目标目录]" >&2
  echo "例如: ./deploy-remote.sh -i ~/.ssh/aliyun.pem root@你的服务器IP" >&2
  exit 1
fi

run_ssh() {
  if [ -n "$KEY" ]; then ssh -i "$KEY" "$@"; else ssh "$@"; fi
}

echo "==> 同步代码到 ${TARGET}:${REMOTE_DIR}"
run_ssh "$TARGET" "mkdir -p '${REMOTE_DIR}'"
tar -czf - \
  --exclude=./.git \
  --exclude=./.venv \
  --exclude=./.env \
  --exclude=./.mimosa \
  --exclude=./__pycache__ \
  --exclude=./server/__pycache__ \
  . | run_ssh "$TARGET" "tar -xzf - -C '${REMOTE_DIR}'"

# 国内构建源：apt 默认走阿里云内网镜像（仅阿里云 ECS 可达，不占公网带宽）；
# 非阿里云服务器执行前覆盖：APT_MIRROR=mirrors.aliyun.com ./deploy-remote.sh ...
# pip 走公网阿里云源（体积小，无需内网）；均可用环境变量换成其他源
APT_MIRROR="${APT_MIRROR:-mirrors.cloud.aliyuncs.com}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"

echo "==> 远程构建镜像并启动容器（apt/pip 源: ${APT_MIRROR}）"
run_ssh "$TARGET" "cd '${REMOTE_DIR}' && docker build \
  --build-arg APT_MIRROR='${APT_MIRROR}' \
  --build-arg PIP_INDEX_URL='${PIP_INDEX_URL}' \
  -t kindle-calendar:latest . && docker compose -f docker-compose.image.yml up -d"

echo "==> 健康检查"
sleep 3
run_ssh "$TARGET" "curl -sf http://127.0.0.1:8080/health && echo ''"

echo "==> 完成。Kindle 拉取地址: http://<服务器IP>:8080/dashboard.png"
