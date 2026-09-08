"""
@module bizops.objects.bizops.BusinessProfile

Row class BusinessProfile of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BusinessProfile(treeObject):
    """A LIVE business: which model it runs, which rung it is on,
    which capabilities it actually has today."""

    @treeObjectInit
    def __init__(self, name='', display_name='',
                 business_model_ref='', current_stage='',
                 headcount=1, weekly_hours=10.0,
                 capabilities_json='[]', region_note='',
                 lead_limit_days=30, readiness_sold_threshold=1,
                 is_prior=True, provenance_id='biz-1', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.business_model_ref = business_model_ref
        self.current_stage = current_stage
        self.headcount = headcount
        self.weekly_hours = weekly_hours
        self.capabilities_json = capabilities_json
        self.region_note = region_note
        #: The advance-order promise ceiling (Dustin: default one
        #: month, ADJUSTABLE) — quotes beyond it refuse honestly.
        self.lead_limit_days = lead_limit_days
        #: Units a variant must have MADE AND SOLD before it may
        #: escalate (advance orders etc). Default 1, adjustable.
        self.readiness_sold_threshold = readiness_sold_threshold
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
