"""
@cross-cutting
@module simulations.newtonian_pendulum_viz_states
@tags @xc:bindings, @xc:render-3d

Visualization companion state for the Newtonian pendulum:

  * NewtonianPendulumRodSimState — the rigid rod, pivot → bob.

The rod carries no physics — it's a thin per-timestep render record that
mirrors the bob's just-computed position (via the runner's cross-class
`depends_on` context) and renders as a CONNECTION binding (pivot → bob).

The gravity/net FORCE ARROWS used to be companion classes here too, each a
connection from the bob to `bob + viz_force_scale · F`. They've been replaced
by viz-only "State Projection" `vector` bindings on the bob itself (see
newtonian_pendulum_seed `_NEWTON_BINDINGS`), which read the bob's core
fgrav_*/fnet_* fields directly and draw an arrow — no companion class, rows,
or dependency chain. Wind's arrow will be one more such vector binding.

@consumers
  - polariServer.defClassList
  - simulations.newtonian_pendulum_seed (rod step solution + 3D connection binding)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class NewtonianPendulumRodSimState(treeObject):
    """The rigid rod: a connection from the pivot (origin) to the bob.
    `bob_*` mirrors the bob's 3D position for the current step."""

    simulation_definition_name = 'newtonian-pendulum-3d'

    # t=0: bob at the 30° release point.
    default_initial_field_values = {
        'bob_x': 0.5,
        'bob_y': -0.8660254037844387,
        'bob_z': 0.0,
    }
    field_save_policy = {'bob_x': 'core', 'bob_y': 'core', 'bob_z': 'core'}

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        simulation_run_ref: str = '',
        step: int = 0,
        time: float = 0.0,
        bob_x: float = 0.0,
        bob_y: float = 0.0,
        bob_z: float = 0.0,
        manager=None,
    ):
        self.name = name
        self.simulation_run_ref = simulation_run_ref
        self.step = step
        self.time = time
        self.bob_x = bob_x
        self.bob_y = bob_y
        self.bob_z = bob_z
