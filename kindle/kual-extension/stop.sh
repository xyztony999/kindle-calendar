#!/bin/sh
DASH_DIR="/mnt/us/kindle-calendar"
PIDFILE="$DASH_DIR/dash.pid"

if [ -f "$PIDFILE" ]; then
    kill "$(cat "$PIDFILE")" 2>/dev/null
    rm -f "$PIDFILE"
fi

pkill -f "/mnt/us/kindle-calendar/dash.sh" 2>/dev/null
/usr/sbin/eips 0 1 "台历已停止"
