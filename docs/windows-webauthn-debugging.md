# Windows WebAuthn Debugging

This project was debugged by separating browser UI symptoms from the Windows CTAP/WebAuthn provider path and the authenticator's raw protocol behavior.

## Useful Windows evidence

For the validated physical flow, Windows reported:
- provider: `MicrosoftCtapHidProvider`;
- CTAP2/FIDO2 path;
- `U2fProtocol=false`;
- successful physical MakeCredential/GetAssertion operations.

A useful event channel during investigation was:
`Microsoft-Windows-WebAuthN/Operational`

Do not publish raw event logs without review. They may contain relying-party names, account identifiers, credential-related values, timestamps or other user-specific context.

## Debugging order

When a hardware-key flow fails, separate the layers:
1. USB enumeration — does Windows see a healthy device/interface?
2. CTAP GetInfo — what versions, transports and options does the authenticator actually advertise?
3. MakeCredential/GetAssertion — does the physical CTAP operation complete?
4. WebAuthn processing — what attestation/provider path does Windows report?
5. Relying-party policy — does the service accept/classify the authenticator as intended?
## Failure modes encountered during development

Two project-specific lessons were particularly useful:

- Removing USB interfaces too aggressively at compile time produced Windows enumeration failures. The working KL profile keeps the upstream build structure but masks the runtime interfaces to the intended FIDO HID profile.
- Generating X.509 material during boot interfered with normal authenticator initialization and caused CTAP GetInfo processing failures. Provisioning was moved out of ordinary boot/runtime behavior.

These failures are retained as engineering lessons rather than hidden experiments: the safer architecture is to keep provisioning explicit and runtime behavior minimal.

## Evidence discipline

A browser success page is not enough to diagnose trust behavior. For a meaningful interoperability claim, correlate:
- physical device interaction;
- Windows/WebAuthn provider evidence;
- CTAP/attestation contents;
- cryptographic verification;
- the relying party's final classification/decision.

If the first four succeed but the relying party still rejects or classifies the credential differently, treat it as a trust/policy interoperability question—not proof that the CTAP implementation failed.