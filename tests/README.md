# Tests

This directory is inherited primarily from upstream `pico-fido` and contains protocol/integration test tooling.

## Important provenance boundary

The presence of upstream test code does **not** mean the KL Security Key profile has independently passed every upstream or FIDO Alliance conformance test.

Karaaslan Labs currently publishes only evidence that was actually validated on the KL engineering reference, including:
- physical WebAuthn registration;
- physical authentication/GetAssertion;
- Windows CTAP2 provider path;
- packed-attestation signature verification;
- KL attestation certificate-chain verification;
- AAGUID agreement across authenticator data and certificate extension.

A prior upstream conformance-results document was intentionally removed from this derivative candidate because it described an upstream test run and could be misread as KL Security Key certification/conformance evidence.

FIDO Alliance certification is a separate process and is not claimed by this project.