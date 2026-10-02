# Architecture

## Project boundary

KL Security Key is a Karaaslan Labs experimental profile layered on the upstream `pico-fido` codebase. The repository deliberately separates upstream provenance from KL-specific behavior.

The validated hardware reference is an RP2040 Zero-style board with 2 MB flash and no secure element.

## Source layers

1. **Upstream `pico-fido` source** — pinned base commit documented in `UPSTREAM.md`.
2. **Upstream `pico-keys-sdk` submodule** — pinned to an exact clean commit.
3. **KL root-source changes** — AAGUID, user-presence policy, GetInfo cleanup, version and attestation policy.
4. **KL SDK overlay** — `scripts/apply-sdk-overlay.py`, applied only to the expected SDK commit.
5. **KL documentation/evidence** — threat model, PKI explanation, debugging methodology and public certificate.

The SDK overlay is fail-closed: `scripts/apply-sdk-overlay.py` reconstructs the expected modified SDK files from the pinned upstream commit and refuses mixed, unknown or drifted states.

## Validated reference profile

The reference build enables:
- `FORCE_BUTTON_WAIT=ON`;
- `KL_FIDO_ONLY_RUNTIME=ON`;
- `KL_PACKED_BASIC_ATTESTATION=ON`.

At runtime, the validated profile exposes the FIDO HID path while the source can still compile upstream components. GetInfo transport advertising follows the selected runtime profile rather than being hard-coded independently.
## Identity

KL model AAGUID:
`d9359dc7-6938-5822-b951-006507247d8f`

Manufacturer/product strings for the KL profile are `Karaaslan Labs` / `KL Security Key`.

The engineering build has used USB VID/PID `0x2E8A:0x10FE`, which belongs to the upstream/project allocation context and is **not** Karaaslan Labs-owned USB identity. This is one reason binary distribution is not the initial public-release target.

## User presence and verification

The validated board uses its physical BOOT/BOOTSEL button as user presence. The KL change ensures the `FORCE_BUTTON_WAIT` policy also applies to GetAssertion, so the validated register/authenticate flow requires physical interaction.

PIN/user-verification behavior remains provided by the underlying authenticator stack; this repository does not record a device PIN.

## Frozen hardware reference vs. public candidate

The physically tested v5.2 firmware is preserved outside the curated repository as an immutable engineering checkpoint.

The public-source candidate is a cleaned, reviewable reconstruction of the intended behavior. It has been compile-tested, but its generated binary is not described as byte-for-byte identical to the frozen physical reference unless the hashes actually match.

That distinction is intentional: source hygiene and reproducibility must not rewrite history about which exact binary was physically tested.