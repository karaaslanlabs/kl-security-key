# Security Policy

## Scope

Security issues in KL-specific changes, build scripts, attestation handling, user-presence behavior, USB-profile changes, or integration behavior are in scope for Karaaslan Labs.

Issues that reproduce unchanged in upstream `pico-fido` / `pico-keys-sdk` should also be reported to the relevant upstream project.

## Reporting

Please do **not** open a public issue for an unpatched vulnerability.

Contact Karaaslan Labs at `contact@karaaslanlabs.com` with:
- affected commit/profile;
- hardware/board details;
- attack prerequisites;
- security impact;
- minimal reproduction steps;
- sanitized logs or traces if useful.

Never send private attestation keys, root private keys, PINs, credentials, account tokens, credential databases, or raw device images containing secrets.

## Response boundary

This experimental project has no guaranteed security-response SLA. Reports will be triaged according to impact and reproducibility.