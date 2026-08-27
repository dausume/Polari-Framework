"""
@module cntfet.cnt_basis

S1 aligned-CNT FET object layer (CNT_FET_SIMULATION_PLAN.md,
ratified D1-D18). Decomposed objects (D2b) — geometry, material,
gate stack, contact, transport model, parasitics — NEVER one giant
row; parameter ROLES are schema (D8); Rc is first-class (D9).

The S1 scope is deliberately narrow (the ratified first target):
ONE aligned semiconducting CNT — one chirality, one gate stack, one
temperature, one contact prior — DC Id-Vg and Id-Vd only. No
variability, no multi-tube aggregation (S2+); fields that will hold
those knobs later say so instead of pretending.

This module is THIN by construction (D14): no heavy deps — numpy
only in the evaluation kernels, nothing quantum-chemical. Fidelity
kernels are optional engines behind knobs; the capability endpoint
refuses honestly when one is absent.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
  - cntfet.cnt_derive (derivation), cnt_api (knob surface)
  - cntfet.selftest_cntfet
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


class AlignedCNTFETGeometry(treeObject):
    """Device geometry. tube_count is FROZEN at 1 for S1 (the plan's
    smallest-object rule); pitch exists for S2+ aggregation and is
    honestly unused today."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        lg_nm: float = 15.0,
        l_ext_nm: float = 0.0,
        l_c_nm: float = 0.0,
        tube_count: int = 1,
        pitch_nm: float = 0.0,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.lg_nm = lg_nm
        self.l_ext_nm = l_ext_nm
        self.l_c_nm = l_c_nm
        self.tube_count = tube_count
        self.pitch_nm = pitch_nm
        self.notes = notes


class GateStack(treeObject):
    """The gate dielectric + electrostatic geometry. S1 idealizes to
    the GAA cylinder ([VS1] Fig.1 + eq.(1)); cox/cinv are derived."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        geometry: str = 'gaa-cylindrical',
        dielectric_material: str = 'HfO2',
        t_ox_nm: float = 3.0,
        k_ox: float = 16.0,
        # Derived:
        cox_f_per_m: float = 0.0,
        cqe_f_per_m: float = 0.0,
        cinv_f_per_m: float = 0.0,
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.geometry = geometry
        self.dielectric_material = dielectric_material
        self.t_ox_nm = t_ox_nm
        self.k_ox = k_ox
        self.cox_f_per_m = cox_f_per_m
        self.cqe_f_per_m = cqe_f_per_m
        self.cinv_f_per_m = cinv_f_per_m
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes


class CNTContact(treeObject):
    """Contacts as their OWN object (D9: Rc never folds into
    mobility). rc_ohm = per-terminal series resistance PRIOR;
    rq_floor_ohm = the derived quantum floor it can never beat."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        metal: str = 'Pd',
        rc_ohm: float = 5500.0,
        rc_source: str = '',
        rc_confidence: str = 'medium',
        rq_floor_ohm: float = 0.0,
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.metal = metal
        self.rc_ohm = rc_ohm
        self.rc_source = rc_source
        self.rc_confidence = rc_confidence
        self.rq_floor_ohm = rq_floor_ohm
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes


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


class CNTParasitics(treeObject):
    """S1 minimal: a single lumped parasitic capacitance prior.
    Fringe/coupling decomposition is S2+ ([VS2] extrinsics)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        c_par_f: float = 0.0,
        source: str = 'S1 default 0 — DC-only target; [VS2] '
                      'extrinsic elements are S2+',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.c_par_f = c_par_f
        self.source = source
        self.notes = notes


class AlignedCNTFETDevice(treeObject):
    """The composed one-tube device — references the decomposed
    objects by name. SIBLING of electrodevice's percolation-film
    FET (D5), never its successor; nothing here scales film results."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        polarity: str = 'n',
        material: str = '',
        geometry: str = '',
        gate_stack: str = '',
        contact: str = '',
        transport: str = '',
        parasitics: str = '',
        temperature_k: float = 300.0,
        manufacturing_regime: str = 'aggressively_scaled',
        # S3: which process set (cnt_process_basis rows sharing
        # this name) predicts the population around the targets.
        process_set: str = '',
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.polarity = polarity
        self.material = material
        self.geometry = geometry
        self.gate_stack = gate_stack
        self.contact = contact
        self.transport = transport
        self.parasitics = parasitics
        self.temperature_k = temperature_k
        self.manufacturing_regime = manufacturing_regime
        self.process_set = process_set
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes

    @property
    def figures_of_merit(self):
        """fi-2: the device's figures of merit + their characteristic
        ideals, computed LIVE from the derived model (never stored —
        a property is invisible to persistence, which walks
        __dict__). The generic scoring engine reaches these through
        objectRef bindings with path 'figures_of_merit.<key>'
        (cnt_scoring seeds); an underived device answers with a
        named refusal, not zeros."""
        from cntfet.cnt_scoring import figures_of_merit
        return figures_of_merit(getattr(self, 'manager', None),
                                self.name)


