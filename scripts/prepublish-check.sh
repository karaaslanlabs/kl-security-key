#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK="$ROOT/pico-keys-sdk"
EXPECTED_SDK="50699e53e8ada214c27f6c9b66ea3b6f127fc655"
EXPECTED_ROOT_SHA="29591f774b9fe727afb3afa4bbf2b27c3076c62958e4a3eef226a073444d830e"

fail() { echo "PREPUBLISH FAIL: $*" >&2; exit 1; }

cd "$ROOT"
git diff --check

actual_sdk="$(git -C "$SDK" rev-parse HEAD)"
[[ "$actual_sdk" == "$EXPECTED_SDK" ]] || fail "SDK commit drift: $actual_sdk"
[[ -z "$(git -C "$SDK" status --porcelain)" ]] || fail "SDK submodule is dirty"
[[ ! -e "$SDK/third-party" ]] || fail "SDK dependency cache must be absent from publish candidate"
python3 "$ROOT/scripts/apply-sdk-overlay.py" --check

actual_root_sha="$(sha256sum certs/KL-Security-Key-Root-CA-v1.cert.pem | awk '{print $1}')"
[[ "$actual_root_sha" == "$EXPECTED_ROOT_SHA" ]] || fail "public Root CA hash mismatch"
[[ ! -x certs/KL-Security-Key-Root-CA-v1.cert.pem ]] || fail "public Root CA certificate must not be executable"

python3 -m py_compile tools/verify_packed_attestation.py
scan_args=(--exclude=.git --exclude=prepublish-check.sh --exclude-dir='build*' --exclude-dir='__pycache__')

if grep -RIlE -- '-----BEGIN ([A-Z0-9 ]+ )?PRIVATE KEY-----' "${scan_args[@]}" . >/dev/null 2>&1; then
  fail "private-key PEM block found in publish candidate"
fi
if grep -RIlE 'C:\\Users\\|/home/karaaslan|Ömer' "${scan_args[@]}" . >/dev/null 2>&1; then
  fail "local host/user path leaked into publish candidate"
fi
if grep -RIlE '89fb94b7-06c9-3673-9b7e-30526d968145|FIDO_2_2' "${scan_args[@]}" . >/dev/null 2>&1; then
  fail "stale upstream identity/GetInfo marker found"
fi
if grep -RIlE 'gh[opsu]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}' "${scan_args[@]}" . >/dev/null 2>&1; then
  fail "credential-like token material found in publish candidate"
fi

for forbidden in \
  .github/FUNDING.yml \
  .github/workflows/codeql.yml \
  .github/workflows/nightly.yml \
  .github/workflows/test.yml \
  ENTERPRISE.md \
  metadata/pico-fido.metadata.json \
  metadata/pico-fido.test.metadata.json \
  tests/fido-alliance-conformance-results.md; do
  [[ ! -e "$forbidden" ]] || fail "misleading/inherited artifact still present: $forbidden"
done

[[ -f .github/workflows/publication-hygiene.yml ]] || fail "publication hygiene workflow missing"
if grep -RIl '\${{ secrets\.' .github/workflows >/dev/null 2>&1; then
  fail "workflow secret reference found in source-first publication CI"
fi
if grep -RIl 'contents: write' .github/workflows >/dev/null 2>&1; then
  fail "workflow has write content permission"
fi
workflow_count="$(find .github/workflows -maxdepth 1 -type f | wc -l | tr -d ' ')"
[[ "$workflow_count" == "1" ]] || fail "unexpected workflow count: $workflow_count"

[[ -z "$(git ls-files '*.uf2' '*.bin' '*.elf' '*.der' '*.p12' '*.pfx' '*.key')" ]] || fail "generated firmware/key container is tracked"
grep -q 'Not FIDO Alliance certified' README.md || fail "README certification disclaimer missing"
grep -q '^## Engineering inquiries$' README.md || fail "README engineering-inquiries heading missing/malformed"
grep -q 'not allocated to Karaaslan Labs' NOTICE.md || fail "USB identity disclaimer missing"

echo "PREPUBLISH CHECK: PASS"
