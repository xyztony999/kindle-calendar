#!/bin/sh
# Kindle 端客户端 v2 — 分区刷新 + 分钟级时钟（无需网络）
# 需要服务端 v2（/api/v1/dashboard.env）与 fbink；二者缺一时自动回退 v1 整图模式。
#
# 部署:
#   1. scp -r kindle/ root@<Kindle的IP>:/mnt/us/kindle-calendar/
#   2. ssh root@<Kindle的IP> "chmod +x /mnt/us/kindle-calendar/*.sh /mnt/us/kindle-calendar/lib/*.sh"
#   3. ssh root@<Kindle的IP> "nohup /mnt/us/kindle-calendar/dash.sh &"  （或用 KUAL 启动）

DASH_DIR="/mnt/us/kindle-calendar"
CONFIG="$DASH_DIR/config.sh"
DASH_PNG="$DASH_DIR/dashboard.png"
LOG_FILE="$DASH_DIR/dash.log"
LIB="$DASH_DIR/lib/display.sh"
STATE_DIR="$DASH_DIR/state"
CACHE_DIR="$DASH_DIR/cache"
GLYPH_DIR="$CACHE_DIR/glyphs"

# 默认值（可被 config.sh 覆盖）
SERVER_URL=""
API_URL=""
INTERVAL=900
FULL_REFRESH_EVERY=6
WIFI_ON_DEMAND=false
WIFI_WAIT=15
CLOCK_ENABLED=1

[ -f "$CONFIG" ] && . "$CONFIG"

if [ -f "$LIB" ]; then
    . "$LIB"
else
    echo "缺少 lib/display.sh" >&2
    exit 1
fi

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

prevent_sleep() {
    if [ -f /sys/devices/platform/misc/rtc/wakealarm ]; then
        echo 0 > /sys/devices/platform/misc/rtc/wakealarm 2>/dev/null
    fi
}

fetch_url() {
    # $1=目标路径 $2=URL
    if command -v wget >/dev/null 2>&1; then
        wget -q -T 30 -O "$1.tmp" "$2" && mv "$1.tmp" "$1"
    elif command -v curl >/dev/null 2>&1; then
        curl -s --connect-timeout 30 --max-time 60 -o "$1.tmp" "$2" && mv "$1.tmp" "$1"
    else
        log "ERROR: 未找到 wget 或 curl"
        return 1
    fi
}

wait_for_network() {
    i=0
    while [ "$i" -lt 10 ]; do
        ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1 && return 0
        i=$((i + 1))
        sleep 3
    done
    log "WARN: 网络未就绪，仍尝试拉取"
    return 1
}

# ───────── v2: 分区模式 ─────────

env_sync() {
    fetch_url "$CACHE_DIR/dashboard.env" "$API_URL" || return 1
    # shellcheck disable=SC1090
    . "$CACHE_DIR/dashboard.env"
}

# sync_region <NAME大写> <flash 0|1>：ETAG 变化时拉取并绘制；flash=1 时无条件重绘缓存图
sync_region() {
    up="$1"
    flash="${2:-0}"
    lc=$(printf '%s' "$up" | tr '[:upper:]' '[:lower:]')
    eval url="\$R_${up}_URL"
    eval etag="\$R_${up}_ETAG"
    eval x="\$R_${up}_X"
    eval y="\$R_${up}_Y"
    [ -n "$url" ] || return 1

    last=""
    [ -f "$STATE_DIR/$lc.etag" ] && last="$(cat "$STATE_DIR/$lc.etag")"
    if [ "$last" != "$etag" ]; then
        fetch_url "$CACHE_DIR/$lc.png" "$url" || return 1
        fbink_img "$CACHE_DIR/$lc.png" "$x" "$y" GC16 "$flash" || return 1
        echo "$etag" > "$STATE_DIR/$lc.etag"
    elif [ "$flash" = "1" ] && [ -f "$CACHE_DIR/$lc.png" ]; then
        fbink_img "$CACHE_DIR/$lc.png" "$x" "$y" GC16 1
    fi
}

REGIONS="HEADER WEATHER SUN SCENE QUOTE"

