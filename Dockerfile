FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
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
ENV FONT_PATH=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
ENV PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY server/ server/
COPY config.example.yaml config.example.yaml
COPY start.sh start.sh
RUN chmod +x start.sh

EXPOSE 8080

CMD ["/app/start.sh"]
