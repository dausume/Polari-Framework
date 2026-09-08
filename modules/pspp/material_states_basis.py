"""
@module pspp.material_states_basis

The MaterialState DAG (plan pspp-2) — a material is one identity with
a HISTORY of durable states ('raw powder' → 'activated slurry' →
'cured solid' → branches like 'carbonated'), not one property sheet.
States are the citable subjects claims attach to; edges arrive with
MaterialProcessExecution in pspp-4 (parent_state_ids_json carries the
DAG shape meanwhile).

ProcessingStage (extensible ROWS, deliberately not an enum — ChatGPT
convergence) is orthogonal to thermodynamic_phase: a geopolymer gel is
thermodynamically condensed but occupies its own place in a process
route; a polymer melt and a curing resin are both liquids in different
processing stages.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.custom.state_resolution (canonical resolution, invariant I1)
  - pspp.claims_basis (subject_state_key = MaterialState.name)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/material_states/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from pspp.objects.material_states._shared import CANONICAL_STATE, SEED_PROCESSING_STAGES, THERMODYNAMIC_PHASES, _STAGE_PROVENANCE, _row  # noqa: F401
from pspp.objects.material_states.MaterialState import MaterialState  # noqa: F401
from pspp.objects.material_states.ProcessingStage import ProcessingStage  # noqa: F401
