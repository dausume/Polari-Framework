"""
@module cntfet.objects.cnt.CNTContact

Row class CNTContact of the cntfet module — one class per file (design §7), split
from cnt_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CNTContact(treeObject):
    """Contacts as their OWN object (D9: Rc never folds into
    mobility). rc_ohm = per-terminal series resistance PRIOR;
    rq_floor_ohm = the derived quantum floor it can never beat."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        metal: str = 'Pd',
        rc_ohm: float = 5500.0,
        rc_source: str = '',
        rc_confidence: str = 'medium',
        rq_floor_ohm: float = 0.0,
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.metal = metal
        self.rc_ohm = rc_ohm
        self.rc_source = rc_source
        self.rc_confidence = rc_confidence
        self.rq_floor_ohm = rq_floor_ohm
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes
