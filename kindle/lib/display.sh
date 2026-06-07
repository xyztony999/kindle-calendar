#!/bin/sh
# 公共显示函数 — 被 documents/*.sh 和 dash.sh 引用

init_kindle_display() {
    /etc/init.d/framework stop >/dev/null 2>&1
    initctl stop webreader >/dev/null 2>&1
    lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
}

restore_kindle_ui() {
    lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>/dev/null
    initctl start webreader >/dev/null 2>&1
    /etc/init.d/framework start >/dev/null 2>&1
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

# 拉取前开 WiFi；拉取后是否关闭由 WIFI_ON_DEMAND 控制
# false = 保持 WiFi 不断（不会出现「飞行模式」图标）
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
