"""
@module motors.scale_goals_basis

goal-1..3 (MOTOR_GOALS_PLAN): the M0 approach RESTRUCTURED around
GOALS AND CONSTRAINTS. Instead of analysing one fixed movement, a
goal names a TARGET SCALE (wristwatch → desk → wall → large wall →
tower) and a MATERIAL POLICY (locally-made-only / local plus
imported bare wire / anything), and the engine derives what each
known part archetype must deliver — then scores feasibility with
every blocker NAMED.

The physics is the arc's own, reused not restated:
- coil voltage = MMF·ρ·MTL/A_copper — TURNS CANCEL (mag-25), so the
  cell picks the gauge floor at every scale;
- turns = f·W/A_wound — the WINDOW picks the gauge ceiling, because
  battery life needs turns and turns need window;
- the wire LADDER rung follows from the gauge (wire_ladder), and
  the material policy says which rungs we may assume;
- hand imbalance torque m·g·r (eq-hand-imbalance-torque) is what
  scales the MMF prior between scales — stated as a CRUDE scaling,
  never silently.

Scale rows and goal rows are DATA (knobs); scoring weights are on
the goal; the engine only derives, refuses, and suggests.

@consumers motors.motor_api, motors.motors_selftest,
polariServer seed passes (via seed_scale_goals — the arch-1 upsert
path, never the legacy insert-only list)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/scale_goals/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import math
from objectTreeDecorators import treeObject, treeObjectInit
from composition.custom.data_refs import resolve_named, rows
from composition.design_matrix_basis import matrix_report
from composition.custom.part_roles import role_viability
from composition.custom.seed_upsert import upsert_seed_pairs
from motors.physics_equations_seed import evaluate_named
from motors.custom.simple_first import AWG_MM, ENAMEL_MM, RHO_CU, rung_for

from motors.objects.scale_goals._shared import G, HOURS_PER_YEAR, MATERIAL_POLICIES, MOVEMENT_SLOTS, PROV, SCRAMBLE_FILL, SEED_CLOCK_SCALES, SEED_MOTOR_GOALS, SWEEP_EQUATIONS, TOLERANCE_RUNGS, _WEIGHTS, _eval, _local_options, _rung_leq, gauge_sweep, goal_feasibility, hand_imbalance_nm, scale_study, screen_slot  # noqa: F401
from motors.objects.scale_goals.ClockScaleDefinition import ClockScaleDefinition  # noqa: F401
from motors.objects.scale_goals.MotorGoalSpec import MotorGoalSpec  # noqa: F401

from composition.custom.seed_upsert import upsert_seed_pairs

def seed_scale_goals(manager):
    """Through the arch-1 upsert path — changed priors reach live
    rows."""
    return upsert_seed_pairs(manager, [
        ('ClockScaleDefinition', ClockScaleDefinition,
         SEED_CLOCK_SCALES),
        ('MotorGoalSpec', MotorGoalSpec, SEED_MOTOR_GOALS),
    ], tag='ScaleGoalsSeed')
