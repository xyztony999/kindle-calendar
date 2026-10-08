#!/bin/sh
# 作为「书」打开：图书馆里点书名 → 全屏台历
# 本书只是启动器：拉起 dash.sh 守护（v2 分区刷新 + 分钟时钟）并常驻等待，
# 按 Home 返回书库后仍在后台运行；再点一次书 = 重启台历。
# dash.sh 缺失时回退为 v1 整图循环。
# 复制到 Kindle 根目录 documents/天气台历.sh

DASH_DIR="/mnt/us/kindle-calendar"
LIB="$DASH_DIR/lib/display.sh"
CONFIG="$DASH_DIR/config.sh"
DASH_SH="$DASH_DIR/dash.sh"
DASH_PIDFILE="$DASH_DIR/dash.pid"
DASH_PNG="$DASH_DIR/dashboard.png"
LOG_FILE="$DASH_DIR/dash.log"
PIDFILE="$DASH_DIR/book.pid"
EIPS="/usr/sbin/eips"

INTERVAL=900
WIFI_WAIT=15
WIFI_ON_DEMAND=false
BOOK_FULLSCREEN=false
SERVER_URL="https://kindle-calendar.tonyxyz.cn/dashboard.png"

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

# 防止重复打开多个实例：停掉旧书进程与旧 dash 守护
if [ -f "$PIDFILE" ]; then
    old_pid="$(cat "$PIDFILE" 2>/dev/null)"
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
        kill "$old_pid" 2>/dev/null
        sleep 1
    fi
fi
if [ -f "$DASH_PIDFILE" ]; then
    kill "$(cat "$DASH_PIDFILE" 2>/dev/null)" 2>/dev/null
    rm -f "$DASH_PIDFILE"
    sleep 1
fi
pkill -f "$DASH_SH" 2>/dev/null && sleep 1

echo $$ > "$PIDFILE"

cleanup() {
    rm -f "$PIDFILE"
    if [ -f "$DASH_PIDFILE" ]; then
        kill "$(cat "$DASH_PIDFILE" 2>/dev/null)" 2>/dev/null
        rm -f "$DASH_PIDFILE"
    fi
    pkill -f "$DASH_SH" 2>/dev/null
    restore_kindle_ui
}
trap cleanup EXIT INT TERM HUP

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [book] $1" >> "$LOG_FILE"
}

log "打开天气台历 (BOOK_FULLSCREEN=${BOOK_FULLSCREEN:-false})"
init_book_display

# 等待首次拉取期间先显示上次的整图缓存，避免空白
if [ -f "$DASH_PNG" ]; then
    show_dashboard_png "$DASH_PNG" 1
fi

# ── v2：拉起 dash.sh 守护并常驻等待 ──
if [ -f "$DASH_SH" ]; then
    log "启动 dash.sh 守护（v2 分区模式）"
    "$DASH_SH" >> "$LOG_FILE" 2>&1 &
    dash_pid=$!
    echo "$dash_pid" > "$DASH_PIDFILE"
    wait "$dash_pid"
    log "dash.sh 已退出"
    exit 0
fi

# ── v1 回退：本书自带整图循环（无 dash.sh 时）──
log "未找到 dash.sh，回退 v1 整图模式"

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
