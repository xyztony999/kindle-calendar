"""Execute client functions with fake networking and display, without Kindle hardware."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "kindle/dash.sh").read_text(encoding="utf-8")
SH = shutil.which("sh")
if not SH and shutil.which("git"):
    candidate = Path(shutil.which("git")).parent.parent / "bin/sh.exe"
    if candidate.exists():
        SH = str(candidate)


def function(name):
    return re.search(r"^" + name + r"\(\) \{\n.*?^\}", SOURCE, re.M | re.S).group(0)


@unittest.skipUnless(SH, "POSIX shell unavailable")
class KindleDeviceTests(unittest.TestCase):
    def run_shell(self, script):
        result = subprocess.run([SH, "-s"], input=script, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_fetch_confirmation_only_after_assets_and_display_and_before_wifi_off(self):
        # v2.2：do_fetch = net_fetch_assets（子进程逻辑：开网拉取后关网）+ fetch_consume
        # （主循环：本地重绘，全部成功才后台上报确认；上报输出被 >/dev/null 吞掉，用文件观察）
        setup = """
PAGES=today
CUR_PAGE=today
R_TODAY_REGIONS=HEADER
SETTINGS_VERSION=abc123
CLOCK_ENABLED=0
STATE_DIR=$(mktemp -d)
CACHE_DIR=$(mktemp -d)
: > "$CACHE_DIR/dashboard.env"
wifi_on() { echo wifi_on; }
wifi_off() { echo wifi_off; }
wait_for_network() { :; }
apply_clock() { :; }
ensure_cur_page() { :; }
log() { :; }
clear_screen() { :; }
draw_clock() { :; }
fetch_backoff() { :; }
report_device() { echo report:$1:$2 > "$STATE_DIR/report.log"; }
env_sync() { return "$env_fail"; }
sync_region_asset() { return "$asset_fail"; }
goto_page() { echo draw; return "$draw_fail"; }
"""
        base = setup + function("net_fetch_assets") + "\n" + function("fetch_consume") + "\n" + function("do_fetch")
        for env_fail, asset_fail, draw_fail in [(0,0,0), (1,0,0), (0,1,0), (0,0,1)]:
            with self.subTest(env=env_fail, asset=asset_fail, draw=draw_fail):
                output = self.run_shell(base + f"""
env_fail={env_fail}; asset_fail={asset_fail}; draw_fail={draw_fail}
do_fetch
wait
echo --report--
cat "$STATE_DIR/report.log" 2>/dev/null || true
""")
                expected = env_fail == asset_fail == draw_fail == 0
                self.assertEqual("report:v2:abc123" in output, expected)
                if expected:
                    # 网络窗口先关，再本地重绘，确认发生在绘制之后
                    self.assertLess(output.index("wifi_on"), output.index("wifi_off"))
                    self.assertLess(output.index("wifi_off"), output.index("draw"))
                    self.assertLess(output.index("draw"), output.index("--report--"))

    def test_reporting_uses_existing_host_and_is_nonfatal(self):
        setup = """
API_URL=https://calendar.example/api/v1/dashboard.env?lang=en
INTERVAL=900
wget() { printf '%s\\n' "$*"; return 1; }
curl() { echo curl-failed; return 1; }
log() { echo "$*"; }
"""
        output = self.run_shell(setup + function("report_device") + '\nreport_device v2 abc123\necho survived\n')
        self.assertIn("https://calendar.example/api/v1/device/heartbeat", output)
        self.assertIn("interval_s=900&mode=v2", output)
        self.assertIn("applied_version=abc123", output)
        self.assertIn("X-Kindle-Device: dash", output)
        self.assertIn("survived", output)

    def test_wget_failure_falls_back_once_to_curl(self):
        setup = """
API_URL=https://calendar.example/api/v1/dashboard.env
INTERVAL=900
wget() { echo wget-400 >&2; return 1; }
curl() { echo curl-success >&2; return 0; }
log() { echo "$*"; }
"""
        output = self.run_shell(setup + function("report_device") + '\nreport_device v2 abc123\n')
        self.assertIn("wget failed: wget-400", output)
        self.assertIn("device report accepted: mode=v2 version=abc123", output)
        self.assertNotIn("keeping previous", output)

    def test_wget_form_does_not_add_duplicate_content_type(self):
        setup = """
API_URL=https://calendar.example/api/v1/dashboard.env
INTERVAL=900
wget() {
    case "$*" in *Content-Type*) echo duplicate-header >&2; return 1;; esac
    case "$*" in *'--post-data=interval_s=900&mode=v2&applied_version=abc123'*) return 0;; esac
    echo bad-form >&2; return 1
}
curl() { return 1; }
log() { echo "$*"; }
"""
        output = self.run_shell(setup + function("report_device") + '\nreport_device v2 abc123\n')
        self.assertIn("device report accepted", output)
        self.assertNotIn("wget failed", output)

    def test_failed_display_propagates(self):
        setup = """
