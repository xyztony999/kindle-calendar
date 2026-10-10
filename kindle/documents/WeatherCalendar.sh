#!/bin/sh
# 英文书库入口。只声明语言，然后交给同目录的中文启动器拉起同一套 dash.sh。
# 书名是文件名去掉 .sh，所以这里必须叫 WeatherCalendar.sh，不要改成带空格的文件。
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
export KC_BOOK_LANG=en
exec "$HERE/天气台历.sh"
