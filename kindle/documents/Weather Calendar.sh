#!/bin/sh
# 文件名带空格。这不是英文入口，只转入同目录的中文启动器。
# 英文入口是不带空格的 WeatherCalendar.sh。
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
TARGET="$HERE/天气台历.sh"
LOG_DIR="/mnt/us/kindle-calendar"
if [ -f "$TARGET" ]; then
    exec "$TARGET"
fi
mkdir -p "$LOG_DIR" 2>/dev/null
echo "$(date '+%Y-%m-%d %H:%M:%S') [book] Weather Calendar: missing sibling launcher" >> "$LOG_DIR/dash.log" 2>/dev/null
exit 1
