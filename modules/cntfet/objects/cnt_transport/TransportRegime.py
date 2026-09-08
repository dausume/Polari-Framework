"""
@module cntfet.objects.cnt_transport.TransportRegime

Row class TransportRegime of the cntfet module — one class per file (design §7), split
from cnt_transport_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.objects.cnt_transport._shared import FIDELITY

class TransportRegime(treeObject):
    """One transport regime as a ROW (the cnt_states shape):
    criteria_json over the transport frame (see transport_frame)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        order: int = 0,
        description: str = '',
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
