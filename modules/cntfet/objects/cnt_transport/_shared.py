"""@module cntfet.objects.cnt_transport._shared — what the cnt_transport row classes share (constants, seeds, helpers); split from cnt_transport_basis.py (sap-2c)."""
from cntfet.custom.cnt_constants import KB_J_PER_K, Q_C, lit_value
from cntfet.custom.cnt_bandstructure import M0_KG, m_eff_over_m0
from cntfet.cnt_device_viz_seed import _device_graph
from cntfet.cnt_states_basis import OPS, evaluate_criteria
import json
import math
from cntfet.custom.cnt_derive import get_row, resolve_components

FIDELITY = ('F1 (VS_MINIMAL compact model + Lundstrom scattering '
            'theory): mean free paths are LIT anchors with cited '
            'd/T scalings, the defect and aging terms are PRIORS; '
            'F3/NEGF transmission is row-backed work, not a hidden '
            'fallback')
TRANSPORT_KNOBS = {
    # regime thresholds on transmission T
    't_ballistic': 0.9,
    't_quasi': 0.6,
    't_semi': 0.3,
    # which transmission the regime is classified on:
    # 'channel' = λ_eff/(λ_eff+Lg) (Lundstrom, the channel alone)
    # 'total'   = channel · T_c (contacts folded in)
    'regime_on': 'channel',
    # defect-impurity PRIOR: λ_def at the reference purity; scales
    # as (1 - purity_ref)/(1 - purity)
    'lambda_def_ref_nm': 1000.0,
    'purity_ref': 0.9999,
    # aging PRIOR: λ_def(t) = λ_def0/(1 + t/tau)
    'aging_tau_hours': 8760.0,
    # reference temperature the mfp anchors are quoted at
    't0_k': 300.0,
}
REF_D_NM = lit_value('d0_nm')          # 1.2 nm (the [FC10] tube)
def _c(lhs, op, rhs, why):
    return {'lhs': lhs, 'op': op, 'rhs': rhs, 'why': why}
_NO_AGING = {'kind': 'none', 'form': 'lambda0',
             'why': 'phonon populations are set by temperature, not '
                    'by history — phonon mfps do not age',
             'confidence': 'high'}
