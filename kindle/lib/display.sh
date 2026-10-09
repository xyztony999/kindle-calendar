#!/bin/sh
# 公共显示函数 — 被 dash.sh / documents/*.sh / KUAL 引用
# v2.1: fbink 分区刷新 + 清屏/反色 + eips 整图回退（v1 行为）

EIPS="${EIPS:-/usr/sbin/eips}"
DASH_DIR="${DASH_DIR:-/mnt/us/kindle-calendar}"

FRAMEWORK_STOPPED=0
INVERT="${INVERT:-0}"  # 反色开关：1 时所有 fbink 绘制附加 -h

# 定位 fbink：项目 bin/ 优先，其次 PATH
find_fbink() {
    if [ -n "$FBINK" ] && [ -x "$FBINK" ]; then
        return 0
    fi
    # 必须同时是文件且可执行：误放目录时 -x 也为真，会把目录当二进制执行导致白屏
    if [ -f "$DASH_DIR/bin/fbink" ] && [ -x "$DASH_DIR/bin/fbink" ]; then
        FBINK="$DASH_DIR/bin/fbink"
        return 0
    fi
    if command -v fbink >/dev/null 2>&1; then
        FBINK="$(command -v fbink)"
        return 0
    fi
    FBINK=""
    return 1
}

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

# 清屏：整屏清除 + 全刷（启动/模式切换/反色前调用，消除旧内容残留重影）
clear_screen() {
    [ -n "$FBINK" ] || return 1
    "$FBINK" -c -f -W GC16 >/dev/null 2>&1
}

# fbink 在 (x,y) 画 PNG；wfm=A2|GC16；flash=1 时强制全刷；反色时附加 -h
fbink_img() {
    png="$1" x="$2" y="$3" wfm="$4" flash="${5:-0}"
    [ -n "$FBINK" ] || return 1
    [ -f "$png" ] || return 1
    extra=""
    [ "$INVERT" = "1" ] && extra="-h"
    if [ "$flash" = "1" ]; then
        "$FBINK" $extra -f -g "file=$png,x=$x,y=$y" -W "$wfm" >/dev/null 2>&1
    else
        "$FBINK" $extra -g "file=$png,x=$x,y=$y" -W "$wfm" >/dev/null 2>&1
    fi
}

# 整图显示（v1 兼容）：fbink 或 eips
show_dashboard_png() {
    png="$1"
    full="${2:-0}"
    [ -f "$png" ] || return 1
    if find_fbink; then
        wfm="GC16"
        if [ "$full" = "1" ]; then
            "$FBINK" -f -g "file=$png,x=0,y=0" -W "$wfm" >/dev/null 2>&1
        else
            "$FBINK" -g "file=$png,x=0,y=0" -W "$wfm" >/dev/null 2>&1
        fi
    else
        if [ "$full" = "1" ]; then
            "$EIPS" -f -g "$png" >/dev/null 2>&1
        else
            "$EIPS" -g "$png" >/dev/null 2>&1
        fi
    fi
}

wifi_on() {
    # 8.8.8.8 在国内网络常不可达，用阿里 DNS 探测，避免误判掉线多等 15s
    if [ "$WIFI_ON_DEMAND" != "true" ] && ping -c 1 -W 3 223.5.5.5 >/dev/null 2>&1; then
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
