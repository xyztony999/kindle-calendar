#!/bin/sh
# Kindle 端客户端 — 通过 WiFi 从云端拉取 PNG，无需 PC 常开
# 部署:
#   1. scp config.sh dash.sh root@<Kindle的IP>:/mnt/us/kindle-calendar/
#   2. ssh root@<Kindle的IP> "chmod +x /mnt/us/kindle-calendar/*.sh"
#   3. ssh root@<Kindle的IP> "nohup /mnt/us/kindle-calendar/dash.sh &"

DASH_DIR="/mnt/us/kindle-calendar"
CONFIG="$DASH_DIR/config.sh"
DASH_PNG="$DASH_DIR/dashboard.png"
LOG_FILE="$DASH_DIR/dash.log"
EIPS="/usr/sbin/eips"
LIB="$DASH_DIR/lib/display.sh"

# 加载配置
if [ -f "$CONFIG" ]; then
    . "$CONFIG"
else
    SERVER_URL="https://your-app.onrender.com/dashboard.png"
    INTERVAL=900
    FULL_REFRESH_EVERY=6
    WIFI_ON_DEMAND=false
    WIFI_WAIT=15
fi

if [ -f "$LIB" ]; then
    . "$LIB"
else
    show_dashboard_png() {
        png="$1"
        full="${2:-0}"
        [ -f "$png" ] || return 1
        if [ "$full" = "1" ]; then
            "$EIPS" -f -g "$png" >/dev/null 2>&1
        else
            "$EIPS" -g "$png" >/dev/null 2>&1
        fi
    }
    wifi_on() {
        if [ "$WIFI_ON_DEMAND" != "true" ] && ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
            return 0
        fi
        lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
        lipc-send-event com.lab126.wan autoConnectWan 2>/dev/null
        sleep "${WIFI_WAIT:-15}"
    }
    wifi_off() {
        if [ "$WIFI_ON_DEMAND" = "true" ]; then
            lipc-set-prop com.lab126.cmd wirelessEnable 0 2>/dev/null
        fi
    }
fi

refresh_count=0
mkdir -p "$DASH_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

wait_for_network() {
    i=0
    while [ "$i" -lt 10 ]; do
        if ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
            return 0
        fi
        i=$((i + 1))
        sleep 3
    done
    log "WARN: 网络未就绪，仍尝试拉取"
    return 1
}

fetch_image() {
    if command -v wget >/dev/null 2>&1; then
        wget -q -T 30 -O "$DASH_PNG.tmp" "$SERVER_URL" && mv "$DASH_PNG.tmp" "$DASH_PNG"
    elif command -v curl >/dev/null 2>&1; then
        curl -s --connect-timeout 30 -o "$DASH_PNG.tmp" "$SERVER_URL" && mv "$DASH_PNG.tmp" "$DASH_PNG"
    else
        log "ERROR: 未找到 wget 或 curl"
        return 1
    fi
}

display_image() {
    if [ ! -f "$DASH_PNG" ]; then
        log "ERROR: 图像文件不存在"
        return 1
    fi

    refresh_count=$((refresh_count + 1))
    if [ $((refresh_count % FULL_REFRESH_EVERY)) -eq 0 ]; then
        show_dashboard_png "$DASH_PNG" 1
        log "全刷显示"
    else
        show_dashboard_png "$DASH_PNG" 0
        log "局部刷新"
    fi
}

prevent_sleep() {
    if [ -f /sys/devices/platform/misc/rtc/wakealarm ]; then
        echo 0 > /sys/devices/platform/misc/rtc/wakealarm 2>/dev/null
    fi
}

do_refresh() {
    wifi_on
    wait_for_network

    if fetch_image; then
        display_image
    else
        log "拉取失败"
    fi

    wifi_off
}

log "=== kindle-calendar 启动（WiFi 自主拉取）==="
log "URL: $SERVER_URL"
log "间隔: ${INTERVAL}s  WiFi按需: ${WIFI_ON_DEMAND:-false}"

# 启动时立即刷新一次
prevent_sleep
do_refresh

while true; do
    prevent_sleep
    sleep "$INTERVAL"
    do_refresh
done