SEED_SCATTERING_MECHANISMS = [
    {
        'name': 'acoustic-phonon',
        'display_name': 'Acoustic-phonon scattering',
        'order': 0,
        'description': 'Carriers exchange small energies with '
                       'long-wavelength lattice vibrations; the '
                       'low-bias mfp in a clean tube, ~300 nm at '
                       'room temperature [JAV04]/[PARK04]. Scales '
                       'with diameter (larger tubes: weaker '
                       'coupling) and inversely with temperature '
                       '(phonon population ∝ T) — Perebeinos '
                       'scaling, recorded in LIT lambda_ap_nm.',
        'lambda_formula': 'λ_ac = λ_ac0 · (d/d0) · (T0/T),  λ_ac0 = '
                          '300 nm at d0 = 1.2 nm, T0 = 300 K',
        'lambda0_nm': lit_value('lambda_ap_nm'),
        'temperature_exponent': 1.0,
        'diameter_exponent': 1.0,
        'bias_condition_json': json.dumps({'activates_when': 'always'}),
        'process_knob_json': json.dumps({
            'row': 'CNTPurificationProcess', 'field': 'diameter_mu_nm',
            'how': 'sets d in (d/d0); the device row temperature_k '
                   'sets T'}),
        'time_profile_json': json.dumps(_NO_AGING),
        'enforced_properties_json': json.dumps({
            'ion': 'Ion = Ion_ballistic · B, B = T/(2−T), T = '
                   'λ/(λ+Lg) [LUN97] — negligible at Lg ≪ 300 nm',
            'v_inj': 'v_inj = v_T · B',
            'mu_app': 'sets the long-channel apparent mobility '
                      'μ = v_T λ/(2kT/q)',
            'ss': 'none (SS is electrostatic)'}),
        'confidence': 'medium',
        'notes': '[JAV04] [PARK04] [LUN97]',
        'is_prior': False,
    },
    {
        'name': 'optical-phonon',
        'display_name': 'Optical-phonon emission (bias-activated)',
        'order': 1,
        'description': 'A carrier that has gained ħω_op ≈ 0.18 eV '
                       'from the field emits an optical phonon '
                       'within ~10–15 nm [JAV04]/[PARK04] — the '
                       'high-bias mfp that caps CNT current near '
                       '25 µA. Below q·Vds = ħω_op the carrier '
                       'cannot pay for the phonon and this branch '
                       'is INACTIVE (the switch is the bias, not a '
                       'fit).',
        'lambda_formula': 'λ_op = 12.5 nm (d/d0);  active iff q·Vds ≥ '
                          'ħω_op = 0.18 eV',
        'lambda0_nm': lit_value('lambda_op_nm'),
        'temperature_exponent': 0.0,
        'diameter_exponent': 1.0,
        'bias_condition_json': json.dumps({
            'activates_when': 'q*vds >= hw_op',
            'hw_op_ev': lit_value('hw_op_eV')}),
        'process_knob_json': json.dumps({
            'row': 'CNTPurificationProcess', 'field': 'diameter_mu_nm',
            'how': 'sets d in (d/d0); the bias point sets on/off'}),
        'time_profile_json': json.dumps(_NO_AGING),
        'enforced_properties_json': json.dumps({
            'ion': 'at Vdd the dominant 1/λ term: T collapses toward '
                   'λ_op/(λ_op+Lg) and Ion = Ion_ballistic · B',
            'v_inj': 'v_inj = v_T · B — the velocity-saturation '
                     'mechanism at high field',
            'mu_app': 'μ_app falls with 1/λ_eff at high bias',
            'ss': 'none (SS is electrostatic)'}),
        'confidence': 'low',
        'notes': '[JAV04] [PARK04] [VS1] eq.(3) context; LIT '
                 'lambda_op_nm confidence low (10–15 nm midpoint)',
        'is_prior': False,
    },
    {
        'name': 'defect-impurity',
        'display_name': 'Defect / impurity scattering (PRIOR)',
        'order': 2,
        'description': 'Lattice defects, adsorbates and charged '
                       'impurities scatter elastically; density is '
                       'not measured on this line, so the mfp is a '
                       'PRIOR tied to the purification row: the '
                       'unsorted fraction (1 − purity) stands in as '
                       'the defect-density proxy. Defects '
                       'ACCUMULATE (dose, oxidation, adsorption) — '
                       'the aging law is a labelled prior.',
        'lambda_formula': 'λ_def = λ_def_ref · (1 − purity_ref)/'
                          '(1 − purity);  λ_def_ref = 1000 nm at '
                          'purity_ref = 0.9999 (KNOB, PRIOR)',
        'lambda0_nm': TRANSPORT_KNOBS['lambda_def_ref_nm'],
        'temperature_exponent': 0.0,
        'diameter_exponent': 0.0,
        'bias_condition_json': json.dumps({'activates_when': 'always'}),
        'process_knob_json': json.dumps({
            'row': 'CNTPurificationProcess',
            'field': 'semiconducting_purity',
            'how': 'defect density ∝ (1 − purity) — a proxy, PRIOR'}),
        'time_profile_json': json.dumps({
            'kind': 'aging', 'tau_hours': TRANSPORT_KNOBS[
                'aging_tau_hours'],
            'form': 'lambda0/(1+t/tau)',
            'why': 'defects accumulate roughly linearly with '
                   'exposure so 1/λ_def grows linearly in t; τ = 1 '
                   'year is an engineering guess',
            'confidence': 'low'}),
        'enforced_properties_json': json.dumps({
            'ion': 'Ion drifts down as B(t) falls: Ion(t) = '
                   'Ion_ballistic · B(λ_eff(t))',
            'v_inj': 'v_inj = v_T · B(t)',
            'mu_app': 'μ_app(t) = v_T λ_eff(t)/(2kT/q) — the '
                      'classical mobility-degradation signature',
            'ss': 'none here (trap-induced SS drift is a separate '
                  'electrostatic row, not this mechanism)'}),
        'confidence': 'low',
        'notes': '[LUN97] framework; density prior — replace with '
                 'line data',
        'is_prior': True,
    },
    {
        'name': 'contact-interface',
        'display_name': 'Contact interface (transmission factor)',
        'order': 3,
        'description': 'The metal/tube interface reflects part of '
                       'the flux: with Rc above the quantum floor '
                       'RQ/2 = h/(4q²)/2 per terminal [VS1] §IV the '
                       'contact transmits T_c = (RQ/2)/Rc (≤ 1). '
                       'NOT a mean free path — it multiplies the '
                       'channel transmission and is reported beside '
                       'it, because the VS current already carries '
                       'Rc as series resistance (no double count).',
        'lambda_formula': 'T_c = min(1, (RQ/2)/Rc);  T_total = '
                          'T_channel · T_c',
        'lambda0_nm': 0.0,
        'temperature_exponent': 0.0,
        'diameter_exponent': 0.0,
        'bias_condition_json': json.dumps({'activates_when': 'always'}),
        'process_knob_json': json.dumps({
            'row': 'ContactFormationProcess', 'field': 'rc_median_ohm',
            'how': 'Rc vs RQ/2 (LIT rq_half_ohm)'}),
        'time_profile_json': json.dumps({
            'kind': 'none', 'form': 'T_c',
            'why': 'contact aging (electromigration, oxidation) is '
                   'a separate row when measured',
            'confidence': 'low'}),
        'enforced_properties_json': json.dumps({
            'ion': 'already in the VS current as Rs = Rd = Rc — '
                   'reported, not re-applied',
            'v_inj': 'none', 'mu_app': 'none',
            'ss': 'none (SS is electrostatic)'}),
        'confidence': 'high',
        'notes': '[VS1] §IV; [RAH03] contact as a transmission',
        'is_prior': False,
    },
    {
        'name': 'alignment-misorientation',
        'display_name': 'Alignment misorientation (path length)',
        'order': 4,
        'description': 'A tube crossing the gate at angle θ makes '
                       'the carrier path Lg/cos θ long — it does '
                       'not add a scatterer, it lengthens the '
                       'channel every mfp is compared with. Uses '
                       'the alignment row\'s σ_θ (the S3 sampler\'s '
                       'own rule) as the representative angle.',
        'lambda_formula': 'Lg_eff = Lg/cos(σ_θ);  T = λ_eff/(λ_eff + '
                          'Lg_eff)',
        'lambda0_nm': 0.0,
        'temperature_exponent': 0.0,
        'diameter_exponent': 0.0,
        'bias_condition_json': json.dumps({'activates_when': 'always'}),
        'process_knob_json': json.dumps({
            'row': 'CNTAlignmentProcess', 'field': 'angle_sigma_deg',
            'how': 'θ = σ_θ (1-sigma representative tube)'}),
        'time_profile_json': json.dumps({
            'kind': 'none', 'form': 'Lg_eff',
            'why': 'geometry is fixed at fabrication',
            'confidence': 'high'}),
        'enforced_properties_json': json.dumps({
            'ion': 'longer path → lower T → Ion = Ion_ballistic · B',
            'v_inj': 'v_inj = v_T · B',
            'mu_app': 'none directly (μ_app is per unit length)',
            'ss': 'none (SS is electrostatic)'}),
        'confidence': 'medium',
        'notes': '[LUN97] T = λ/(λ+L) with L the actual path',
        'is_prior': False,
    },
]
def _regime(name, display_name, order, description, criteria,
            governing):
    return {'name': name, 'display_name': display_name, 'order': order,
            'description': description,
            'criteria_json': json.dumps(criteria),
            'governing_equation': governing}
