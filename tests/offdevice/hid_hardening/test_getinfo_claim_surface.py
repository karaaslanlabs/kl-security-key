"""CTAP 2.3 Proposed Standard claim-surface checks (source-only; NOT conformance).

Checks only what the pinned KL GetInfo C source advertises. A green test is
NOT evidence that those capabilities work, nor an authorization to claim
FIDO certification, real-device interoperability or security assurance.
"""
import os
from pathlib import Path
import re
import unittest

ROOT = Path(os.environ["KL_GETINFO_SOURCE_ROOT"]).resolve() if "KL_GETINFO_SOURCE_ROOT" in os.environ else Path(__file__).resolve().parents[3]
GETINFO = ROOT / "src/fido/cbor_get_info.c"
INFO = GETINFO.read_text(encoding="utf-8")


def section(first, second):
    start = INFO.index('CBOR_CHECK(cbor_encode_uint(&mapEncoder, ' + first + '));')
    end = INFO.index('CBOR_CHECK(cbor_encode_uint(&mapEncoder, ' + second + '));', start + 1)
    return INFO[start:end]


class GetInfoAdvertisedClaims(unittest.TestCase):
    def test_versions_are_declared_not_proven(self):
        versions = section("0x01", "0x02")
        for label in ("FIDO_2_0", "FIDO_2_1", "FIDO_2_3"):
            self.assertEqual(versions.count('"' + label + '"'), 1)
        self.assertNotIn('"FIDO_2_2"', versions)

    def test_u2f_advertisement_has_alwaysuv_gate(self):
        versions = section("0x01", "0x02")
        self.assertRegex(versions, r"if\s*\(!alwaysUv\)\s*\{\s*CBOR_CHECK\(cbor_encode_text_stringz\(&arrayEncoder,\s*\"U2F_V2\"\)\)")
        self.assertRegex(versions, r"3\s*\+\s*!alwaysUv")

    def test_ctap23_required_extensions_are_declared(self):
        extensions = section("0x02", "0x03")
        for label in ("hmac-secret", "credProtect"):
            self.assertIn('"' + label + '"', extensions)

    def test_rk_credential_management_and_pinuv_auth_are_declared(self):
        opts = section("0x04", "0x05")
        for label in ("rk", "credMgmt", "pinUvAuthToken"):
            self.assertIn('"' + label + '"', opts)
        self.assertRegex(opts, r'"credMgmt"\)\);\s*CBOR_CHECK\(cbor_encode_boolean\(&arrayEncoder,\s*true\)')
        self.assertRegex(opts, r'"pinUvAuthToken"\)\);\s*CBOR_CHECK\(cbor_encode_boolean\(&arrayEncoder,\s*true\)')

    def test_client_pin_is_state_dependent(self):
        opts = section("0x04", "0x05")
        self.assertRegex(opts, r'"clientPin"\)\);\s*CBOR_CHECK\(cbor_encode_boolean\(&arrayEncoder,\s*file_has_data\(ef_pin\)\)')
        self.assertNotIn('cbor_encode_text_stringz(&arrayEncoder, "uv")', opts)

    def test_pin_protocol_2_advertised(self):
        protocols = section("0x06", "0x07")
        self.assertIn("cbor_encoder_create_array(&mapEncoder, &arrayEncoder, 2)", protocols)
        self.assertRegex(protocols, r'cbor_encode_uint\(&arrayEncoder,\s*2\)')

    def test_fido_only_runtime_declares_only_usb(self):
        transports = section("0x09", "0x0A")
        self.assertIn("#ifdef KL_FIDO_ONLY_RUNTIME", transports)
        fido_only = transports.split("#ifdef KL_FIDO_ONLY_RUNTIME", 1)[1].split("#else", 1)[0]
        self.assertIn('"usb"', fido_only)
        self.assertNotIn('"smart-card"', fido_only)
        self.assertIn("cbor_encoder_create_array(&mapEncoder, &arrayEncoder, 1)", fido_only)

    def test_no_false_certification_metadata_claim(self):
        self.assertNotIn('cbor_encode_text_stringz(&arrayEncoder, "certifications")', INFO)
        self.assertNotIn('cbor_encode_text_stringz(&mapEncoder, "certifications")', INFO)


if __name__ == "__main__":
    unittest.main(verbosity=2)
