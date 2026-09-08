"""
@module motors.motor_drive_basis

mag-6: DRIVE AS DATA — SimpleFOC first (Dustin: the open-source FOC
stack IS the v1 controller; rank open-source-non-polari — exactly
what stage 0/1 should buy, not build), FPGA timing = the escalation
rung, named not promised.

- MotorControllerProfile rows: board + firmware params as DATA so a
  design GENERATES its SimpleFOC config snippet (pole pairs from
  the design's own params, AS5600 sensor, current/voltage limits).
- PhaseBindingDefinition rows: motor phase -> shield terminal (the
  level_bridge mirror); the FPGA PWM channel column exists for the
  escalation and stays empty until that rung is real.
- Honesty: M0's Lavet stepper needs NO FOC (a 1 Hz alternating
  pulse source drives it — 555/Arduino class); asking for its FOC
  config REFUSES saying exactly that. Hardware-facing rows are
  knobs + suggestions, never auto-acting; simulation-only until
  hardware tiers say otherwise.

@consumers motors.motor_api, polariServer
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/motor_drive/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from magnetics.custom.magnet_analysis import _named, _rows

from motors.objects.motor_drive._shared import CONTROLLER_BOARDS, SEED_CONTROLLER_PROFILES, SEED_PHASE_BINDINGS, simplefoc_config  # noqa: F401
from motors.objects.motor_drive.MotorControllerProfile import MotorControllerProfile  # noqa: F401
from motors.objects.motor_drive.PhaseBindingDefinition import PhaseBindingDefinition  # noqa: F401
