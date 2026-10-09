/* tapread — Kindle 触摸事件读取助手（v2.1 页面导航用）
 *
 * 读取触摸屏 evdev 设备，向 stdout 输出行协议（API 契约 I-6）：
 *   D <x> <y>   触摸按下
 *   U <x> <y>   触摸抬起
 * 调试模式（-v）：把所有 EV_ABS/EV_KEY/SYN 事件打到 stderr，
 *   用于真机排查触摸协议（PW2 为 cyttsp4_mt，event1）。
 *
 * 按下/抬起判定（兼容 type-A / type-B 多点协议）：
 *   BTN_TOUCH            → 1/0（权威）
 *   ABS_MT_TRACKING_ID   → >=0 / -1
 *   ABS_MT_PRESSURE 或 ABS_MT_TOUCH_MAJOR → >0 判按下（type-A 兜底）
 *
 * 交叉编译：
 *   arm-linux-gnueabihf-gcc -O2 -static -o tapread tapread.c
 * 放置：/mnt/us/kindle-calendar/bin/tapread && chmod +x
 */

#include <dirent.h>
#include <fcntl.h>
#include <linux/input.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>

static int verbose = 0;

static int name_matches(const char *name)
{
    static const char *keys[] = {
        "touch", "cyttsp", "atmel", "goodix", "elan",
        "ft5x06", "ili210x", "synaptics", "zinitix", NULL};
    for (int i = 0; keys[i]; i++)
        if (strstr(name, keys[i]))
            return 1;
    return 0;
}

static int open_touch_device(const char *explicit_path)
{
    char name[256];
    char path[64];

    if (explicit_path) {
        int fd = open(explicit_path, O_RDONLY);
        if (fd >= 0)
            return fd;
        return -1;
    }

    for (int i = 0; i < 32; i++) {
        snprintf(path, sizeof(path), "/dev/input/event%d", i);
        int fd = open(path, O_RDONLY);
        if (fd < 0)
            continue;
        memset(name, 0, sizeof(name));
        if (ioctl(fd, EVIOCGNAME(sizeof(name) - 1), name) >= 0 && name_matches(name)) {
            fprintf(stderr, "tapread: using %s (%s)\n", path, name);
            return fd;
        }
        close(fd);
    }
    /* 名称探测失败：回退第一个有 ABS_MT 能力的设备 */
    for (int i = 0; i < 6; i++) {
        snprintf(path, sizeof(path), "/dev/input/event%d", i);
        int fd = open(path, O_RDONLY);
        if (fd < 0)
            continue;
        unsigned long absbits[(ABS_MAX + 1) / (8 * sizeof(unsigned long))] = {0};
        if (ioctl(fd, EVIOCGBIT(EV_ABS, sizeof(absbits)), absbits) >= 0 &&
            (absbits[ABS_MT_POSITION_X / (8 * sizeof(unsigned long))] &
             (1UL << (ABS_MT_POSITION_X % (8 * sizeof(unsigned long)))))) {
            fprintf(stderr, "tapread: fallback %s (no name match)\n", path);
            return fd;
        }
        close(fd);
    }
    return -1;
}

int main(int argc, char **argv)
{
    const char *explicit_path = NULL;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-v"))
            verbose = 1;
        else
            explicit_path = argv[i];
    }

    int fd = open_touch_device(explicit_path);
    if (fd < 0) {
        fprintf(stderr, "tapread: no touchscreen found\n");
        return 1;
    }

    setvbuf(stdout, NULL, _IOLBF, 0);

    struct input_event ev;
    int x = -1, y = -1, down = 0, emitted = 0;

    while (1) {
        ssize_t n = read(fd, &ev, sizeof(ev));
        if (n != (ssize_t)sizeof(ev))
            break;

        if (ev.type == EV_ABS) {
            switch (ev.code) {
            case ABS_MT_POSITION_X:
            case ABS_X:
                x = ev.value;
                break;
            case ABS_MT_POSITION_Y:
            case ABS_Y:
                y = ev.value;
                break;
            case ABS_MT_TRACKING_ID:
                down = (ev.value >= 0);
                break;
            case ABS_MT_PRESSURE:
            case ABS_MT_TOUCH_MAJOR:
                if (ev.value > 0)
                    down = 1;
                break;
            }
            if (verbose)
                fprintf(stderr, "E ABS code=%u val=%d\n", ev.code, ev.value);
        } else if (ev.type == EV_KEY && ev.code == BTN_TOUCH) {
            down = ev.value;
            if (verbose)
                fprintf(stderr, "E KEY BTN_TOUCH val=%d\n", ev.value);
        } else if (ev.type == EV_SYN && ev.code == SYN_REPORT) {
            if (verbose)
                fprintf(stderr, "E SYN down=%d x=%d y=%d\n", down, x, y);
            if (down && !emitted && x >= 0 && y >= 0) {
                printf("D %d %d\n", x, y);
                emitted = 1;
            } else if (!down && emitted) {
                printf("U %d %d\n", x, y);
                emitted = 0;
                x = y = -1; /* 抬起后等待下一次按下 */
            }
        }
    }
    close(fd);
    return 0;
}
