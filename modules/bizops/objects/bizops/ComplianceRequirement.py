"""
@module bizops.objects.bizops.ComplianceRequirement

Row class ComplianceRequirement of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ComplianceRequirement(treeObject):
    """One legal/market/voluntary requirement that gates SELLING a
    kind of product in a CONTEXT (general goods, food-contact,
    marketed-for-children, plant-safe claim...). required_level
    names the attainment rung that satisfies it. NOT LEGAL ADVICE —
    reference_note points at the source, verify locally."""

    @treeObjectInit
    def __init__(self, name='', display_name='', kind='legal-mandatory',
                 applies_context='general-goods', required_level='',
                 requirement='', reference_note='', is_prior=True,
                 provenance_id='biz-4', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: legal-mandatory | market-rule | voluntary-standard.
        self.kind = kind
        #: The sale context this gates (a claim or market).
        self.applies_context = applies_context
        #: COMPLIANCE_LEVELS rung that satisfies it.
        self.required_level = required_level
        self.requirement = requirement
        self.reference_note = reference_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
