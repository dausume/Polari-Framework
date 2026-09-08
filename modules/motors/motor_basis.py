"""
@module motors.motor_basis

SECTION C (mag-5 core): MOTORS AS A LADDER OF BUILDABLE SAMPLES
(Dustin 2026-07-29: "start as simple as we can and go to more
advanced, both in terms of tolerances and in terms of samples
people can build", end goal = the dual-stator axial-flux machine).

- MotorDesignDefinition rows: one motor design per row, carrying
  its LADDER RUNG (M0..M3), its §2c tolerance tier (T0..T3), its
  topology + parameters, the materials BY CATALOG REFERENCE
  (mag-2r roles decide viability; gates/watermarks travel), and
  build_requirements_json — the builder-facing sample spec (tools,
  materials, skills, rough hours), easiest rung first.
- MotorVerificationRun rows: NEVER seeded — observed state only.
  M0's verification method is TIME ITSELF: command N pulses at
  1 Hz, count steps taken, compare accumulated rotation against
  wall-clock progression; missed steps over hours ARE the quality
  metric. Measured runs are what earn made-and-measured.

@consumers motors.custom.motor_designer, motors.motor_api, polariServer
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/motor/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from motors.objects.motor._shared import LADDER_RUNGS, MOTOR_TOPOLOGIES, SEED_MOTOR_DESIGNS, TOLERANCE_TIERS  # noqa: F401
from motors.objects.motor.MotorDesignDefinition import MotorDesignDefinition  # noqa: F401
from motors.objects.motor.MotorVerificationRun import MotorVerificationRun  # noqa: F401
