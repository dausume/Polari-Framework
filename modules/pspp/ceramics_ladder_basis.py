"""
@module pspp.ceramics_ladder_basis

mtt-2 ceramics: the THERMAL ESCALATION LADDER — the bootstrapping
spine where each furnace is built from the output of the previous one,
climbing from a simple geopolymer oven up to a steelmaking-grade
furnace that can make bio-galvanized steel. This is the "thermal
strain of material refinement" (Dustin) — modeled as DATA (rungs the
maker climbs), the backing for the manufacturing-tools / furnace tech
tree nodes.

Each rung declares the furnace temperature it reaches, the ceramic
LINING it needs (with a LOCAL option and, where it matters, a non-local
OLIVINE/carbon-negative option), the rung it depends on, and what it
unlocks. `validate_ladder` proves the bootstrapping is physically
consistent: every rung's lining must be FIREABLE at the previous
rung's temperature AND WITHSTAND this rung's temperature — you can only
build a furnace from a material your current furnace can already make.

The CNT rung is deliberately honest: catalytic-CVD nanotube growth is
only ~700-1100 C (reachable mid-ladder), but its real gate is a
CONTROLLED ATMOSPHERE + catalyst reactor, NOT heat — so it branches
off as a specialized-refinement capability, not just a hotter furnace.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.pspp_api (/api/pspp/ceramics/ladder)
  - pspp.ceramics_ladder_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/ceramics_ladder/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from pspp.objects.ceramics_ladder._shared import SEED_LADDER_RUNGS, _LAD_PROV, _MTREE, _get, _lining, _loads, _row, _unlocks, ladder_path, rung_dict, rung_unlocking, validate_ladder  # noqa: F401
from pspp.objects.ceramics_ladder.LadderRung import LadderRung  # noqa: F401
