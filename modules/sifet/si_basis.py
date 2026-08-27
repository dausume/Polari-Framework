"""
@module sifet.si_basis

fp-2 object layer: silicon MOSFET decomposed into doping profiles,
a (thermal or sol-gel) gate dielectric, the sol-gel process, the
FET SHAPE (planar / SOI / FinFET / GAA) and the device row that
references them by name (cnt_basis style: decomposed objects, D8
roles, derived fields stamped with derived_at/provenance_json by
si_device.derive_si_device — never typed).

Sol-gel dielectric numbers are PRIORS from the open literature
(plan §2 decision 4) and say so on the row (confidence + citation).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
    — to be wired by the integrator
  - sifet.si_device, sifet.selftest_sifet
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SiliconDopingProfile(treeObject):
    """One doping region: channel/body or source-drain."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        dopant_type: str = 'p',          # 'n' | 'p'
        species: str = 'B',              # P | As | B
        concentration_cm3: float = 1e17,
        method: str = 'implant',         # implant | diffusion | in-situ
        activation_fraction: float = 1.0,
        junction_depth_nm: float = 0.0,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.dopant_type = dopant_type
        self.species = species
        self.concentration_cm3 = concentration_cm3
        self.method = method
        self.activation_fraction = activation_fraction
        self.junction_depth_nm = junction_depth_nm
        self.notes = notes


class SolGelDielectric(treeObject):
    """Gate dielectric row — thermal SiO2 is the reference member
    of the same class (precursor 'thermal-oxidation'). k / breakdown
    / leakage are PRIORS; leakage never enters Id (refused)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        material: str = 'SiO2',          # SiO2 | HfO2 | ZrO2
        precursor: str = 'TEOS',         # TEOS | Hf-alkoxide | HfCl4 | thermal-oxidation
        solvent: str = 'ethanol',
        hydrolysis_ratio: float = 4.0,   # r = [H2O]/[alkoxide]
        anneal_c: float = 500.0,
        anneal_min: float = 60.0,
        thickness_nm: float = 2.0,
        k_rel: float = 3.9,
        breakdown_mv_per_cm: float = 10.0,
        leakage_prior_a_per_cm2: float = 1e-8,
        density_fraction_of_thermal: float = 1.0,
        confidence: str = 'high',
        citation: str = '[SZE07]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.material = material
        self.precursor = precursor
        self.solvent = solvent
        self.hydrolysis_ratio = hydrolysis_ratio
        self.anneal_c = anneal_c
        self.anneal_min = anneal_min
        self.thickness_nm = thickness_nm
        self.k_rel = k_rel
        self.breakdown_mv_per_cm = breakdown_mv_per_cm
        self.leakage_prior_a_per_cm2 = leakage_prior_a_per_cm2
        self.density_fraction_of_thermal = density_fraction_of_thermal
        self.confidence = confidence
        self.citation = citation
        self.notes = notes


class SolGelProcess(treeObject):
    """How the sol-gel film is laid down and cured."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        deposition: str = 'spin',        # spin | dip
        spin_rpm: float = 3000.0,
        layers: int = 1,
        cure_profile_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.deposition = deposition
        self.spin_rpm = spin_rpm
        self.layers = layers
        self.cure_profile_json = cure_profile_json
        self.notes = notes


