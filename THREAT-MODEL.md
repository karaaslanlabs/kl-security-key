# Threat Model — KL Security Key Experimental RP2040 Profile

## Scope
This document describes the validated KL Security Key experimental profile on an RP2040 Zero-style board. It is not a certification statement.

## Security boundary
The authenticator enforces physical user presence for the validated registration and assertion flow and supports PIN-based user verification. The tested profile exposes FIDO HID at runtime.

## Important hardware limitation
RP2040 does not provide a secure element or equivalent hardware-backed private-key boundary for this project. A determined attacker with physical possession and appropriate equipment may be able to extract flash-resident secrets. This prototype must not be described as equivalent to commercial high-assurance security tokens with dedicated secure hardware.

## Attestation boundary
The validated device uses a device-specific attestation private key and a Karaaslan Labs attestation certificate chaining to the KL Security Key Root CA. The private device key is not part of this repository. The Root CA private key is also excluded and must remain private.

The public Root CA certificate is trust metadata, not a Web PKI/TLS trust anchor. Because the validated reference uses a device-specific attestation certificate, exposing that certificate to multiple relying parties can create a correlation/privacy risk. The current attestation chain is engineering evidence, not a claim of a production-scale privacy-preserving batch attestation design.

## Identity boundary
The KL AAGUID is project-controlled. Current engineering builds have used upstream/project USB VID/PID values that are not owned by Karaaslan Labs. Distribution must not imply ownership of those identifiers.

## Trust / relying-party boundary
Successful CTAP/WebAuthn registration and authentication do not guarantee that a relying party will classify or allow this authenticator. Metadata publication also does not equal certification or universal trust.

## Non-goals
- resistance to invasive physical extraction comparable to secure-element products;
- FIDO certification claims;
- bypassing relying-party allowlists or vendor trust policy;
- emulating another manufacturer's identity, certificates, AAGUID or USB identity.
