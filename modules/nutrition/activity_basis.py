"""
@cross-cutting
@module nutrition.activity_basis
@tags @xc:bindings

nmp-5 — activity as data: ActivityDefinition rows for a CURATED
common subset of the 2024 Adult Compendium (real codes, values
VERBATIM from vendor/compendium_2024_adult_mets.csv at import — the
full 1,111-activity catalog stays searchable through the vendor CSV
and any activity can be materialized on demand; seeding all 1,111
as DB rows would be boot weight nothing needs yet). ActivityLog =
one logged session with first-class TIMING (decision 14 / nmp-5b).

Intensity bands by the Compendium MET cutoffs: light < 3.0,
moderate 3.0-5.9, vigorous >= 6.0.

Attribution (required): Herrmann SD et al., 2024 Adult Compendium
of Physical Activities, pacompendium.com — values unaltered.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.activity_analysis
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-5
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/activity/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit
from nutrition.custom.vendor_data import compendium_mets

from nutrition.objects.activity._shared import COMPENDIUM_ATTRIBUTION, INTENSITY_BANDS, SEED_ACTIVITY_DEFINITIONS, _CURATED, _build_seed, intensity_band  # noqa: F401
from nutrition.objects.activity.ActivityDefinition import ActivityDefinition  # noqa: F401
from nutrition.objects.activity.ActivityLog import ActivityLog  # noqa: F401
