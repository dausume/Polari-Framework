"""
@module bizops.objects.bizops.BusinessStageDefinition

Row class BusinessStageDefinition of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BusinessStageDefinition(treeObject):
    """One rung of the business ladder: headcount, committed hours,
    sales channels and sourcing posture AT that rung."""

    @treeObjectInit
    def __init__(self, name='', stage_index=0, display_name='',
                 headcount=1, weekly_hours=10.0,
                 time_commitment='off-time',
                 work_mode='order-driven',
                 sales_channels_json='[]',
                 sourcing_posture='retail-available',
                 capabilities_json='[]', is_prior=True,
                 provenance_id='biz-1', notes='', manager=None):
        self.name = name
        self.stage_index = stage_index
        self.display_name = display_name
        self.headcount = headcount
        #: Productive hours/week the stage can actually field.
        self.weekly_hours = weekly_hours
        self.time_commitment = time_commitment
        #: pre-staged-speculative (stage 0: produce what you can
        #: afford, VARY the products, then try to sell) | mixed |
        #: order-driven.
        self.work_mode = work_mode
        self.sales_channels_json = sales_channels_json
        #: retail-available | bulk | local-partners |
        #: self-made-intermediaries — where inputs come from.
        self.sourcing_posture = sourcing_posture
        self.capabilities_json = capabilities_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
