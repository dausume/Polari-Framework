"""
@module foodstate.objects.food_contracts.FoodDomainContract

Row class FoodDomainContract of the foodstate module — one class per file (design §7), split
from food_contracts_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FoodDomainContract(treeObject):
    """One property domain's contract: the quantities a FoodState
    answers there, each with its expected provenance rung and why it
    matters. Revisable data — the deliberate alternative to freezing
    per-quantity schemas before the physics basis exists."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # 'composition' | 'structure' | 'physical' | 'chemical' |
        # 'physiological-functional-performance'
        domain: str = '',
        display_name: str = '',
        description: str = '',
        # JSON list of {quantity, unit, expected_provenance, why}.
        contract_json: str = '[]',
        # Which pspp EvidenceMethod rows quantities here may cite.
        evidence_methods_json: str = '[]',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.domain = domain
        self.display_name = display_name
        self.description = description
        self.contract_json = contract_json
        self.evidence_methods_json = evidence_methods_json
        self.provenance_id = provenance_id
        self.notes = notes
