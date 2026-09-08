"""
@module cntfet.objects.cnt_process.GateStackProcess

Row class GateStackProcess of the cntfet module — one class per file (design §7), split
from cnt_process_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class GateStackProcess(treeObject):
    """Gate-stack spread: t_ox, k_ox, and the threshold shift from
    interface/fixed charge (the Vt sigma every real CNT line
    fights)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        process_set: str = '',
        manufacturing_regime: str = '',
        tox_sigma_nm: float = 0.1,
        kox_sigma: float = 0.5,
        vt_sigma_v: float = 0.05,
        source: str = '',
        confidence: str = 'low',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.process_set = process_set
        self.manufacturing_regime = manufacturing_regime
        self.tox_sigma_nm = tox_sigma_nm
        self.kox_sigma = kox_sigma
        self.vt_sigma_v = vt_sigma_v
        self.source = source
        self.confidence = confidence
        self.notes = notes
