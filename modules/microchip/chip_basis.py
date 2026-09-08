"""
@module microchip.chip_basis

The microchip DESIGN-LEVEL ladder as data (Dustin 2026-08-21):
device -> standard-cell -> functional-block -> core -> chip, with
an interface for traversing between levels. DELIBERATELY SEPARABLE
from the foundational device modules: a singular FET is defined by
cntfet/electrodevice (each carrying its OWN scale axes — the D6
manufacturing_regime ladder and the D12 physics_fidelity axis);
this module only REFERENCES device rows by {module, class, name},
never imports device code. Absent device modules degrade to honest
'absent' artifacts, not errors.

Two seeded designs:
  - polari-cnt-ladder: OUR ladder — device level LIVE (the S1
    aligned tube + the D5 film sibling), upper levels UNBUILT with
    plan pointers (S4 cells, S6 blocks/core, S7 chip) — refusal,
    never pretense.
  - rv16x-nano-precedent: the Hills 2019 Nature RV16X-NANO
    decomposed onto the same ladder, every node cited to [HIL19]
    through cntfet's reference-anchor rows (cite+values bucket;
    the paper's design collateral was never released — scientific
    reference ONLY).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
  - microchip.custom.chip_traverse (the traversal engine)
  - microchip.microchip_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/chip/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from microchip.objects.chip._shared import SEED_DESIGN_LEVELS, SEED_DESIGN_NODES, _HIL  # noqa: F401
from microchip.objects.chip.DesignLevelDefinition import DesignLevelDefinition  # noqa: F401
from microchip.objects.chip.MicrochipDesignNode import MicrochipDesignNode  # noqa: F401
