"""
@module mech.objects.motion.MechMotionSimState

Row class MechMotionSimState of the mech module — one class per file (design §7).
The per-step state of a 1-DOF motion run — the row `simulations.simulation_series.build_series`
reads (it filters on `simulation_run_ref`, orders by `step`, reads `time`),
exactly as NewtonianPendulumBobSimState is read for the pendulum.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MechMotionSimState(treeObject):
    """One recorded step of the 1-DOF engine. Identity is composite on
    (simulation_run_ref, step); rows are named '<run>-mech-motion-<step>'.
    `q` is mm for a linear joint and rad for a rotary one; `drive`,
    `friction`, `normal`, `side_force` are N (linear) or N·m (rotary)."""

    simulation_definition_name = 'mech-motion-1dof'

    default_initial_field_values = {
        'q': 0.0, 'q_dot': 0.0, 'q_ddot': 0.0, 'drive': 0.0,
        'friction': 0.0, 'normal': 0.0, 'side_force': 0.0,
        'tip_moment_nm': 0.0, 'power_w': 0.0, 'at_limit': False,
    }

    field_save_policy = {
        'q': 'core', 'q_dot': 'core', 'q_ddot': 'core', 'drive': 'core',
        'friction': 'core', 'normal': 'core', 'side_force': 'core',
        'tip_moment_nm': 'core', 'power_w': 'core', 'at_limit': 'core',
    }

    @treeObjectInit
    def __init__(self, name='', simulation_run_ref='', run_ref='',
                 step=0, time=0.0, t_s=0.0, q=0.0, q_dot=0.0,
                 q_ddot=0.0, drive=0.0, friction=0.0, normal=0.0,
                 side_force=0.0, tip_moment_nm=0.0, power_w=0.0,
                 at_limit=False, manager=None):
        self.name = name
        #: core SimulationRun name — what build_series / run_scope filter on.
        self.simulation_run_ref = simulation_run_ref
        #: MechMotionRun name (the mech-side run this step belongs to).
        self.run_ref = run_ref
        self.step = step
        #: Seconds — the field build_series returns as `times`.
        self.time = time
        #: Same value as `time`, under the name the plan uses.
        self.t_s = t_s
        #: Position (mm) or angle (rad).
        self.q = q
        #: mm/s or rad/s.
        self.q_dot = q_dot
        #: mm/s² or rad/s².
        self.q_ddot = q_ddot
        #: Drive force (N) / torque (N·m): applied for a force drive,
        #: REQUIRED for a position or velocity drive (the hand-effort number).
        self.drive = drive
        #: Friction force / torque, signed (opposes motion).
        self.friction = friction
        #: Normal force the friction acts through (N) — or the equivalent
        #: coulomb level for a rotary joint.
        self.normal = normal
        #: Load carried across the joint, perpendicular to its axis (N).
        self.side_force = side_force
        #: Cantilever moment about the slide's support at this extension (N·m).
        self.tip_moment_nm = tip_moment_nm
        #: drive × velocity (W).
        self.power_w = power_w
        #: True on the step a hard stop (joint limit) was hit.
        self.at_limit = at_limit
