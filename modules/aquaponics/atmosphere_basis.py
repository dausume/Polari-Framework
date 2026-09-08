"""
@cross-cutting
@module aquaponics.atmosphere_basis
@tags @xc:bindings

AtmosphereDefinition (aqp-5). Dustin 2026-07-08: "fully simulate
atmospheric conditions." One auto-CRUDE object holding the full
atmospheric state the plant exchanges gas and water with — open air
or a CONTROLLED environment (grow tent, greenhouse, or the
fridge-ambient idiom from the MVW print sim), so the effect of
enclosure on CO2 supply is answered by analysis, not assumed.

The gas-exchange + VPD MATH lives in atmosphere_analysis.py.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - aquaponics.custom.atmosphere_analysis / aquaponics.atmosphere_api
@see /AQUAPONICS_MODULE_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/atmosphere/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from aquaponics.objects.atmosphere.AtmosphereDefinition import AtmosphereDefinition  # noqa: F401
