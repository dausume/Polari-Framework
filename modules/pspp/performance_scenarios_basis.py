"""
@module pspp.performance_scenarios_basis

Performance = a material STATE, in a GEOMETRY, under an EXPOSURE,
with LOADS, over TIME (plan pspp-9). Engines declare the structure
descriptors they read (require_descriptors gate) and produce CLAIMS
with evidence — v1 ships the two plan engines, both reusing existing
house math instead of inventing physics:

- elastic-bounds: Voigt/Reuss/Hill bounds via formulation_math over
  scenario-declared phase moduli — bounds, honestly labeled; the
  porosity->stiffness knockdown is a NAMED GAP until a cited
  relation loads (invariant I5).
- water-transport: reads the porosity/permeability descriptors; when
  hydraulicPermeability exists it claims it (and points at the live
  Darcy engine for field solves); missing descriptors refuse naming
  the exact knob.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/performance_scenarios/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from pspp.material_structure_basis import require_descriptors
from pspp.exposure_scenarios_basis import exposure_index

from pspp.objects.performance_scenarios._shared import PERFORMANCE_ENGINES, _claim, _elastic_bounds, _water_transport, run_performance_scenario  # noqa: F401
from pspp.objects.performance_scenarios.MaterialPerformanceScenario import MaterialPerformanceScenario  # noqa: F401
