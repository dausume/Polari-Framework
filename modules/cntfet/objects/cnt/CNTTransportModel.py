"""
@module cntfet.objects.cnt.CNTTransportModel

Row class CNTTransportModel of the cntfet module — one class per file (design §7), split
from cnt_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CNTTransportModel(treeObject):
    """The transport parameterization (D3 labeling is DATA here).
    physics_fidelity picks the evaluated profile (D12): VS_MINIMAL
    (F1 compact: channel + Rc + SCE) is S1's default; TOB_F2 is the
    quasi-ballistic reference kernel. Derived VS parameters are
    stamped by the derive act."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        model_family: str = 'VS-CNFET-derived',
        implementation: str = 'independent',
        numerically_equivalent_to_stanford: bool = False,
        equation_revision: str = '',
        physics_fidelity: str = 'VS_MINIMAL',
        # Calibration-role inputs (priors, tunable):
        vt0_v: float = 0.3,
        vt0_source: str = 'uncalibrated prior — [FC10] reports '
                          'curves vs |Vgs-Vt|; absolute Vt not '
                          'anchored. TUNABLE.',
        efsd_ev: float = 0.1,
        efsd_source: str = 'prior: Fermi level above Ec in the '
                           'doped S/D extensions ([VS1] Sec.II.C '
                           'E_fsd). TUNABLE.',
        # Derived VS parameters ([VS1] eqs 4, 8, 9):
        vxo_m_per_s: float = 0.0,
        mu_cm2_per_vs: float = 0.0,
        n_ss: float = 0.0,
        dibl_v_per_v: float = 0.0,
        dvt_v: float = 0.0,
        lambda_nm: float = 0.0,
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.model_family = model_family
        self.implementation = implementation
        self.numerically_equivalent_to_stanford = (
            numerically_equivalent_to_stanford)
        self.equation_revision = equation_revision
        self.physics_fidelity = physics_fidelity
        self.vt0_v = vt0_v
        self.vt0_source = vt0_source
        self.efsd_ev = efsd_ev
        self.efsd_source = efsd_source
        self.vxo_m_per_s = vxo_m_per_s
        self.mu_cm2_per_vs = mu_cm2_per_vs
        self.n_ss = n_ss
        self.dibl_v_per_v = dibl_v_per_v
        self.dvt_v = dvt_v
        self.lambda_nm = lambda_nm
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes
