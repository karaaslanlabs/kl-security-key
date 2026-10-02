# Interoperability Case Study — Protocol Success vs. Relying-Party Trust

Date of engineering experiment: 2026-10-01

## Question

Can a custom authenticator be technically valid at the CTAP/WebAuthn layer while still failing a relying party's higher-level hardware-key qualification policy?

The KL Security Key experiment produced exactly that separation.

## Physical authenticator evidence

The tested device:
- enumerated cleanly on Windows;
- completed a physical WebAuthn MakeCredential operation;
- used `MicrosoftCtapHidProvider`;
- followed the CTAP2 path (`U2fProtocol=false`);
- returned KL AAGUID `d9359dc7-6938-5822-b951-006507247d8f`;
- returned packed ES256 attestation with a KL `x5c` leaf;
- passed attestation-signature and KL Root CA chain verification;
- successfully authenticated with the created credential in a normal WebAuthn test flow.

That establishes a working protocol/cryptographic path for the tested flow.
## OpenAI account-security enrollment experiment

In a dated OpenAI Advanced Account Security enrollment test, the physical KL credential could be registered at the WebAuthn level. Windows evidence showed a successful physical MakeCredential operation with the KL AAGUID and packed attestation.

However, the OpenAI UI classified the resulting credential as a generic passkey rather than satisfying the specific supported-hardware-security-key qualification gate. Retrying did not change that outcome.

This repository does **not** infer OpenAI's internal recognition rules from that result. The experiment does not establish OpenAI compatibility, endorsement, partnership, or support for KL Security Key.

No attempt was made to impersonate another security-key vendor, reuse another vendor's AAGUID/certificates, or bypass the relying party's trust policy.

## Microsoft Entra tenant-local AAGUID interoperability

On 2026-10-02, a dedicated Microsoft Entra tenant was configured with a device-bound passkey profile that allowed only the KL Security Key AAGUID for a narrowly targeted user group. Attestation enforcement was deliberately left off for this tenant-local interoperability proof.

The physical KL Security Key then:
- registered successfully as a device-bound passkey/security key;
- appeared in Entra authentication-method details with AAGUID `d9359dc7-6938-5822-b951-006507247d8f`;
- completed a fresh Microsoft Entra sign-in using the physical key, PIN/user verification and physical user presence.

Entra reported the method as not attested, which is consistent with the deliberate `Enforce attestation = OFF` policy. This result demonstrates tenant-local AAGUID-targeted interoperability. It does **not** establish Microsoft certification, global vendor recognition, trusted-attestation status or manufacturer authenticity outside that tenant policy.

## Engineering conclusion

The useful result was diagnostic separation:

**protocol + cryptography PASS ≠ relying-party trust/qualification PASS**

A relying party can apply metadata, certification, attestation-root, device-policy, allowlist or other trust requirements beyond basic WebAuthn protocol success. Which mechanisms a particular service uses must be established from evidence rather than guessed.

This distinction is central to KL Security Key's interoperability/debugging methodology.