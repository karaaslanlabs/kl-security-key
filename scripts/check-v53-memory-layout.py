#!/usr/bin/env python3
"""Off-device RP2040 ELF RAM-layout regression gate (NOT live heap validation).

Checks the address space left after linked static sections. The remaining
address interval is an upper-bound planning signal, not measured free heap.
"""
import argparse
from pathlib import Path
import subprocess
import sys

MAIN_SRAM_START = 0x20000000
MAIN_SRAM_END = 0x20040000
SCRATCH_END = 0x20042000
EXPECTED = (
    "__data_start__", "__data_end__", "__bss_start__", "__bss_end__",
    "__end__", "__HeapLimit", "__StackLimit",
    "__StackOneBottom", "__StackOneTop", "__StackBottom", "__StackTop",
)
DEFAULT_MIN_GAP = 128 * 1024

def parse_symbols(text):
    result = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[-1] in EXPECTED:
            result[parts[-1]] = int(parts[0], 16)
    missing = [name for name in EXPECTED if name not in result]
    if missing:
        raise ValueError("missing linker symbols: " + ", ".join(missing))
    return result

def validate(symbols, min_gap):
    d = symbols
    if not (MAIN_SRAM_START <= d["__data_start__"] <= d["__data_end__"]
            <= d["__bss_start__"] <= d["__bss_end__"]
            == d["__end__"] < d["__HeapLimit"] == d["__StackLimit"]
            == MAIN_SRAM_END):
        raise ValueError("unexpected main SRAM/heap address ordering")
    if not (MAIN_SRAM_END < d["__StackOneBottom"] < d["__StackOneTop"]
            <= d["__StackBottom"] < d["__StackTop"] == SCRATCH_END):
        raise ValueError("unexpected scratch RAM core stack layout")
    gap = d["__HeapLimit"] - d["__end__"]
    if gap < min_gap:
        raise ValueError(
            f"static-to-heap-limit address gap {gap} is below gate {min_gap}"
        )
    return {
        "static_end": d["__end__"],
        "heap_limit": d["__HeapLimit"],
        "linker_gap_bytes": gap,
        "linker_gap_kib": round(gap / 1024, 2),
        "linker_gate_bytes": min_gap,
        "core0_stack_reservation_bytes": d["__StackTop"] - d["__StackBottom"],
        "core1_stack_reservation_bytes": d["__StackOneTop"] - d["__StackOneBottom"],
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--elf", type=Path, required=True)
    p.add_argument("--toolchain-bin", type=Path, required=True)
    p.add_argument("--min-linker-gap-bytes", type=int, default=DEFAULT_MIN_GAP)
    args = p.parse_args()
    try:
        if not args.elf.is_file():
            raise ValueError("ELF not found")
        if args.min_linker_gap_bytes < 0:
            raise ValueError("negative threshold is not valid")
        nm = args.toolchain_bin / "arm-none-eabi-nm"
        r = subprocess.run([str(nm), "-n", str(args.elf)], capture_output=True, text=True)
        if r.returncode:
            raise ValueError("cannot examine ELF symbols: " + r.stderr[-300:])
        info = validate(parse_symbols(r.stdout), args.min_linker_gap_bytes)
        for key, value in info.items():
            print(f"{key.upper()}={value}")
        print("RP2040_LINKER_MEMORY_BUDGET_PASS")
        print("CAVEAT: address gap is NOT guaranteed free heap or measured live stack usage.")
        return 0
    except (OSError, ValueError) as err:
        print("RP2040_LINKER_MEMORY_BUDGET_FAIL: " + str(err), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
