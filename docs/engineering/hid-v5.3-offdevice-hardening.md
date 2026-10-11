# KL Security Key  HID v5.3 off-device engineering package

**Status:** WIP / host tests passed / hardware HOLD / no certification claim.

- Public main baseline: `71c419cc402241bbbe3e892195d051a6d6f89956`.
- SDK submodule baseline: `50699e53e8ada214c27f6c9b66ea3b6f127fc655`.
- Frozen v5.2 reference UF2 SHA256:
  `8b50a9fc27094e682e0436c494a6320a97c47fdcb05bbefffe98729f18abe0d8`.
- **Experimental** v5.3 UF2 SHA256 (off-device, never flashed):
  `c7c022c26764d8ab98795d8b5e75d0e42f15b0f0260514f10b08e501a8c80b9d`.

Changes captured here as two reviewable patches:

1. Product guards: error handling in FIDO/OTP callers and experimental version
   identifier.
2. SDK hardening: bounded dedicated CTAPHID TX buffer, RX framing checks,
   allocation failure cleanup/retry, GET RESPONSE offsets, stale padding
   prevention, and explicit INIT/VERSION field initialization.

The work was independently reproduced with real embedded HID/APDU **source**
compiled into native sanitizer-backed harnesses (not a physical authenticator).
Original recovery suite reported 20/20 host scenarios PASS, including all
7609+1 PING lengths and 15 allocation failure combinations. The on-device
firmware has NOT been exercised or FIDO conformance tested.

**STOP / not merge-ready:** The public repo pins an upstream SDK gitlink.
The patch must ultimately be integrated into a reviewed upstream/forked SDK
commit and the gitlink updated, or an equivalent reproducible SDK patch
workflow must be validated in CI. Root+SDK patch files alone do **not** make
the public repo build the candidate. The experimental lab also includes
local frozen-firmware sources/configurations not represented by this patch.

**Known blockers:** separate memory/USB hardware validation on safe spare
hardware; reviewer flagged multi-interface keyboard OTP buffer pointer
lifetime risk, unclosed for non-FIDO-only modes. Unpublished draft; no
physical flash/reset, credential/attestation mutation, MDS, or certification
claim.

### Additional keyboard-HID OTP callback hardening (isolated test)
The original keyboard GET_REPORT callback redirected the global APDU response
pointer to an 8-byte temporary report and did not restore its length/pointer;
the status reply also left the first byte uninitialized. The exact source
function harness reproduced 5 failures before the patch and passed after
restoring APDU state, clearing 8 output bytes and returning only 8 bytes.
This **does not** validate full OTP firmware behavior or close hardware gates.

### Off-device firmware build from pinned source

The standalone `scripts/build-hid-v53-offdevice.sh` creates **disposable**
Git clones of the current branch and pinned SDK, applies the existing KL USB
identity/FIDO-only overlay plus the two v5.3 patches, then builds RP2040 UF2
with packed basic attestation **disabled**. It neither contacts a USB device
nor reads device-specific private keys. The main checkout is never modified.

For an off-device ARM build on Linux/WSL with a locally installed Pico SDK
and ARM GNU toolchain:

```bash
export PICO_SDK_PATH=/path/to/pico-sdk
export PICO_TOOLCHAIN_PATH=/path/to/arm-toolchain/bin
# Optional for disconnected workstations (must be trusted pinned sources):
# export KL_PINNED_SDK_SOURCE=/path/to/pinned-sdk-git-checkout
# export KL_SDK_THIRD_PARTY_CACHE=/path/to/third-party
# export KL_OFFLINE_PICOTOOL_SOURCE=/path/to/picotool-git-clone
export KL_V53_OUT_FILE=/path/outside/repository/v53-offdevice.uf2
bash scripts/build-hid-v53-offdevice.sh
```

The script normalizes temporary build directory names in compiler-generated
`__FILE__` strings and pins `SOURCE_DATE_EPOCH` to the reviewed Git commit.
It refuses to overwrite an existing UF2 and refuses output inside the Git
checkout. Any generated UF2 is **only** an off-device experimental artifact:
not a provisioned authenticator, certification, device interoperability
result, or production release. Toolchain, Pico SDK and cached dependencies
must be pinned separately before claiming cross-machine reproducibility.

The GitHub host CI checks script syntax only; the complete ARM firmware
build is verified in a separate Linux/WSL lab environment, not in that CI job.


### Local byte-for-byte reproducibility validation (source snapshot)

