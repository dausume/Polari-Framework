"""
@cross-cutting
@module simulations.pendulum_string_sim_state
@tags @xc:bindings, @xc:render-2d

PendulumStringSimState — one row per persisted timestep of the pendulum's
string. The string visually anchors the bob to the pivot; this class
tracks the bob endpoint and (currently approximated) tension. Paired
with PendulumBobSimState under the same `simulation_run_ref` and `time`
grid so the viewer's scrubber animates both in lockstep.

Why a second SimState class instead of widening PendulumBobSimState:
each sub-system that has its own variables, units, and lifecycle gets
its own State class. The pendulum's bob and its string are conceptually
distinct (different physical roles, different units), and the
visualization rendering them is also distinct — the bob is a point
shape, the string is a connection-mode binding. Splitting now sets the
pattern for sims with many cooperating sub-systems (e.g. multi-body,
cell-population, network).

Tension is the magnitude of the string force pulling the bob toward the
pivot at this instant (a real solver would expose this; the seed
approximates it as m·g·cos θ + m·L·ω² — the centripetal + radial-gravity
contribution).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.seed_data (200-row precomputed trajectory)
  - SimSpace2D binding (renders a connection from pivot (0,0) to bob)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PendulumStringSimState(treeObject):
    """State snapshot of a pendulum's string at one recorded timestep.

    Mirrors PendulumBobSimState's row identity convention; the binding
    that renders it uses `kind: 'connection'` with the source at the
    pivot (0,0 constant) and the target at (bob_x, bob_y).
    """

    simulation_definition_name = 'pendulum-2d'

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        simulation_run_ref: str = '',
        step: int = 0,
        time: float = 0.0,
        # Bob endpoint — identical to PendulumBobSimState.x/y; recorded
        # on this class too so the connection-mode binding can resolve
        # endpoints from a single row (no cross-class join needed).
        bob_x: float = 0.0,
        bob_y: float = 0.0,
        # String tension in newtons. Centripetal + radial-gravity
        # contribution; sign is positive (the string pulls the bob in).
        tension: float = 0.0,
        manager=None,
    ):
        self.name = name
        self.simulation_run_ref = simulation_run_ref
        self.step = step
        self.time = time
        self.bob_x = bob_x
        self.bob_y = bob_y
        self.tension = tension
