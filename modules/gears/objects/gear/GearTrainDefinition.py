"""
@module gears.objects.gear.GearTrainDefinition

Row class GearTrainDefinition of the gears module — one class per file (design §7), split
from gear_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from gears.objects.gear._shared import TOLERANCE_TIERS

class GearTrainDefinition(treeObject):
    """One drivetrain: the unit that solves. Input torque/speed may
    come from a motor row (gr-5 splice) or be stated directly for
    teaching/sizing."""

    @treeObjectInit
    def __init__(self, name='', display_name='', description='',
                 input_shaft='', output_shaft='',
                 input_torque_nm=0.0, input_speed_rpm=0.0,
                 motor_design_ref='', tolerance_tier='T0',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.input_shaft = input_shaft
        self.output_shaft = output_shaft
        #: Stated drive, used when no motor is referenced.
        self.input_torque_nm = input_torque_nm
        self.input_speed_rpm = input_speed_rpm
        #: gr-5: when set, the motor's own torque curve drives the
        #: train and the parity watermarks travel through.
        self.motor_design_ref = motor_design_ref
        self.tolerance_tier = (tolerance_tier
                               if tolerance_tier in TOLERANCE_TIERS
                               else 'T0')
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
