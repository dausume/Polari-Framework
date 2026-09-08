"""
@cross-cutting
@module tanks.tank_basis
@tags @xc:bindings

Freshwater + saltwater TANK ecosystem models (tank-1) — the alternate
nutrient source from Dustin's food-forest specs. Own module + own data,
framework-core only. Models the modular 30-gallon interconnected tank
system as objects, so the ecosystem's nutrient CYCLING and harvestable
YIELD can be simulated (tank_analysis) — especially the iodine / sodium
/ chloride the hydroponic garden CANNOT supply (closing the nut-5 gap).

Three treeObjects (auto-CRUDE + persisted — object-coherence):

  TankDefinition        one vessel: volume, water type, ecological role,
                        room-temperature target.
  AquacultureSpecies    one organism in the roster — its ecological
                        ROLE(s) (nutrient regulator, filter feeder,
                        detritus eater, glass cleaner, nutrient
                        replenisher, oxygenator), whether it is edible /
                        wax-use, its per-individual daily N/P water flux
                        (+ adds, − removes), and its harvestable
                        biomass + the DietaryNutrients that biomass
                        yields (seaweed → iodine/sodium/chloride).
  TankSystemDefinition  an interconnected set of tanks + the species
                        stock → one runnable, rankable ecosystem
                        (mirrors PotSystemDefinition).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - tanks.custom.tank_analysis (nutrient balance, harvest yield, regulation)
@see /SALTWATER_FOOD_FOREST_SPEC.md, /HOUSEHOLD_NUTRITION_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/tank/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from tanks.objects.tank._shared import SPECIES_ROLES, SUBSTRATE_KINDS, TANK_ROLES, WATER_TYPES  # noqa: F401
from tanks.objects.tank.TankDefinition import TankDefinition  # noqa: F401
from tanks.objects.tank.TankSubstrateDefinition import TankSubstrateDefinition  # noqa: F401
from tanks.objects.tank.AquacultureSpecies import AquacultureSpecies  # noqa: F401
from tanks.objects.tank.TankSystemDefinition import TankSystemDefinition  # noqa: F401
