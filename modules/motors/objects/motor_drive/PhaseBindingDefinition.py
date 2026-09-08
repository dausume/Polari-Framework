"""
@module motors.objects.motor_drive.PhaseBindingDefinition

Row class PhaseBindingDefinition of the motors module — one class per file (design §7), split
from motor_drive_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PhaseBindingDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', design_ref='', phase='A',
                 shield_terminal='', fpga_pwm_channel='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.design_ref = design_ref
        self.phase = phase
        self.shield_terminal = shield_terminal
        #: EMPTY until the FPGA escalation rung is real — named,
        #: not promised (hardware architecture seam).
        self.fpga_pwm_channel = fpga_pwm_channel
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
