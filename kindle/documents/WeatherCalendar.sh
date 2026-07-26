#!/bin/sh
# 英文文件名版，内容与 天气台历.sh 相同

DASH_DIR="/mnt/us/kindle-calendar"
LIB="$DASH_DIR/lib/display.sh"
CONFIG="$DASH_DIR/config.sh"
DASH_PNG="$DASH_DIR/dashboard.png"
LOG_FILE="$DASH_DIR/dash.log"
PIDFILE="$DASH_DIR/book.pid"
EIPS="/usr/sbin/eips"

INTERVAL=900
WIFI_WAIT=15
WIFI_ON_DEMAND=false
BOOK_FULLSCREEN=false
SERVER_URL="https://kindle-calendar.tonyxyz.com/dashboard.png"

if [ -f "$CONFIG" ]; then
    . "$CONFIG"
fi

if [ -f "$LIB" ]; then
    . "$LIB"
else
    FRAMEWORK_STOPPED=0
    init_book_display() {
        if [ "$BOOK_FULLSCREEN" = "true" ]; then
            /etc/init.d/framework stop >/dev/null 2>&1
            FRAMEWORK_STOPPED=1
        fi
    }
    restore_kindle_ui() {
        [ "$FRAMEWORK_STOPPED" = "1" ] && /etc/init.d/framework start >/dev/null 2>&1
        FRAMEWORK_STOPPED=0
    }
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
        lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
        sleep "${WIFI_WAIT:-15}"
    }
    wifi_off() {
        [ "$WIFI_ON_DEMAND" = "true" ] && lipc-set-prop com.lab126.cmd wirelessEnable 0 2>/dev/null
    }
    sleep_interval() {
        s="$1"
        i=0
        while [ "$i" -lt "$s" ]; do sleep 1; i=$((i + 1)); done
    }
fi

mkdir -p "$DASH_DIR"

if [ -f "$PIDFILE" ]; then
    old_pid="$(cat "$PIDFILE" 2>/dev/null)"
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
        kill "$old_pid" 2>/dev/null
        sleep 1
    fi
fi
echo $$ > "$PIDFILE"

cleanup() {
    rm -f "$PIDFILE"
    restore_kindle_ui
}
trap cleanup EXIT INT TERM HUP

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [book] $1" >> "$LOG_FILE"
}

fetch_png() {
    if command -v wget >/dev/null 2>&1; then
        wget -q -T 30 -O "$DASH_PNG.tmp" "$SERVER_URL" && mv "$DASH_PNG.tmp" "$DASH_PNG"
    elif command -v curl >/dev/null 2>&1; then
        curl -s --connect-timeout 30 --max-time 60 -o "$DASH_PNG.tmp" "$SERVER_URL" && mv "$DASH_PNG.tmp" "$DASH_PNG"
    else
        return 1
    fi
}

refresh_once() {
    wifi_on
    if fetch_png; then
        log "拉取成功"
        show_dashboard_png "$DASH_PNG" 1
        ok=0
    else
        log "拉取失败"
        ok=1
    fi
    wifi_off
    return $ok
}

log "打开天气台历 (BOOK_FULLSCREEN=${BOOK_FULLSCREEN:-false})"
init_book_display

if [ -f "$DASH_PNG" ]; then
    show_dashboard_png "$DASH_PNG" 1
fi

refresh_once

count=0
while true; do
    sleep_interval "$INTERVAL"
    count=$((count + 1))
    wifi_on
    if fetch_png; then
        if [ $((count % 6)) -eq 0 ]; then
            show_dashboard_png "$DASH_PNG" 1
        else
            show_dashboard_png "$DASH_PNG" 0
        fi
    fi
    wifi_off
done
