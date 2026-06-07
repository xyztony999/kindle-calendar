#!/bin/sh
DASH_DIR="/mnt/us/kindle-calendar"
CONFIG="$DASH_DIR/config.sh"
DASH_PNG="$DASH_DIR/dashboard.png"
LIB="$DASH_DIR/lib/display.sh"
EIPS="/usr/sbin/eips"

. "$CONFIG" 2>/dev/null
WIFI_ON_DEMAND="${WIFI_ON_DEMAND:-false}"

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

init_kindle_display 2>/dev/null || /etc/init.d/framework stop >/dev/null 2>&1

wifi_on

if command -v wget >/dev/null 2>&1; then
    wget -q -T 30 -O "$DASH_PNG.tmp" "$SERVER_URL" && mv "$DASH_PNG.tmp" "$DASH_PNG"
elif command -v curl >/dev/null 2>&1; then
    curl -s --connect-timeout 30 -o "$DASH_PNG.tmp" "$SERVER_URL" && mv "$DASH_PNG.tmp" "$DASH_PNG"
fi

if [ -f "$DASH_PNG" ]; then
    show_dashboard_png "$DASH_PNG" 1
fi

wifi_off
