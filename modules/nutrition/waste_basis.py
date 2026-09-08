"""
@cross-cutting
@module nutrition.waste_basis
@tags @xc:bindings

mpb-4 (waste half) — the waste ledger: food that left the kitchen
uneaten is usually the biggest hidden budget leak, so it gets its
own facts:

  WasteRecord   one discarded lot: household × food × amount ×
                REASON × date. The $ value is DERIVED at read time
                from the best observed price (labeled estimate) —
                never stored, so a price correction re-prices past
                waste honestly.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.waste_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-4
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/waste/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.waste._shared import SEED_WASTE_RECORDS, WASTE_REASONS, _PROV  # noqa: F401
from nutrition.objects.waste.WasteRecord import WasteRecord  # noqa: F401
