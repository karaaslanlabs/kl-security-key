# Attestation and PKI

## Model identity

KL Security Key uses AAGUID:
`d9359dc7-6938-5822-b951-006507247d8f`

The validated physical reference produced WebAuthn `fmt=packed` attestation using ES256 (`alg=-7`) with an `x5c` certificate entry.

The AAGUID observed in authenticator data matched the AAGUID extension in the attestation leaf certificate.

## Trust chain

The lab PKI uses a Karaaslan Labs KL Security Key Root CA and a device-specific attestation leaf certificate.

Published trust material:
- `certs/KL-Security-Key-Root-CA-v1.cert.pem`
- SHA-256: `29591f774b9fe727afb3afa4bbf2b27c3076c62958e4a3eef226a073444d830e`

The Root CA **private key is not part of this repository**.
The device attestation private key is also not published and was never exported from the device workflow used for the validated reference.

The public Root CA certificate is authenticator trust metadata; it is not a publicly trusted TLS/Web PKI CA.

## Provisioning model

The reference device generated/retained its own device key material and was provisioned with the corresponding KL attestation leaf certificate. Certificate persistence was verified before the packed-attestation registration test.

The public build option `KL_PACKED_BASIC_ATTESTATION` tells the authenticator to use provisioned device attestation material for ordinary packed attestation. It does **not** create or ship private key material.

A fresh board therefore needs a separate, security-reviewed provisioning process before this profile can produce the same KL Root CA-chained `x5c` behavior. The original lab device's certificate must not be copied as a universal identity for other devices.

## What was cryptographically verified

On the physical reference:
- packed attestation signature verified with the leaf public key;
- leaf certificate signature verified under the KL Root CA;
- authData AAGUID matched the KL model AAGUID;
- certificate AAGUID extension matched the same model AAGUID.

These checks establish internal consistency of the tested attestation path. They do not establish FIDO certification or relying-party acceptance.

## Metadata / attestation semantics

Karaaslan Labs has prepared MDS-readiness material, but no metadata statement is published in this repository yet.

FIDO defines `basic_full` around an attestation private key shared by a class/model of authenticators. The frozen KL reference instead uses a device-specific attestation key and device-specific leaf, so this repository does not describe that frozen profile as `basic_full` for MDS purposes. A truthful MDS profile must be selected and physically validated separately before submission.

A device-specific attestation certificate can also act as a cross-relying-party correlation handle. The current `x5c` design is therefore retained as engineering evidence, not presented as the final privacy model for broad distribution.
