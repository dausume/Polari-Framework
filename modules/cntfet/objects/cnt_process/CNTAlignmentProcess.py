"""
@module cntfet.objects.cnt_process.CNTAlignmentProcess

Row class CNTAlignmentProcess of the cntfet module — one class per file (design §7), split
from cnt_process_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CNTAlignmentProcess(treeObject):
    """Tube-axis alignment: angle spread. A misaligned tube's
    effective channel lengthens by 1/cos(theta)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        process_set: str = '',
        manufacturing_regime: str = '',
        angle_sigma_deg: float = 0.0,
        source: str = '',
        confidence: str = 'low',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.process_set = process_set
        self.manufacturing_regime = manufacturing_regime
        self.angle_sigma_deg = angle_sigma_deg
        self.source = source
        self.confidence = confidence
        self.notes = notes
