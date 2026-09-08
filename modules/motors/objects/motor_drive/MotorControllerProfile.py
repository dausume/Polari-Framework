"""
@module motors.objects.motor_drive.MotorControllerProfile

Row class MotorControllerProfile of the motors module — one class per file (design §7), split
from motor_drive_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from motors.objects.motor_drive._shared import CONTROLLER_BOARDS

class MotorControllerProfile(treeObject):
    @treeObjectInit
    def __init__(self, name='', display_name='',
                 board='simplefoc-shield-v2', sensor='as5600-i2c',
                 supply_voltage_v=12.0, current_limit_a=1.0,
                 voltage_limit_v=6.0, velocity_limit_rad_s=20.0,
                 item_ref='simplefoc-driver-board',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.board = (board if board in CONTROLLER_BOARDS
                      else 'simplefoc-shield-v2')
        self.sensor = sensor
        self.supply_voltage_v = supply_voltage_v
        self.current_limit_a = current_limit_a
        self.voltage_limit_v = voltage_limit_v
        self.velocity_limit_rad_s = velocity_limit_rad_s
        #: supplychain vocabulary — the mag-1 citations price it.
        self.item_ref = item_ref
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
