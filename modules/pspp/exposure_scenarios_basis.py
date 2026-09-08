"""
@module pspp.exposure_scenarios_basis

Reusable exposure environments (plan pspp-9; ChatGPT convergence:
PerformanceScenario = MaterialState + Geometry + ExposureScenario +
Loads). An exposure is a named, editable environment row — the same
'outdoor' or 'hydroponic' row serves geopolymers, waxes, alloys —
so disciplines share environments instead of re-describing them.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.performance_scenarios_basis (scenarios reference these by name)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/exposure_scenarios/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from pspp.objects.exposure_scenarios._shared import SEED_EXPOSURE_SCENARIOS, _PROV, _row, exposure_index  # noqa: F401
from pspp.objects.exposure_scenarios.ExposureScenario import ExposureScenario  # noqa: F401