CACHE_DIR=.
STATE_DIR=.
R_TODAY_HEADER_X=0
R_TODAY_HEADER_Y=0
R_TODAY_HEADER_ETAG=version
fbink_img() { return 1; }
"""
        # Supply a virtual cache file without touching the workspace.
        output = self.run_shell(setup + function("draw_region").replace('[ -f "$CACHE_DIR/$lc.png" ] || return 1', ':') +
                                '\nif draw_region TODAY_HEADER 0 1; then echo bad; else echo failed; fi\n')
        self.assertIn("failed", output)
        self.assertNotIn("bad", output)

    def test_draw_clock_24h_and_12h(self):
        setup = """
CLOCK_ENABLED=1
CLOCK_X=100
CLOCK_Y=50
CLOCK_DIGIT_W=40
CLOCK_DIGIT_H=60
CLOCK_COLON_W=20
CLOCK_GAP=5
CLOCK_SUF_W=14
CLOCK_SUF_H=12
CLOCK_HOUR12=0
STATE_DIR=$(mktemp -d)
GLYPH_DIR=$(mktemp -d)
for g in 0 1 2 3 4 5 6 7 8 9 colon am pm; do : > "$GLYPH_DIR/$g.png"; done
apply_clock() { :; }
date() { case "$1" in +%H) printf '%s\\n' "$FAKE_H";; +%M) printf '%s\\n' "$FAKE_M";; *) command date "$@";; esac; }
fbink_img() { echo "draw:${1##*/}@$2,$3"; }
"""
        base = setup + function("draw_clock")
        # 24h 首绘 5 格；分钟不变零输出；分钟变化只差分个位
        out = self.run_shell(base + """
FAKE_H=09; FAKE_M=05
draw_clock
echo --same--
draw_clock
echo --min--
FAKE_M=06
draw_clock
""")
        self.assertIn("draw:0.png@100,50", out)
        self.assertIn("draw:9.png@145,50", out)
        self.assertIn("draw:colon.png@190,50", out)
        self.assertIn("draw:5.png@260,50", out)
        same = out.split("--same--")[1].split("--min--")[0]
        self.assertNotIn("draw:", same)
        minute = out.split("--min--")[1]
        self.assertEqual(minute.strip(), "draw:6.png@260,50")

        # 切 12h：单数字小时起点右移半格 + am 后缀底对齐；位数变化整只重画
        out = self.run_shell(base + """
FAKE_H=09; FAKE_M=05
CLOCK_HOUR12=1
draw_clock
echo --min2--
FAKE_M=06
draw_clock
echo --two-digit--
FAKE_H=12; FAKE_M=30
draw_clock
""")
        self.assertIn("draw:9.png@122,50", out)          # 100 + (40+5)/2
        self.assertIn("draw:am.png@282,98", out)         # 末位 237+45=282, y=50+60-12
        minute = out.split("--min2--")[1].split("--two-digit--")[0]
        # 个位差分；后缀 am 未变（am→pm 才重画）
        self.assertEqual(minute.strip(), "draw:6.png@237,50")
        two = out.split("--two-digit--")[1]
        self.assertIn("draw:1.png@100,50", two)          # 两位小时回到原始起点
        self.assertIn("draw:pm.png@305,98", two)         # 260+45=305

    def test_draw_clock_mode_switch_full_redraw(self):
        setup = """
CLOCK_ENABLED=1
CLOCK_X=100
CLOCK_Y=50
CLOCK_DIGIT_W=40
CLOCK_DIGIT_H=60
CLOCK_COLON_W=20
CLOCK_GAP=5
CLOCK_SUF_W=14
CLOCK_SUF_H=12
STATE_DIR=$(mktemp -d)
GLYPH_DIR=$(mktemp -d)
for g in 0 1 2 3 4 5 6 7 8 9 colon am pm; do : > "$GLYPH_DIR/$g.png"; done
apply_clock() { :; }
date() { case "$1" in +%H) printf '%s\\n' "$FAKE_H";; +%M) printf '%s\\n' "$FAKE_M";; *) command date "$@";; esac; }
fbink_img() { echo "draw:${1##*/}@$2,$3"; }
"""
        base = setup + function("draw_clock")
        out = self.run_shell(base + """
FAKE_H=09; FAKE_M=05
draw_clock
CLOCK_HOUR12=1
echo --switch--
draw_clock
echo --last--
cat "$STATE_DIR/clock.last"
""")
        switched = out.split("--switch--")[1].split("--last--")[0]
        # 模式切换：位数 5→4 → 整只重画（含冒号）
        self.assertIn("draw:colon.png@167,50", switched)
        self.assertIn("draw:am.png@282,98", switched)
        self.assertEqual(out.split("--last--")[1].strip(), "9:05 am")
