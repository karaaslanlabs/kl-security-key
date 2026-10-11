"""Negative, device-free tests for exclusive UF2 output containment."""
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "scripts" / "write-v53-uf2.py"
M0, M1, END = 0x0A324655, 0x9E5D5157, 0x0AB16F30


class UF2OutputProtection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="kl-v53-output-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.outdir = self.base / "output"
        self.outdir.mkdir()
        self.source = self.base / "valid.uf2"
        block = bytearray(512)
        struct.pack_into("<8I", block, 0, M0, M1, 0, 0x10000000, 256, 0, 1, 0)
        struct.pack_into("<I", block, 508, END)
        self.source.write_bytes(block)
        self.dest = self.outdir / "candidate.uf2"

    def call(self, target=None, check=False, source=True):
        args = [sys.executable, str(HELPER), "--repo", str(self.repo),
                "--out", str(target if target is not None else self.dest)]
        if source:
            args += ["--source", str(self.source)]
        if check:
            args.append("--check-only")
        return subprocess.run(args, text=True, capture_output=True)

    def test_valid_candidate_exclusive_copy_and_verified_contents(self):
        self.assertEqual(self.call(check=True).returncode, 0)
        self.assertFalse(self.dest.exists())
        copied = self.call()
        self.assertEqual(copied.returncode, 0, copied.stderr)
        self.assertEqual(self.dest.read_bytes(), self.source.read_bytes())
        self.assertIn("OFFDEVICE_UF2_CREATED", copied.stdout)
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.dest.read_bytes(), self.source.read_bytes())

    def test_existing_file_preserved(self):
        self.dest.write_bytes(b"keep original")
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.dest.read_bytes(), b"keep original")

    def test_dangling_final_symlink_is_rejected(self):
        self.dest.symlink_to(self.base / "nonexistent")
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.dest.is_symlink())

    def test_repo_target_rejected(self):
        self.assertNotEqual(self.call(self.repo / "candidate.uf2").returncode, 0)
        self.assertFalse((self.repo / "candidate.uf2").exists())

    def test_symlink_parent_into_repo_rejected(self):
        alias = self.base / "aliased-repo"
        alias.symlink_to(self.repo, target_is_directory=True)
        self.assertNotEqual(self.call(alias / "candidate.uf2").returncode, 0)

    def test_dotdot_into_repo_rejected(self):
        self.assertNotEqual(self.call(self.outdir / ".." / "repo" / "candidate.uf2").returncode, 0)

    def test_relative_or_missing_parent_rejected(self):
        self.assertNotEqual(self.call("candidate.uf2").returncode, 0)
        self.assertNotEqual(self.call(self.base / "missing" / "candidate.uf2").returncode, 0)

    def test_invalid_uf2_cannot_create_file(self):
        self.source.write_bytes(bytes(512))
        failed = self.call()
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("invalid source UF2", failed.stderr)
        self.assertFalse(self.dest.exists())


if __name__ == "__main__":
    unittest.main()
