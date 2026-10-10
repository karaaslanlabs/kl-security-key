# KL Security Key  HID v5.3 off-device engineering package

**Status:** WIP / host tests passed / hardware HOLD / no certification claim.

- Public main baseline: `71c419cc402241bbbe3e892195d051a6d6f89956`.
- SDK submodule baseline: `50699e53e8ada214c27f6c9b66ea3b6f127fc655`.
- Frozen v5.2 reference UF2 SHA256:
  `8b50a9fc27094e682e0436c494a6320a97c47fdcb05bbefffe98729f18abe0d8`.
- **Experimental** v5.3 UF2 SHA256 (off-device, never flashed):
  `2f526a52f345e04d24e84772315d3bb3fa534748a614d081a2f4254277a7932b`.

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
