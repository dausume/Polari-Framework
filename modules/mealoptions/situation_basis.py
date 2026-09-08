"""
@module mealoptions.situation_basis

mlg-3 — the meal-SITUATION portability vocabulary (MEAL_LOGISTICS_PLAN
§2, D7/D8), moved here in mo-1 with its name unchanged:

  MealSituation   where a meal is eaten and what that needs
                  (lunchbox, cold packs, pack minutes, pack-when),
                  with the FSIS cold-chain citation on the rows that
                  need it.

The per-entry row (MealLogistics — names a person and an entry) and
the eating-time profile (MealTimeProfile — names a person) stay in
nutrition.logistics_basis.
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/situation/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from mealoptions.objects.situation._shared import COLD_CHAIN_CITATION, SEED_MEAL_SITUATIONS, _PROV, _s  # noqa: F401
from mealoptions.objects.situation.MealSituation import MealSituation  # noqa: F401
