"""
@module odooconnect.odoo_scenarios_basis

BusinessScenarioDefinition — business simulations as DATA (od-5).
The guiding idea (Dustin 2026-07-28): businesses that do "whatever
they can" with "the tools they have". Scenario v1 is the wax-print
mold + geopolymer goods micro-business with two EXPLICIT prerequisite
assumptions (in assumptions_json, listed not hidden):
  1. feedstock is BOUGHT from a purely commercial supplier — the
     local hydroponic farm growing the wax source is scenario 2;
  2. a working wax 3D printer already exists (energy/labor/printer
     amortization excluded from v1 unit economics).

A scenario names a BASE OdooInstanceConfig that MUST be
mode=simulation — the engine refuses operations configs outright —
and runs in its own THROWAWAY database (scenario_db), so even the
sim database never accumulates scenario junk.

@consumers polariServer seed_pairs, odooconnect.custom.odoo_scenario_engine
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/odoo_scenarios/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from odooconnect.objects.odoo_scenarios._shared import SEED_BUSINESS_SCENARIOS  # noqa: F401
from odooconnect.objects.odoo_scenarios.BusinessScenarioDefinition import BusinessScenarioDefinition  # noqa: F401
