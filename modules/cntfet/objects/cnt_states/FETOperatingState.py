"""
@module cntfet.objects.cnt_states.FETOperatingState

Row class FETOperatingState of the cntfet module — one class per file (design §7), split
from cnt_states_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.objects.cnt_states._shared import FIDELITY

class FETOperatingState(treeObject):
    """One operating state of a FET as a ROW: its ordering along a
    rising-Vgs sweep, the physics ("why"), and the qualifying
    criteria as data (see module docstring)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        order: int = 0,
        # 'rising' | 'falling' | 'any' — which sweep direction the
        # state is defined on (transition-on vs transition-off)
        direction: str = 'any',
        description: str = '',
        # JSON list of {lhs, op, rhs, why}; lhs/rhs are frame keys
        # (see frame_at) or numbers. ALL must pass.
        criteria_json: str = '[]',
        # the characteristic equation(s) that govern Id here
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
        self.direction = direction
        self.description = description
        self.criteria_json = criteria_json
        self.governing_equation = governing_equation
        self.fidelity = fidelity
        self.origin = origin
        self.notes = notes
        self.is_prior = is_prior
