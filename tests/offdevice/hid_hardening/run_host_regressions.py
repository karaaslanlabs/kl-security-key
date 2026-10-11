#!/usr/bin/env python3
"""KL Security Key HID hardening: off-device, ASan/UBSan, real-source host tests.

No USB/device access. Does not flash, reset, provision or read private keys.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk", type=Path, required=True, help="Patched SDK checkout")
    parser.add_argument("--results", type=Path, help="Optional JSON results output")
    args = parser.parse_args()
    sdk = args.sdk.expanduser().resolve()
    hid = sdk / "src/usb/hid/hid.c"
    apdu = sdk / "src/apdu.c"
    if not hid.is_file() or not apdu.is_file():
        parser.error("Expected SDK src/usb/hid/hid.c and src/apdu.c")
    tests = Path(__file__).resolve().parent
    stubs = tests / "embedded-stubs"
    common = [
        "gcc", "-DTEST_CURRENT=1", "-std=gnu11", "-g", "-O1",
        "-Wall", "-Wextra", "-Werror", "-fno-omit-frame-pointer",
        "-fsanitize=address,undefined", "-no-pie", "-DUSB_ITF_HID",
        '-DHID_SOURCE="' + str(hid) + '"',
        "-I" + str(stubs),
        "-I" + str(sdk / "src/usb/hid"),
        "-I" + str(sdk / "src/usb"),
        "-I" + str(sdk / "src"),
    ]
    cases = [
        ["pending-apdu-leak"], ["before-init"], ["all"],
        ["fido-only", "0"], ["fido-only", "15"],
    ] + [["oom", str(i)] for i in range(1, 16)]
    results = []
    with tempfile.TemporaryDirectory(prefix="kl-hid-native-") as work:
        folder = Path(work)
        targets = {}
        for name, source, extra in [
            ("hid", tests / "real_hid_harness.c", []),
            ("apdu", tests / "real_apdu_harness.c",
             ["-Wno-unused-function", "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections"]),
        ]:
            executable = folder / name
            apdu_define = ['-DAPDU_SOURCE="' + str(apdu) + '"'] if name == "apdu" else []
            cmd = common[:1] + extra + apdu_define + common[1:] + [str(source), "-o", str(executable)]
            built = subprocess.run(cmd, capture_output=True, text=True)
            if built.returncode:
                print("COMPILE_FAIL", name, built.stderr[-2500:])
                raise SystemExit(2)
            print("COMPILE_PASS", name)
            targets[name] = executable
        env = {**os.environ, "ASAN_OPTIONS": "detect_leaks=0"}
        suite = [("hid", case) for case in cases] + [("apdu", [])]
        for name, argv in suite:
            proc = subprocess.run([str(targets[name])] + argv, capture_output=True, text=True, env=env)
            entry = {
                "suite": name, "args": argv, "exit": proc.returncode,
                "last_output": (proc.stdout + proc.stderr).strip().splitlines()[-3:],
            }
            results.append(entry)
            print(("PASS" if proc.returncode == 0 else "FAIL"),
                  name, "/".join(argv or ["integration"]))
            if proc.returncode:
                print((proc.stdout + proc.stderr)[-3000:])
    passed = sum(x["exit"] == 0 for x in results)
    print("OFFDEVICE_REGRESSION", passed, "/", len(results))
    if args.results:
        args.results.parent.mkdir(parents=True, exist_ok=True)
        args.results.write_text(json.dumps({
            "sdk_commit_expected": "50699e53e8ada214c27f6c9b66ea3b6f127fc655",
            "physical_device_tested": False,
            "sanitizers": ["address", "undefined"],
            "passed": passed, "total": len(results), "cases": results,
        }, indent=2) + "\n")
        print("RESULTS_FILE", args.results)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
