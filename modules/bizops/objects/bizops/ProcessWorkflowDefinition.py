"""
@module bizops.objects.bizops.ProcessWorkflowDefinition

Row class ProcessWorkflowDefinition of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ProcessWorkflowDefinition(treeObject):
    """A generic production workflow (wax-mold printing, geopolymer
    casting in wax molds, ceramic molds from wax masters) with
    volume-scaled labor priors — hours are FLAGGED estimates until
    timed runs replace them."""

    @treeObjectInit
    def __init__(self, name='', display_name='',
                 product_item_ref='', mold_strategy='',
                 hours_per_unit_ref=0.0, hours_per_mold_ref=0.0,
                 passive_hours_per_batch=0.0,
                 volume_exponent=0.667, steps_json='[]',
                 is_prior=True, provenance_id='biz-1', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.product_item_ref = product_item_ref
        #: MOLD_STRATEGY_PRIORS key this workflow rides on.
        self.mold_strategy = mold_strategy
        #: Attended hours per unit at the 1 L reference size.
        self.hours_per_unit_ref = hours_per_unit_ref
        #: Attended hours to MAKE one mold at reference size.
        self.hours_per_mold_ref = hours_per_mold_ref
        #: Unattended time (cure, firing) — gates throughput, not
        #: labor.
        self.passive_hours_per_batch = passive_hours_per_batch
        #: Shell-dominated ops scale ~V^(2/3).
        self.volume_exponent = volume_exponent
        self.steps_json = steps_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
