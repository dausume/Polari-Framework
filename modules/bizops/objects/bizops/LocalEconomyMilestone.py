"""
@module bizops.objects.bizops.LocalEconomyMilestone

Row class LocalEconomyMilestone of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LocalEconomyMilestone(treeObject):
    """One rung of the LOCAL ECONOMY track toward a functioning
    local economic baseline (the OSEB made operational). Status is
    DERIVED from live rows by kind — never hand-flipped."""

    @treeObjectInit
    def __init__(self, name='', display_name='', track_order=0,
                 kind='', target_ref='', description='',
                 is_prior=True, provenance_id='biz-1', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.track_order = track_order
        #: local-available-source-for | makeable-intermediary |
        #: mutual-loop-exists | business-at-stage | reclaim-active |
        #: crush-loop-logged — each evaluated against live tables.
        self.kind = kind
        self.target_ref = target_ref
        self.description = description
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