SEED_TRANSPORT_REGIMES = [
    _regime(
        'ballistic', 'Ballistic', 0,
        'Nearly every carrier injected at the source reaches the '
        'drain without scattering (λ_eff ≫ Lg): the current is the '
        'top-of-the-barrier limit Ion_ballistic [RAH03], v_inj ≈ '
        'v_T, and performance is set by electrostatics and contacts '
        'alone — mobility is not a meaningful figure here.',
        [_c('t_regime', '>=', 't_ballistic',
            'T at or above the ballistic threshold (knob)')],
        'Id = Id_ballistic;  B = T/(2−T) → 1'),
    _regime(
        'quasi-ballistic', 'Quasi-ballistic', 1,
        'Most carriers cross unscattered but back-scattering near '
        'the source is no longer negligible: Ion = Ion_ballistic·B '
        'with B between ~0.43 and ~0.82. The device still behaves '
        'as velocity-limited (Fsat → 1) and scaling Lg down still '
        'buys current.',
        [_c('t_regime', '>=', 't_quasi',
            'T at or above the quasi-ballistic floor (knob)'),
         _c('t_regime', '<', 't_ballistic',
            'below the ballistic threshold')],
        'Id = Id_ballistic · T/(2−T)  [LUN97]'),
    _regime(
        'semi-scattered', 'Semi-scattered', 2,
        'Scattering and ballistic flux are comparable (λ_eff ~ Lg): '
        'B falls to ~0.18–0.43, the current sits well below the '
        'ballistic limit and mobility starts to matter. Typical of '
        'a short device at Vdd once optical-phonon emission switches '
        'on.',
        [_c('t_regime', '>=', 't_semi',
            'T at or above the semi-scattered floor (knob)'),
         _c('t_regime', '<', 't_quasi',
            'below the quasi-ballistic floor')],
        'Id = Id_ballistic · T/(2−T),  T ~ 0.3–0.6'),
    _regime(
        'scattered', 'Scattered (diffusive)', 3,
        'Carriers scatter many times crossing the channel (λ_eff ≪ '
        'Lg): the drift-diffusion picture holds, Id ∝ μ_app and '
        'B → λ_eff/(2 Lg). Performance is mobility-limited; the '
        'contributors below say what limits the mobility.',
        [_c('t_regime', '<', 't_semi',
            'below the semi-scattered floor (knob)')],
        'Id ∝ μ_app;  B ≈ λ_eff/(2·Lg)'),
]
def transport_context(manager, device):
    """{lg_nm, d_nm, eg_ev, rc_ohm, purity, angle_sigma_deg,
    temperature_k, process_set, priors} or (None, refusal). The
    device's process rows are fetched by process_set exactly as the
    S3 sampler does; low-confidence rows are listed, not hidden."""
    if manager is None or device is None:
        return None, {'ok': False, 'error': 'no manager / device'}
    if not hasattr(device, 'material'):
        # fp-2: a SiliconMOSFET row shares the VS model but not the
        # CNT process rows (purity / alignment / Rc) this context
        # reads — refuse by name rather than invent phonon data.
        return None, {'ok': False,
                      'error': 'transport context is CNT-specific today '
                               '(process rows: purity, alignment, Rc); '
                               f'"{getattr(device, "name", "?")}" is '
                               'not an AlignedCNTFETDevice — a silicon '
                               'scattering basis (phonon/impurity/'
                               'surface-roughness mfps) is a sifet '
                               'follow-up, not a hidden default'}
    rows, missing = resolve_components(manager, device)
    if missing:
        return None, {'ok': False,
                      'error': f'missing component rows: {missing}'}
    process_set = getattr(device, 'process_set', '')
    if not process_set:
        return None, {'ok': False,
                      'refusal': 'device declares no process_set — '
                                 'the scattering contributors read '
                                 'their knobs (purity, alignment '
                                 'angle, Rc) from its process rows'}
    from cntfet.custom.cnt_montecarlo import gather_process_set
    procs, refusal, priors = gather_process_set(
        manager, process_set,
        getattr(device, 'manufacturing_regime', ''))
    if refusal:
        return None, {'ok': False, 'refusal': refusal}
    mat, geo = rows['material'], rows['geometry']
    return {
        'lg_nm': float(geo.lg_nm),
        'd_nm': float(mat.diameter_nm),
        'eg_ev': float(mat.eg_ev),
        'rc_ohm': float(rows['contact'].rc_ohm),
        'purity': float(
            procs['CNTPurificationProcess'].semiconducting_purity),
        'angle_sigma_deg': float(
            procs['CNTAlignmentProcess'].angle_sigma_deg),
        'temperature_k': float(device.temperature_k),
        'process_set': process_set,
        'priors': priors,
    }, None