class SiliconFETShape(treeObject):
    """The electrostatic shape: planar bulk / SOI / FinFET / GAA.
    scale_length_formula is DATA (the equation the derive uses)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        kind: str = 'planar-bulk',       # planar-bulk | soi | finfet | gaa-nanosheet
        channel_width_nm: float = 1000.0,
        fin_height_nm: float = 0.0,
        fin_width_nm: float = 0.0,
        n_fins: int = 1,
        gate_all_around: bool = False,
        scale_length_formula: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.kind = kind
        self.channel_width_nm = channel_width_nm
        self.fin_height_nm = fin_height_nm
        self.fin_width_nm = fin_width_nm
        self.n_fins = n_fins
        self.gate_all_around = gate_all_around
        self.scale_length_formula = scale_length_formula
        self.notes = notes


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


SI_CLASSES = (SiliconDopingProfile, SolGelDielectric, SolGelProcess,
              SiliconFETShape, SiliconMOSFET)

# ---- seeds ---------------------------------------------------------
SEED_SI_DIELECTRICS = [
    {'name': 'thermal-sio2-2nm', 'material': 'SiO2',
     'precursor': 'thermal-oxidation', 'solvent': 'none',
     'hydrolysis_ratio': 0.0, 'anneal_c': 900.0, 'anneal_min': 0.0,
     'thickness_nm': 2.0, 'k_rel': 3.9, 'breakdown_mv_per_cm': 10.0,
     'leakage_prior_a_per_cm2': 1e-2,
     'density_fraction_of_thermal': 1.0, 'confidence': 'high',
     'citation': '[SZE07]',
     'notes': 'REFERENCE dielectric: 2 nm thermal SiO2 (k 3.9, Ebd '
              '~10 MV/cm). Direct-tunnelling leakage at 2 nm is '
              'large (~1e-2 A/cm^2 prior) and NOT modeled — refused.'},
    {'name': 'solgel-sio2-teos-4nm', 'material': 'SiO2',
     'precursor': 'TEOS', 'solvent': 'ethanol', 'hydrolysis_ratio': 4.0,
     'anneal_c': 500.0, 'anneal_min': 60.0,
     'thickness_nm': 4.0, 'k_rel': 3.8, 'breakdown_mv_per_cm': 6.0,
     'leakage_prior_a_per_cm2': 1e-7,
     'density_fraction_of_thermal': 0.9, 'confidence': 'low',
     'citation': '[BS90] chemistry; [SG-SIO2] priors',
     'notes': 'Sol-gel SiO2 from TEOS (hydrolysis r = 4, 500 C/60 '
              'min anneal): ~90 % of thermal density, k ~3.8, Ebd '
              '~6 MV/cm PRIOR. Exists to compare against thermal '
              'SiO2 at the thicker film a spin-on process gives.'},
    {'name': 'solgel-hfo2-4nm', 'material': 'HfO2',
     'precursor': 'Hf-alkoxide', 'solvent': '2-methoxyethanol',
     'hydrolysis_ratio': 2.0, 'anneal_c': 400.0, 'anneal_min': 60.0,
     'thickness_nm': 4.0, 'k_rel': 18.0, 'breakdown_mv_per_cm': 4.0,
     'leakage_prior_a_per_cm2': 1e-6,
     'density_fraction_of_thermal': 0.85, 'confidence': 'low',
     'citation': '[BS90] chemistry; [SG-HFO2] priors',
     'notes': 'Sol-gel HfO2 (Hf-alkoxide, 400 C anneal): k 16-20 '
              '(18 used), EOT = 3.9/18 x 4 nm = 0.87 nm, leakage '
              '~1e-6 A/cm^2 and Ebd ~4 MV/cm PRIORS from the open '
              'TFT literature (citation to be verified). Exists to '
              'compare a high-k spin-on film against thermal SiO2: '
              'higher Cinv, lower Vt roll-off, at a leakage the '
              'model does not represent.'},
]

SEED_SI_PROCESSES = [
    {'name': 'spin-3000-1layer', 'deposition': 'spin',
     'spin_rpm': 3000.0, 'layers': 1,
     'cure_profile_json': '{"steps": [{"c": 120, "min": 10, '
                          '"why": "solvent bake"}, {"c": 400, '
                          '"min": 60, "why": "densify"}]}',
     'notes': 'Single spin coat + two-step cure ([BS90] Ch.13 film '
              'drying/densification).'},
    {'name': 'thermal-oxidation', 'deposition': 'spin',
     'spin_rpm': 0.0, 'layers': 0, 'cure_profile_json': '{}',
     'notes': 'Placeholder process row for the thermal-oxide '
              'reference (no sol-gel step).'},
]

SEED_SI_DOPINGS = [
    {'name': 'si-channel-p-1e17', 'dopant_type': 'p', 'species': 'B',
     'concentration_cm3': 1e17, 'method': 'implant',
     'activation_fraction': 1.0, 'junction_depth_nm': 0.0,
     'notes': 'NMOS body/channel: boron 1e17 cm^-3 (phi_F ~ 0.42 V, '
              'x_dmax ~ 104 nm at 300 K).'},
    {'name': 'si-channel-n-1e17', 'dopant_type': 'n', 'species': 'P',
     'concentration_cm3': 1e17, 'method': 'implant',
     'activation_fraction': 1.0, 'junction_depth_nm': 0.0,
     'notes': 'PMOS n-well/channel: phosphorus 1e17 cm^-3.'},
    {'name': 'si-sd-n-plus-1e20', 'dopant_type': 'n', 'species': 'As',
     'concentration_cm3': 1e20, 'method': 'implant',
     'activation_fraction': 0.8, 'junction_depth_nm': 30.0,
     'notes': 'NMOS source/drain: As 1e20 (80 % active). Enters '
              'only the Rc prior today.'},
    {'name': 'si-sd-p-plus-1e20', 'dopant_type': 'p', 'species': 'B',
     'concentration_cm3': 1e20, 'method': 'implant',
     'activation_fraction': 0.8, 'junction_depth_nm': 30.0,
     'notes': 'PMOS source/drain: B 1e20 (80 % active).'},
]

SEED_SI_SHAPES = [
    {'name': 'planar-90nm-class', 'kind': 'planar-bulk',
     'channel_width_nm': 1000.0, 'fin_height_nm': 0.0,
     'fin_width_nm': 0.0, 'n_fins': 1, 'gate_all_around': False,
     'scale_length_formula': 'lambda = sqrt((eps_si/eps_ox) t_ox '
                             'x_dmax)  [TN09] Sec.3.2.1',
     'notes': 'Planar bulk, W = 1 um (so Id reads as A per um).'},
    {'name': 'finfet-class', 'kind': 'finfet',
     'channel_width_nm': 0.0, 'fin_height_nm': 40.0,
     'fin_width_nm': 10.0, 'n_fins': 1, 'gate_all_around': False,
     'scale_length_formula': 'lambda = sqrt((eps_si/(2 eps_ox)) t_si '
                             't_ox (1 + eps_ox t_si/(4 eps_si t_ox)))'
                             '  [SUZ93]',
     'notes': 'Tri-gate fin H 40 / W 10 nm, one fin: W_eff = 90 nm. '
              'Body fully depleted at 1e17 (x_dmax >> W/2).'},
]

SEED_SI_DEVICES = [
    {'name': 'si-nmos-planar-90', 'polarity': 'n',
     'shape': 'planar-90nm-class', 'channel_doping': 'si-channel-p-1e17',
     'sd_doping': 'si-sd-n-plus-1e20', 'dielectric': 'thermal-sio2-2nm',
     'process': 'thermal-oxidation', 'lg_nm': 90.0, 'w_nm': 1000.0,
     'temperature_k': 300.0, 'vfb_v': -0.6,
     'vfb_source': 'PRIOR: near-midgap metal gate phi_m ~ 4.4 eV on '
                   'p-Si 1e17 (phi_s = chi + Eg/2 + phi_F ~ 5.03 eV)',
     'rc_ohm_um': 200.0, 'vdd_v': 1.0,
     'notes': 'THE silicon reference: planar bulk NMOS, Lg 90 nm, '
              '2 nm thermal SiO2. Exists to compare against the CNT '
              'S1 device on every fv/fi surface and as the thermal-'
              'oxide baseline for the sol-gel variants. Derive before '
              'use.'},
    {'name': 'si-pmos-planar-90', 'polarity': 'p',
     'shape': 'planar-90nm-class', 'channel_doping': 'si-channel-n-1e17',
     'sd_doping': 'si-sd-p-plus-1e20', 'dielectric': 'thermal-sio2-2nm',
     'process': 'thermal-oxidation', 'lg_nm': 90.0, 'w_nm': 1000.0,
     'temperature_k': 300.0, 'vfb_v': 0.6,
     'vfb_source': 'PRIOR: near-midgap metal gate phi_m ~ 4.8 eV on '
                   'n-Si 1e17 (phi_s ~ 4.19 eV)',
     'rc_ohm_um': 300.0, 'vdd_v': 1.0,
     'notes': 'Complementary partner of si-nmos-planar-90: same '
              'stack, n-well, Vt NEGATIVE, hole mobility ~1/2.5 of '
              'electrons — exists to show why the p device needs '
              'W_p/W_n ~ mu_n/mu_p for drive match (fp-3 pairs). '
              'Derive before use.'},
    {'name': 'si-nmos-planar-solgel-hfo2', 'polarity': 'n',
     'shape': 'planar-90nm-class', 'channel_doping': 'si-channel-p-1e17',
     'sd_doping': 'si-sd-n-plus-1e20', 'dielectric': 'solgel-hfo2-4nm',
     'process': 'spin-3000-1layer', 'lg_nm': 90.0, 'w_nm': 1000.0,
     'temperature_k': 300.0, 'vfb_v': -0.6,
     'vfb_source': 'PRIOR: same gate metal as si-nmos-planar-90 '
                   '(HfO2 dipole / fixed-charge Vfb shift NOT modeled)',
     'rc_ohm_um': 200.0, 'vdd_v': 1.0,
     'notes': 'si-nmos-planar-90 with the 4 nm sol-gel HfO2 film: '
              'exists to compare EOT 0.87 nm high-k vs 2 nm SiO2 — '
              'higher Cinv (drive), smaller scale length (less Vt '
              'roll-off / DIBL) — with the sol-gel leakage prior '
              'stated, not simulated. Derive before use.'},
    {'name': 'si-nmos-finfet-solgel-hfo2', 'polarity': 'n',
     'shape': 'finfet-class', 'channel_doping': 'si-channel-p-1e17',
     'sd_doping': 'si-sd-n-plus-1e20', 'dielectric': 'solgel-hfo2-4nm',
     'process': 'spin-3000-1layer', 'lg_nm': 20.0, 'w_nm': 90.0,
     'temperature_k': 300.0, 'vfb_v': -0.6,
     'vfb_source': 'PRIOR: as si-nmos-planar-90',
     'rc_ohm_um': 200.0, 'vdd_v': 0.8,
     'notes': 'FinFET-class NMOS, Lg 20 nm, one fin (W_eff 90 nm) '
              'with sol-gel HfO2 (conformality of a spin-on film on '
              'a fin is a stated PRIOR gap). Exists to compare the '
              'fully-depleted body (n_ss -> 1, tiny DIBL) against '
              'the planar 90 nm class. Derive before use.'},
]

SEED_TABLES = (
    ('SolGelDielectric', SEED_SI_DIELECTRICS),
    ('SolGelProcess', SEED_SI_PROCESSES),
    ('SiliconDopingProfile', SEED_SI_DOPINGS),
    ('SiliconFETShape', SEED_SI_SHAPES),
    ('SiliconMOSFET', SEED_SI_DEVICES),
)
