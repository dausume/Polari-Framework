"""
@module motors.motor_parts_basis

mag-11: THE PER-PART BILL — every physical piece of the motor tied
to the material it is made of, the properties that RESULT from that
choice, and WHAT THE PIECE IS FOR in the clock.

Until now the pieces and the materials lived apart: geometry was
MathShapeDefinition rows, materials were per-SLOT on the design
(rotor_material / stator_material / winding_material), and nothing
said which shape was made of what, how much it weighed, what it
cost, or why it existed. A reader could see a stator plate and a
list of magnetic options and had to join them in their head.

A MotorPartDefinition row makes that join explicit and, more
importantly, carries the FUNCTION — the sentence that says why the
part is in the machine at all. "The window in the stator plate
forces flux around the rotor instead of across it" is not
decoration; it is the reason the part is shaped the way it is, and
it belongs next to the material and the mass.

Everything numeric DERIVES:
  volume    from the part's own MathShapeDefinition (mathshapes
            shape_properties — the SAME geometry the viewer draws
            and the mould would cast, so the mass cannot drift from
            the picture)
  mass      volume x the material's density property
  cost      mass x the cascaded make-or-buy price (supplychain)
and each one REFUSES rather than guessing when its input is absent:
no shape row, no volume; no density, no mass; no cascade, no cost.

@consumers motors.motor_api, motors.motors_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/motor_parts/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit
from magnetics.custom.magnet_analysis import _named, _rows

from motors.objects.motor_parts._shared import PART_FUNCTIONS, PART_REUSE, SEED_MOTOR_PARTS, _UNIT_TO_CM3, _part_volume_cm3, _prop_entry, part_report  # noqa: F401
from motors.objects.motor_parts.MotorPartDefinition import MotorPartDefinition  # noqa: F401
