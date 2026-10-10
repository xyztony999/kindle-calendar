#!/bin/sh
# Kindle 端客户端 v2.1 — 五页面集 + 双导航（触摸优先/轮播降级）+ 三月预裁翻月 + 启动清屏
# 需要服务端 v2.1（/api/v1/dashboard.env）与 fbink；缺一时自动回退 v1 整图模式。
# 触摸需要 bin/tapread（可选）：存在则进入沉浸模式并启用手势；不存在则仅轮播。
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
EVENTS_FILE="$STATE_DIR/touch.events"
TAPREAD_PID_FILE="$STATE_DIR/tapread.pid"

# 默认值（可被 config.sh 覆盖）
SERVER_URL=""
API_URL=""
INTERVAL=900
FULL_REFRESH_EVERY=6
WIFI_ON_DEMAND=false
WIFI_WAIT=15
CLOCK_ENABLED=1
ROTATE_ENABLED=1
ROTATE_TODAY_S=120
ROTATE_OTHER_S=30
ROTATE_SUPPRESS_S=120
MONTH_LIMIT=24  # 翻月范围（±N 月），env 可覆盖；±1 为预裁资产零延迟，超出按需拉取
TOUCH_MODE=force      # force：tapread 在位即沉浸（tapread 已真机验证）；auto：先验证；off：纯轮播
TOUCH_VERIFY_S=90     # auto 模式验证窗口
TOUCH_DEAD_S=0        # 沉浸后无触摸事件自动恢复的秒数；0=关闭（tapread 已稳定，避免误踢回书库）

[ -f "$CONFIG" ] && . "$CONFIG"

# config.sh 本地覆盖值（env 下发默认值后以此恢复）
LOCAL_ROTATE_ENABLED="$ROTATE_ENABLED"
LOCAL_ROTATE_TODAY_S="$ROTATE_TODAY_S"
LOCAL_ROTATE_OTHER_S="$ROTATE_OTHER_S"

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
        ping -c 1 -W 3 223.5.5.5 >/dev/null 2>&1 && return 0
        i=$((i + 1))
        sleep 3
    done
    log "WARN: 网络未就绪，仍尝试拉取"
    return 1
}

# ───────── v2.1: 多页分区模式 ─────────

env_sync() {
    if fetch_url "$CACHE_DIR/dashboard.env" "$API_URL"; then
        # shellcheck disable=SC1090
        . "$CACHE_DIR/dashboard.env"
        # 恢复 config.sh 本地轮播覆盖
        [ "$LOCAL_ROTATE_ENABLED" != "1" ] && ROTATE_ENABLED="$LOCAL_ROTATE_ENABLED"
        [ -n "$LOCAL_ROTATE_TODAY_S" ] && [ "$LOCAL_ROTATE_TODAY_S" != "120" ] && ROTATE_TODAY_S="$LOCAL_ROTATE_TODAY_S"
        [ -n "$LOCAL_ROTATE_OTHER_S" ] && [ "$LOCAL_ROTATE_OTHER_S" != "30" ] && ROTATE_OTHER_S="$LOCAL_ROTATE_OTHER_S"
        return 0
    fi
    # 诊断：非静默重试一次，把 wget 的真实报错记进日志（DNS/TLS/路由）
    log "env 拉取诊断: $(wget -T 10 -O /dev/null "$API_URL" 2>&1 | head -2 | tr '\n' ' ')"
    return 1
}

# sync_region_asset <VAR前缀 如 TODAY_HEADER>：ETAG 变化时拉取资产（不绘制）
sync_region_asset() {
    up="$1"
    lc=$(printf '%s' "$up" | tr '[:upper:]' '[:lower:]')
    eval url="\$R_${up}_URL"
    eval etag="\$R_${up}_ETAG"
    [ -n "$url" ] || return 1

    last=""
    [ -f "$STATE_DIR/$lc.fetchetag" ] && last="$(cat "$STATE_DIR/$lc.fetchetag")"
    [ "$last" = "$etag" ] && return 0
    if fetch_url "$CACHE_DIR/$lc.png" "$url"; then
        echo "$etag" > "$STATE_DIR/$lc.fetchetag"
        return 0
    fi
    return 1
}

