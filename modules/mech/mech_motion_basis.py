"""
@module mech.mech_motion_basis

mxc-4 (MECH_FREECAD_INTERCHANGE_PLAN §3.5, §9.1, D-mxc-4, D-mxc-11): loads,
motion cases, runs and their per-step state as ROWS, over ONE 1-DOF
rigid-body engine (mech.custom.motion_engine) that is linear AND rotary.
The drawer is the first consumer; the M1 printer axis (mxc-8) and the
clock rotor (mxc-7) call the same engine with their own model dicts.

Honesty pinned here so it travels on every payload:
- rigid body, one degree of freedom, no compliance, no backlash dynamics;
- friction coefficients and ratings are KNOBS until a measured run lands;
- FreeCAD Motion is the kinematic reference (position formula only) —
  it knows no mass, friction or force, and (verified 2026-11-03) does
  not honour the joint's LengthMax either;
- stress / deflection are materialsScience's FEM (D-mxc-7): a run only
  NAMES a FEMModelDefinition in `fem_model_ref`.

@consumers mech.custom.motion_runs, mech.mech_motion_seed, polariServer
"""
# The classes live one-per-file under objects/motion/; this file re-exports
# them (design §7) and holds what they share.
from objectTreeDecorators import treeObject, treeObjectInit  # noqa: F401

from mech.objects.motion._shared import (  # noqa: F401
    CHECK_KINDS, DRIVE_KINDS, ENGINE_KINDS, LOAD_KINDS, MOTION_SIM_DEF,
    RUNNING_GEAR, SIGNALS,
)
from mech.objects.motion.MechLoadCase import MechLoadCase  # noqa: F401
from mech.objects.motion.MechMotionCase import MechMotionCase  # noqa: F401
from mech.objects.motion.MechMotionRun import MechMotionRun  # noqa: F401
from mech.objects.motion.MechMotionSimState import MechMotionSimState  # noqa: F401
from mech.objects.motion.MechMotionVector import MechMotionVector  # noqa: F401
