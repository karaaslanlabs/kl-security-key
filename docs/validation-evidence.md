# Validation Evidence

This document separates the **physically validated frozen reference** from the **curated public-source candidate**. They are related engineering states, but they are not represented as byte-identical firmware.

## Physical reference — frozen v5.2

Frozen artifact SHA-256:
`8b50a9fc27094e682e0436c494a6320a97c47fdcb05bbefffe98729f18abe0d8`

Validated on the physical KL Security Key reference:
- Windows USB enumeration: PASS;
- WebAuthn registration: PASS;
- WebAuthn authentication/GetAssertion: PASS;
- physical user presence for both flows: PASS;
- Windows provider: `MicrosoftCtapHidProvider`;
- CTAP2 path (`U2fProtocol=false`);
- GetInfo cleanup: `FIDO_2_0`, `FIDO_2_1`, `FIDO_2_3`, USB profile, firmware version `0x0801`;
- packed ES256 attestation with `x5c`: PASS;
- attestation signature verification: PASS;
- leaf → KL Root CA signature verification: PASS;
- KL AAGUID agreement between authData and certificate extension: PASS.
Public verification identifiers:
- AAGUID: `d9359dc7-6938-5822-b951-006507247d8f`;
- attestation leaf SHA-256: `54d00d678a181ba51e4b2568249a374c7a40aa2fc1e02fee6fcbe96b8bb248c1`;
- public Root CA file SHA-256: `29591f774b9fe727afb3afa4bbf2b27c3076c62958e4a3eef226a073444d830e`.

Raw account/browser logs are intentionally not published as evidence because they can contain user-specific or relying-party context.

## Curated public-source candidate

The candidate is built from:
- root base commit: `f01fa1e2817a845e44d788f3f633a1f122ce332e`;
- SDK base commit: `50699e53e8ada214c27f6c9b66ea3b6f127fc655`;
- reviewed KL root-source changes;
- deterministic SDK overlay `scripts/apply-sdk-overlay.py`.

Reference-profile clean build after the attestation hash-policy review:
- build: PASS;
- UF2 SHA-256: `a48546aeb7d32760faf119f2617a0d55e594e3734b8855a7c6b8fca8da21cee5`.

This candidate binary has **not yet been substituted for the frozen physical reference and is not claimed physically revalidated**. Publication can therefore remain source-first while the frozen v5.2 hardware result stays the authoritative runtime evidence.