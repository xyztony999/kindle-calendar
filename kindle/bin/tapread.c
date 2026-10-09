/* tapread — Kindle 触摸事件读取助手（v2.1 页面导航用）
 *
 * 读取触摸屏 evdev 设备，向 stdout 输出行协议（API 契约 I-6）：
 *   D <x> <y>   触摸按下
 *   U <x> <y>   触摸抬起
 *
 * 长按/点击判定由 dash.sh 根据相邻 D/U 行的时间差完成。
 * 自动探测触摸设备：按名称匹配（cyttsp/atmel/goodix/elan/touch 等），
 * 找不到时回退遍历全部 event 设备。
 *
 * 交叉编译（在 PC 上，任一 ARM 交叉工具链均可）：
 *   arm-linux-gnueabi-gcc -O2 -static -o tapread tapread.c
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

static int name_matches(const char *name)
{
    static const char *keys[] = {
        "touch", "cyttsp", "atmel", "goodix", "elan",
        "ft5x06", "ili210x", "synaptics", "zinitix", NULL};
    for (int i = 0; keys[i]; i++)
        if (strstr(name, keys[i]))
            return 1;
    /* 大小写不敏感再扫一遍（如 "Touchscreen"） */
    for (int i = 0; keys[i]; i++) {
        size_t kl = strlen(keys[i]);
        for (const char *p = name; *p; p++) {
            size_t j;
            for (j = 0; j < kl && p[j]; j++)
                if (p[j] >= 'A' && p[j] <= 'Z' ? p[j] + 32 != keys[i][j] : p[j] != keys[i][j])
                    break;
            if (j == kl)
                return 1;
        }
    }
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
    /* 名称探测失败：回退 event0..event5 中第一个有 ABS_MT 的设备 */
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
    int fd = open_touch_device(argc > 1 ? argv[1] : NULL);
    if (fd < 0) {
        fprintf(stderr, "tapread: no touchscreen found\n");
        return 1;
    }

    /* 行缓冲 + 立即刷出，保证 dash.sh 每行可读 */
    setvbuf(stdout, NULL, _IOLBF, 0);

    struct input_event ev;
    int x = -1, y = -1, down = 0, emitted = 0;

    while (1) {
        ssize_t n = read(fd, &ev, sizeof(ev));
        if (n != (ssize_t)sizeof(ev))
            break;

        if (ev.type == EV_ABS) {
            if (ev.code == ABS_MT_POSITION_X || ev.code == ABS_X)
                x = ev.value;
            else if (ev.code == ABS_MT_POSITION_Y || ev.code == ABS_Y)
                y = ev.value;
            else if (ev.code == ABS_MT_TRACKING_ID)
                down = (ev.value >= 0);
        } else if (ev.type == EV_KEY && ev.code == BTN_TOUCH) {
            down = ev.value;
        } else if (ev.type == EV_SYN && ev.code == SYN_REPORT) {
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