class CNTFETParameterRow(treeObject):
    """D8 as schema: one parameter, one role, one source — the
    'which conclusions rest on measurement vs calibration' query
    surface. Stamped by the derive act, one row per parameter."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device: str = '',
        parameter: str = '',
        value: float = 0.0,
        unit: str = '',
        role: str = '',
        source: str = '',
        confidence: str = '',
        derived_from: str = '',
        equation: str = '',
        stamped_at: str = '',
        manager=None,
    ):
        self.name = name
        self.device = device
        self.parameter = parameter
        self.value = value
        self.unit = unit
        self.role = role
        self.source = source
        self.confidence = confidence
        self.derived_from = derived_from
        self.equation = equation
        self.stamped_at = stamped_at


class CNTCalibrationAnchor(treeObject):
    """One digitized/extracted literature value with FULL D18
    provenance: raw points + figure id + axis scaling + extraction
    method + error estimate + normalizations + any fitted params.
    status='refusing' rows name data we do NOT have (refusal, never
    invention)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        source_reference: str = '',
        doi: str = '',
        figure: str = '',
        extraction_method: str = '',
        digitization_error: str = '',
        axis_scaling_json: str = '{}',
        raw_points_json: str = '[]',
        normalizations_json: str = '{}',
        fitted_params_json: str = '{}',
        value: float = 0.0,
        unit: str = '',
        conditions_json: str = '{}',
        status: str = 'ready',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.source_reference = source_reference
        self.doi = doi
        self.figure = figure
        self.extraction_method = extraction_method
        self.digitization_error = digitization_error
        self.axis_scaling_json = axis_scaling_json
        self.raw_points_json = raw_points_json
        self.normalizations_json = normalizations_json
        self.fitted_params_json = fitted_params_json
        self.value = value
        self.unit = unit
        self.conditions_json = conditions_json
        self.status = status
        self.notes = notes


