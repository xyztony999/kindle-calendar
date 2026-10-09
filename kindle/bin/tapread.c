/* tapread — Kindle 触摸事件读取助手（freestanding 版）
 *
 * 为什么不用 libc：PW2（i.MX6 SoloLite，Cortex-A9 无 NEON）上，常见交叉
 * 工具链的静态 glibc 自带 NEON/VFP 指令 → SIGILL（Illegal instruction）。
 * 本文件以裸 Linux ARM 系统调用实现（-nostdlib），纯整数代码，armv5te 起
 * 任意内核可跑。
 *
 * 输出（stdout）：D <x> <y>（按下）/ U <x> <y>（抬起）
 * 调试（stderr，始终开启；dash.sh 里被重定向到 /dev/null）：
 *   tapread: using /dev/input/event1 (cyttsp4_mt)
 *   E ABS code=<c> val=<v> / E KEY BTN_TOUCH val=<v> / E SYN down=<d> x=<x> y=<y>
 *
 * 构建（任意 ARM 交叉 gcc）：
 *   arm-...-gcc -nostdlib -static -ffreestanding -fno-stack-protector \
 *     -fno-builtin -march=armv5te -marm -Os -o tapread tapread.c
 */

typedef unsigned int u32;
typedef unsigned short u16;
typedef int s32;

/* ── ARM EABI 裸系统调用 ── */

static long sys3(long n, long a, long b, long c) {
    register long r7 __asm__("r7") = n;
    register long r0 __asm__("r0") = a;
    register long r1 __asm__("r1") = b;
    register long r2 __asm__("r2") = c;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r7), "r"(r1), "r"(r2) : "memory");
    return r0;
}

#define SYS_EXIT 1
#define SYS_READ 3
#define SYS_WRITE 4
#define SYS_OPEN 5
#define SYS_CLOSE 6
#define SYS_IOCTL 54

/* gcc -ffreestanding 下仍可能生成对 memset/memcpy 的调用 */
void *memset(void *d, int c, unsigned n) {
    char *p = (char *)d;
    while (n--)
        *p++ = (char)c;
    return d;
}
void *memcpy(void *d, const void *s, unsigned n) {
    char *p = (char *)d;
    const char *q = (const char *)s;
    while (n--)
        *p++ = *q++;
    return d;
}

__asm__(
    ".global _start\n"
    "_start:\n"
    "   sub sp, sp, #8\n" /* 保证 8 字节对齐 */
    "   bl  cmain\n");

/* ── 小工具：字符串 / 数字输出 ── */

static void wstr(int fd, const char *s) {
    unsigned n = 0;
    while (s[n])
        n++;
    sys3(SYS_WRITE, fd, (long)s, n);
}

static void wuint(int fd, u32 v) {
    /* 无除法版数字输出：libgcc 的 __aeabi_idiv 可能在无 udiv 的 A9 上
       产生非法指令，freestanding 下也不用除法助手 */
    static const u32 POW10[10] = {
        1000000000u, 100000000u, 10000000u, 1000000u, 100000u,
        10000u, 1000u, 100u, 10u, 1u};
    char b[11];
    int i = 0;
    int started = 0;
    for (int d = 0; d < 10; d++) {
        int c = 0;
        while (v >= POW10[d]) {
            v -= POW10[d];
            c++;
        }
        if (c || started || d == 9) {
            b[i++] = (char)('0' + c);
            started = 1;
        }
    }
    sys3(SYS_WRITE, fd, (long)b, i);
}

static void wint(int fd, s32 v) {
    if (v < 0) {
        wstr(fd, "-");
        wuint(fd, (u32)(-(long)v));
    } else {
        wuint(fd, (u32)v);
    }
}

static unsigned slen(const char *s) {
    unsigned n = 0;
    while (s[n])
        n++;
    return n;
}

static int seq_contains(const char *name, const char *key) {
    unsigned kl = slen(key);
    if (!kl)
        return 0;
    for (const char *p = name; *p; p++) {
        unsigned j = 0;
        while (j < kl && p[j] && p[j] == key[j])
            j++;
        if (j == kl)
            return 1;
    }
    return 0;
}

/* ── input ABI（32 位内核，16 字节事件）── */

struct kev {
    long sec;
    long usec;
    u16 type;
    u16 code;
    s32 value;
};

#define EV_SYN 0x00
#define EV_KEY 0x01
#define EV_ABS 0x03
#define SYN_REPORT 0x00
#define BTN_TOUCH 0x14a
#define ABS_X 0x00
#define ABS_Y 0x01
#define ABS_MT_POSITION_X 0x35
#define ABS_MT_POSITION_Y 0x36
#define ABS_MT_TRACKING_ID 0x39
#define ABS_MT_PRESSURE 0x2a
#define ABS_MT_TOUCH_MAJOR 0x30