# draw_region <VAR前缀> [flash] [force]：绘制分区
#   flash=1 全刷；force=1 无视「已绘制 ETAG」跳过（翻页必须整页重绘——
#   ETAG 跳过是"内容变了才画"，但切页时屏幕上是别的页，内容没变也得画）
draw_region() {
    up="$1"
    flash="${2:-0}"
    force="${3:-0}"
    lc=$(printf '%s' "$up" | tr '[:upper:]' '[:lower:]')
    eval x="\$R_${up}_X"
    eval y="\$R_${up}_Y"
    eval etag="\$R_${up}_ETAG"
    [ -f "$CACHE_DIR/$lc.png" ] || return 1

    if [ "$flash" != "1" ] && [ "$force" != "1" ]; then
        drawn=""
        [ -f "$STATE_DIR/$lc.etag" ] && drawn="$(cat "$STATE_DIR/$lc.etag")"
        [ "$drawn" = "$etag" ] && return 0
    fi
    if fbink_img "$CACHE_DIR/$lc.png" "$x" "$y" GC16 "$flash"; then
        echo "$etag" > "$STATE_DIR/$lc.etag"
    fi
}

# goto_page <page> [flash]：同步并整页绘制（翻页语义：force 全量重绘）
goto_page() {
    page="$1"
    flash="${2:-0}"
    upper=$(printf '%s' "$page" | tr '[:lower:]' '[:upper:]')
    eval regions=\"\$R_${upper}_REGIONS\"
    [ -n "$regions" ] || return 1

    # 月历页：TITLE/GRID——±1 月用预裁键（零延迟），其余偏移动态拉取
    for r in $regions; do
        if [ "$page" = "month" ] && { [ "$r" = "TITLE" ] || [ "$r" = "GRID" ]; }; then
            case "$MONTH_OFFSET" in
                -1) sync_region_asset "${upper}_${r}_PREV"
                    draw_region "${upper}_${r}_PREV" "$flash" 1 ;;
                1)  sync_region_asset "${upper}_${r}_NEXT"
                    draw_region "${upper}_${r}_NEXT" "$flash" 1 ;;
                0)  sync_region_asset "${upper}_${r}_CUR"
                    draw_region "${upper}_${r}_CUR" "$flash" 1 ;;
                *)  ensure_month_asset "$r" "$MONTH_OFFSET"
                    lc="$r"
                    if [ -f "$CACHE_DIR/${lc}_m${MONTH_OFFSET}.png" ]; then
                        eval x="\$R_MONTH_${r}_X"
                        eval y="\$R_MONTH_${r}_Y"
                        fbink_img "$CACHE_DIR/${lc}_m${MONTH_OFFSET}.png" "$x" "$y" GC16 "$flash"
                    else
                        log "动态月资产缺失 offset=$MONTH_OFFSET region=$r"
                    fi ;;
            esac
        else
            sync_region_asset "${upper}_${r}"
            draw_region "${upper}_${r}" "$flash" 1
        fi
    done
    if [ "$page" = "today" ]; then
        rm -f "$STATE_DIR/clock.last"
        draw_clock
    fi
}

# ensure_month_asset <TITLE|GRID> <offset>：动态月份资产本地缓存
# （文件存在即用；跨天清除，由 do_fetch 后的重绘触发重拉）
ensure_month_asset() {
    r="$1"
    off="$2"
    [ -n "$off" ] && [ "$off" != "0" ] || return 1
    f="$CACHE_DIR/month_${r}_m${off}.png"
    [ -f "$f" ] && return 0

    eval tmpl="\$R_MONTH_${r}_TMPL"
    [ -n "$tmpl" ] || return 1
    url=$(printf '%s' "$tmpl" | sed "s/{o}/$off/")
    wifi_on
    if ! fetch_url "$f" "$url"; then
        rm -f "$f"
        log "动态月资产拉取失败 offset=$off"
    fi
    wifi_off
    [ -f "$f" ]
}

