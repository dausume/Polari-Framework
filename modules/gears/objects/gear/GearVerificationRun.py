"""
@module gears.objects.gear.GearVerificationRun

Row class GearVerificationRun of the gears module — one class per file (design §7), split
from gear_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class GearVerificationRun(treeObject):
    """A MEASURED run on a real train — never seeded, observed state
    only (the MotorVerificationRun rule). Measured efficiency and
    backlash replace the priors; that replacement is the whole
    point of the ladder."""

    @treeObjectInit
    def __init__(self, name='', train_ref='', kind='sim',
                 measured_ratio=None, measured_efficiency=None,
                 measured_backlash_mm=None, notes='', manager=None):
        self.name = name
        self.train_ref = train_ref
        #: 'sim' | 'measured' — only 'measured' rows count toward
        #: made-and-measured.
        self.kind = kind
        self.measured_ratio = measured_ratio
        self.measured_efficiency = measured_efficiency
        self.measured_backlash_mm = measured_backlash_mm
        self.notes = notes
