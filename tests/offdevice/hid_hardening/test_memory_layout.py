"""Off-device tests for the RP2040 ELF linker-budget policy.

Synthetic linker symbols only; no firmware, USB hardware, or private keys.
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check-v53-memory-layout.py"
SPEC = importlib.util.spec_from_file_location("kl_v53_memory_layout", SCRIPT)
memory_layout = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(memory_layout)


def sample_symbols():
    return {
        "__data_start__": 0x20000000,
        "__data_end__": 0x20001F48,
        "__bss_start__": 0x20002000,
        "__bss_end__": 0x20017480,
        "__end__": 0x20017480,
        "__HeapLimit": 0x20040000,
        "__StackLimit": 0x20040000,
        "__StackOneBottom": 0x20040400,
        "__StackOneTop": 0x20040C00,
        "__StackBottom": 0x20041800,
        "__StackTop": 0x20042000,
    }


class LinkerMemoryBudgetTests(unittest.TestCase):
    def test_documented_snapshot_passes_project_floor(self):
        result = memory_layout.validate(sample_symbols(), 128 * 1024)
        self.assertEqual(result["linker_gap_bytes"], 166784)
        self.assertEqual(result["core0_stack_reservation_bytes"], 2048)
        self.assertEqual(result["core1_stack_reservation_bytes"], 2048)

    def test_too_high_minimum_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "below gate"):
            memory_layout.validate(sample_symbols(), 200 * 1024)

    def test_corrupt_heap_boundary_fails_closed(self):
        symbols = sample_symbols()
        symbols["__HeapLimit"] = 0x2003F000
        with self.assertRaisesRegex(ValueError, "unexpected main SRAM"):
            memory_layout.validate(symbols, 128 * 1024)

    def test_corrupt_scratch_stack_order_fails_closed(self):
        symbols = sample_symbols()
        symbols["__StackOneTop"] = symbols["__StackOneBottom"]
        with self.assertRaisesRegex(ValueError, "unexpected scratch RAM"):
            memory_layout.validate(symbols, 128 * 1024)

    def test_missing_symbol_fails_closed(self):
        symbol_lines = [
            f"{value:08x} B {name}" for name, value in sample_symbols().items()
            if name != "__HeapLimit"
        ]
        with self.assertRaisesRegex(ValueError, "missing linker symbols"):
            memory_layout.parse_symbols("\n".join(symbol_lines))

    def test_nm_symbol_parser_round_trip(self):
        symbols = sample_symbols()
        lines = [f"{value:08x} B {name}" for name, value in symbols.items()]
        self.assertEqual(memory_layout.parse_symbols("\n".join(lines)), symbols)


if __name__ == "__main__":
    unittest.main()
