#!/bin/sh
# KUAL Scriptlet：启动天气台历
# 用法：KUAL 里运行一次；或复制到 extensions 做成菜单项

DASH_DIR="/mnt/us/kindle-calendar"
DASH_SH="$DASH_DIR/dash.sh"
PIDFILE="$DASH_DIR/dash.pid"

mkdir -p "$DASH_DIR"
chmod +x "$DASH_SH" 2>/dev/null

# 已在运行则跳过
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "台历已在运行 (PID $(cat "$PIDFILE"))"
    exit 0
fi

nohup "$DASH_SH" >/dev/null 2>&1 &
echo $! > "$PIDFILE"
echo "台历已启动，日志: $DASH_DIR/dash.log"
