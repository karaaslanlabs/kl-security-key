#!/usr/bin/env python3
"""Verify an ES256 packed WebAuthn attestation against a supplied root CA."""

import argparse
import hashlib
import re
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ObjectIdentifier
from fido2 import cbor

AAGUID_OID = ObjectIdentifier("1.3.6.1.4.1.45724.1.1.4")


def clean_hex(value: str) -> str:
    cleaned = "".join(re.findall(r"[0-9A-Fa-f]", value))
    if len(cleaned) % 2:
        raise ValueError("hex input has an odd number of digits")
    return cleaned


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response-hex-file", required=True, type=Path,
                        help="File containing only the CTAP MakeCredential CBOR response as hex")
    parser.add_argument("--client-data-hash", required=True,
                        help="32-byte clientDataHash as hex")
    parser.add_argument("--root", required=True, type=Path,
                        help="PEM root certificate used to verify the attestation leaf")
    parser.add_argument("--expected-aaguid",
                        help="Optional expected AAGUID (UUID text or 32 hex digits)")
    return parser.parse_args()


def normalize_aaguid(value: str) -> str:
    return clean_hex(value).lower()


def main() -> int:
    args = parse_args()
    response_bytes = bytes.fromhex(clean_hex(args.response_hex_file.read_text()))
    client_data_hash = bytes.fromhex(clean_hex(args.client_data_hash))
    if len(client_data_hash) != 32:
        raise ValueError("clientDataHash must be exactly 32 bytes")

    response = cbor.decode(response_bytes)
    fmt = response[1]
    auth_data = response[2]
    att_stmt = response[3]

    if fmt != "packed":
        raise ValueError(f"expected packed attestation, got {fmt!r}")
    if att_stmt.get("alg") != -7:
        raise ValueError(f"reference verifier supports ES256 alg=-7, got {att_stmt.get('alg')!r}")
    x5c = att_stmt.get("x5c")
    if not x5c:
        raise ValueError("packed attestation does not contain x5c")

    leaf = x509.load_der_x509_certificate(x5c[0])
    root = x509.load_pem_x509_certificate(args.root.read_bytes())
    leaf.public_key().verify(
        att_stmt["sig"], auth_data + client_data_hash, ec.ECDSA(hashes.SHA256())
    )
    root.public_key().verify(
        leaf.signature,
        leaf.tbs_certificate_bytes,
        ec.ECDSA(leaf.signature_hash_algorithm),
    )

    if len(auth_data) < 53:
        raise ValueError("authenticator data is too short to contain an attested AAGUID")
    auth_aaguid = auth_data[37:53].hex()
    ext = leaf.extensions.get_extension_for_oid(AAGUID_OID).value
    ext_bytes = bytes(ext.value)
    if len(ext_bytes) == 18 and ext_bytes[:2] == b"\x04\x10":
        ext_bytes = ext_bytes[2:]
    if len(ext_bytes) != 16:
        raise ValueError(f"unexpected AAGUID extension encoding/length: {ext_bytes.hex()}")
    cert_aaguid = ext_bytes.hex()

    if auth_aaguid != cert_aaguid:
        raise ValueError(f"AAGUID mismatch: authData={auth_aaguid}, cert={cert_aaguid}")
    if args.expected_aaguid and auth_aaguid != normalize_aaguid(args.expected_aaguid):
        raise ValueError(
            f"unexpected AAGUID: expected {normalize_aaguid(args.expected_aaguid)}, got {auth_aaguid}"
        )

    print(f"fmt={fmt}")
    print("alg=-7 (ES256)")
    print(f"aaguid={auth_aaguid}")
    print(f"leaf_sha256={hashlib.sha256(x5c[0]).hexdigest()}")
    print("attestation_signature=PASS")
    print("leaf_to_root_signature=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())