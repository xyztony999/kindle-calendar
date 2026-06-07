#!/bin/sh
# 公共显示函数 — 被 documents/*.sh 和 dash.sh 引用

FRAMEWORK_STOPPED=0

init_kindle_display() {
    /etc/init.d/framework stop >/dev/null 2>&1
    initctl stop webreader >/dev/null 2>&1
    lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
    FRAMEWORK_STOPPED=1
}

restore_kindle_ui() {
    if [ "$FRAMEWORK_STOPPED" != "1" ]; then
        return 0
    fi
    lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>/dev/null
    initctl start webreader >/dev/null 2>&1
    /etc/init.d/framework start >/dev/null 2>&1
    FRAMEWORK_STOPPED=0
}

# 脚本书模式：默认不关闭系统界面，按 Home 可返回书库
init_book_display() {
    if [ "$BOOK_FULLSCREEN" = "true" ]; then
        init_kindle_display
    else
        lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
    fi
}

show_dashboard_png() {
    png="$1"
    full="${2:-0}"
    eips_cmd="${EIPS:-/usr/sbin/eips}"

    [ -f "$png" ] || return 1

    if [ "$full" = "1" ]; then
        "$eips_cmd" -f -g "$png" >/dev/null 2>&1
    else
        "$eips_cmd" -g "$png" >/dev/null 2>&1
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

# 分段 sleep，便于 Home 退出时更快响应
sleep_interval() {
    seconds="$1"
    elapsed=0
    while [ "$elapsed" -lt "$seconds" ]; do
        sleep 1
        elapsed=$((elapsed + 1))
    done
}
