# kindle/bin/ — 设备端二进制

## fbink（v2 分区模式必需）

[FBInk](https://github.com/NiLuJe/FBInk)（MIT）是越狱社区标准的 framebuffer 工具
（KOReader 同款底层），提供分区刷新与波形控制（A2/GC16）。

**本仓库已内置 Kindle 版二进制**（v1.25.0 K5 构建，适配 Touch 及之后所有机型
包括 PW2/PW3/PW5），来源为 [MobileRead 发布帖](https://www.mobileread.com/forums/showthread.php?t=299620)。
无需另外下载，直接同步到设备：

```bash
scp kindle/bin/fbink root@<Kindle的IP>:/mnt/us/kindle-calendar/bin/fbink
# 无 SSH 时：USB 连接，把 kindle/bin/fbink 文件拷到 USB 盘 kindle-calendar/bin/ 下
```

> 注意 `bin/fbink` 必须是**文件**而非目录：误把 FBInk 源码解压到此处会导致
> 显示函数把它当作二进制执行而静默失败（白屏）。display.sh 已加 -f 防御。

没有 fbink 也能用：`dash.sh` 会自动回退 v1 整图模式（eips），
只是没有分钟级时钟和分区刷新。

## tapread（v2.1 触摸翻页，可选）

源码在本目录 `tapread.c`：读取触摸屏 evdev 设备，输出 `D x y` / `U x y`
行协议（长按/点击判定由 dash.sh 完成）。自动按名称探测触摸设备，
找不到时回退含 ABS_MT 能力的设备。

**需要交叉编译**（Kindle 上无工具链）：

```bash
# Ubuntu/Debian: apt install gcc-arm-linux-gnueabi
arm-linux-gnueabi-gcc -O2 -static -o tapread tapread.c
scp tapread root@<Kindle的IP>:/mnt/us/kindle-calendar/bin/tapread
ssh root@<Kindle的IP> "chmod +x /mnt/us/kindle-calendar/bin/tapread"
```

验证：`ssh root@<Kindle的IP> /mnt/us/kindle-calendar/bin/tapread`，
点按屏幕应输出 `D x y` / `U x y` 行（Ctrl-C 退出）。

放置 tapread 后 `dash.sh` 自动进入沉浸模式并启用手势（左右边缘翻页、
月历页左右下角翻月、右上角刷新、长按右上角退出、底部中央夜间反色）；
不放则仅有自动轮播（今日页 120s、其余 30s）。

