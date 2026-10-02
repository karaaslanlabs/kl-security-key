# Upstream and Derivative Provenance

KL Security Key is an experimental Karaaslan Labs derivative of the open-source `pico-fido` project.

## Upstream projects
- Main upstream: `polhenarejos/pico-fido`
- Base source commit used for this public candidate: `f01fa1e2817a845e44d788f3f633a1f122ce332e`
- SDK upstream: `polhenarejos/pico-keys-sdk`
- Pinned SDK commit: `50699e53e8ada214c27f6c9b66ea3b6f127fc655`
- License: GNU Affero General Public License v3.0 (AGPL-3.0)

## Karaaslan Labs changes
This derivative adds or changes, among other things:
- KL Security Key AAGUID and manufacturer/product identity;
- runtime FIDO-HID-only profile support;
- physical user-presence enforcement for the validated KL profile;
- corrected GetInfo version/transport declarations for that profile;
- explicit opt-in use of a provisioned device key/certificate for ordinary packed attestation;
- KL attestation CSR identity and supporting documentation/evidence.

SDK changes are applied by `scripts/apply-sdk-overlay.py`, which is pinned to the exact upstream SDK commit and refuses mixed or unknown source states.

Karaaslan Labs does not claim authorship of upstream Pico FIDO / Pico Keys SDK code. Original upstream copyright and license notices are intentionally preserved.