_MECH_FIELDS = ('name', 'display_name', 'order', 'description',
                'lambda_formula', 'lambda0_nm', 'temperature_exponent',
                'diameter_exponent', 'bias_condition_json',
                'process_knob_json', 'time_profile_json',
                'enforced_properties_json', 'confidence', 'is_prior')
def _table_rows(manager, cls):
    table = getattr(manager, 'objectTables', {}).get(cls) or {}
    return list(table.values() if isinstance(table, dict) else table)
def mechanism_defs(manager=None):
    rows = []
    if manager is not None:
        for row in _table_rows(manager, 'ScatteringMechanism'):
            rows.append({f: getattr(row, f, None) for f in _MECH_FIELDS})
    if not rows:
        rows = [dict(s) for s in SEED_SCATTERING_MECHANISMS]
    return sorted(rows, key=lambda r: (r['order'], r['name']))
def regime_defs(manager=None):
    rows = []
    if manager is not None:
        for row in _table_rows(manager, 'TransportRegime'):
            rows.append({'name': row.name,
                         'display_name': row.display_name,
                         'order': row.order,
                         'description': row.description,
                         'criteria_json': row.criteria_json,
                         'governing_equation': row.governing_equation})
    if not rows:
        rows = [dict(s) for s in SEED_TRANSPORT_REGIMES]
    return sorted(rows, key=lambda r: (r['order'], r['name']))
def transmission(lambda_nm, lg_nm):
    """[LUN97] T = λ/(λ + L)."""
    return lambda_nm / (lambda_nm + lg_nm)
def ballistic_efficiency(t):
    """[LUN97] B = T/(2 − T): Ion = Ion_ballistic · B."""
    return t / (2.0 - t)
def vs_model_ballisticity(p):
    """The compact model's own v_xo/vB = λ_v/(λ_v + 2 Lg) [VS1]
    §II.D — a fitted definition, reported beside Lundstrom's."""
    lam_v = lit_value('lambda_v_nm')
    lg_nm = p['lg_m'] * 1e9
    return lam_v / (lam_v + 2.0 * lg_nm)
def contact_transmission(rc_ohm):
    """T_c = min(1, (RQ/2)/Rc) [VS1] §IV."""
    rq_half = lit_value('rq_half_ohm')
    return min(1.0, rq_half / rc_ohm) if rc_ohm > 0 else 1.0
