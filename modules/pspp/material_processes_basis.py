"""
@module pspp.material_processes_basis

The PROCESS layer (plan pspp-4) — processing is a first-class
TRANSFORMATION, not a material property (Ch.8.2-8.6 review: mixing,
curing, heating, dehydration, condensation, annealing, crystallization
are things that HAPPEN TO a material). Executions are the edges of the
MaterialState DAG.

Invariant I2 lives here: every definition DECLARES its execution
effect — TRANSFORMATIVE (creates child states, even when some
resulting structure is unknown) or OBSERVATIONAL (attaches claims to
the existing state, never a new state). The discriminator is declared,
never inferred.

Heating methods (conventional/microwave/RF/Joule/laser) are one
process concept with different energy-deposition models — they change
kinetics, not chemistry. Crystallization is nucleation + growth
PROCESSES, never `material.phase = leucite` by assignment (F10).
Admissibility reuses the existing thermal-window machinery (the
no-volatiles rule becomes a process gate).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.material_states_basis (executions produce/annotate states)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/material_processes/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from pspp.objects.material_processes._shared import ENERGY_DEPOSITION_MODELS, EXECUTION_EFFECTS, SEED_PROCESS_DEFINITIONS, _PROC_PROVENANCE, _loads, _row, admissible_schedule, validate_execution  # noqa: F401
from pspp.objects.material_processes.MaterialProcessDefinition import MaterialProcessDefinition  # noqa: F401
from pspp.objects.material_processes.MaterialProcessExecution import MaterialProcessExecution  # noqa: F401
