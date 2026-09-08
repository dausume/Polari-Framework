"""
@module foodstate.food_materials_basis

fsp-1 — the COMMON-BASE-INGREDIENTS roster (Dustin 2026-09-01:
"start putting together a database of common base ingredients").
One FoodMaterial identity row per base ingredient; nmp decision 8
(meals build STRICTLY from base ingredients + meats) makes this
roster the meal-planning vocabulary.

v1 roster = the 49 foods of the vendored, sha-pinned FDC subset
(`modules/nutrition/custom/vendor/fdc_foundation_subset.csv`, CC0,
retrieved 2026-08-20) — every identity resolves to a pinned fdc_id
from the vendor file itself, never from memory (derive-or-cite).
Extending the roster = add a slug + category here AND a vendored
row set; an identity without vendor rows would refuse coverage
honestly, not invent it.

The identity's name doubles as the pspp material key: composition
claims land on the canonical subject '<name>#as-defined'
(pspp sync-on-need — no MaterialState row is required to exist).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
  - foodstate.custom.food_composition (claims + coverage)
  - foodstate.food_materials_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/food_materials/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from foodstate.objects.food_materials._shared import ROSTER, ROSTER_CATEGORIES, _PROV, _display, build_food_material_seeds  # noqa: F401
from foodstate.objects.food_materials.FoodMaterial import FoodMaterial  # noqa: F401
