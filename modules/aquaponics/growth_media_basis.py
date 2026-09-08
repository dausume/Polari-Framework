"""
@cross-cutting
@module aquaponics.growth_media_basis
@tags @xc:bindings

Multiscale soil + water + nutrient profiles (aqp-2). Dustin 2026-07-08:
"multiscale soil definitions, and multiscale water definitions with
nutrient profiles for both … water has an aquaponic or hydroponic
source and … tunable nutrient profiles."

Four classes, all auto-CRUDE + persisted (object-coherence — the
recipe IS the row, every concentration a knob):

  NutrientSpecies  — the shared vocabulary: one row per nutrient/gas
                     (nitrate-N, P, K, …, dissolved-O2, dissolved-CO2)
                     with role, unit, and a healthy typical range.
                     Grounds both media profiles AND per-part plant
                     I/O (aqp-4).
  NutrientProfile  — a named set of concentrations over species, with
                     pH / EC / temperature. Referenced by soils AND
                     waters; tunable.
  SoilDefinition   — a growing medium as a MULTISCALE object: bulk
                     hydrology (field capacity, wilting point,
                     conductivity, CEC) + per-scale structure
                     descriptors (aggregate → pore → colloid).
  WaterDefinition  — the aquaponic/hydroponic solution as a MULTISCALE
                     object: bulk state (T, pH, EC, dissolved gases) +
                     source (kind + feed rate) + per-scale descriptors
                     (ionic ↔ bulk-flow).

Analysis math lives in media_analysis.py.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - aquaponics.custom.media_analysis / aquaponics.media_api
@see /AQUAPONICS_MODULE_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/growth_media/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from aquaponics.objects.growth_media._shared import NUTRIENT_ROLES, SOIL_TEXTURES, WATER_SOURCES  # noqa: F401
from aquaponics.objects.growth_media.NutrientSpecies import NutrientSpecies  # noqa: F401
from aquaponics.objects.growth_media.NutrientProfile import NutrientProfile  # noqa: F401
from aquaponics.objects.growth_media.SoilDefinition import SoilDefinition  # noqa: F401
from aquaponics.objects.growth_media.WaterDefinition import WaterDefinition  # noqa: F401
