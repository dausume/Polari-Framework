"""
@module scoring.objects.agreement_policy.AgreementPolicy

Row class AgreementPolicy of the scoring module — one class per file (design §7), split
from agreement_policy_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AgreementPolicy(treeObject):
    """One configurable set of agreement-classification bands."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        direction_bands_json: str = '[]',
        weight_bands_json: str = '[]',
        similarity_bands_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.direction_bands_json = direction_bands_json
        self.weight_bands_json = weight_bands_json
        self.similarity_bands_json = similarity_bands_json
        self.notes = notes
