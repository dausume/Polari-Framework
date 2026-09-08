"""
@cross-cutting
@module aquaponics.pot_system_basis
@tags @xc:bindings

PotSystemDefinition + survival/impact synthesis (aqp-6) — binds a pot,
soil, water, plant and atmosphere into ONE configurable object
(object-coherence), then answers the two questions Dustin asked:

  system_survival — for every input the plant needs, does this
                    configuration SUPPLY the per-part MIN band? The
                    delivery rate of each nutrient (water flow ×
                    concentration), root-zone O2 (dissolved), CO2
                    (atmosphere gas-exchange verdict), light and VPD
                    are each compared to the plant's requirement; the
                    LIMITING factor is named. "survival conditions."
  system_impact   — environmental impact over the plant's lifetime:
                    permanent carbon sequestered (+ CO2-equivalent),
                    net CO2 fixed / O2 released, nutrient REMOVED from
                    the aquaponic loop (the bioremediation benefit),
                    and water throughput. Persisted to
                    impact_result_json so the context-scoring engine
                    can rank configurations through its objectRef seam
                    (the beeswax@L1 FEM idiom).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - aquaponics.pot_system_api / scoring (via impact_result_json)
@see /AQUAPONICS_MODULE_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/pot_system/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.custom.atmosphere_analysis import (
    atmosphere_state, environment_gas_exchange, LOW_LIGHT_PPFD,
)
from aquaponics.custom.plant_analysis import (
    CO2_PER_CARBON, plant_gas_nutrient_budget, plant_lifetime_capture,
)

from aquaponics.objects.pot_system._shared import SURVIVAL_STATUSES, _by_name, _f, _parse, _system, system_impact, system_survival  # noqa: F401
from aquaponics.objects.pot_system.PotSystemDefinition import PotSystemDefinition  # noqa: F401
