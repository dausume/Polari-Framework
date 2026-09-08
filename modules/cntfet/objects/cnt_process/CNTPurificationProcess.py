"""
@module cntfet.objects.cnt_process.CNTPurificationProcess

Row class CNTPurificationProcess of the cntfet module — one class per file (design §7), split
from cnt_process_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CNTPurificationProcess(treeObject):
    """Semiconducting sorting + diameter distribution. A metallic
    tube (probability 1 - purity) kills a one-tube FET outright.
    RINSE/DREAM ride here as explicit mitigation knobs (their
    Hills-2019 numbers are cited anchors)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        process_set: str = '',
        manufacturing_regime: str = '',
        semiconducting_purity: float = 0.9999,
        diameter_mu_nm: float = 1.2,
        diameter_sigma_nm: float = 0.1,
        rinse_applied: bool = True,
        dream_design_context: bool = False,
        source: str = '',
        confidence: str = 'low',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.process_set = process_set
        self.manufacturing_regime = manufacturing_regime
        self.semiconducting_purity = semiconducting_purity
        self.diameter_mu_nm = diameter_mu_nm
        self.diameter_sigma_nm = diameter_sigma_nm
        self.rinse_applied = rinse_applied
        self.dream_design_context = dream_design_context
        self.source = source
        self.confidence = confidence
        self.notes = notes