Two clean, separate, disposable RP2040 builds from the same WIP source snapshot
(before this documentation/build-tool commit) produced **byte-identical**
UF2 images, SHA-256:

`c6723cae9e54eb690235cb5cd3a9e639c0bc93c7e38e1e55296a03c8b6b3e8ed`

An earlier pair of builds with randomized temporary directory paths embedded
in diagnostics differed in 88 bytes. Normalizing `__FILE__` paths via
`-ffile-prefix-map` while preserving the RP2040 architecture/ABI flags,
and pinning `SOURCE_DATE_EPOCH` to the source commit fixed this issue.

**The hash identifies that specific source commit and toolchain environment.**
Future WIP commits may change the source-derived `PICO_BUILD_NUMBER`, so their
UF2 hashes must be recomputed; do not treat the value above as the universal
hash for v5.3. This verification is limited to the local pinned WSL/GCC/Pico
SDK build setup, not cross-machine reproducibility or live hardware.

### Strict local dependency provenance gate (off-device, no downloads)

For reproducible local ARM builds, set `KL_V53_STRICT_PINS=1`. This mode
requires a locally cached third-party source tree and picotool Git checkout.
Before applying firmware patches, the builder runs
`scripts/check-v53-build-inputs.py` read-only against clean source clones.

Current exact pins are Pico SDK `079c6f39023649b154152db30f1d781e884879bc`,
SDK submodule `50699e53e8ada214c27f6c9b66ea3b6f127fc655`,
Pico TinyUSB `86ad6e56c1700e85f1c5678607a762cfe3aa2f47`,
Mbed TLS `068ff080b369adfac81509f9b57b2afabaf82dc5`,
TinyCBOR `c0aad2fb2137a31b9845fbaae3653540c410f215`,
picotool 2.3.0 tag commit `6f6458d792b93685a11423b244a585eaa99eafcf`,
and xPack GNU Arm GCC 15.2.1 (20251203).

Example with locally prepared trusted checkouts:

```bash
export KL_V53_STRICT_PINS=1
export KL_SDK_THIRD_PARTY_CACHE=/path/to/pinned/third-party
export KL_OFFLINE_PICOTOOL_SOURCE=/path/to/pinned/picotool-git
bash scripts/build-hid-v53-offdevice.sh
```

This gate checks local Git commits, relevant working-tree cleanliness,
the exact picotool tag commit and compiler version; it does **not** validate
the full upstream supply chain or authorize publishing binaries, flashing,
resetting or using hardware. It is separate from GitHub Actions: no full
GitHub-hosted ARM build is claimed.


### RP2040 linker RAM budget gate (off-device static check)

The isolated ARM builder runs `scripts/check-v53-memory-layout.py`
**after** linking the ELF and **before** reporting a successful UF2 build.
It checks RP2040 main RAM and scratch-stack linker symbols, and enforces
a **project policy** minimum 128 KiB address gap between `__end__`
and `__HeapLimit`. The threshold is an engineering regression budget,
not a chip or FIDO requirement.

At the audited source commit, linker evidence shows:
- `.data`: 8,008 bytes, `.bss`: 87,128 bytes
- Static end: `0x20017480`; `__HeapLimit=0x20040000`
- Linker gap: **166,784 bytes (162.88 KiB)**; policy PASS
- Core 0 and core 1 linker stack reservations: **2,048 bytes each**
- Production HID real-source host test: one FIDO-only HID interface has
  **9,742 bytes logical initial HID allocations** across four `calloc`
  calls. The requested buffer sizes exclude malloc metadata, USB queues,
  timeout arrays and other runtime allocations.

A higher test threshold of 200 KiB was deliberately rejected, proving
the negative gate triggers. These figures are **not** runtime free-heap
measurement. RP2040 heap fragmentation, core-stack high-water mark,
USB interrupt/core concurrency and allocation failure outside HID remain
untested on actual hardware. The WIP branch remains NOT merge-ready.


### USB timeout storage hardening  off-device

The v5.3 SDK patch now avoids dynamic allocation for the small interface
timeout table. Its bounded, fixed-size storage corresponds to the five
possible current USB slots (HID CTAP, HID keyboard, CCID, WCID, LWIP).
The timeout setter checks the configured interface range, and invalid
status lookups fail closed. A native sanitizer harness compiles the relevant
real SDK functions to check bounds and behavior. An original-source
negative run demonstrated the pre-fix failure, and the patched source
passed. Real RP2040 heap/USB concurrency behavior is still unverified.
