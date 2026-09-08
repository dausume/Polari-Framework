"""
@module cntfet.objects.cnt_process.LithographyProcess

Row class LithographyProcess of the cntfet module — one class per file (design §7), split
from cnt_process_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LithographyProcess(treeObject):
    """Feature-size + overlay spread. S3 uses the Lg (feature)
    axis; overlay enters with multi-layer layout work (S7)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        process_set: str = '',
        manufacturing_regime: str = '',
        feature_sigma_nm: float = 1.0,
        overlay_sigma_nm: float = 2.0,
        source: str = '',
        confidence: str = 'low',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.process_set = process_set
        self.manufacturing_regime = manufacturing_regime
        self.feature_sigma_nm = feature_sigma_nm
        self.overlay_sigma_nm = overlay_sigma_nm
        self.source = source
        self.confidence = confidence
        self.notes = notes
