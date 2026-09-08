"""
@cross-cutting
@module aquaponics.plant_growth_basis
@tags @xc:bindings

aqp-8 — PlantGrowthModel: the per-part growth knobs, a SIBLING row
keyed to an aqp-4 PlantPart (extends aqp-4, does not rebuild it —
file-size-decomposition + "reuse PlantPart, don't duplicate"). One
row per part carries how that part grows and its volume->mass density
(the interaction currency Dustin asked for).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - aquaponics.plant_growth_normalized_basis.free_soil_constants (2026-07-15
    — the PRIMARY reader now; the detailed model's own per-part rate
    source, see that module's docstring)
  - aquaponics.custom.plant_growth_simplified (reads the SAME constants
    indirectly, via free_soil_constants — no longer has its own
    separate PlantGrowthModel lookup)
@see /AQUAPONICS_PHASE2_PLAN.md §aqp-8, /AQUAPONICS_POT_SHAPE_PLAN.md phase 9
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/plant_growth/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from aquaponics.objects.plant_growth.PlantGrowthModel import PlantGrowthModel  # noqa: F401
