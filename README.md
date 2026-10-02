# KL Security Key

**An open FIDO2/WebAuthn authenticator engineering and interoperability project by Karaaslan Labs.**

KL Security Key is an experimental RP2040-based authenticator profile built as a derivative of [`polhenarejos/pico-fido`](https://github.com/polhenarejos/pico-fido). The project documents the engineering path from a generic development board to a distinct authenticator identity with physical user presence, WebAuthn registration/authentication, and manufacturer-rooted packed attestation.

> **Status:** experimental engineering/research project. Not FIDO Alliance certified. Not a commercial high-assurance security token.

## Why this repository exists

The useful part of this project is not simply “RP2040 can run FIDO2.” The focus is the integration work around authenticator identity, attestation, Windows/WebAuthn behavior, reproducible source changes, and explicit trust boundaries.

The validated engineering reference includes:
- KL Security Key AAGUID: `d9359dc7-6938-5822-b951-006507247d8f`;
- external USB FIDO2/CTAP authenticator behavior;
- physical user-presence enforcement for registration and assertion;
- PIN/user-verification support through the underlying authenticator stack;
- WebAuthn registration and authentication validated on Windows;
- packed ES256 attestation with `x5c` using a provisioned device-specific key/certificate;
- a Karaaslan Labs attestation root and public trust certificate;
- standards cleanup for the validated runtime profile.
## What is verified vs. what is not

Verified on the physical engineering reference:
- fresh WebAuthn registration: PASS;
- authentication/GetAssertion with the same credential: PASS;
- Windows provider: `MicrosoftCtapHidProvider`;
- CTAP2 path (`U2fProtocol=false`);
- packed attestation signature: PASS;
- attestation leaf → KL Security Key Root CA verification: PASS;
- AAGUID agreement between authenticator data and certificate extension: PASS.

Not claimed:
- FIDO Alliance certification;
- secure-element-level physical key protection;
- universal relying-party trust or allowlisting;
- YubiKey/Nitrokey or other vendor equivalence;
- Karaaslan Labs ownership of the upstream/project USB VID/PID;
- compatibility with any service merely because protocol registration succeeds.

See [`THREAT-MODEL.md`](THREAT-MODEL.md) before using this work outside a lab or research context.
## Source and build model

The repository keeps the upstream `pico-keys-sdk` submodule pinned to a known commit. KL-specific SDK changes are applied by a deterministic, exact-commit-pinned overlay script instead of pretending the modified SDK is original Karaaslan Labs code.

Reference build flow:

```bash
git submodule update --init
export PICO_SDK_PATH=/path/to/pico-sdk
export PICO_TOOLCHAIN_PATH=/path/to/arm-none-eabi-toolchain
./scripts/build-kl-reference.sh
```

`build-kl-reference.sh` enables the validated KL engineering profile:
- `FORCE_BUTTON_WAIT=ON`
- `KL_FIDO_ONLY_RUNTIME=ON`
- `KL_PACKED_BASIC_ATTESTATION=ON`

The packed-attestation option expects valid device attestation key/certificate material to have been provisioned separately. This repository does **not** publish private attestation keys and does not auto-provision the certificate of the original lab device.

Binary distribution is intentionally not the initial publication target while USB identity/distribution requirements remain unresolved. Source, documentation and validation methodology are the primary artifacts.
## Documentation

- [`docs/architecture.md`](docs/architecture.md) — profile boundaries and source layout.
- [`docs/attestation-and-pki.md`](docs/attestation-and-pki.md) — AAGUID, packed attestation and PKI model.
- [`docs/windows-webauthn-debugging.md`](docs/windows-webauthn-debugging.md) — evidence-led Windows debugging workflow.
- [`docs/interoperability-case-study.md`](docs/interoperability-case-study.md) — what the real relying-party experiment demonstrated and what it did not.
- [`docs/validation-evidence.md`](docs/validation-evidence.md) — frozen physical evidence vs. curated source-build evidence.
- [`UPSTREAM.md`](UPSTREAM.md) — exact upstream provenance and derivative changes.
- [`THREAT-MODEL.md`](THREAT-MODEL.md) — security boundaries and non-claims.

## License and upstream credit

KL Security Key is derived from `polhenarejos/pico-fido` and uses `polhenarejos/pico-keys-sdk`. The source remains under the GNU Affero General Public License v3.0; see [`LICENSE`](LICENSE) and [`UPSTREAM.md`](UPSTREAM.md).

Karaaslan Labs does not claim authorship of upstream Pico FIDO/Pico Keys SDK code. Original notices are preserved and KL-specific modifications are documented separately.

## Project status

This repository is prepared as a technical proof and open engineering project, not as a consumer hardware launch. Firmware used on the physical validated reference is frozen separately from the curated public-source candidate; public-source builds are validated independently and must not be described as binary-identical unless their hashes actually match.

Karaaslan Labs: <https://karaaslanlabs.com>## Engineering inquiries

For bounded WebAuthn/passkey debugging or FIDO2 authenticator/attestation engineering inquiries, contact `contact@karaaslanlabs.com`.

The repository is the technical proof surface; commercial work is scoped separately and does not imply certification, product support, or relying-party acceptance guarantees.
