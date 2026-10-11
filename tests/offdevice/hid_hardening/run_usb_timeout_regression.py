#!/usr/bin/env python3
"""Native sanitizer regression of real usb.c timeout routines, with host stubs.

Only source extraction into a disposable native program. Never touches USB
hardware, firmware identity, attestation material, or a physical key.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HOST_STUBS = r"""
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#define ENABLE_EMULATION 1
#define PICOKEYS_ERR_FILE_NOT_FOUND -1
#define PICOKEYS_ERR_BLOCKED -2
#define PICOKEYS_OK 0
#define EV_EXEC_FINISHED 3
#define MODE_PROCESSING 4
#define MODE_MOUNTED 5
typedef struct { int placeholder; } queue_t;
static queue_t card_to_usb_q;
static uint8_t ITF_TOTAL;
static uint8_t card_locked_itf;
static uint32_t timeout;
static uint32_t now_ms;
static bool queue_try_remove(queue_t *q, uint32_t *p) { (void)q; (void)p; return false; }
static uint32_t board_millis(void) { return now_ms; }
static void timeout_stop(void) { timeout = 0; }
static int led_get_mode(void) { return 0; }
static void led_set_mode(int x) { (void)x; }
"""

TEST_CASES = r"""
static int failures = 0;
static void check(bool condition, const char *name) {
    if (!condition) { fprintf(stderr, "USB_TIMEOUT_FAIL %s\n", name); failures++; }
}
int main(void) {
    ITF_TOTAL = 1;
    card_locked_itf = 0;
    timeout = 100;
    usb_set_timeout_counter(0, 200);
    now_ms = 299;
    check(card_status(0) == PICOKEYS_ERR_FILE_NOT_FOUND, "not_expired");
    now_ms = 301;
    check(card_status(0) == PICOKEYS_ERR_BLOCKED, "expired");
    /* A misrouted interface must not write beyond the fixed table. */
    usb_set_timeout_counter(255, 0xffffffffu);
    timeout = 100;
    now_ms = 299;
    check(card_status(0) == PICOKEYS_ERR_FILE_NOT_FOUND, "invalid_setter_no_overwrite");
    /* All possible configured interfaces are bounded; no dynamic allocation. */
    ITF_TOTAL = 5;
    usb_set_timeout_counter(4, 40);
    card_locked_itf = 4;
    timeout = 100;
    now_ms = 141;
    check(card_status(4) == PICOKEYS_ERR_BLOCKED, "last_interface_timeout");
    card_locked_itf = 5;
    timeout = 100;
    check(card_status(5) == PICOKEYS_ERR_BLOCKED, "invalid_status_fails_closed");
    if (!failures) puts("USB_TIMEOUT_NATIVE_SOURCE_PASS bounds_and_timeouts");
    return failures ? 1 : 0;
}
"""

def extract(source, signature):
    m = re.search(signature + r"\s*\{", source, re.MULTILINE | re.DOTALL)
    if not m:
        raise ValueError("missing expected function: " + signature)
    i, depth = m.end(), 1
    while i < len(source) and depth:
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
        i += 1
    if depth:
        raise ValueError("unbalanced function braces")
    return source[m.start():i]

def prepare(src):
    declaration = re.search(
        r"(?m)^static uint32_t \*timeout_counter = NULL;|^#define USB_TIMEOUT_COUNTER_CAPACITY 5u\nstatic uint32_t timeout_counter\[USB_TIMEOUT_COUNTER_CAPACITY\] = \{0\};",
        src,
    )
    if not declaration:
        raise ValueError("USB timeout storage not recognized")
    get_timeout = extract(src, r"void usb_set_timeout_counter\(uint8_t itf, uint32_t v\)")
    status = extract(src, r"int card_status\(uint8_t itf\)")
    return HOST_STUBS + "\n" + declaration.group() + "\n" + get_timeout + "\n" + status + "\n" + TEST_CASES

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--usb-source", type=Path, required=True)
    p.add_argument("--expect-baseline-failure", action="store_true")
    args = p.parse_args()
    src = args.usb_source.read_text(encoding="utf-8")
    if not args.expect_baseline_failure:
        if "calloc(ITF_TOTAL, sizeof(uint32_t))" in src:
            raise ValueError("USB dynamic timeout allocation unexpectedly persists")
        if "memset(timeout_counter, 0, sizeof(timeout_counter));" not in src:
            raise ValueError("USB timeout table does not reset during init")
    with tempfile.TemporaryDirectory(prefix="kl-usb-timeout-native-") as t:
        file = Path(t) / "usb_timeout_native.c"
        exe = Path(t) / "usb_timeout_native"
        file.write_text(prepare(src), encoding="utf-8")
        flags = ["gcc", "-std=gnu11", "-O1", "-g", "-Wall", "-Wextra",
                 "-Wno-unused-function", "-fsanitize=address,undefined",
                 "-fno-omit-frame-pointer", "-no-pie", str(file), "-o", str(exe)]
        cp = subprocess.run(flags, capture_output=True, text=True)
        if cp.returncode:
            print("USB_TIMEOUT_COMPILE_FAIL\n" + cp.stderr[-4000:])
            return 2
        print("USB_TIMEOUT_SOURCE_COMPILE_PASS", flush=True)
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0")
        cp = subprocess.run([str(exe)], capture_output=True, text=True, env=env)
        if args.expect_baseline_failure:
            if cp.returncode == 0:
                print("USB_TIMEOUT_BASELINE_UNEXPECTED_PASS")
                return 1
            print("USB_TIMEOUT_BASELINE_FAILURE_REPRODUCED")
            return 0
        print((cp.stdout + cp.stderr)[-4000:])
        return cp.returncode

if __name__ == "__main__":
    sys.exit(main())
