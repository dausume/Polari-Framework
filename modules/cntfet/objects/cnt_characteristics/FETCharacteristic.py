"""
@module cntfet.objects.cnt_characteristics.FETCharacteristic

Row class FETCharacteristic of the cntfet module — one class per file (design §7), split
from cnt_characteristics_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FETCharacteristic(treeObject):
    @treeObjectInit
    def __init__(
        self,
        name: str = '',            # kebab key
        display_name: str = '',
        order: int = 0,
        group: str = '',           # iv | switching | transport | fields | quality
        description: str = '',     # the physics
        performance_meaning: str = '',
        equation: str = '',
        related_states_json: str = '[]',
        related_regimes_json: str = '[]',
        related_terms_json: str = '[]',
        views_json: str = '[]',    # [{kind, graphName|componentName|simSpaceName, dataPath, title, why}]
        # fp-6: input | output | transfer | structure — how a device
        # datasheet organises characteristics (Dustin 2026-08-27)
        category: str = '',
        # fp-6: the average-person explanation (no equations)
        explain: str = '',
        citations_json: str = '[]',
        fidelity: str = '',
        origin: str = 'seeded',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.group = group
        self.description = description
        self.performance_meaning = performance_meaning
        self.equation = equation
        self.related_states_json = related_states_json
        self.related_regimes_json = related_regimes_json
        self.related_terms_json = related_terms_json
        self.views_json = views_json
        self.category = category
        self.explain = explain
        self.citations_json = citations_json
        self.fidelity = fidelity
        self.origin = origin
        self.notes = notes
        self.is_prior = is_prior
