"""
@cross-cutting
@module simulations.material_condensation_state
@tags @xc:bindings

MaterialCondensationState — one persisted timestep of the MATERIAL
CONDENSATION space: the first-principles stage of the multi-scale
pendulum composition (Milestone B).

The simulation models a candidate process point: hold a substance at a
target temperature and pressure, relax the sample's temperature toward
the target (Newtonian cooling), and check the phase against a simplified
pressure-shifted melting line (Clausius-Clapeyron-flavored):

    T_m(P) = melt_temp_ref + melt_slope_k_per_pa * (P - 101325)
    solid  = T < T_m(P)
    rho(T) = density_solid_ref * (1 - thermal_expansion * (T - T_ref))
    ball_mass = rho * (4/3) * pi * ball_radius_target^3

The melting line T_m(P) is ALSO persisted per step as `melt_temp` so
graphs can plot temperature against it and show the solidification
crossing as data (the graph engine has no reference-line feature —
the melt line is a computed state field, per the explainability plan).

All of it is authored as no-code MatrixEquationOperations (see
material_space_seed). SUBSTANCE parameters (melt_temp_ref, slope,
density, expansion) and PROCESS parameters (target_temp, pressure_pa —
the solution-search candidates) live in the SimulationDefinition's
parameters_json and per-run parameter overrides, NOT on the row.

The stage's gate (`solid-ball-achievable`) reads the latest row: the
stage is achieved when phase_solid is 1, and the proven ball's
mass/radius/density flow into the pendulum's initial conditions via the
stage `derive` map — Dustin's canonical first-principles flow.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.material_space_seed (sim def + step solution + gate)
  - simulations.multi_scale_seed (the material-precondition stage)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class MaterialCondensationState(treeObject):
    """One persisted timestep of the material condensation process.

    Identity is composite on (simulation_run_ref, step); the runner names
    rows "<run>-material-condensation-<step>". Membership in the
    material-condensation simulation is declared by the class attribute.
    """

    simulation_definition_name = 'material-condensation'

    # t=0: the sample starts at ambient temperature, phase/density/ball
    # not yet evaluated (the first step computes them).
    # NOTE (migration): `melt_temp` was added 2026-07-05. Existing DB
    # volumes gain the column at boot via managedDB._syncTableColumns
    # (ALTER TABLE ADD COLUMN); pre-upgrade rows read back NULL → the
    # field default (0.0), so the melt-line series simply starts at the
    # first post-upgrade step.
    default_initial_field_values = {
        'temperature': 293.15,
        'melt_temp': 0.0,
        'phase_solid': 0.0,
        'density': 0.0,
        'ball_mass': 0.0,
        'ball_radius': 0.0,
    }

    # Everything is written fresh each step by the Complete solution and
    # read by the gate + downstream derive — all core.
    field_save_policy = {
        'temperature': 'core',
        'melt_temp': 'core',
        'phase_solid': 'core',
        'density': 'core',
        'ball_mass': 'core',
        'ball_radius': 'core',
    }

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        simulation_run_ref: str = '',
        step: int = 0,
        time: float = 0.0,
        # Sample temperature (K) — relaxes toward the candidate target.
        temperature: float = 293.15,
        # The pressure-shifted melting line T_m(P) (K) at this step's
        # process pressure — persisted so graphs can plot the sample
        # temperature against it and show the solidification crossing.
        melt_temp: float = 0.0,
        # 1.0 when the sample is below the pressure-shifted melting line
        # (solid), else 0.0. THE quantity the stage gate proves.
        phase_solid: float = 0.0,
        # Density at the current temperature (kg/m^3).
        density: float = 0.0,
        # The ball the substance would form at ball_radius_target (kg, m).
        ball_mass: float = 0.0,
        ball_radius: float = 0.0,
        manager=None,
    ):
        self.name = name
        self.simulation_run_ref = simulation_run_ref
        self.step = step
        self.time = time
        self.temperature = temperature
        self.melt_temp = melt_temp
        self.phase_solid = phase_solid
        self.density = density
        self.ball_mass = ball_mass
        self.ball_radius = ball_radius
