"""
@module motors.m1_positioning_basis

m1-5: THE POSITIONING PROOF — the timekeeping proof's analog for a
rung whose product is POSITION. The target device is the wax
printer's axis (manufacturing-devices/wax-3d-printer, powered-by
electric-motors/m1-switched-reluctance): "keeps time" becomes
"lands on the commanded position through a leadscrew."

Requirements are ROWS (PrinterAxisRequirement): leadscrew lead,
axis load force, drive efficiency, position tolerance — every one
a NAMED prior with the measurement that would replace it. Steps/mm
DERIVES (12 steps/rev from the m1-1 arithmetic, lead from the
row); it is never seeded, because seeding a derivable number is
how two copies drift.

THE PROOF runs the m1-1 solver under the axis's reflected load
torque and turns the step history into a POSITION LEDGER in mm:
- zero missed steps -> every step advances EXACTLY one step angle,
  so the whole error is the one-time REST-BAND offset and it does
  NOT grow with the move (pinned by running the control twice, at
  N and 2N steps: same error, not double). The band itself came
  out of cons-3's exact arc overlap — beta_r - beta_s of flat,
  zero-torque alignment — and it is also the axis's BACKLASH on
  reversal, in mm, from geometry rather than from a gear;
- a missed step is not M0's gentle non-event: with no detent, a
  reluctance machine that misses SLIPS BACKWARD a full pole pitch
  (loss of synchronism, exactly as real stepper datasheets warn) —
  so the weak drive loses MORE than its missed steps, every slip
  is NAMED, and the ledger still balances exactly by two paths
  (final-position delta vs the sum of per-step shortfalls).

THE VERDICT: can this M1, with today's materials, hold the
printer's axis duty — and if not, WHICH knob moves it. The knobs
are QUANTIFIED live (bio-steel stator via material override, gear
reduction ratio derived from the shortfall), never hand-waved.

@consumers motors.motor_api, motors.m1_views_seed (sections),
polariServer seed pass (seed_m1_axis)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/m1_positioning/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import math
from objectTreeDecorators import treeObject, treeObjectInit
from composition.custom.data_refs import rows
from moduleService.seed_upsert import upsert_seed_pairs
from motors.custom.m1_sequencing import (
    STEP_DEG, holding_torque, pull_in_load_limit, sequence_sim,
)

from motors.objects.m1_positioning._shared import M1_DESIGN, PROV, SEED_AXIS_REQUIREMENTS, STEPS_PER_REV, _req, axis_report, positioning_proof  # noqa: F401
from motors.objects.m1_positioning.PrinterAxisRequirement import PrinterAxisRequirement  # noqa: F401

from moduleService.seed_upsert import upsert_seed_pairs

def seed_m1_axis(manager):
    return upsert_seed_pairs(manager, [
        ('PrinterAxisRequirement', PrinterAxisRequirement,
         SEED_AXIS_REQUIREMENTS),
    ], tag='M1AxisSeed')