def effective_length_nm(lg_nm, angle_sigma_deg):
    return lg_nm / max(0.2, math.cos(math.radians(angle_sigma_deg)))
def thermal_velocity_m_per_s(temperature_k, eg_ev):
    """1-D non-degenerate v_T = sqrt(2kT/(π m*)), m* = Eg/(2 vF²)
    [GUO04]."""
    m_star = m_eff_over_m0(eg_ev) * M0_KG
    return math.sqrt(2.0 * KB_J_PER_K * temperature_k
                     / (math.pi * m_star))
def apparent_mobility_cm2_per_vs(lambda_eff_nm, temperature_k, eg_ev):
    """μ = v_T λ/(2 kT/q) [LUN97]; cm²/(V s)."""
    vt = thermal_velocity_m_per_s(temperature_k, eg_ev)
    phit = KB_J_PER_K * temperature_k / Q_C
    return vt * lambda_eff_nm * 1e-9 / (2.0 * phit) * 1e4
def _aged(lambda_nm, profile, t_hours, knobs):
    """Apply a row's time profile (PRIOR) at t; returns (λ, flag)."""
    kind = (profile or {}).get('kind', 'none')
    if kind == 'aging' and lambda_nm is not None:
        tau = float(profile.get('tau_hours') or knobs['aging_tau_hours'])
        return lambda_nm / (1.0 + t_hours / tau), True
    return lambda_nm, False
def mechanism_lambdas(mechs, p, device_ctx, vds, temperature_k,
                      t_hours=0.0, knobs=None):
    """Per mechanism {name, display_name, lambda_nm | None, active,
    why, contribution (fraction of 1/λ_eff), transmission_factor,
    enforced, is_prior, prior_used}; plus the Matthiessen
    lambda_eff_nm, the contact factor and the effective length.
    Pure over its inputs."""
    k = {**TRANSPORT_KNOBS, **(knobs or {})}
    d_nm = device_ctx['d_nm']
    t0 = k['t0_k']
    out, inv_sum = [], 0.0
    t_c, lg_eff = 1.0, device_ctx['lg_nm']
    priors_used = []
    for m in mechs:
        cond = json.loads(m.get('bias_condition_json') or '{}')
        profile = json.loads(m.get('time_profile_json') or '{}')
        active, why = True, 'always active'
        rule = cond.get('activates_when', 'always')
        if rule == 'q*vds >= hw_op':
            hw = float(cond.get('hw_op_ev', lit_value('hw_op_eV')))
            active = vds >= hw
            why = (f'q·Vds = {vds:.3f} eV '
                   f'{">=" if active else "<"} ħω_op = {hw:g} eV → '
                   f'{"emission allowed" if active else "cannot emit"}')
        lam = None
        prior_used = False
        name = m['name']
        if name == 'contact-interface':
            t_c = contact_transmission(device_ctx['rc_ohm'])
            why = (f'T_c = min(1, RQ/2 / Rc) = min(1, '
                   f'{lit_value("rq_half_ohm"):.0f}/'
                   f'{device_ctx["rc_ohm"]:.0f}) = {t_c:.3f} — '
                   'multiplicative, not a mfp')
        elif name == 'alignment-misorientation':
            lg_eff = effective_length_nm(device_ctx['lg_nm'],
                                         device_ctx['angle_sigma_deg'])
            why = (f'Lg_eff = {device_ctx["lg_nm"]:g}/cos('
                   f'{device_ctx["angle_sigma_deg"]:g}°) = '
                   f'{lg_eff:.2f} nm — lengthens the path, not a mfp')
        elif float(m.get('lambda0_nm') or 0.0) > 0.0:
            lam = float(m['lambda0_nm'])
            lam *= (d_nm / REF_D_NM) ** float(
                m.get('diameter_exponent') or 0.0)
            lam *= (t0 / temperature_k) ** float(
                m.get('temperature_exponent') or 0.0)
            if name == 'defect-impurity':
                # PRIOR: density ∝ (1 - purity)
                defect = max(1.0 - device_ctx['purity'], 1e-12)
                lam = (k['lambda_def_ref_nm']
                       * (1.0 - k['purity_ref']) / defect)
                prior_used = True
                why = (f'λ_def = {k["lambda_def_ref_nm"]:g}·'
                       f'(1−{k["purity_ref"]})/(1−'
                       f'{device_ctx["purity"]}) = {lam:.1f} nm (PRIOR)')
            lam, aged = _aged(lam, profile, t_hours, k)
            if aged:
                prior_used = True
                why += (f'; aged {t_hours:g} h: λ/(1+t/'
                        f'{profile.get("tau_hours"):g}) (PRIOR)')
            if not active:
                lam = None
            else:
                inv_sum += 1.0 / lam
        if prior_used:
            priors_used.append(name)
        out.append({
            'name': name, 'display_name': m.get('display_name', name),
            'lambda_nm': lam, 'active': active, 'why': why,
            'lambda_formula': m.get('lambda_formula', ''),
            'enforced': json.loads(m.get('enforced_properties_json')
                                   or '{}'),
            'time_profile': profile,
            'is_prior': bool(m.get('is_prior')),
            'prior_used': prior_used,
            'transmission_factor': t_c if name == 'contact-interface'
            else None,
        })
    lambda_eff = 1.0 / inv_sum if inv_sum > 0 else float('inf')
    for row in out:
        lam = row['lambda_nm']
        row['contribution'] = ((1.0 / lam) / inv_sum
                               if lam and inv_sum > 0 else 0.0)
    return {'mechanisms': out, 'lambda_eff_nm': lambda_eff,
            'contact_transmission': t_c, 'lg_eff_nm': lg_eff,
            'priors_used': priors_used, 'knobs': k}
