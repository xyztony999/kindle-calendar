#!/bin/bash
# 部署前检查：在服务器项目目录执行  bash check-files.sh
set -e

DIR="${1:-/www/wwwroot/kindle-calendar}"
echo "检查目录: $DIR"
echo "---"

missing=0
for f in Dockerfile docker-compose.baota.yml start.sh requirements.txt config.example.yaml server/app.py server/renderer.py server/weather.py; do
  if [ -f "$DIR/$f" ]; then
    echo "OK  $f"
  else
    echo "MISS $f"
    missing=1
  fi
done

echo "---"
if [ "$missing" -eq 1 ]; then
  echo "有文件缺失，请补全后再构建"
  exit 1
fi

echo "文件齐全。推荐执行:"
echo "  cd $DIR && docker build -t kindle-calendar:latest ."
echo "  docker compose -f docker-compose.image.yml up -d"
