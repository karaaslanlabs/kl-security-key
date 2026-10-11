# HID v5.3 off-device hardening (WIP, not conformance)

This is an **experimental off-device patch-and-test bundle** derived from
the historical PR base commit `71c419cc402241bbbe3e892195d051a6d6f89956`
(not the current `main` commit). The pinned `pico-keys-sdk` submodule is
`50699e53e8ada214c27f6c9b66ea3b6f127fc655`. Its gitlink is unchanged.
None of this constitutes a firmware release, hardware proof, or certification.

## Supported v5.3 source and build order

The authoritative WIP entrypoint is
`KL_BUILD_PROFILE=v53-offdevice KL_V53_STRICT_PINS=1 bash scripts/build-kl-reference.sh`.
Configure pinned source/toolchain, third-party cache, offline picotool and
the off-repository output path per `docs/engineering/hid-v5.3-offdevice-hardening.md`.
It delegates to the isolated builder **before** the reference-profile cleanup.
Source composition is **KL USB/FIDO-only overlay first**, then the product
and SDK v5.3 patches. The default `reference` build **does not** include
v5.3 firmware changes.

For native host tests only, use a **separate disposable checkout** with the
pinned SDK; never apply these patches to the preserved original SDK tree:

```bash
git submodule update --init pico-keys-sdk
python3 scripts/apply-sdk-overlay.py --check
python3 scripts/apply-sdk-overlay.py
git apply --check patches/hid-v5.3-product-guards.patch
git -C pico-keys-sdk apply --check ../patches/hid-v5.3-sdk-hardening.patch
git apply patches/hid-v5.3-product-guards.patch
git -C pico-keys-sdk apply ../patches/hid-v5.3-sdk-hardening.patch
python3 tests/offdevice/hid_hardening/run_host_regressions.py --sdk pico-keys-sdk
python3 tests/offdevice/hid_hardening/run_otp_callback_regression.py --otp-source src/fido/otp.c
python3 tests/offdevice/hid_hardening/run_usb_timeout_regression.py --usb-source pico-keys-sdk/src/usb/usb.c
python3 -m unittest discover -s tests/offdevice/hid_hardening -p 'test_memory_layout.py' -v
python3 -m unittest discover -s tests/offdevice/hid_hardening -p 'test_build_profile.py' -v
```

Host tests require native GCC, Python 3, AddressSanitizer and UBSan.
GitHub CI tests this composed source path, **not** a full ARM firmware build.
The harness compiles the actual `hid.c` and `apdu.c` against stubs for
application/USB/hardware interfaces. It never opens a USB device. Its tests
include max payload 7609, buffer bounds, padding, CID/sequence, partial
allocation failure/retry, APDU GET RESPONSE, and pending-APDU INIT/VERSION
data exposure. These host results **do not prove RP2040 runtime correctness**.

**Known unresolved:** live MCU heap availability, concurrent USB activity,
keyboard-enabled OTP report-buffer lifetime, firmware attestation identity
on hardware, and official FIDO conformance. The WIP source and draft PR
are already public; that **does not** authorize a firmware binary release,
physical flash/reset, MDS publication, or security/certification claims.
Route unpublished security findings privately.

Do not commit UF2s, sensitive PKI material, device-specific attestation
identifiers, or locally generated logs.

GitHub Actions workflow:
`.github/workflows/hid-v5.3-offdevice-regression.yml` checks the SDK pin,
applies KL overlay **before** both patches, validates source composition
and routing, then runs HID/APDU, OTP, USB timeout and memory policy host tests.
Green CI does **not** prove GitHub ARM compilation or device/FIDO conformance.

## Keyboard HID / OTP report regression

Run with the product patch applied:

```bash
python3 tests/offdevice/hid_hardening/run_otp_callback_regression.py --otp-source src/fido/otp.c
```

This test extracts the exact `otp_status` and `otp_hid_get_report_cb`
function implementations from `otp.c`, compiles them with minimal stubs
under AddressSanitizer and UBSan, and checks response-pointer restoration,
status length restoration, initialized first byte, guarded report boundaries,
and report length clamping. It is **not** a build or integration test of
the entire OTP translation unit or live keyboard HID hardware.


## USB timeout table (native real-source regression)

`run_usb_timeout_regression.py` extracts the actual SDK `usb.c`
timeout setter and status callback, compiles the functions with native stubs
and runs them under ASan/UBSan. The test exercises timeout timing, bounds,
and an invalid interface. A one-time baseline negative test reproduced the
pre-fix failure with the original dynamically allocated timeout table.

The v5.3 SDK patch replaces that small timeout allocation with fixed-size
storage limited to the five currently supported USB interface slots.
The baseline and frozen hardware are unchanged. This native test is not
live USB/IRQ or cross-core concurrency verification.
