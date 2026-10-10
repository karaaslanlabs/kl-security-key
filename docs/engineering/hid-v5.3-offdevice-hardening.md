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
