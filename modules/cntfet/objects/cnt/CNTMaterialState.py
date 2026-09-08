"""
@module cntfet.objects.cnt.CNTMaterialState

Row class CNTMaterialState of the cntfet module — one class per file (design §7), split
from cnt_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CNTMaterialState(treeObject):
    """One semiconducting CNT identity: chirality is the ONLY input
    (physical role); diameter/Eg/vF/m* are DERIVED, never typed."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        chirality_n: int = 16,
        chirality_m: int = 0,
        # Derived at the last derive act (cnt_bandstructure):
        diameter_nm: float = 0.0,
        eg_ev: float = 0.0,
        vf_m_per_s: float = 0.0,
        m_eff_over_m0: float = 0.0,
        semiconducting: bool = True,
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.chirality_n = chirality_n
        self.chirality_m = chirality_m
        self.diameter_nm = diameter_nm
        self.eg_ev = eg_ev
        self.vf_m_per_s = vf_m_per_s
        self.m_eff_over_m0 = m_eff_over_m0
        self.semiconducting = semiconducting
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes
