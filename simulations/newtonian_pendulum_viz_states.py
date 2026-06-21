"""
@cross-cutting
@module simulations.newtonian_pendulum_viz_states
@tags @xc:bindings, @xc:render-3d

Visualization companion state classes for the Newtonian pendulum. None
of these carry physics — each is a thin per-timestep render record that
reads the bob's just-computed vectors (via the runner's cross-class
`depends_on` context) and lays out one 3D connection:

  * NewtonianPendulumRodSimState           — the rigid rod, pivot → bob.
  * NewtonianPendulumGravityVectorSimState — red arrow: gravity force on the bob.
  * NewtonianPendulumNetVectorSimState     — green arrow: net force on the bob.

Each renders as a CONNECTION binding (source → target). The force arrows
draw from the bob position to `bob + viz_force_scale · F`. Splitting each
vector into its own class is what lets several arrows coexist on one bob
without colliding on the connection id (`{class}:{inst}`); wind's arrow
joins later as a fourth class with the same shape.

NOTE: every class defines its OWN `__init__` (no shared base). The
framework's typing/registration discovers fields from the concrete class's
constructor, so a shared base `__init__` left the force-vector classes
without discoverable fields — they registered but produced no usable rows
(the rod, which already had its own __init__, rendered fine). Matching the
one-__init__-per-class convention used by every other *SimState fixes it.

@consumers
  - polariServer.defClassList
  - simulations.seed_data (step solutions + 3D connection bindings)
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


# Connection arrows share the src/tip schema; only the t=0 tip differs
# (gravity points straight down; net points along the resultant).
_FORCE_VECTOR_SAVE_POLICY = {
    'src_x': 'core', 'src_y': 'core', 'src_z': 'core',
    'tip_x': 'core', 'tip_y': 'core', 'tip_z': 'core',
}


class NewtonianPendulumGravityVectorSimState(treeObject):
    """Red arrow — gravity force on the bob. t=0 tip = bob + 0.03·(0,−9.81,0)."""

    simulation_definition_name = 'newtonian-pendulum-3d'
    field_save_policy = _FORCE_VECTOR_SAVE_POLICY
    default_initial_field_values = {
        'src_x': 0.5, 'src_y': -0.8660254037844387, 'src_z': 0.0,
        'tip_x': 0.5, 'tip_y': -1.1603254037844387, 'tip_z': 0.0,
    }

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        simulation_run_ref: str = '',
        step: int = 0,
        time: float = 0.0,
        src_x: float = 0.0,
        src_y: float = 0.0,
        src_z: float = 0.0,
        tip_x: float = 0.0,
        tip_y: float = 0.0,
        tip_z: float = 0.0,
        manager=None,
    ):
        self.name = name
        self.simulation_run_ref = simulation_run_ref
        self.step = step
        self.time = time
        self.src_x = src_x
        self.src_y = src_y
        self.src_z = src_z
        self.tip_x = tip_x
        self.tip_y = tip_y
        self.tip_z = tip_z


class NewtonianPendulumNetVectorSimState(treeObject):
    """Green arrow — net force on the bob. t=0 tip = bob + 0.03·(−4.2479,−2.4527,0)."""

    simulation_definition_name = 'newtonian-pendulum-3d'
    field_save_policy = _FORCE_VECTOR_SAVE_POLICY
    default_initial_field_values = {
        'src_x': 0.5, 'src_y': -0.8660254037844387, 'src_z': 0.0,
        'tip_x': 0.3725644, 'tip_y': -0.9396072, 'tip_z': 0.0,
    }

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        simulation_run_ref: str = '',
        step: int = 0,
        time: float = 0.0,
        src_x: float = 0.0,
        src_y: float = 0.0,
        src_z: float = 0.0,
        tip_x: float = 0.0,
        tip_y: float = 0.0,
        tip_z: float = 0.0,
        manager=None,
    ):
        self.name = name
        self.simulation_run_ref = simulation_run_ref
        self.step = step
        self.time = time
        self.src_x = src_x
        self.src_y = src_y
        self.src_z = src_z
        self.tip_x = tip_x
        self.tip_y = tip_y
        self.tip_z = tip_z
