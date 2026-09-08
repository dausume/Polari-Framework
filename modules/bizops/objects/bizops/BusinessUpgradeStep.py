"""
@module bizops.objects.bizops.BusinessUpgradeStep

Row class BusinessUpgradeStep of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from bizops.objects.bizops._shared import UPGRADE_KINDS

class BusinessUpgradeStep(treeObject):
    """One discrete upgrade EDGE: hire a person onto a task, change
    a process, or add a capability — with the evidence gate that
    should be TRUE before taking it (gates are suggestions with
    evidence, never auto-applied)."""

    @treeObjectInit
    def __init__(self, name='', display_name='', from_stage='',
                 to_stage='', kind='process-change',
                 role_or_capability='', evidence_gate='',
                 effects_json='{}', is_prior=True,
                 provenance_id='biz-1', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.from_stage = from_stage
        #: '' = stays on the same stage (capability adds).
        self.to_stage = to_stage
        self.kind = (kind if kind in UPGRADE_KINDS
                     else 'process-change')
        self.role_or_capability = role_or_capability
        #: Plain-language condition the flow report evaluates or
        #: surfaces (e.g. 'backlog exceeds capacity two plans
        #: running').
        self.evidence_gate = evidence_gate
        #: JSON: {weekly_hours_delta, weekly_cost_delta,
        #: capabilities_added: [...]} — what taking the step does.
        self.effects_json = effects_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
