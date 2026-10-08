FROM python:3.12-slim

# 国内服务器构建时可传国内镜像源加速（deploy-remote.sh / deploy.sh 会自动传阿里云源）：
#   docker build --build-arg APT_MIRROR=mirrors.aliyun.com \
#                --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ .
# 留空（默认）则直连官方源，适合境外 CI runner
ARG APT_MIRROR=""
ARG PIP_INDEX_URL=""

RUN if [ -n "$APT_MIRROR" ]; then \
        sed -i "s|deb.debian.org|$APT_MIRROR|g; s|security.debian.org|$APT_MIRROR|g" \
            /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list 2>/dev/null || true; \
    fi \
    && apt-get update && apt-get install -y --no-install-recommends \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONPATH=/app
ENV LOCATION_NAME=北京
ENV LATITUDE=39.9042
ENV LONGITUDE=116.4074
ENV TIMEZONE=Asia/Shanghai
ENV SCREEN_WIDTH=758
ENV SCREEN_HEIGHT=1024
# 印刷杂志风使用思源宋体；Serif Regular/Bold 基础包 fonts-noto-cjk 已包含，
# -extra 包只有 Light/Medium 等额外字重（渲染代码未使用），不必安装
ENV FONT_PATH=/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc
ENV PORT=8080

COPY requirements.txt .
RUN if [ -n "$PIP_INDEX_URL" ]; then pip config set global.index-url "$PIP_INDEX_URL"; fi \
    && pip install --no-cache-dir -r requirements.txt gunicorn

COPY server/ server/
COPY config.example.yaml config.example.yaml
COPY start.sh start.sh
# Windows 检出的脚本可能带 CRLF，exec 会报 no such file or directory，构建时统一剥掉
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

EXPOSE 8080

CMD ["/app/start.sh"]
