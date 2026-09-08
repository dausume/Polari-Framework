"""
@module microchip.chip_families_basis

Rank-1 DEVICE FAMILIES as data (MICROCHIP_LADDER_PLAN §2c, ratified
2026-08-31): rank 1 of the design ladder is `device`, and FET is its
first FAMILY, not its definition. Peer families (capacitor,
memristor, photonic, MEMS, inductor, spintronic) enter at rank 1
under the same contract — characterized behavior, derive-or-cite,
refusals by name — and rungs 2+ mix families freely (a 1T1C DRAM
cell is FET + capacitor; an RRAM crossbar is memristors + FET
selectors + CMOS periphery).

SHELL DISCIPLINE: a non-FET family ships here as a SHELL — the
characterization CONTRACT it must satisfy is data (`contract_json`,
revisable), but NO device treeObject class is defined until that
family's own arc characterizes something real (the per-class
schema-freeze rule: defining fields before the physics basis exists
locks in the wrong schema). Every shell says exactly that, plus its
first composition target and plan pointer — refusal, never pretense.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
  - microchip.chip_api (GET /api/microchip/families[/{name}])
  - microchip.families_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/chip_families/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from microchip.objects.chip_families._shared import SEED_DEVICE_FAMILIES, _SHELL_NOTE, families_report, family_report  # noqa: F401
from microchip.objects.chip_families.DeviceFamilyDefinition import DeviceFamilyDefinition  # noqa: F401
