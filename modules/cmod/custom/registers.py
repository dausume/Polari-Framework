"""
@module cmod.custom.registers

ucd-0a (2026-10-07): the register snapshot moved to board.custom.registers (the SoC address space is a board-object
fact, materialized there as Register rows). This module re-exports it so cmod's callers (atoms, manifest, analyse,
selftest_uno, cmod_cli) keep their `from cmod.custom import registers as R` unchanged.
"""
from board.custom.registers import (HERE, PERIPHERAL_RULES, load, parse_dm, peripheral, refresh,  # noqa: F401
                                    snapshot_path)
