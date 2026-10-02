# Contributing

KL Security Key is an experimental AGPL-3.0 derivative project. Contributions should stay small, auditable and explicit about security impact.

## Before opening a pull request

For a bug report or change, include:
- affected board/profile and commit;
- expected vs. actual behavior;
- reproduction/validation steps;
- security or compatibility impact;
- sanitized evidence when useful.

Do not include private keys, PINs, credentials, account data, raw secret-bearing flash images, or other sensitive material.

Security vulnerabilities must follow [`SECURITY.md`](SECURITY.md) rather than a public issue.

## Licensing

The repository is licensed under AGPL-3.0. By submitting a contribution, you represent that you have the right to submit it and that your contribution may be distributed under the repository license.

This repository does **not** use the upstream project's proprietary/Enterprise contribution terms as a Karaaslan Labs policy.

## Engineering expectations

- preserve upstream attribution and provenance;
- avoid identity spoofing or vendor/certification claims;
- add tests/evidence for behavior changes;
- keep experimental switches explicit and fail closed on drift;
- document any new trust or secret boundary.