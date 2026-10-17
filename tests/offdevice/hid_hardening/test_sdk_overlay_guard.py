#!/usr/bin/env python3
"""Off-device SDK overlay fail-closed tests; all writes stay in disposable clones."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(os.environ["KL_OVERLAY_TEST_SOURCE_ROOT"]).resolve() if "KL_OVERLAY_TEST_SOURCE_ROOT" in os.environ else Path(__file__).resolve().parents[3]
SDK_SOURCE = Path(os.environ.get("KL_OVERLAY_TEST_SDK_SOURCE", str(ROOT / "pico-keys-sdk"))).resolve()
OVERLAY_SOURCE = Path(os.environ.get("KL_OVERLAY_TEST_SCRIPT_SOURCE", str(ROOT / "scripts" / "apply-sdk-overlay.py"))).resolve()
PIN = "50699e53e8ada214c27f6c9b66ea3b6f127fc655"
TARGETS = ("src/usb/usb.c", "src/usb/usb_descriptors.c")


def execute(*args):
    return subprocess.run(args, text=True, capture_output=True)


class OverlayGuard(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="kl-overlay-negative-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sdk = self.root / "pico-keys-sdk"
        (self.root / "scripts").mkdir()
        shutil.copyfile(OVERLAY_SOURCE, self.root / "scripts" / "apply-sdk-overlay.py")
        result = execute("git", "clone", "-q", "--no-hardlinks", str(SDK_SOURCE), str(self.sdk))
        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
        actual = execute("git", "-C", str(self.sdk), "rev-parse", "HEAD")
        self.assertEqual(actual.stdout.strip(), PIN)
        clean = execute("git", "-C", str(self.sdk), "status", "--porcelain")
        self.assertEqual(clean.stdout.strip(), "")

    def overlay(self, *args):
        return execute(sys.executable, str(self.root / "scripts" / "apply-sdk-overlay.py"), *args)

    def rejects(self, *args):
        result = self.overlay(*args)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any(x in result.stdout + result.stderr for x in ("refusing overlay", "unexpected SDK dirt")), result.stdout + result.stderr)

    def test_clean_check_readonly_and_apply_idempotent(self):
        before = {x: (self.sdk / x).read_bytes() for x in TARGETS}
        check = self.overlay("--check")
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertEqual({x: (self.sdk / x).read_bytes() for x in TARGETS}, before)
        applied = self.overlay()
        self.assertEqual(applied.returncode, 0, applied.stderr)
        after = {x: (self.sdk / x).read_bytes() for x in TARGETS}
        self.assertNotEqual(after, before)
        for flags in [("--check",), ()]:
            result = self.overlay(*flags)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({x: (self.sdk / x).read_bytes() for x in TARGETS}, after)

    def test_wrong_sdk_commit_rejected(self):
        result = execute("git", "-C", str(self.sdk), "-c", "user.name=LocalTest",
                         "-c", "user.email=local@example.invalid", "commit",
                         "-q", "--allow-empty", "-m", "temporary pin negative fixture")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.overlay("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected SDK", result.stdout + result.stderr)

    def test_changed_sdk_source_and_unrelated_dirty_rejected(self):
        path = self.sdk / TARGETS[0]
        path.write_text(path.read_text() + "\n/* disposable negative fixture */\n")
        self.rejects("--check")

    def test_partial_overlay_rejected(self):
        self.assertEqual(self.overlay().returncode, 0)
        original = execute("git", "-C", str(self.sdk), "show", PIN + ":" + TARGETS[1])
        self.assertEqual(original.returncode, 0, original.stderr)
        (self.sdk / TARGETS[1]).write_text(original.stdout)
        self.rejects("--check")

    def test_unrelated_sdk_change_rejected(self):
        f = self.sdk / "src/apdu.c"
        f.write_text(f.read_text() + "\n/* disposable unrelated change */\n")
        self.rejects("--check")

    def test_extra_dirty_file_rejected(self):
        self.assertEqual(self.overlay().returncode, 0)
        (self.sdk / "untracked-guard-test.txt").write_text("test")
        self.rejects("--check")


if __name__ == "__main__":
    unittest.main(verbosity=2)
