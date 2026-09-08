"""
@module bizops.objects.bizops.QualityCheckRecord

Row class QualityCheckRecord of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class QualityCheckRecord(treeObject):
    """One QA check RUN: which batch, how many passed/failed, what
    the defects were — pass rates derive from these."""

    @treeObjectInit
    def __init__(self, name='', business_ref='', variant='',
                 check_ref='', batch_note='', units_checked=0,
                 units_passed=0, defects_note='', checked_at='',
                 is_prior=False, provenance_id='biz-4', notes='',
                 manager=None):
        self.name = name
        self.business_ref = business_ref
        self.variant = variant
        self.check_ref = check_ref
        self.batch_note = batch_note
        self.units_checked = units_checked
        self.units_passed = units_passed
        self.defects_note = defects_note
        self.checked_at = checked_at
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
