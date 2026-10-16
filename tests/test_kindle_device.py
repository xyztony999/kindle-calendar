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
        setup = """
PAGES=today
CUR_PAGE=today
R_TODAY_REGIONS=HEADER
SETTINGS_VERSION=abc123
CLOCK_ENABLED=0
wifi_on() { echo wifi_on; }
wifi_off() { echo wifi_off; }
wait_for_network() { :; }
apply_clock() { :; }
ensure_cur_page() { :; }
log() { :; }
report_device() { echo report:$1:$2; }
env_sync() { return "$env_fail"; }
sync_region_asset() { return "$asset_fail"; }
goto_page() { echo draw; return "$draw_fail"; }
"""
        base = setup + function("do_fetch")
        for env_fail, asset_fail, draw_fail in [(0,0,0), (1,0,0), (0,1,0), (0,0,1)]:
            with self.subTest(env=env_fail, asset=asset_fail, draw=draw_fail):
                output = self.run_shell(base + f"\nenv_fail={env_fail}; asset_fail={asset_fail}; draw_fail={draw_fail}; do_fetch\n")
                expected = env_fail == asset_fail == draw_fail == 0
                self.assertEqual("report:v2:abc123" in output, expected)
                if expected:
                    self.assertLess(output.index("draw"), output.index("report:"))
                    self.assertLess(output.index("report:"), output.index("wifi_off"))

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
