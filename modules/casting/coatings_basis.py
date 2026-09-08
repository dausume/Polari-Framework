"""
@cross-cutting
@module casting.coatings_basis
@tags @xc:bindings

cast-8: coatings, recycling, and the FULL chain report — mostly
BINDING what already exists rather than building:

  MoldCoatingDefinition   release/sealing coats as data: what they
                          are made of, how hot they survive, which
                          mold materials they apply to, and whether
                          they are locally renewable (the
                          solgel_sourcing accessibility vocabulary).
  CastingRunRecord        one physical/simulated cast — links a
                          chain stage to the EXISTING
                          waxprint.MoldLifecycleRecord (reuse
                          counting lives there; we do not duplicate
                          it) and to a fill run.
  chain_full_report       chain_report (parity + thermal) + the
                          shrink two-pass + per-stage mold ECONOMICS
                          from supplychain.custom.mold_analysis's
                          MOLD_STRATEGY_PRIORS (mass, cycle life,
                          release kg/cast, end-of-life: wax MELTS to
                          reclaim, geopolymer/ceramic CRUSH to
                          aggregate) + release-coating RESOLUTION
                          (a stage whose strategy demands release
                          gets the best applicable coating row —
                          renewable first — or a named absence).

@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-8)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/coatings/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from casting.custom.chain_analysis import (
    _process_temp, _stages_of, chain_report,
    shrink_compensation_report,
)
from casting.custom.wax_feasibility import _row_named, _rows
from objectTreeDecorators import treeObject, treeObjectInit

from casting.objects.coatings._shared import COATING_PURPOSES, SEED_MOLD_COATINGS, _STRATEGY_OF, _WAX_KINDS, _strategy_for, chain_full_report, resolve_release_coating  # noqa: F401
from casting.objects.coatings.MoldCoatingDefinition import MoldCoatingDefinition  # noqa: F401
from casting.objects.coatings.CastingRunRecord import CastingRunRecord  # noqa: F401
