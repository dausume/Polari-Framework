"""
@cross-cutting
@module waxprint.sim_state_basis
@tags @xc:bindings, @xc:render-3d

WaxPrintSimState — one persisted timestep of the wax-print simulation.
The "time" axis is BUILD HEIGHT: step i is the print state at height
z_i, so scrubbing the run watches the wall grow layer by layer and the
resolution degrade as deposited heat accumulates (the visual "does the
physics make sense" check Dustin asked for). One SimState row per height
sample; the wax-print SimulationDefinition lists this class, and the
SimSpace3D scene binds these fields → a stacked column of bead voxels
coloured by melt state / temperature.

Fields are written fresh each step by the waxprint runner (sim_runner)
from the wp-1..3 physics, and read by the SimSpace scene + the
SimSpaceEvaluationEquation condition overlays.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - waxprint.custom.sim_runner (projects physics onto these rows)
  - waxprint.sim_seed (SimulationDefinition + SimSpace scene + evals)
@see /WAX_PRINT_VOXEL_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/sim_state/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from waxprint.objects.sim_state.WaxPrintSimState import WaxPrintSimState  # noqa: F401
