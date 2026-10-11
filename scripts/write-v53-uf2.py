#!/usr/bin/env python3
"""Strict, no-clobber handoff of an off-device UF2 to an existing output directory.

No USB/device interaction, no flash, no attestation or private key access.
"""
import argparse
import hashlib
import os
from pathlib import Path
import struct
import sys

MAGIC0, MAGIC1, END_MAGIC = 0x0A324655, 0x9E5D5157, 0x0AB16F30


def stop(message):
    raise ValueError("UF2_OUTPUT_STOP: " + message)


def safe_target(repo: Path, raw: str) -> Path:
    repo = repo.resolve(strict=True)
    dest = Path(raw).expanduser()
    if not dest.is_absolute() or dest.suffix.lower() != ".uf2":
        stop("expected an absolute output .uf2 filename")
    if not dest.parent.is_dir():
        stop("output parent must already exist")
    parent = dest.parent.resolve(strict=True)
    if os.path.commonpath((str(repo), str(parent))) == str(repo):
        stop("output is inside the firmware source repository")
    target = parent / dest.name
    if os.path.lexists(str(dest)) or os.path.lexists(str(target)):
        stop("output file already exists (including symlink)")
    return target


def verify_uf2(source: Path) -> str:
    if not source.is_file():
        stop("source UF2 does not exist")
    size = source.stat().st_size
    if size == 0 or size % 512:
        stop("source UF2 is not block-aligned")
    count = size // 512
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for i in range(count):
            block = stream.read(512)
            header = struct.unpack_from("<8I", block, 0)
            footer, = struct.unpack_from("<I", block, 508)
            if (header[0] != MAGIC0 or header[1] != MAGIC1
                    or footer != END_MAGIC or header[5] != i
                    or header[6] != count or header[4] > 476):
                stop("invalid source UF2 framing or block sequence")
            digest.update(block)
    return digest.hexdigest()


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    target = safe_target(args.repo, args.out)
    if args.check_only:
        print("UF2_OUTPUT_TARGET_PASS", target)
        return
    if args.source is None:
        stop("--source is required when writing")
    expected = verify_uf2(args.source)
    # Exclusive-create is atomic; existing files and final-path symlinks fail.
    fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as target_stream, args.source.open("rb") as source_stream:
        while chunk := source_stream.read(64 * 1024):
            target_stream.write(chunk)
        target_stream.flush()
        os.fsync(target_stream.fileno())
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual != expected:
        stop("written UF2 digest mismatch; preserve candidate for investigation")
    print("OFFDEVICE_UF2_CREATED", target, "SHA256", actual)


if __name__ == "__main__":
    try:
        run()
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
