"""
@module cntfet.objects.cnt_regimes.FETRegime

Row class FETRegime of the cntfet module — one class per file (design §7), split
from cnt_regimes_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.objects.cnt_regimes._shared import FIDELITY

class FETRegime(treeObject):
    """One IV regime of a FET as a ROW: ordering (precedence), the
    physics ("why"), the governing drive law, and the qualifying
    criteria as data over `regime_frame` (see module docstring)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        order: int = 0,
        description: str = '',
        # JSON list of {lhs, op, rhs, why}; lhs/rhs are frame keys
        # (see regime_frame) or numbers. ALL must pass.
        criteria_json: str = '[]',
        governing_equation: str = '',
        fidelity: str = FIDELITY,
        origin: str = 'seeded',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.description = description
        self.criteria_json = criteria_json
        self.governing_equation = governing_equation
        self.fidelity = fidelity
        self.origin = origin
        self.notes = notes
        self.is_prior = is_prior