#define IOC_READ 2u
#define EVIOCGNAME(len) (IOC_READ << 30 | (len) << 16 | 0x45u << 8 | 0x06u)
#define EVIOCGBIT(ev, len) (IOC_READ << 30 | (len) << 16 | 0x45u << 8 | (0x20u + (ev)))

static const char *TOUCH_KEYS[] = {
    "touch", "cyttsp", "atmel", "goodix", "elan",
    "ft5x06", "ili210x", "synaptics", "zinitix", 0};

static int open_touch(void) {
    char path[24];
    char name[256];
    const char *pre = "/dev/input/event";
    unsigned pl = slen(pre);

    for (int i = 0; i < 32; i++) {
        /* path = pre + i 的十进制（无除法拼法） */
        unsigned k = pl;
        if (i >= 20) {
            path[k++] = '2';
            path[k++] = (char)('0' + (i - 20));
        } else if (i >= 10) {
            path[k++] = '1';
            path[k++] = (char)('0' + (i - 10));
        } else {
            path[k++] = (char)('0' + i);
        }
        path[k] = 0;
        long fd = sys3(SYS_OPEN, (long)path, 0 /*O_RDONLY*/, 0);
        if (fd < 0)
            continue;
        memset(name, 0, sizeof(name));
        long r = sys3(SYS_IOCTL, fd, (long)EVIOCGNAME(sizeof(name) - 1), (long)name);
        if (r > 0) {
            name[r] = 0;
            for (int t = 0; TOUCH_KEYS[t]; t++) {
                if (seq_contains(name, TOUCH_KEYS[t])) {
                    wstr(2, "tapread: using ");
                    wstr(2, path);
                    wstr(2, " (");
                    wstr(2, name);
                    wstr(2, ")\n");
                    return (int)fd;
                }
            }
        }
        sys3(SYS_CLOSE, fd, 0, 0);
    }
    /* 回退：第一个带 ABS_MT_POSITION_X 能力的设备 */
    for (int i = 0; i < 6; i++) {
        unsigned k = pl;
        path[k++] = (char)('0' + i);
        path[k] = 0;
        long fd = sys3(SYS_OPEN, (long)path, 0, 0);
        if (fd < 0)
            continue;
        u32 bits[2] = {0, 0};
        sys3(SYS_IOCTL, fd, (long)EVIOCGBIT(EV_ABS, sizeof(bits)), (long)bits);
        u32 bit = 1u << (ABS_MT_POSITION_X % 32);
        if (bits[ABS_MT_POSITION_X / 32] & bit) {
            wstr(2, "tapread: fallback ");
            wstr(2, path);
            wstr(2, "\n");
            return (int)fd;
        }
        sys3(SYS_CLOSE, fd, 0, 0);
    }
    return -1;
}

static void report_event(const char *tag, u16 code, s32 value) {
    wstr(2, "E ");
    wstr(2, tag);
    wstr(2, " code=");
    wuint(2, code);
    wstr(2, " val=");
    wint(2, value);
    wstr(2, "\n");
}

static void emit(const char *du, int x, int y) {
    wstr(1, du);
    wstr(1, " ");
    wint(1, x);
    wstr(1, " ");
    wint(1, y);
    wstr(1, "\n");
}

void cmain(void) {
    int fd = open_touch();
    if (fd < 0) {
        wstr(2, "tapread: no touchscreen found\n");
        sys3(SYS_EXIT, 1, 0, 0);
    }

    struct kev ev;
    int x = -1, y = -1, down = 0, emitted = 0;

    for (;;) {
        long n = sys3(SYS_READ, fd, (long)&ev, sizeof(ev));
        if (n != sizeof(ev))
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
                down = ev.value >= 0;
                break;
            case ABS_MT_PRESSURE:
            case ABS_MT_TOUCH_MAJOR:
                if (ev.value > 0)
                    down = 1;
                break;
            }
            report_event("ABS", ev.code, ev.value);
        } else if (ev.type == EV_KEY && ev.code == BTN_TOUCH) {
            down = ev.value;
            report_event("KEY BTN_TOUCH", ev.code, ev.value);
        } else if (ev.type == EV_SYN && ev.code == SYN_REPORT) {
            wstr(2, "E SYN down=");
            wint(2, down);
            wstr(2, " x=");
            wint(2, x);
            wstr(2, " y=");
            wint(2, y);
            wstr(2, "\n");
            if (down && !emitted && x >= 0 && y >= 0) {
                emit("D", x, y);
                emitted = 1;
            } else if (!down && emitted) {
                emit("U", x, y);
                emitted = 0;
                x = y = -1;
            }
        }
    }
    sys3(SYS_CLOSE, fd, 0, 0);
    sys3(SYS_EXIT, 0, 0, 0);
}
