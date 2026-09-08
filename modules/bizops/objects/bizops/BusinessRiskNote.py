"""
@module bizops.objects.bizops.BusinessRiskNote

Row class BusinessRiskNote of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BusinessRiskNote(treeObject):
    """One risk/danger a new business maker must hear BEFORE it
    bites — attached to a walkthrough step, with severity and the
    mitigation stated plainly. Rows, so the register grows from
    experience."""

    @treeObjectInit
    def __init__(self, name='', step_ref='', severity='medium',
                 risk='', mitigation='', is_prior=True,
                 provenance_id='biz-3', notes='', manager=None):
        self.name = name
        #: Which walkthrough step this belongs to.
        self.step_ref = step_ref
        #: low | medium | high | safety-critical.
        self.severity = severity
        self.risk = risk
        self.mitigation = mitigation
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
