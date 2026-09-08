"""
@module cntfet.objects.cnt_process.CNTPlacementProcess

Row class CNTPlacementProcess of the cntfet module — one class per file (design §7), split
from cnt_process_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CNTPlacementProcess(treeObject):
    """Tube placement: pitch spread + the missing-tube
    probability. At S3's one-tube scope a missing tube IS a dead
    device; pitch matters from the multi-tube arc onward."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        process_set: str = '',
        manufacturing_regime: str = '',
        pitch_mu_nm: float = 0.0,
        pitch_sigma_nm: float = 0.0,
        missing_tube_prob: float = 0.0,
        source: str = '',
        confidence: str = 'low',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.process_set = process_set
        self.manufacturing_regime = manufacturing_regime
        self.pitch_mu_nm = pitch_mu_nm
        self.pitch_sigma_nm = pitch_sigma_nm
        self.missing_tube_prob = missing_tube_prob
        self.source = source
        self.confidence = confidence
        self.notes = notes
