#!/usr/bin/env bash
# KL Security Key v5.3: isolated build/reproducibility check; NEVER flashes hardware.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK="${KL_PINNED_SDK_SOURCE:-$ROOT/pico-keys-sdk}"
EXPECTED_SDK=50699e53e8ada214c27f6c9b66ea3b6f127fc655
: "${PICO_SDK_PATH:?Set PICO_SDK_PATH to a locally installed, pinned Raspberry Pi Pico SDK}"
: "${PICO_TOOLCHAIN_PATH:?Set PICO_TOOLCHAIN_PATH to the ARM GCC toolchain bin path}"
command -v cmake >/dev/null
command -v git >/dev/null
command -v ninja >/dev/null
command -v python3 >/dev/null
test -x "$PICO_TOOLCHAIN_PATH/arm-none-eabi-gcc" || {
  echo "Expected toolchain binary at PICO_TOOLCHAIN_PATH/arm-none-eabi-gcc" >&2
  exit 2
}
test "$(git -C "$SDK" rev-parse HEAD)" = "$EXPECTED_SDK" || {
  echo "Refusing build: wrong SDK submodule commit" >&2
  exit 3
}
test -f "$ROOT/patches/hid-v5.3-product-guards.patch"
test -f "$ROOT/patches/hid-v5.3-sdk-hardening.patch"

WORK="$(mktemp -d -t kl-hid-v53-arm-XXXXXXXX)"
cleanup() { if [[ "${KL_V53_KEEP_BUILD:-0}" != 1 ]]; then rm -rf "$WORK"; fi; }
trap cleanup EXIT

# Clone the exact WIP commit and pinned SDK commit, never alter original checkout.
git clone -q --no-hardlinks "$ROOT" "$WORK/repo"
git clone -q --no-hardlinks "$SDK" "$WORK/repo/pico-keys-sdk"
test "$(git -C "$WORK/repo" rev-parse HEAD)" = "$(git -C "$ROOT" rev-parse HEAD)"
test "$(git -C "$WORK/repo/pico-keys-sdk" rev-parse HEAD)" = "$EXPECTED_SDK"
test -z "$(git -C "$WORK/repo/pico-keys-sdk" status --porcelain)"

if [[ -n "${KL_SDK_THIRD_PARTY_CACHE:-}" ]]; then
  test -d "$KL_SDK_THIRD_PARTY_CACHE" || { echo "Invalid third-party cache path" >&2; exit 5; }
  cp -a "$KL_SDK_THIRD_PARTY_CACHE" "$WORK/repo/pico-keys-sdk/third-party"
fi

# The existing KL overlay contains the FIDO-only USB and public descriptor changes.
python3 "$WORK/repo/scripts/apply-sdk-overlay.py"
git -C "$WORK/repo" apply --check patches/hid-v5.3-product-guards.patch
git -C "$WORK/repo/pico-keys-sdk" apply --check ../patches/hid-v5.3-sdk-hardening.patch
git -C "$WORK/repo" apply patches/hid-v5.3-product-guards.patch
git -C "$WORK/repo/pico-keys-sdk" apply ../patches/hid-v5.3-sdk-hardening.patch
echo "ISOLATED_KL_OVERLAY_AND_HID_V53_PATCHES_PASS"

# Optionally use a known local picotool Git checkout for fully offline builds.
# The SDK still verifies its required picotool tag (e.g. v2.3.0).
picotool_args=()
if [[ -n "${KL_OFFLINE_PICOTOOL_SOURCE:-}" ]]; then
  test -d "$KL_OFFLINE_PICOTOOL_SOURCE/.git" || {
    echo "Expected local picotool Git repository" >&2; exit 7;
  }
  picotool_args+=("-DPICOTOOL_GIT_REPOSITORY_URL=$KL_OFFLINE_PICOTOOL_SOURCE")
fi

# Some upstream diagnostics embed __FILE__ strings, including the random
# mktemp directory suffix. Normalize all source paths to make UF2s repeatable.
# Also pin compiler date/time macros to the reviewed branch commit time.
export SOURCE_DATE_EPOCH
SOURCE_DATE_EPOCH="$(git -C "$ROOT" show -s --format=%ct HEAD)"
file_prefix_flag="-ffile-prefix-map=$WORK=/kl-security-key-v53"
# Do NOT replace the Pico SDK's CMAKE_*_FLAGS with just a prefix map:
# these flags also carry mandatory RP2040 CPU/thumb/TLS ABI options.
rp2040_abi_flags="-mcpu=cortex-m0plus -mthumb -mfloat-abi=soft -ftls-model=local-exec"

# Explicitly disable packed basic attestation for this disposable build:
# the build may NEVER read a device private key or access the physical key.
cmake -S "$WORK/repo" -B "$WORK/build" -G Ninja \
  "${picotool_args[@]}" \
  "-DCMAKE_C_FLAGS=$rp2040_abi_flags $file_prefix_flag" \
  "-DCMAKE_CXX_FLAGS=$rp2040_abi_flags $file_prefix_flag" \
  "-DCMAKE_ASM_FLAGS=$rp2040_abi_flags $file_prefix_flag" \
  -DPICO_SDK_PATH="$PICO_SDK_PATH" \
  -DPICO_TOOLCHAIN_PATH="$PICO_TOOLCHAIN_PATH" \
  -DCMAKE_BUILD_TYPE=Release \
  -DPICO_BOARD=pico \
  -DFORCE_BUTTON_WAIT=ON \
  -DKL_FIDO_ONLY_RUNTIME=ON \
  -DKL_PACKED_BASIC_ATTESTATION=OFF \
  -DENABLE_OTP_APP=ON \
  -DENABLE_OATH_APP=ON
cmake --build "$WORK/build" --parallel "${JOBS:-4}"
UF2="$WORK/build/pico_fido.uf2"
test -f "$UF2"
echo "ISOLATED_V53_ARM_BUILD_PASS"
sha256sum "$UF2"
if [[ -n "${KL_V53_OUT_FILE:-}" ]]; then
  # Store the off-device artifact only at an explicit OUTSIDE-REPO destination.
  case "$KL_V53_OUT_FILE" in "$ROOT"/*) echo "Refusing to place UF2 in Git repo" >&2; exit 6;; esac
  # Never overwrite any file, particularly the frozen v5.2 reference.
  test ! -e "$KL_V53_OUT_FILE" && test ! -L "$KL_V53_OUT_FILE" || {
    echo "Refusing to overwrite an existing output file" >&2; exit 8;
  }
  mkdir -p "$(dirname "$KL_V53_OUT_FILE")"
  cp -n "$UF2" "$KL_V53_OUT_FILE"
  echo "OFFDEVICE_UF2_COPIED $KL_V53_OUT_FILE"
fi
if [[ "${KL_V53_KEEP_BUILD:-0}" == 1 ]]; then
  echo "DISPOSABLE_BUILD_PRESERVED $WORK"
fi
