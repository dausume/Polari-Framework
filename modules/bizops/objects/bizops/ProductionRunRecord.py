"""
@module bizops.objects.bizops.ProductionRunRecord

Row class ProductionRunRecord of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ProductionRunRecord(treeObject):
    """A TIMED production run — the 'proper record of how long it
    takes to make things'. These rows are what unlock advance
    orders: customer lead-time promises are computed from MEASURED
    rates only, never from planning priors."""

    @treeObjectInit
    def __init__(self, name='', business_ref='', variant='',
                 unit_volume_l=1.0, units_made=0,
                 attended_hours=0.0, molds_made=0,
                 mold_hours=0.0, run_note='', is_prior=False,
                 provenance_id='biz-2', notes='', manager=None):
        self.name = name
        self.business_ref = business_ref
        self.variant = variant
        self.unit_volume_l = unit_volume_l
        self.units_made = units_made
        #: Actual attended hours for the units (excl. mold making).
        self.attended_hours = attended_hours
        self.molds_made = molds_made
        self.mold_hours = mold_hours
        self.run_note = run_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