def transport_frame(p, device_ctx, vds, t_hours=0.0, knobs=None,
                    manager=None, mechs=None):
    """Every number a regime criterion may cite, at one bias and
    time. Thresholds are frame keys so criteria_json can name them."""
    ml = mechanism_lambdas(mechs or mechanism_defs(manager), p,
                           device_ctx, vds, device_ctx['temperature_k'],
                           t_hours, knobs)
    k = ml['knobs']
    t_ch = transmission(ml['lambda_eff_nm'], ml['lg_eff_nm'])
    t_tot = t_ch * ml['contact_transmission']
    t_reg = t_ch if k['regime_on'] == 'channel' else t_tot
    return {
        'vds': vds, 't_hours': t_hours,
        'lambda_eff_nm': ml['lambda_eff_nm'],
        'lg_nm': device_ctx['lg_nm'], 'lg_eff_nm': ml['lg_eff_nm'],
        'transmission': t_ch,
        'contact_transmission': ml['contact_transmission'],
        'transmission_total': t_tot,
        't_regime': t_reg,
        'ballistic_efficiency': ballistic_efficiency(t_ch),
        'vs_model_ballisticity': vs_model_ballisticity(p),
        't_ballistic': k['t_ballistic'], 't_quasi': k['t_quasi'],
        't_semi': k['t_semi'],
        'mechanisms': ml['mechanisms'],
        'priors_used': ml['priors_used'],
        'knobs': k,
    }
def classify_regime(frame, manager=None, defs=None):
    """(regime name, evaluations) — first row whose criteria ALL
    pass, every row's numbers shown."""
    chosen, evaluations = None, []
    for r in (defs or regime_defs(manager)):
        ev = evaluate_criteria(json.loads(r['criteria_json']), frame)
        passed = bool(ev) and all(e['passed'] for e in ev)
        evaluations.append({'regime': r['name'],
                            'display_name': r['display_name'],
                            'passed': passed, 'criteria': ev,
                            'governing_equation':
                                r['governing_equation'],
                            'description': r['description']})
        if passed and chosen is None:
            chosen = r['name']
    return chosen, evaluations
def _log_times(horizon_hours, points=25):
    """t = 0 then ~24 log-spaced points up to the horizon."""
    if horizon_hours <= 0:
        return [0.0]
    lo = math.log10(max(1.0, horizon_hours / 1e4))
    hi = math.log10(horizon_hours)
    n = points - 1
    pts = [10 ** (lo + (hi - lo) * i / (n - 1)) for i in range(n)]
    pts[-1] = float(horizon_hours)   # exact endpoint (no fp drift)
    return [0.0] + pts
