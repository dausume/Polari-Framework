"""
@module sifet.objects.si.SiliconMOSFET

Row class SiliconMOSFET of the sifet module — one class per file (design §7), split
from si_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SiliconMOSFET(treeObject):
    """The device row: references + priors in, derived VS parameters
    stamped by derive_si_device."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        polarity: str = 'n',
        shape: str = '',
        channel_doping: str = '',
        sd_doping: str = '',
        dielectric: str = '',
        process: str = '',
        lg_nm: float = 90.0,
        w_nm: float = 1000.0,
        temperature_k: float = 300.0,
        vfb_v: float = -0.6,
        vfb_source: str = 'prior',
        rc_ohm_um: float = 200.0,
        vdd_v: float = 1.0,
        physics_fidelity: str = 'VS_SI_MINIMAL',
        # Derived (si_device.derive_si_device):
        vt0_v: float = 0.0,
        n_ss: float = 0.0,
        dibl_v_per_v: float = 0.0,
        dvt_v: float = 0.0,
        mu_cm2_per_vs: float = 0.0,
        vxo_m_per_s: float = 0.0,
        cinv_f_per_m: float = 0.0,
        lambda_nm: float = 0.0,
        equation_revision: str = '',
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.polarity = polarity
        self.shape = shape
        self.channel_doping = channel_doping
        self.sd_doping = sd_doping
        self.dielectric = dielectric
        self.process = process
        self.lg_nm = lg_nm
        self.w_nm = w_nm
        self.temperature_k = temperature_k
        self.vfb_v = vfb_v
        self.vfb_source = vfb_source
        self.rc_ohm_um = rc_ohm_um
        self.vdd_v = vdd_v
        self.physics_fidelity = physics_fidelity
        self.vt0_v = vt0_v
        self.n_ss = n_ss
        self.dibl_v_per_v = dibl_v_per_v
        self.dvt_v = dvt_v
        self.mu_cm2_per_vs = mu_cm2_per_vs
        self.vxo_m_per_s = vxo_m_per_s
        self.cinv_f_per_m = cinv_f_per_m
        self.lambda_nm = lambda_nm
        self.equation_revision = equation_revision
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes
