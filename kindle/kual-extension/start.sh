#!/bin/sh
DASH_DIR="/mnt/us/kindle-calendar"
PIDFILE="$DASH_DIR/dash.pid"

mkdir -p "$DASH_DIR"
chmod +x "$DASH_DIR/dash.sh" 2>/dev/null

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    /usr/sbin/eips 0 1 "台历已在运行"
    exit 0
fi

nohup "$DASH_DIR/dash.sh" >/dev/null 2>&1 &
echo $! > "$PIDFILE"
/usr/sbin/eips 0 1 "台历已启动"
