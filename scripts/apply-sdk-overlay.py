#!/usr/bin/env python3
"""Apply the reviewed KL SDK overlay to the exact pinned upstream SDK commit."""

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / "pico-keys-sdk"
EXPECTED_SDK = "50699e53e8ada214c27f6c9b66ea3b6f127fc655"

USB_OLD = '''    enabled_usb_itf = PHY_USB_ITF_ALL;
#ifndef ENABLE_EMULATION
    if (phy_data.enabled_usb_itf_present) {
        enabled_usb_itf = phy_data.enabled_usb_itf;
    }
#endif
'''
USB_NEW = '''#ifdef KL_FIDO_ONLY_RUNTIME
    enabled_usb_itf = PHY_USB_ITF_HID;
#else
    enabled_usb_itf = PHY_USB_ITF_ALL;
#ifndef ENABLE_EMULATION
    if (phy_data.enabled_usb_itf_present) {
        enabled_usb_itf = phy_data.enabled_usb_itf;
    }
#endif
#endif
'''

REPLACEMENTS = {
    "src/usb/usb.c": [(USB_OLD, USB_NEW)],
    "src/usb/usb_descriptors.c": [
        ('#define URL  "www.picokeys.com"', '#define URL  "www.karaaslanlabs.com"'),
        ('TUD_BOS_WEBUSB_DESCRIPTOR(VENDOR_REQUEST_WEBUSB, 1)',
         'TUD_BOS_WEBUSB_DESCRIPTOR(VENDOR_REQUEST_WEBUSB, 0)'),
        ('    "Pol Henarejos",                     // 1: Manufacturer\n'
         '    "Pico Key",                       // 2: Product',
         '    "Karaaslan Labs",                     // 1: Manufacturer\n'
         '    "KL Security Key",                       // 2: Product'),
    ],
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(SDK), *args], text=True).strip()


def expected_files() -> dict[str, str]:
    result: dict[str, str] = {}
    for rel, replacements in REPLACEMENTS.items():
        base = subprocess.check_output(
            ["git", "-C", str(SDK), "show", f"{EXPECTED_SDK}:{rel}"], text=True
        )
        expected = base
        for old, new in replacements:
            if expected.count(old) != 1:
                raise SystemExit(f"overlay source invariant failed for {rel}")
            expected = expected.replace(old, new)
        result[rel] = expected
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate applicability without modifying files")
    args = parser.parse_args()
    head = git("rev-parse", "HEAD")
    if head != EXPECTED_SDK:
        raise SystemExit(f"refusing overlay: expected SDK {EXPECTED_SDK}, found {head}")

    expected = expected_files()
    base_files = {
        rel: subprocess.check_output(
            ["git", "-C", str(SDK), "show", f"{EXPECTED_SDK}:{rel}"], text=True
        )
        for rel in REPLACEMENTS
    }
    current = {rel: (SDK / rel).read_text() for rel in REPLACEMENTS}
    status = git("status", "--porcelain")
    dirty_paths = {line[3:] for line in status.splitlines() if len(line) >= 4}
    meaningful_dirty = {p for p in dirty_paths if not p.startswith("third-party/")}

    if all(current[rel] == base_files[rel] for rel in REPLACEMENTS):
        if meaningful_dirty:
            raise SystemExit(f"refusing overlay: unrelated SDK changes: {sorted(meaningful_dirty)}")
        if args.check:
            print("KL SDK OVERLAY CHECK: PASS")
            return 0
        for rel, content in expected.items():
            (SDK / rel).write_text(content)
        print("KL SDK OVERLAY: APPLIED")
        return 0

    if all(current[rel] == expected[rel] for rel in REPLACEMENTS):
        allowed = {"src/usb/usb.c", "src/usb/usb_descriptors.c"}
        if meaningful_dirty != allowed:
            raise SystemExit(f"overlay present with unexpected SDK dirt: {sorted(meaningful_dirty)}")
        print("KL SDK OVERLAY: ALREADY APPLIED")
        return 0

    raise SystemExit("refusing overlay: SDK files are in a mixed or unknown state")


if __name__ == "__main__":
    raise SystemExit(main())