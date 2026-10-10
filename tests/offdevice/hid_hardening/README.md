# HID v5.3 off-device hardening (WIP, not conformance)

This is a **local patch-and-test preparation bundle** based on the public
`karaaslanlabs/kl-security-key` main commit `71c419cc402241bbbe3e892195d051a6d6f89956`
and `pico-keys-sdk` submodule commit
`50699e53e8ada214c27f6c9b66ea3b6f127fc655`.

The upstream SDK is a Git submodule. The SDK patch is intentionally not
applied to the upstream gitlink, and is not a new certified/published release.

From the repository root on a disposable working copy:

```bash
git apply --check patches/hid-v5.3-product-guards.patch
git apply patches/hid-v5.3-product-guards.patch
git submodule update --init pico-keys-sdk
git -C pico-keys-sdk apply --check ../patches/hid-v5.3-sdk-hardening.patch
git -C pico-keys-sdk apply ../patches/hid-v5.3-sdk-hardening.patch
python3 tests/offdevice/hid_hardening/run_host_regressions.py --sdk pico-keys-sdk
```

Requires gcc, Python 3, AddressSanitizer and UBSan on the **host**.
The harness compiles the actual `hid.c` and `apdu.c` against stubs for
application/USB/hardware interfaces. It never opens a USB device. Its tests
include max payload 7609, buffer bounds, padding, CID/sequence, partial
allocation failure/retry, APDU GET RESPONSE, and pending-APDU INIT/VERSION
data exposure. These host results **do not prove RP2040 runtime correctness**.

**Known unresolved:** live MCU heap availability, concurrent USB activity,
keyboard-enabled OTP report-buffer lifetime, firmware attestation identity
on hardware, and official FIDO conformance. No physical flash/reset, MDS
publication, product/security qualification claim, or GitHub publication
is authorized by this WIP bundle.

Do not commit UF2s, sensitive PKI material, device-specific attestation
identifiers, or locally generated logs.
