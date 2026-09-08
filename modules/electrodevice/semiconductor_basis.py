"""
@module electrodevice.semiconductor_basis

THE DEDICATED SEMICONDUCTOR DATA SECTION (Dustin 2026-07-10):
general semiconductor / band-structure character derived from
EXECUTED material sims — the DFT fragment models (pyscf B3LYP
frontier orbitals) — never hand-typed:

  gap_ev        = LUMO - HOMO of the material's fragment model
  carrier_type  = classified from the CHEMICAL-POTENTIAL (midgap)
                  shift vs the pristine reference: mu down = hole-
                  rich = 'p'; mu up = 'n'; |shift| < 0.3 eV =
                  'intrinsic'
  level_shift_ev= the signed mu shift vs reference

Every derived number carries provenance + the sims' own honesty
notes (Kohn-Sham orbitals approximate frontier levels; small
fragments overestimate bulk-tube gaps). The validator
(device_validator) is the judge of whether these results meet
semiconductor-device standards — derivation here never self-blesses.

@consumers
  - electrodevice.custom.device_derive (transistor threshold heuristics)
  - electrodevice.device_validator_basis (the standards judge)
  - electrodevice.device_api (/api/electrodevice/semiconductors)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/semiconductor/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit

from electrodevice.objects.semiconductor._shared import SEED_SEMICONDUCTOR_PROFILES, _frontier, classify_carrier, derive_semiconductor, get_profile  # noqa: F401
from electrodevice.objects.semiconductor.SemiconductorProfile import SemiconductorProfile  # noqa: F401
