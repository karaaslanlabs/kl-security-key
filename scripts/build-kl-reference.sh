#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK="$ROOT/pico-keys-sdk"
: "${PICO_SDK_PATH:?Set PICO_SDK_PATH to your Raspberry Pi Pico SDK path}"
BUILD_DIR="${BUILD_DIR:-$ROOT/build-kl-reference}"
JOBS="${JOBS:-2}"

if [[ -n "${PICO_TOOLCHAIN_PATH:-}" ]]; then
  export PATH="$PICO_TOOLCHAIN_PATH/bin:$PATH"
fi
if ! command -v arm-none-eabi-gcc >/dev/null 2>&1; then
  echo "arm-none-eabi-gcc not found. Set PICO_TOOLCHAIN_PATH or add the toolchain bin directory to PATH." >&2
  exit 4
fi

had_third_party=0
[[ -e "$SDK/third-party" ]] && had_third_party=1
cleanup() {
  git -C "$SDK" restore src/usb/usb.c src/usb/usb_descriptors.c >/dev/null 2>&1 || true
  if [[ "$had_third_party" == 0 ]]; then
    rm -rf "$SDK/third-party"
  fi
}
trap cleanup EXIT

python3 "$ROOT/scripts/apply-sdk-overlay.py"
cmake_args=(
  -S "$ROOT" -B "$BUILD_DIR"
  -DCMAKE_BUILD_TYPE=Release
  -DPICO_BOARD=pico
  -DPICO_SDK_PATH="$PICO_SDK_PATH"
  -DFORCE_BUTTON_WAIT=ON
  -DKL_FIDO_ONLY_RUNTIME=ON
  -DKL_PACKED_BASIC_ATTESTATION=ON
)

if [[ -n "${PICO_TOOLCHAIN_PATH:-}" ]]; then
  cmake_args+=("-DPICO_TOOLCHAIN_PATH=$PICO_TOOLCHAIN_PATH")
fi
if [[ -n "${PICOTOOL_FETCH_FROM_GIT_PATH:-}" ]]; then
  cmake_args+=("-DPICOTOOL_FETCH_FROM_GIT_PATH=$PICOTOOL_FETCH_FROM_GIT_PATH")
fi

cmake "${cmake_args[@]}"
cmake --build "$BUILD_DIR" -j"$JOBS"

UF2="$BUILD_DIR/pico_fido.uf2"
if [[ ! -f "$UF2" ]]; then
  echo "Expected UF2 not produced: $UF2" >&2
  exit 5
fi
sha256sum "$UF2"