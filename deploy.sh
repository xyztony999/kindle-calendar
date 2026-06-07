#!/bin/bash
# 在服务器上执行（SSH / 宝塔终端），不要用宝塔「编排」界面构建
set -e

cd "$(dirname "$0")"
echo "==> 当前目录: $(pwd)"

for f in Dockerfile docker-compose.yml start.sh requirements.txt server/app.py; do
  if [ ! -f "$f" ]; then
    echo "ERROR: 缺少文件 $f"
    echo "请确认整个 kindle-calendar 项目已上传到此目录"
    exit 1
  fi
done

echo "==> 构建镜像..."
docker build -t kindle-calendar:latest .

echo "==> 启动容器..."
docker compose -f docker-compose.image.yml up -d

echo "==> 健康检查..."
sleep 2
curl -sf http://127.0.0.1:8080/health && echo "" || echo "WARN: 健康检查失败，请执行: docker logs kindle-calendar"

echo "==> 完成。测试: curl http://127.0.0.1:8080/dashboard.png -o /tmp/test.png"
