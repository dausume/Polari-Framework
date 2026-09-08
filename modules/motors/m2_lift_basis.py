"""
@module motors.m2_lift_basis

m2-5: THE LIFT PROOF — the positioning proof's analog for a rung
whose product is FORCE HELD OVER TIME. The target device is the
crucible hoist (manufacturing-devices/crucible-hoist, powered-by
electric-motors/m2-pm-rotor): "lands on the commanded position"
becomes "gets a full crucible off the floor, and keeps it there
when the power goes away."

Requirements are ROWS (CrucibleHoistRequirement): crucible mass,
drum radius, worm ratio, worm efficiency, pulley advantage, lift
speed — every one a NAMED PRIOR carrying the measurement that
would replace it.

THE PROOF drives the m2-1 solver under the reflected hoist load
and asks whether the rotor stays IN STEP with the 1.5 drive
margin. Two facts make it different from M1's:

1. THE TORQUE DEMAND IS COMPUTED TWICE — down the chain of ratios
   and through the power balance — and the two must agree to
   1e-9. They agree analytically, which is the point: the check
   catches implementation drift, and it also shows the assumed
   LIFT SPEED cancelling out of the torque entirely. Speed sets
   power and time; it does not set whether the thing lifts.

2. HOLDING IS NOT THE MOTOR'S JOB. A worm at ~0.4 efficiency is
   lossy, and lossy is exactly why it self-locks: the load cannot
   drive the worm backwards. So the crucible stays up with the
   power off because of GEOMETRY, and never because the motor
   cogs — the m2-1 model predicts zero cogging by construction
   and this payload refuses to borrow any.

@consumers motors.motor_api (/api/motors/m2-lift-proof),
motors.m2_views_seed (sections), polariServer seed pass (seed_m2_hoist)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/m2_lift/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import math
from objectTreeDecorators import treeObject, treeObjectInit
from composition.custom.data_refs import rows
from composition.custom.seed_upsert import upsert_seed_pairs
from motors.custom.m2_rotation import (
    NO_COGGING_FACT, pull_out_load_limit, rotation_sim,
)

from motors.objects.m2_lift._shared import G, LIFT_MARGIN, M2_DESIGN, PROV, SEED_HOIST_REQUIREMENTS, _req, hoist_report, lift_proof  # noqa: F401
from motors.objects.m2_lift.CrucibleHoistRequirement import CrucibleHoistRequirement  # noqa: F401

from composition.custom.seed_upsert import upsert_seed_pairs

def seed_m2_hoist(manager):
    return upsert_seed_pairs(manager, [
        ('CrucibleHoistRequirement', CrucibleHoistRequirement,
         SEED_HOIST_REQUIREMENTS),
    ], tag='M2HoistSeed')