def transport_report(manager, device, p, vgs=0.6, vds=0.6,
                     t_hours=0.0, horizon_hours=8760 * 5, knobs=None):
    """The /transport payload (see module docstring)."""
    if device is not None and not hasattr(device, 'material'):
        # fg-4: a SiliconMOSFET row has its OWN cited scattering
        # basis now (sifet.custom.si_transport) — one dispatch point so
        # /transport, the summary and fet-overview all un-refuse
        # together; absent module → the old honest refusal below.
        try:
            from sifet.custom.si_transport import si_transport_report
        except ImportError:
            pass
        else:
            return si_transport_report(manager, device, p, vgs=vgs,
                                       vds=vds, t_hours=t_hours,
                                       horizon_hours=horizon_hours,
                                       knobs=knobs)
    ctx, refusal = transport_context(manager, device)
    if refusal is not None:
        return refusal
    mechs = mechanism_defs(manager)
    defs = regime_defs(manager)
    frame = transport_frame(p, ctx, vds, t_hours, knobs, manager, mechs)
    regime, evaluations = classify_regime(frame, defs=defs)
    k = frame['knobs']
    b = frame['ballistic_efficiency']
    mu_app = apparent_mobility_cm2_per_vs(
        frame['lambda_eff_nm'], ctx['temperature_k'], ctx['eg_ev'])
    series = []
    for t in _log_times(horizon_hours):
        f = transport_frame(p, ctx, vds, t, knobs, manager, mechs)
        r, _ev = classify_regime(f, defs=defs)
        series.append({'t_hours': t,
                       'lambda_eff_nm': f['lambda_eff_nm'],
                       'transmission': f['transmission'],
                       'transmission_total': f['transmission_total'],
                       'regime': r,
                       'ion_factor': f['ballistic_efficiency']})
    priors = sorted(set(ctx['priors'])
                    | {f'ScatteringMechanism.{n}'
                       for n in frame['priors_used']})
    active = [m for m in frame['mechanisms'] if m['lambda_nm']]
    top = (max(active, key=lambda m: m['contribution'])['name']
           if active else None)
    return {
        'ok': True, 'device': device.name, 'fidelity': FIDELITY,
        'temperature_k': ctx['temperature_k'],
        'processSet': ctx['process_set'],
        'knobs': k,
        'bias': {'vgs': vgs, 'vds': vds, 't_hours': t_hours},
        'context': {kk: ctx[kk] for kk in
                    ('lg_nm', 'd_nm', 'eg_ev', 'rc_ohm', 'purity',
                     'angle_sigma_deg', 'temperature_k')},
        'mechanisms': frame['mechanisms'],
        'topContributor': top,
        'lambda_eff_nm': frame['lambda_eff_nm'],
        'lg_eff_nm': frame['lg_eff_nm'],
        'transmission': frame['transmission'],
        'contact_transmission': frame['contact_transmission'],
        'transmission_total': frame['transmission_total'],
        'ballistic_efficiency': b,
        'vs_model_ballisticity': frame['vs_model_ballisticity'],
        'ballisticity_note': (
            'two definitions, both stated: Lundstrom T = λ_eff/'
            '(λ_eff+Lg) with B = T/(2−T) [LUN97] (ours, from the '
            'mechanism rows) vs the VS model\'s fitted v_xo/vB = '
            'λ_v/(λ_v+2Lg), λ_v = 440 nm [VS1] §II.D — they need '
            'not agree; the gap is calibration-visible'),
        'regime': {'name': regime, 'classified_on': k['regime_on'],
                   't_regime': frame['t_regime'],
                   'evaluations': evaluations},
        'regimes': defs,
        'enforced': {
            'ion_factor': b,
            'ion_formula': 'Ion = Ion_ballistic · B, B = T/(2−T) '
                           '[LUN97]',
            'v_inj_over_vT': b,
            'v_inj_formula': 'v_inj = v_T · B',
            'mu_app_cm2_per_vs': mu_app,
            'mu_formula': 'μ_app = v_T λ_eff/(2kT/q), v_T = '
                          'sqrt(2kT/(π m*)), m* = Eg/(2vF²)',
            'ss_effect': 'none (SS is electrostatic)',
        },
        'timeSeries': series,
        'horizon_hours': horizon_hours,
        'priorFlagged': priors,
        'honesty': ('scattering mfps are literature anchors with '
                    'cited scalings; the defect term and every time '
                    'profile are PRIORS labelled low-confidence '
                    f'({len(priors)} flagged) — the series is a '
                    'prior trajectory until an aging measurement '
                    'row replaces it; regime classified on the '
                    f'{k["regime_on"]} transmission (knob)'),
    }
LG_GRID_NM = [5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200, 300, 500,
              700, 1000]
def _regime_bands(defs, k):
    """(name, lo, hi) T-intervals per regime from the knobs."""
    edges = {'ballistic': (k['t_ballistic'], 1.0),
             'quasi-ballistic': (k['t_quasi'], k['t_ballistic']),
             'semi-scattered': (k['t_semi'], k['t_quasi']),
             'scattered': (0.0, k['t_semi'])}
    return [(r['name'],) + edges[r['name']] for r in defs
            if r['name'] in edges]
