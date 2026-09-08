"""
@cross-cutting
@module aquaponics.plant_basis
@tags @xc:bindings

Plant profile PER PART (aqp-4). Dustin 2026-07-08: "the plant should
have a profile per part of the plant that analyses the permanent
structure of the plant and its composition so we can assess its
capture of carbon and other nutrients permanently through the lifetime
by volume per part … needed and min-max nutrient input and output per
part … including carbon dioxide and oxygen."

Two classes, auto-CRUDE + persisted:

  PlantDefinition — the whole plant: species, lifetime, growth stages,
                    mature size.
  PlantPart       — one part (root/stem/leaf/flower/fruit): its mature
                    volume + dry density, what FRACTION is permanent
                    structure, its FATE (harvested / senesces / soil-
                    incorporated / standing) — the honesty seam that
                    separates biomass CAPTURED from carbon PERMANENTLY
                    sequestered — its dry composition (carbon +
                    nutrients by mass), and its per-species net daily
                    flux at maturity with needed + MIN-MAX bands
                    (nutrients, and the atmospheric gases CO2 and O2).

The capture + budget MATH lives in plant_analysis.py.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - aquaponics.custom.plant_analysis / aquaponics.plant_api
@see /AQUAPONICS_MODULE_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/plant/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from aquaponics.objects.plant._shared import PART_FATES, PLANT_PARTS  # noqa: F401
from aquaponics.objects.plant.PlantDefinition import PlantDefinition  # noqa: F401
from aquaponics.objects.plant.PlantPart import PlantPart  # noqa: F401
