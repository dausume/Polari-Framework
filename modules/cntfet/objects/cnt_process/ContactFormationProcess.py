"""
@module cntfet.objects.cnt_process.ContactFormationProcess

Row class ContactFormationProcess of the cntfet module — one class per file (design §7), split
from cnt_process_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ContactFormationProcess(treeObject):
    """Contact resistance spread (D9 stays first-class in
    variability too: Rc gets ITS OWN distribution, never folded
    into mobility spread). Lognormal — Rc is positive and
    right-skewed in practice."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        process_set: str = '',
        manufacturing_regime: str = '',
        rc_median_ohm: float = 5500.0,
        rc_sigma_ln: float = 0.2,
        min_contact_length_nm: float = 20.0,
        source: str = '',
        confidence: str = 'low',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.process_set = process_set
        self.manufacturing_regime = manufacturing_regime
        self.rc_median_ohm = rc_median_ohm
        self.rc_sigma_ln = rc_sigma_ln
        self.min_contact_length_nm = min_contact_length_nm
        self.source = source
        self.confidence = confidence
        self.notes = notes