def transport_vs_lg_rows(id_fn, p, device, manager, knobs=None,
                         vds=0.6):
    """T(Lg) at this device's λ_eff (line), regime bands over the T
    thresholds, a guide at this device's Lg."""
    ctx, refusal = transport_context(manager, device)
    if refusal is not None:
        return None, refusal
    frame = transport_frame(p, ctx, vds, 0.0, knobs, manager)
    k = frame['knobs']
    lam = frame['lambda_eff_nm']
    rows = [{'series': f'T(Lg), λ_eff = {lam:.1f} nm at Vds = {vds:g} V',
             'style': 'line', 'dash': False, 'x': lg,
             'y': transmission(lam, lg)} for lg in LG_GRID_NM]
    for name, lo, hi in _regime_bands(regime_defs(manager), k):
        for x in (LG_GRID_NM[0], LG_GRID_NM[-1]):
            rows.append({'series': name, 'style': 'band',
                         'dash': False, 'x': x, 'lo': lo, 'hi': hi})
    rows.append({'series': f'this device Lg = {ctx["lg_nm"]:g} nm',
                 'style': 'guide', 'dash': True, 'x': ctx['lg_nm'],
                 'y': None, 'label': f'Lg = {ctx["lg_nm"]:g} nm'})
    return rows, None
def scattering_contribution_rows(id_fn, p, device, manager, knobs=None,
                                 vds=0.6):
    """Categorical x = mechanism; y = fraction of 1/λ_eff (dot).
    Inactive/non-mfp mechanisms are a separate dot series at 0 with
    the reason as the label, so 'not contributing' is shown, not
    omitted. An hguide at 0.5 marks 'dominant'."""
    ctx, refusal = transport_context(manager, device)
    if refusal is not None:
        return None, refusal
    frame = transport_frame(p, ctx, vds, 0.0, knobs, manager)
    rows = []
    for m in frame['mechanisms']:
        if m['lambda_nm']:
            rows.append({'series': f'fraction of 1/λ_eff at Vds = {vds:g} V',
                         'style': 'dot', 'dash': False,
                         'x': m['name'], 'y': m['contribution'],
                         'label': f'λ = {m["lambda_nm"]:.1f} nm'})
        else:
            rows.append({'series': 'inactive / not a mfp',
                         'style': 'dot', 'dash': True,
                         'x': m['name'], 'y': 0.0, 'label': m['why']})
    rows.append({'series': 'dominant (> 0.5)', 'style': 'hguide',
                 'dash': True, 'x': None, 'y': 0.5,
                 'label': 'dominant'})
    return rows, None
def transport_over_time_rows(id_fn, p, device, manager, knobs=None,
                             vds=0.6, horizon_hours=8760 * 5):
    """T and the Ion factor B vs t (lines) + regime thresholds as
    hguides."""
    rep = transport_report(manager, device, p, vds=vds,
                           horizon_hours=horizon_hours, knobs=knobs)
    if not rep.get('ok'):
        return None, rep
    rows = []
    for pt in rep['timeSeries']:
        rows.append({'series': 'T (channel transmission)',
                     'style': 'line', 'dash': False,
                     'x': pt['t_hours'], 'y': pt['transmission']})
        rows.append({'series': 'Ion factor B = T/(2−T)',
                     'style': 'line', 'dash': False,
                     'x': pt['t_hours'], 'y': pt['ion_factor']})
    k = rep['knobs']
    for key, label in (('t_ballistic', 'ballistic ≥'),
                       ('t_quasi', 'quasi-ballistic ≥'),
                       ('t_semi', 'semi-scattered ≥')):
        rows.append({'series': f'{label} {k[key]:g}', 'style': 'hguide',
                     'dash': True, 'x': None, 'y': k[key],
                     'label': label})
    return rows, None
CURVE_BUILDERS = {
    'transport-vs-lg': transport_vs_lg_rows,
    'scattering-contributions': scattering_contribution_rows,
    'transport-over-time': transport_over_time_rows,
}
SEED_CNT_TRANSPORT_GRAPHS = [
    _device_graph(
        'transport-vs-lg',
        'Transport regime vs gate length: Lundstrom transmission '
        'T = λ_eff/(λ_eff+Lg) at this device\'s effective mean free '
        'path (Matthiessen over the ScatteringMechanism rows, Vdd '
        'bias), regime bands at the T thresholds (knobs), this '
        'device\'s Lg as a guide',
        'Lg (nm)', 'transmission T'),
    _device_graph(
        'scattering-contributions',
        'Scattering contributors at Vdd: each mechanism\'s share of '
        '1/λ_eff (dot, label = its mfp); inactive or non-mfp '
        'mechanisms shown at 0 with the reason; rule at 0.5 = '
        'dominant',
        'mechanism', 'fraction of 1/λ_eff'),
    _device_graph(
        'transport-over-time',
        'Transmission T and the Ion factor B = T/(2−T) over the '
        'aging horizon (PRIOR defect accumulation λ_def/(1+t/τ)); '
        'regime thresholds as rules — where the trajectory crosses '
        'one, the regime label changes',
        't (hours)', 'T / Ion factor'),
]
