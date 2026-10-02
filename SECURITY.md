# Security Policy

## Supported scope

Security reports are accepted for the current `main` branch and the currently documented KL Security Key engineering reference. Historical commits, local experiments, forks, and unmodified upstream behavior are handled on a best-effort basis.

KL-specific security issues can include:
- authenticator / CTAP / WebAuthn behavior introduced by KL changes;
- attestation and certificate handling;
- user-presence and user-verification behavior;
- USB profile and interface changes;
- build, packaging, provisioning, validation, or integration logic maintained by Karaaslan Labs.

Issues that reproduce unchanged in upstream `pico-fido` / `pico-keys-sdk` should also be reported to the relevant upstream project. We may route an upstream-only report to the appropriate maintainer.

## Reporting a vulnerability

Please **do not open a public GitHub issue, discussion, or pull request for an unpatched vulnerability**.

Report privately to `contact@karaaslanlabs.com` and include, when possible:
- affected commit, component, or profile;
- hardware / board details;
- attack prerequisites and required access;
- expected versus observed behavior;
- security impact;
- minimal reproduction steps or proof of concept;
- sanitized logs, traces, or screenshots if useful.

Do **not** send private attestation keys, root private keys, PINs, account credentials, session tokens, credential databases, recovery material, or raw device images containing secrets.

## Coordinated disclosure

Please allow reasonable time for triage, reproduction, remediation, and publication before public disclosure. Karaaslan Labs will use best-effort communication and may request additional technical detail or a disclosure timeline appropriate to the severity and reproducibility of the issue.

If a report affects upstream code or another vendor, coordinated disclosure may require involving that maintainer or vendor before publication.

## Project security boundaries

KL Security Key is an experimental engineering / interoperability project. It is **not represented as**:
- FIDO Alliance certified hardware;
- secure-element-backed high-assurance hardware;
- universally trusted or allowlisted by relying parties;
- a substitute for an independently evaluated commercial security key.

A security report should be evaluated against the project's documented threat model and stated guarantees, not against guarantees the project does not make.

## Bug bounty and response SLA

There is currently **no monetary bug bounty program and no guaranteed response SLA**. Reports are prioritized by credible impact, exploitability, affected scope, and reproducibility.

Responsible, technically useful reports may be acknowledged publicly with the reporter's permission after remediation or coordinated disclosure.