class CNTFETSimResult(treeObject):
    """One evaluation run (Id-Vg / Id-Vd family, ToB reference,
    calibration pass, or equivalence regression) as a row."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device: str = '',
        kind: str = '',
        engine: str = '',
        physics_fidelity: str = '',
        inputs_json: str = '{}',
        series_json: str = '[]',
        metrics_json: str = '{}',
        verdict: str = '',
        ran_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device = device
        self.kind = kind
        self.engine = engine
        self.physics_fidelity = physics_fidelity
        self.inputs_json = inputs_json
        self.series_json = series_json
        self.metrics_json = metrics_json
        self.verdict = verdict
        self.ran_at = ran_at
        self.notes = notes


# ---- S1 seeds: exactly ONE device, decomposed ---------------------
# Chirality (16,0): semiconducting ((n-m) mod 3 = 1), d ~ 1.25 nm —
# the nearest clean zigzag to the [FC10] calibration tube (d ~ 1.2
# nm). Gate: HfO2 t_ox = 3 nm, k_ox = 16 (the [VS1] Fig.2 context is
# EOT ~ 0.7 nm; 3 nm HfO2 -> EOT ~ 0.73 nm). Lg = 15 nm = the [VS1]
# v_xo calibration flagship, inside the model's stated Lg < 30 nm
# quasi-ballistic domain. Contact prior: Rs = 5.5 kOhm per terminal
# (the [VS1] Sec.II.D extraction step (a) value for the [FC10]
# devices). One temperature: 300 K.

SEED_CNT_MATERIALS = [
    {'name': 'cnt-16-0', 'chirality_n': 16, 'chirality_m': 0,
     'notes': 'S1 tube: zigzag (16,0), nearest clean chirality to '
              'the [FC10] d~1.2 nm calibration tube. Derive before '
              'use.'},
]

SEED_CNT_GEOMETRIES = [
    {'name': 'cnt-s1-lg15', 'lg_nm': 15.0, 'l_ext_nm': 0.0,
     'l_c_nm': 20.0, 'tube_count': 1, 'pitch_nm': 0.0,
     'notes': 'S1: one tube, Lg = 15 nm ([VS1] v_xo calibration '
              'flagship). pitch/tube_count aggregation = S2+.'},
    # fi-4 comparator: the same stack at a relaxed Lg = 30 nm so the
    # competitive scoring page has a real second FET (better SCE /
    # DIBL, lower v_xo and drive — the trade-off the terms expose).
    {'name': 'cnt-s1-lg30', 'lg_nm': 30.0, 'l_ext_nm': 0.0,
     'l_c_nm': 20.0, 'tube_count': 1, 'pitch_nm': 0.0,
     'notes': 'Comparator geometry: Lg = 30 nm, otherwise S1. Inside '
              'the [VS1] v_xo(Lg) fit range.'},
    # fv-6 comparator: AGGRESSIVE Lg = 10 nm — the short-channel
    # end of the trade-off (higher v_xo / drive, WORSE DIBL and
    # n_ss as lambda/Lg grows). Below the [FC10] Lg = 15 nm data
    # point, so the v_xo(Lg) fit is an EXTRAPOLATION here.
    {'name': 'cnt-s1-lg10', 'lg_nm': 10.0, 'l_ext_nm': 0.0,
     'l_c_nm': 20.0, 'tube_count': 1, 'pitch_nm': 0.0,
     'notes': 'fv-6 comparator geometry: Lg = 10 nm, otherwise S1. '
              'Extrapolates the [VS1] v_xo(Lg) fit below its 15 nm '
              'flagship — labeled, not hidden.'},
]

SEED_GATE_STACKS = [
    {'name': 'cnt-s1-hfo2-gaa', 'geometry': 'gaa-cylindrical',
     'dielectric_material': 'HfO2', 't_ox_nm': 3.0, 'k_ox': 16.0,
     'notes': 'GAA idealization ([VS1] Fig.1/eq.(1)); k_ox = 16 as '
              'in [VS1] Fig.5. EOT ~ 0.73 nm (paper Fig.2 context '
              '~0.7 nm). Derive before use.'},
    # fv-6 comparator: THINNER oxide (t_ox = 2 nm, same k_ox = 16,
    # EOT ~ 0.49 nm) — larger Cox -> larger Cinv, gm and Cgg; better
    # electrostatic control (shorter lambda) at the cost of gate
    # leakage the S1 model does NOT represent (honest omission).
    {'name': 'cnt-s1-hfo2-gaa-tox2', 'geometry': 'gaa-cylindrical',
     'dielectric_material': 'HfO2', 't_ox_nm': 2.0, 'k_ox': 16.0,
     'notes': 'fv-6 comparator gate stack: HfO2 t_ox = 2 nm, k_ox = '
              '16 (EOT ~ 0.49 nm). Gate tunnelling leakage is NOT '
              'modeled at S1 — the thinner oxide only shows its '
              'upside here. Derive before use.'},
]

SEED_CNT_CONTACTS = [
    {'name': 'cnt-s1-pd-contact', 'metal': 'Pd', 'rc_ohm': 5500.0,
     'rc_source': '[VS1] Sec.II.D extraction step (a): Rs = 5.5 '
                  'kOhm per the reported [FC10] experimental data',
     'rc_confidence': 'medium',
     'notes': 'Per-terminal prior, includes the quantum share; the '
              'derived rq_floor_ohm (~3.23 kOhm) is the physical '
              'floor. S1 keeps ONE prior; Rc(Lc) sub-model = S2 '
              '(Franklin 2014 six-metal table).'},
]

SEED_CNT_TRANSPORT = [
    {'name': 'cnt-s1-vs-transport',
     'physics_fidelity': 'VS_MINIMAL',
     'vt0_v': 0.3, 'efsd_ev': 0.1,
     'notes': 'VS-CNFET-derived (independent clean-room '
              'implementation; NOT the Stanford code). Derive '
              'stamps vxo/mu/nss/dibl/dvt from [VS1] eqs (4),(8),'
              '(9).'},
]

SEED_CNT_PARASITICS = [
    {'name': 'cnt-s1-no-parasitics', 'c_par_f': 0.0,
     'notes': 'S1 is DC-only; extrinsic parasitics enter with '
              '[VS2] at S2+.'},
]

SEED_CNT_DEVICES = [
    {'name': 'cnt-aligned-s1', 'polarity': 'n',
     'material': 'cnt-16-0', 'geometry': 'cnt-s1-lg15',
     'gate_stack': 'cnt-s1-hfo2-gaa', 'contact': 'cnt-s1-pd-contact',
     'transport': 'cnt-s1-vs-transport',
     'parasitics': 'cnt-s1-no-parasitics',
     'temperature_k': 300.0,
     'manufacturing_regime': 'aggressively_scaled',
     'process_set': 's1-target-line',
     'notes': 'THE S1 device: one aligned semiconducting tube, DC '
              'Id-Vg/Id-Vd only. n-type ([VS1] flips the [FC10] '
              'p-type polarity; physics symmetric). Derive before '
              'use.'},
    {'name': 'cnt-aligned-s1-lg30', 'polarity': 'n',
     'material': 'cnt-16-0', 'geometry': 'cnt-s1-lg30',
     'gate_stack': 'cnt-s1-hfo2-gaa', 'contact': 'cnt-s1-pd-contact',
     'transport': 'cnt-s1-vs-transport',
     'parasitics': 'cnt-s1-no-parasitics',
     'temperature_k': 300.0,
     'manufacturing_regime': 'aggressively_scaled',
     'process_set': 's1-target-line',
     'notes': 'fi-4 COMPARATOR: S1 stack at Lg = 30 nm, so the '
              'per-FET scoring page ranks two real devices. Until '
              'derived it scores 0 as UNPROVEN (validity gate) — '
              'POST {"action": "derive"} to make it a candidate.'},
    # ---- fv-6 comparator set (FET_VIEWS_PLAN §1 fv-6) -------------
    {'name': 'cnt-aligned-s1-lg10', 'polarity': 'n',
     'material': 'cnt-16-0', 'geometry': 'cnt-s1-lg10',
     'gate_stack': 'cnt-s1-hfo2-gaa', 'contact': 'cnt-s1-pd-contact',
     'transport': 'cnt-s1-vs-transport',
     'parasitics': 'cnt-s1-no-parasitics',
     'temperature_k': 300.0,
     'manufacturing_regime': 'aggressively_scaled',
     'process_set': 's1-target-line',
     'notes': 'fv-6 COMPARATOR (aggressive Lg): S1 stack at Lg = 10 '
              'nm. Exposes the short-channel trade-off on the '
              'competitive scoring page — higher v_xo / gm per G0 '
              'bought with WORSE DIBL and n_ss (lambda/Lg grows). '
              'v_xo(Lg) is extrapolated below the [FC10] 15 nm '
              'point. Unproven -> scores 0 until derived — POST '
              '{"action": "derive"}.'},
    {'name': 'cnt-aligned-s1-tox2', 'polarity': 'n',
     'material': 'cnt-16-0', 'geometry': 'cnt-s1-lg15',
     'gate_stack': 'cnt-s1-hfo2-gaa-tox2',
     'contact': 'cnt-s1-pd-contact',
     'transport': 'cnt-s1-vs-transport',
     'parasitics': 'cnt-s1-no-parasitics',
     'temperature_k': 300.0,
     'manufacturing_regime': 'aggressively_scaled',
     'process_set': 's1-target-line',
     'notes': 'fv-6 COMPARATOR (thinner oxide): S1 at t_ox = 2 nm '
              'HfO2. Exposes the electrostatics trade-off — larger '
              'Cinv/gm and tighter SCE (shorter lambda) vs the gate '
              'leakage S1 does NOT model, so the page shows only '
              'its upside (stated). Unproven -> scores 0 until '
              'derived — POST {"action": "derive"}.'},
    {'name': 'cnt-aligned-s1-p', 'polarity': 'p',
     'material': 'cnt-16-0', 'geometry': 'cnt-s1-lg15',
     'gate_stack': 'cnt-s1-hfo2-gaa', 'contact': 'cnt-s1-pd-contact',
     'transport': 'cnt-s1-vs-transport',
     'parasitics': 'cnt-s1-no-parasitics',
     'temperature_k': 300.0,
     'manufacturing_regime': 'aggressively_scaled',
     'process_set': 's1-target-line',
     'notes': 'fv-6 COMPARATOR ([VS1] p-twin): S1 rows with polarity '
              '= p. HONESTY: today the polarity flag is a LABEL — '
              'derive/build_vs_params always solve the n-type '
              'system (ptype 0) and the mirrored p-system (solve at '
              '(-Vg,-Vd), negate Id; [VS1] premise ii) is exercised '
              'only inside the inverter/cell twins (ptype 1). So '
              'this row derives to the SAME numbers as S1 and ties '
              'it on the scoring page until derive consumes '
              'polarity; it exists so the pair is visible as a '
              'pair. Unproven -> scores 0 until derived — POST '
              '{"action": "derive"}.'},
]
