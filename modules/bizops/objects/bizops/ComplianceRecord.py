"""
@module bizops.objects.bizops.ComplianceRecord

Row class ComplianceRecord of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from bizops.objects.bizops._shared import COMPLIANCE_LEVELS

class ComplianceRecord(treeObject):
    """What a business has actually ATTAINED for one requirement on
    one product variant: theoretical-pass (analysis says it should
    pass) -> self-test-pass (we tested it ourselves) ->
    certified-third-party-pass. Levels are earned by evidence rows,
    never declared bare."""

    @treeObjectInit
    def __init__(self, name='', business_ref='', variant='',
                 requirement_ref='', level='unassessed',
                 evidence_note='', tested_at='', expires_note='',
                 is_prior=False, provenance_id='biz-4', notes='',
                 manager=None):
        self.name = name
        self.business_ref = business_ref
        self.variant = variant
        self.requirement_ref = requirement_ref
        self.level = (level if level in COMPLIANCE_LEVELS
                      else 'unassessed')
        self.evidence_note = evidence_note
        self.tested_at = tested_at
        self.expires_note = expires_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
