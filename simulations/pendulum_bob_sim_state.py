"""
@cross-cutting
@module simulations.pendulum_bob_sim_state
@tags @xc:bindings, @xc:render-2d

PendulumBobSimState — one row per persisted timestep of the pendulum's
bob. This is one of two `*SimState` classes that compose the pendulum-2d
demo (the other being PendulumStringSimState). Splitting the bob and
the string into separate State classes mirrors the framework's
multi-sub-system convention: a SimulationDefinition orchestrates
several State streams that share a SimulationRun and a common time axis.

Reference physics (seed trajectory):
    θ''(t) = −(g/L) sin θ      full ODE (used)
    bob.x  = L sin θ           Cartesian projection
    bob.y  = −L cos θ
    KE     = ½ m L² ω²
    PE     = m g L (1 − cos θ)

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.seed_data (200-row precomputed trajectory)
  - SimSpace2D binding (renders a circle at bob.x / bob.y, time-filtered)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PendulumBobSimState(treeObject):
    """State snapshot of a pendulum's bob at one recorded timestep.

    Identity is composite on (simulation_run_ref, step). The seeder
    generates row names like "<run>-<step>" so the framework's
    name-keyed storage stays uniqueness-friendly.

    Membership in the pendulum-2d simulation is declared by the class
    attribute below; the simulation-detail page reverse-scans for any
    State class whose simulation_definition_name matches.
    """

    # Class-level back-link — read by the simulation-detail page to list
    # participating State classes. Not part of the per-row schema.
    simulation_definition_name = 'pendulum-2d'

    @treeObjectInit
    def __init__(
        self,
        # Row identity (composite (simulation_run_ref, step) is logical;
        # `name` is the framework's storage key — seeder formats it as
        # "<simulation_run_ref>-bob-<step>").
        name: str = '',
        # Which run this row belongs to — matches SimulationRun.name.
        simulation_run_ref: str = '',
        step: int = 0,
        # Continuous time in seconds since simulation start. Drives the
        # viewer's scrubber via the binding's temporal config.
        time: float = 0.0,
        # Integrator state (radians, rad/s). theta = angle from vertical;
        # +ve = swinging to the right when the pendulum's z-axis is up.
        theta: float = 0.0,
        omega: float = 0.0,
        # Cartesian bob position derived from theta. Pre-computed at seed
        # time so the SimSpace binding can read x/y directly.
        x: float = 0.0,
        y: float = 0.0,
        # Conservation monitor — flat on a well-behaved integrator,
        # drifts on a poorly-tuned one. Read it to validate the run.
        energy_total: float = 0.0,
        manager=None,
    ):
        self.name = name
        self.simulation_run_ref = simulation_run_ref
        self.step = step
        self.time = time
        self.theta = theta
        self.omega = omega
        self.x = x
        self.y = y
        self.energy_total = energy_total