sync_glyphs() {
    key="${CLOCK_DIGIT_W:-0}.${CLOCK_DIGIT_H:-0}.${CLOCK_COLON_W:-0}.${CLOCK_GAP:-0}"
    [ -n "$CLOCK_GLYPH_URL_PREFIX" ] || return 1
    old=""
    [ -f "$STATE_DIR/glyph.key" ] && old="$(cat "$STATE_DIR/glyph.key")"
    [ "$old" = "$key" ] && return 0

    mkdir -p "$GLYPH_DIR"
    rm -f "$GLYPH_DIR"/*.png
    ok=0
    for g in 0 1 2 3 4 5 6 7 8 9 :; do
        if fetch_url "$GLYPH_DIR/$g.png" "${CLOCK_GLYPH_URL_PREFIX}$g.png"; then
            ok=$((ok + 1))
        fi
    done
    if [ "$ok" -eq 11 ]; then
        echo "$key" > "$STATE_DIR/glyph.key"
        return 0
    fi
    return 1
}

# 每分钟更新时钟：只重绘发生变化的字形（A2 快速局刷）
draw_clock() {
    [ "$CLOCK_ENABLED" = "1" ] || return 0
    [ -n "$CLOCK_X" ] || return 0
    str="$(date +%H%M)"
    last=""
    [ -f "$STATE_DIR/clock.last" ] && last="$(cat "$STATE_DIR/clock.last")"
    [ "$str" = "$last" ] && return 0

    x="$CLOCK_X"
    i=1
    while [ "$i" -le 5 ]; do
        if [ "$i" -eq 3 ]; then
            c=":"
            w="$CLOCK_COLON_W"
            prev=":"
        else
            if [ "$i" -le 2 ]; then idx="$i"; else idx=$((i - 1)); fi
            c="$(printf '%s' "$str" | cut -c "$idx")"
            prev="$(printf '%s' "$last" | cut -c "$idx")"
            w="$CLOCK_DIGIT_W"
        fi
        if [ "$c" != "$prev" ] && [ -f "$GLYPH_DIR/$c.png" ]; then
            fbink_img "$GLYPH_DIR/$c.png" "$x" "$CLOCK_Y" A2 0
        fi
        x=$((x + w + CLOCK_GAP))
        i=$((i + 1))
    done
    echo "$str" > "$STATE_DIR/clock.last"
}

do_fetch() {
    wifi_on
    wait_for_network
    if env_sync; then
        for r in $REGIONS; do
            sync_region "$r" "${1:-0}" || log "分区 $r 同步失败"
        done
        sync_glyphs || log "字形同步失败"
    else
        log "env 拉取失败"
    fi
    wifi_off
}

redraw_all_flash() {
    for r in $REGIONS; do
        sync_region "$r" 1 >/dev/null 2>&1
    done
    rm -f "$STATE_DIR/clock.last"
    draw_clock
}

v2_loop() {
    log "=== dash v2 分区模式启动 ==="
    log "API: $API_URL  间隔: ${INTERVAL}s  时钟: ${CLOCK_ENABLED}"
    mkdir -p "$STATE_DIR" "$CACHE_DIR" "$GLYPH_DIR"

    prevent_sleep
    do_fetch 1
    draw_clock

    last_fetch=$(date +%s)
    last_day="$(date +%Y%m%d)"
    last_full="$(cat "$STATE_DIR/lastfull" 2>/dev/null)"

    while true; do
        prevent_sleep
        draw_clock

        now=$(date +%s)
        if [ $((now - last_fetch)) -ge "$INTERVAL" ]; then
            do_fetch
            last_fetch=$(date +%s)
        fi

        day="$(date +%Y%m%d)"
        if [ "$day" != "$last_day" ]; then
            log "跨天，全量刷新"
            do_fetch 1
            last_day="$day"
            last_fetch=$(date +%s)
        elif [ "$(date +%H)" = "03" ] && [ "$last_full" != "$day" ]; then
            log "凌晨清残影全刷"
            redraw_all_flash
            last_full="$day"
            echo "$day" > "$STATE_DIR/lastfull"
        fi

        sleep 5
    done
}

# ───────── v1: 整图模式（回退） ─────────

v1_loop() {
    log "=== dash v1 整图模式（回退）==="
    log "URL: $SERVER_URL"

    refresh_count=0
    do_refresh() {
        wifi_on
        wait_for_network
        if fetch_url "$DASH_PNG" "$SERVER_URL"; then
            refresh_count=$((refresh_count + 1))
            if [ $((refresh_count % FULL_REFRESH_EVERY)) -eq 0 ]; then
                show_dashboard_png "$DASH_PNG" 1
                log "全刷显示"
            else
                show_dashboard_png "$DASH_PNG" 0
                log "局部刷新"
            fi
        else
            log "拉取失败"
        fi
        wifi_off
    }

    prevent_sleep
    do_refresh
    while true; do
        prevent_sleep
        sleep "$INTERVAL"
        do_refresh
    done
}

# ───────── 入口 ─────────

mkdir -p "$DASH_DIR"

if [ -n "$API_URL" ] && find_fbink; then
    v2_loop
else
    [ -z "$API_URL" ] && log "未配置 API_URL"
    find_fbink || log "未找到 fbink（放置于 $DASH_DIR/bin/fbink）"
    v1_loop
fi
