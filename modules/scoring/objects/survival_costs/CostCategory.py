"""
@module scoring.objects.survival_costs.CostCategory

Row class CostCategory of the scoring module — one class per file (design §7), split
from survival_costs_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CostCategory(treeObject):
    """One walkthrough step: what to enter and how to find it."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('housing').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # CATEGORY_KINDS entry — the classification KNOB.
        kind: str = 'survival',
        # The walkthrough prompt shown to the person.
        guidance: str = '',
        # Concrete examples ('rent, mortgage payment, lot fees').
        examples: str = '',
        # ScoreTerm the entered amounts land under.
        term_name: str = '',
        # Whether the survival baseline is incomplete without it.
        required: bool = True,
        sort_order: int = 100,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.kind = kind
        self.guidance = guidance
        self.examples = examples
        self.term_name = term_name
        self.required = required
        self.sort_order = sort_order
        self.notes = notes
