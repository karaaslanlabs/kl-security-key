"""Fail-closed tests for the standard firmware build-profile dispatcher.

No device, SDK tree, firmware output, or remote service is accessed.
"""
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[3]
ENTRY = ROOT / "scripts" / "build-kl-reference.sh"


def invoke(profile, strict=None):
    env = os.environ.copy()
    env.pop("PICO_SDK_PATH", None)
    env.pop("PICO_TOOLCHAIN_PATH", None)
    env.pop("KL_V53_STRICT_PINS", None)
    env["KL_BUILD_PROFILE"] = profile
    if strict is not None:
        env["KL_V53_STRICT_PINS"] = strict
    return subprocess.run(
        ["bash", str(ENTRY)], capture_output=True, text=True, env=env
    )


class BuildProfileRouting(unittest.TestCase):
    def test_unknown_profile_refused_before_any_cleanup(self):
        result = invoke("not-an-approved-profile")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unsupported KL_BUILD_PROFILE", result.stderr)

    def test_v53_requires_explicit_strict_pin_mode(self):
        for strict in [None, "0", "junk"]:
            with self.subTest(strict=strict):
                result = invoke("v53-offdevice", strict)
                self.assertEqual(result.returncode, 2)
                self.assertIn("requires KL_V53_STRICT_PINS=1", result.stderr)

    def test_v53_dispatches_to_isolated_builder(self):
        result = invoke("v53-offdevice", "1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PICO_SDK_PATH", result.stderr)
        self.assertNotIn("Unsupported KL_BUILD_PROFILE", result.stderr)

    def test_entrypoints_parse(self):
        for script in [ENTRY, ROOT / "scripts" / "build-hid-v53-offdevice.sh"]:
            with self.subTest(script=script.name):
                p = subprocess.run(["bash", "-n", str(script)], capture_output=True)
                self.assertEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
