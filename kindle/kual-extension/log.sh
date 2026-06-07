#!/bin/sh
LOG="/mnt/us/kindle-calendar/dash.log"

if [ -f "$LOG" ]; then
    tail -20 "$LOG" > /tmp/calendar-log.txt
    /usr/sbin/eips 0 1 "见 /tmp/calendar-log.txt"
else
    /usr/sbin/eips 0 1 "尚无日志"
fi
