"""
@module motors.objects.motor.MotorVerificationRun

Row class MotorVerificationRun of the motors module — one class per file (design §7), split
from motor_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MotorVerificationRun(treeObject):
    """One verification run — sim or MEASURED (never seeded; runs
    are observed state). For M0 the comparison target is time
    progression itself."""

    @treeObjectInit
    def __init__(self, name='', design_ref='',
                 kind='sim-quasi-static', steps_commanded=0,
                 steps_taken=0, duration_s=0.0,
                 clock_error_s=0.0, notes='', manager=None):
        self.name = name
        self.design_ref = design_ref
        #: 'sim-quasi-static' | 'measured' — only 'measured' rows
        #: count toward made-and-measured.
        self.kind = kind
        self.steps_commanded = steps_commanded
        self.steps_taken = steps_taken
        self.duration_s = duration_s
        #: Accumulated error vs the expected rotation-from-time
        #: (missed steps / rate) — THE clock metric.
        self.clock_error_s = clock_error_s
        self.notes = notes
