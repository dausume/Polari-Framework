"""
@module motors.objects.m2_lift.CrucibleHoistRequirement

Row class CrucibleHoistRequirement of the motors module — one class per file (design §7), split
from m2_lift_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CrucibleHoistRequirement(treeObject):
    """One hoist requirement: a value with units, a basis, and
    (for priors) the measurement that would replace it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', value=0.0,
                 unit='', basis='', replaces_with='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.value = value
        self.unit = unit
        #: WHERE the number comes from — a citation, a standard
        #: part, or an honestly named guess.
        self.basis = basis
        #: The measurement that retires the prior (bench seam).
        self.replaces_with = replaces_with
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