sync_glyphs() {
    key="${CLOCK_DIGIT_W:-0}.${CLOCK_DIGIT_H:-0}.${CLOCK_COLON_W:-0}.${CLOCK_GAP:-0}"
    [ -n "$CLOCK_GLYPH_URL_PREFIX" ] || return 1
    old=""
    [ -f "$STATE_DIR/glyph.key" ] && old="$(cat "$STATE_DIR/glyph.key")"

    # 几何 key 相同还不够：11 个字形文件必须全部在盘（文件名方案变更、
    # 半途失败等都会造成缺文件——例如冒号曾因文件名含':'下载失败）
    complete=1
    for g in 0 1 2 3 4 5 6 7 8 9 :; do
        if [ "$g" = ":" ]; then name="colon"; else name="$g"; fi
        [ -f "$GLYPH_DIR/$name.png" ] || complete=0
    done
    if [ "$old" = "$key" ] && [ "$complete" = "1" ]; then
        return 0
    fi

    mkdir -p "$GLYPH_DIR"
    # 原子同步：全部拉取成功才替换旧字形，失败保留旧集（避免半套字形白块）
    # 注意：冒号字形本地存为 colon.png —— /mnt/us 文件系统不允许文件名含 ':'
    ok=0
    for g in 0 1 2 3 4 5 6 7 8 9 :; do
        if [ "$g" = ":" ]; then name="colon"; else name="$g"; fi
        if fetch_url "$GLYPH_DIR/$name.new" "${CLOCK_GLYPH_URL_PREFIX}$g.png"; then
            ok=$((ok + 1))
        fi
    done
    if [ "$ok" -eq 11 ]; then
        for g in 0 1 2 3 4 5 6 7 8 9 :; do
            if [ "$g" = ":" ]; then name="colon"; else name="$g"; fi
            mv "$GLYPH_DIR/$name.new" "$GLYPH_DIR/$name.png"
        done
        echo "$key" > "$STATE_DIR/glyph.key"
        rm -f "$STATE_DIR/clock.last"
        return 0
    fi
    rm -f "$GLYPH_DIR"/*.new
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
            file="colon"  # 冒号字形本地文件名（文件系统不允许 ':'）
            w="$CLOCK_COLON_W"
            # 首次绘制（last 空）时屏幕上没有冒号，必须视为"变化"补画；
            # 之后再按位比较恒等跳过
            prev="$(printf '%s' "$last" | cut -c 3)"
        else
            if [ "$i" -le 2 ]; then idx="$i"; else idx=$((i - 1)); fi
            c="$(printf '%s' "$str" | cut -c "$idx")"
            prev="$(printf '%s' "$last" | cut -c "$idx")"
            file="$c"
            w="$CLOCK_DIGIT_W"
        fi
        if [ "$c" != "$prev" ] && [ -f "$GLYPH_DIR/$file.png" ]; then
            fbink_img "$GLYPH_DIR/$file.png" "$x" "$CLOCK_Y" A2 0
        fi
        x=$((x + w + CLOCK_GAP))
        i=$((i + 1))
    done
    echo "$str" > "$STATE_DIR/clock.last"
}

# 拉取周期：同步全部页面资产；无论成败都重绘当前页（失败时画本地缓存，不清屏不白屏）
do_fetch() {
    wifi_on
    wait_for_network
    ENV_OK=0
    if env_sync; then
        ENV_OK=1
        for p in ${PAGES:-today}; do
            upper=$(printf '%s' "$p" | tr '[:lower:]' '[:upper:]')
            eval regions=\"\$R_${upper}_REGIONS\"
            for r in $regions; do
                if [ "$p" = "month" ] && { [ "$r" = "TITLE" ] || [ "$r" = "GRID" ]; }; then
                    sync_region_asset "${upper}_${r}_PREV"
                    sync_region_asset "${upper}_${r}_CUR"
                    sync_region_asset "${upper}_${r}_NEXT"
                else
                    sync_region_asset "${upper}_${r}"
                fi
            done
        done
        sync_glyphs || log "字形同步失败"
    else
        log "env 拉取失败"
    fi
    wifi_off
    if goto_page "$CUR_PAGE"; then
        READY_DRAWN=1
    fi
}

redraw_all_flash() {
    goto_page "$CUR_PAGE" 1
    if [ "$CUR_PAGE" = "today" ]; then
        rm -f "$STATE_DIR/clock.last"
        draw_clock
    fi
}

# ───────── 触摸（tapread 行协议：D x y / U x y）─────────

start_tapread() {
    TAPREAD="$DASH_DIR/bin/tapread"
    [ -f "$TAPREAD" ] && [ -x "$TAPREAD" ] || return 1
    : > "$EVENTS_FILE"
    "$TAPREAD" >> "$EVENTS_FILE" 2>/dev/null &
    echo $! > "$TAPREAD_PID_FILE"
    EVENTS_READ=0
    return 0
}

stop_tapread() {
    if [ -f "$TAPREAD_PID_FILE" ]; then
        kill "$(cat "$TAPREAD_PID_FILE")" 2>/dev/null
        rm -f "$TAPREAD_PID_FILE"
    fi
}

# 读取新触摸事件并翻译为手势命令（子壳只写命令，由主循环 apply_gestures 执行）
poll_touch() {
    [ -n "$TOUCH_ENABLED" ] || return 0
    [ -f "$EVENTS_FILE" ] || return 0
    total=$(wc -l < "$EVENTS_FILE" | tr -d ' ')
    [ "$total" -gt "$EVENTS_READ" ] || return 0
    new_start=$((EVENTS_READ + 1))
    EVENTS_READ=$total
    sed -n "${new_start},${total}p" "$EVENTS_FILE" | while read -r act x y; do
        [ -n "$act" ] || continue
        if [ "$act" = "D" ]; then
            echo "$x $y $(date +%s)" > "$STATE_DIR/touch.down"
        elif [ "$act" = "U" ] && [ -f "$STATE_DIR/touch.down" ]; then
            read -r dx dy t0 < "$STATE_DIR/touch.down"
            rm -f "$STATE_DIR/touch.down"
            translate_gesture "$dx" "$dy" "$x" "$y" "$t0"
        fi
    done
}

# 手势 → 命令行写入队列
#   NEXT_PAGE/PREV_PAGE/MONTH_PREV/MONTH_NEXT/INVERT/REFRESH/EXIT（点击热区）
#   SWIPE_L/SWIPE_R（滑动：月历页=翻月，其余页=翻页）
translate_gesture() {
    dx="$1" dy="$2" ux="$3" uy="$4" t0="$5"
    dt=$(( $(date +%s) - t0 ))
    sdx=$((ux - dx)); [ "$sdx" -lt 0 ] && sdx=$((-sdx))
    sdy=$((uy - dy)); [ "$sdy" -lt 0 ] && sdy=$((-sdy))

    # 水平滑（位移 >50 且水平分量明显占优）
    if [ "$sdx" -gt 50 ] && [ "$sdx" -gt $((sdy * 2)) ]; then
        if [ "$ux" -gt "$dx" ]; then
            echo "SWIPE_R" >> "$STATE_DIR/gesture.cmds"
        else
            echo "SWIPE_L" >> "$STATE_DIR/gesture.cmds"
        fi
        return 0
    fi
    [ "$sdx" -gt 30 ] && return 0  # 垂直/无意图滑动忽略

    # 热区（由 env 布局坐标推导）
    header_bot=$(( ${R_TODAY_HEADER_Y:-44} + ${R_TODAY_HEADER_H:-78} ))
    quote_top=${R_TODAY_QUOTE_Y:-948}

    if [ "$dt" -ge 2 ]; then
        if [ "$uy" -lt "$header_bot" ] && [ "$ux" -gt $((SCREEN_W - 80)) ]; then
            echo "EXIT" >> "$STATE_DIR/gesture.cmds"
        fi
        return 0
    fi
    [ "$dt" -ge 1 ] && return 0  # 1~2s 防误触缓冲

    if [ "$uy" -lt "$header_bot" ] && [ "$ux" -gt $((SCREEN_W - 80)) ]; then
        echo "REFRESH" >> "$STATE_DIR/gesture.cmds"
    elif [ "$uy" -ge 900 ]; then
        # 底部：左右角（110px，翻月）；中央（反色）
        if [ "$ux" -lt 110 ]; then
            echo "MONTH_PREV" >> "$STATE_DIR/gesture.cmds"
        elif [ "$ux" -gt $((SCREEN_W - 110)) ]; then
            echo "MONTH_NEXT" >> "$STATE_DIR/gesture.cmds"
        elif [ "$ux" -ge $((SCREEN_W / 2 - 100)) ] && [ "$ux" -le $((SCREEN_W / 2 + 100)) ]; then
            echo "INVERT" >> "$STATE_DIR/gesture.cmds"
        fi
    elif [ "$ux" -lt 80 ]; then
        echo "PREV_PAGE" >> "$STATE_DIR/gesture.cmds"
    elif [ "$ux" -gt $((SCREEN_W - 80)) ]; then
        echo "NEXT_PAGE" >> "$STATE_DIR/gesture.cmds"
    fi
}

# 主循环消费手势命令（在主 shell 中执行，状态可持久）
apply_gestures() {
    [ "$READY" = "1" ] || return 0  # 首绘完成前忽略手势噪声
    [ -s "$STATE_DIR/gesture.cmds" ] || return 0
    LAST_TOUCH_OK=$(date +%s)  # 有命令产出 = tapread 工作正常（看门狗续期）
    while read -r cmd; do
        [ -n "$cmd" ] || continue
        ROTATE_UNTIL=$(( $(date +%s) + ${ROTATE_SUPPRESS_S:-600} ))
        case "$cmd" in
            NEXT_PAGE) switch_page next ;;
            PREV_PAGE) switch_page prev ;;
            MONTH_PREV) [ "$CUR_PAGE" = "month" ] && change_month -1 ;;
            MONTH_NEXT) [ "$CUR_PAGE" = "month" ] && change_month 1 ;;
            # 滑动：月历页=翻月，其余页=翻页（滑动比角落热区好点）
            SWIPE_L) if [ "$CUR_PAGE" = "month" ]; then change_month 1; else switch_page next; fi ;;
            SWIPE_R) if [ "$CUR_PAGE" = "month" ]; then change_month -1; else switch_page prev; fi ;;
            INVERT) toggle_invert ;;
            REFRESH) manual_refresh ;;
            EXIT) exit_request=1; log "长按退出请求" ;;
        esac
    done < "$STATE_DIR/gesture.cmds"
    : > "$STATE_DIR/gesture.cmds"
}

# ───────── 页面焦点 ─────────

switch_page() {
    # 首次成功绘制内容前不切页（env 未就绪时无可画资产，切了也只换焦点不换画面）
    [ "$READY_DRAWN" = "1" ] || return 0
    dir="$1"
    set -- $PAGES
    n=$#
    i=1
    for p in "$@"; do
        [ "$p" = "$CUR_PAGE" ] && break
        i=$((i + 1))
    done
    if [ "$dir" = "next" ]; then
        i=$((i % n + 1))
    else
        i=$((i - 1)); [ "$i" -lt 1 ] && i=$n
    fi
    eval 'new_page=$'$i
    prev_page="$CUR_PAGE"
    CUR_PAGE="$new_page"
    MONTH_OFFSET=0
    if goto_page "$CUR_PAGE"; then
        rotate_arm
    else
        CUR_PAGE="$prev_page"  # 目标页无资产（如该页从未同步过）时回退，保持画面与状态一致
    fi
}

change_month() {
    new=$((MONTH_OFFSET + $1))
    # 跨月范围 ±MONTH_LIMIT（env 下发，默认 24）
    limit=${MONTH_LIMIT:-24}
    [ "$new" -gt "$limit" ] || [ "$new" -lt "$((-limit))" ] && return 0
    MONTH_OFFSET=$new
    if goto_page month; then
        ROTATE_UNTIL=$(( $(date +%s) + ${ROTATE_SUPPRESS_S:-120} ))
    fi
}

toggle_invert() {
    if [ "$INVERT" = "1" ]; then
        INVERT=0
    else
        INVERT=1
    fi
    clear_screen
    redraw_all_flash
    log "反色切换 INVERT=$INVERT"
}

manual_refresh() {
    now=$(date +%s)
    [ $((now - LAST_REFRESH)) -lt 30 ] && return 0  # 防抖 30s
    LAST_REFRESH=$now
    log "手动刷新"
    do_fetch
}

rotate_arm() {
    if [ "$CUR_PAGE" = "today" ]; then
        ROTATE_DEADLINE=$(( $(date +%s) + ROTATE_TODAY_S ))
    else
        ROTATE_DEADLINE=$(( $(date +%s) + ROTATE_OTHER_S ))
    fi
}

# ───────── v2.1 主循环 ─────────

v21_loop() {
    log "=== dash v2.1 启动（五页/双导航）==="
    log "API: $API_URL  间隔: ${INTERVAL}s  轮播: ${ROTATE_ENABLED}  触摸: ${TOUCH_ENABLED:-无}"
    mkdir -p "$STATE_DIR" "$CACHE_DIR" "$GLYPH_DIR"

    CUR_PAGE=today
    MONTH_OFFSET=0
    INVERT=0
    exit_request=0
    LAST_REFRESH=0
    ROTATE_UNTIL=0
    READY=0        # 首次成功绘制前忽略触摸（framework 切换期的噪声事件不触发误退出）
    READY_DRAWN=0  # 首次成功绘制分区内容前不轮播不切页（env 未就绪时无可画资产）
    IMMERSIVE=0    # 是否已停 framework 进入沉浸
    TOUCH_START=0  # auto 验证窗口起点
    LAST_TOUCH_OK=0

    # 触摸策略（TOUCH_MODE）：
    #   auto（默认）— tapread 先跑 TOUCH_VERIFY_S 秒，真的收到触摸事件才进沉浸；无事件则禁触摸、保持轮播+Home 可用
    #   force        — 检测到 tapread 立即沉浸（旧行为，仅确信设备兼容时用）
    #   off          — 不启触摸，纯轮播
    if [ -n "$TOUCH_ENABLED" ]; then
        start_tapread || { TOUCH_ENABLED=""; log "tapread 启动失败，降级轮播"; }
        if [ "$TOUCH_MODE" = "force" ]; then
            init_kindle_display
            IMMERSIVE=1
            IMMERSIVE_SINCE=$(date +%s)
        elif [ "$TOUCH_MODE" = "auto" ]; then
            TOUCH_START=$(date +%s)
            log "触摸 auto 模式：${TOUCH_VERIFY_S}s 验证窗口（点几下屏幕）"
        fi
    fi

    # 启动序列：清屏 → 拉取（失败也画缓存）→ 时钟（BR-3 清屏优先）
    prevent_sleep
    clear_screen
    do_fetch

    # 完全无分区缓存（首次部署/换机）→ 回退 v1 整图，保证不白屏
    if ! ls "$CACHE_DIR"/*.png >/dev/null 2>&1; then
        log "无分区缓存，回退 v1 整图: $SERVER_URL"
        if fetch_url "$DASH_PNG" "$SERVER_URL"; then
            show_dashboard_png "$DASH_PNG" 1
        else
            log "v1 整图也拉取失败（网络问题），保留白屏等待下轮重试"
        fi
    fi

    draw_clock
    READY=1
    rotate_arm

    last_fetch=$(date +%s)
    # env 失败时快速重试（60s），成功后恢复正常 INTERVAL
    [ "$ENV_OK" = "1" ] && FETCH_RETRY="$INTERVAL" || FETCH_RETRY=60
    last_day="$(date +%Y%m%d)"
    last_full="$(cat "$STATE_DIR/lastfull" 2>/dev/null)"

    while true; do
        prevent_sleep
        poll_touch
        apply_gestures
        [ "$exit_request" = "1" ] && break
        [ "$CUR_PAGE" = "today" ] && draw_clock

        now=$(date +%s)

        # auto 模式：验证窗口结束时决定是否进入沉浸
        if [ -n "$TOUCH_ENABLED" ] && [ "$TOUCH_START" -gt 0 ] && [ "$now" -ge $((TOUCH_START + TOUCH_VERIFY_S)) ]; then
            if [ "$LAST_TOUCH_OK" -gt "$TOUCH_START" ]; then
                log "tapread 已验证（收到触摸事件），进入沉浸模式"
                init_kindle_display
                IMMERSIVE=1
                IMMERSIVE_SINCE=$(date +%s)
                clear_screen
                redraw_all_flash
            else
                log "tapread ${TOUCH_VERIFY_S}s 内无事件输出，禁用触摸（轮播 + Home 键保持可用）"
                stop_tapread
                TOUCH_ENABLED=""
            fi
            TOUCH_START=0
        fi

        # 沉浸看门狗（可选，TOUCH_DEAD_S>0 时启用）：长时间无触摸事件 → 自动恢复系统界面
        if [ "$IMMERSIVE" = "1" ] && [ "${TOUCH_DEAD_S:-0}" -gt 0 ]; then
            if [ "$LAST_TOUCH_OK" -gt "$IMMERSIVE_SINCE" ]; then
                IMMERSIVE_SINCE="$LAST_TOUCH_OK"
            elif [ "$now" -ge $((IMMERSIVE_SINCE + TOUCH_DEAD_S)) ]; then
                log "沉浸 ${TOUCH_DEAD_S}s 无触摸事件，自动恢复系统界面（防锁死看门狗）"
                stop_tapread
                TOUCH_ENABLED=""
                restore_kindle_ui
                IMMERSIVE=0
                goto_page "$CUR_PAGE" 1
            fi
        fi

        if [ "$ROTATE_ENABLED" = "1" ] && [ "$READY_DRAWN" = "1" ] && [ "$now" -ge "$ROTATE_DEADLINE" ] && [ "$now" -gt "$ROTATE_UNTIL" ]; then
            # 轮播回到今日页 = 一圈结束：全刷清屏一次，清掉整圈累积的残影
            if [ "$CUR_PAGE" = "almanac" ]; then
                clear_screen
                CUR_PAGE=today
                MONTH_OFFSET=0
                goto_page today
                rm -f "$STATE_DIR/clock.last"
                draw_clock
                rotate_arm
            else
                switch_page next
            fi
        fi
        if [ $((now - last_fetch)) -ge "$FETCH_RETRY" ]; then
            do_fetch
            last_fetch=$(date +%s)
            [ "$ENV_OK" = "1" ] && FETCH_RETRY="$INTERVAL" || FETCH_RETRY=60
        fi

        day="$(date +%Y%m%d)"
        if [ "$day" != "$last_day" ]; then
            log "跨天，全量刷新并回当月"
            MONTH_OFFSET=0
            rm -f "$CACHE_DIR"/month_title_m*.png "$CACHE_DIR"/month_grid_m*.png 2>/dev/null
            do_fetch
            redraw_all_flash
            last_day="$day"
            last_fetch=$(date +%s)
        elif [ "$(date +%H)" = "03" ] && [ "$last_full" != "$day" ]; then
            log "凌晨清残影全刷"
            clear_screen
            redraw_all_flash
            last_full="$day"
            echo "$day" > "$STATE_DIR/lastfull"
        fi

        sleep 1
    done

    # 退出沉浸
    stop_tapread
    restore_kindle_ui
    log "dash v2.1 退出"
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
    if [ "$TOUCH_MODE" != "off" ] && [ -f "$DASH_DIR/bin/tapread" ] && [ -x "$DASH_DIR/bin/tapread" ]; then
        TOUCH_ENABLED=1
    fi
    v21_loop
else
    [ -z "$API_URL" ] && log "未配置 API_URL"
    find_fbink || log "未找到 fbink（放置于 $DASH_DIR/bin/fbink）"
    v1_loop
fi
