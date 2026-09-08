"""
@module cntfet.objects.cnt_taxonomy.ComplementaryPair

Row class ComplementaryPair of the cntfet module — one class per file (design §7), split
from cnt_taxonomy_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ComplementaryPair(treeObject):
    """An n ↔ p device pair as a row: the logic of why they are
    complementary, the conditions (data) `check_pair` evaluates."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        n_device: str = '',
        p_device: str = '',
        logic: str = '',
        # JSON list of {name, expr, why}
        conditions_json: str = '[]',
        how_it_helps: str = '',
        status: str = 'declared',
        notes: str = '',
        origin: str = 'seeded',
        manager=None,
    ):
        self.name = name
        self.n_device = n_device
        self.p_device = p_device
        self.logic = logic
        self.conditions_json = conditions_json
        self.how_it_helps = how_it_helps
        self.status = status
        self.notes = notes
        self.origin = origin
