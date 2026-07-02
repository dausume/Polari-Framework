"""
@cross-cutting
@module simulations.wind_field_grid_sim_state
@tags @xc:bindings, @xc:render-3d

WindFieldGridState — one persisted timestep of the WIND-FIELD space: a
regular 3D grid of wind vectors filling the pendulum's box. This is the
first non-pendulum "space" in the multi-scale PoC: a simulation whose
output is a SAMPLEABLE FIELD, coupled into the Newtonian pendulum via a
SimulationCouplingDefinition (the pendulum's wind Partial reads the wind
velocity sampled at the bob's position).

The runner advances ONE row per class per step, so the whole grid lives
on a single row as a matrix-valued field: `cells_json` is a JSON N×6
matrix, one row per cell — [cx, cy, cz, wx, wy, wz] (cell center in
metres; wind velocity in m/s). Matrix-valued state serialized as a
`*_json` TEXT field is the codebase's standing convention; the no-code
engine's `json_decode` / `json_encode` value sources move it in and out
of MatrixEquationOperation operands.

The field evolves as a deterministic gust model — a spatially-varying,
time-varying sinusoid over the cell centers (see `wind-field-evolve` in
matrices/seed_data via wind_field_seed). Cell CENTERS are carried through
unchanged; only the velocity columns change per step. The wind sim runs
at a COARSER dt than the pendulum (a genuinely different timescale — the
multi-scale point); the pendulum samples the latest wind step ≤ its own
time (zero-order hold).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.wind_field_seed (wind-field-3d sim + step solution)
  - simulations.simulation_coupling (field sampling into the pendulum)
  - SimSpace3D `field` binding (sparse arrows, one per visible cell)
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

# Grid geometry — spans the pendulum's swing volume (viewport extent 1.5;
# the bob lives on the L=1 sphere around the origin pivot).
WIND_GRID_COUNTS = (4, 4, 4)
WIND_GRID_MIN = (-1.2, -1.3, -1.2)
WIND_GRID_MAX = (1.2, 0.2, 1.2)


def build_initial_cells():
    """The step-0 grid: cell centers on the regular lattice, wind velocity
    zero everywhere (calm air until the field's first evolve step)."""
    (nx, ny, nz) = WIND_GRID_COUNTS
    cells = []
    for ix in range(nx):
        for iy in range(ny):
            for iz in range(nz):
                cx = WIND_GRID_MIN[0] + (WIND_GRID_MAX[0] - WIND_GRID_MIN[0]) * ix / (nx - 1)
                cy = WIND_GRID_MIN[1] + (WIND_GRID_MAX[1] - WIND_GRID_MIN[1]) * iy / (ny - 1)
                cz = WIND_GRID_MIN[2] + (WIND_GRID_MAX[2] - WIND_GRID_MIN[2]) * iz / (nz - 1)
                cells.append([round(cx, 6), round(cy, 6), round(cz, 6), 0.0, 0.0, 0.0])
    return cells


class WindFieldGridState(treeObject):
    """One persisted timestep of the wind-field grid.

    Identity is composite on (simulation_run_ref, step); the runner names
    rows "<run>-wind-field-grid-<step>". Membership in the wind-field-3d
    simulation is declared by the class attribute.

    Gust parameters (wind_amp, wind_freq, wind_base_*) live in the
    SimulationDefinition's `parameters_json`, NOT on the row — constants
    of the sim, read into each step's context as `self.<param>`.
    """

    simulation_definition_name = 'wind-field-3d'

    default_initial_field_values = {
        'cells_json': json.dumps(build_initial_cells()),
    }

    # cells_json is the ONLY state — the whole field, written fresh by the
    # evolve step each wind-step, so it must persist (core).
    field_save_policy = {
        'cells_json': 'core',
    }

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        simulation_run_ref: str = '',
        step: int = 0,
        time: float = 0.0,
        # The grid as a matrix-valued field: JSON N×6, one row per cell —
        # [cx, cy, cz, wx, wy, wz] (centers in metres, velocity in m/s).
        cells_json: str = '[]',
        manager=None,
    ):
        self.name = name
        self.simulation_run_ref = simulation_run_ref
        self.step = step
        self.time = time
        self.cells_json = cells_json
