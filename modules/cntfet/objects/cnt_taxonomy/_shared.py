"""@module cntfet.objects.cnt_taxonomy._shared — what the cnt_taxonomy row classes share (constants, seeds, helpers); split from cnt_taxonomy_basis.py (sap-2c)."""
from cntfet.cnt_scoring_seed import (
    CATEGORY as SWITCHING_CATEGORY, CONCEPT_NAME as SWITCHING_CONCEPT,
    FET_TERMS, SCORE_KNOBS, _term, fet_validity, score_device,
)
from cntfet.cnt_states_basis import (
    LN10, STATE_KNOBS, frame_at, model_vt, output_boundary,
    subthreshold_swing_v, transfer_boundaries,
)
from cntfet.cnt_regimes_basis import REGIME_KNOBS, regime_frame
from cntfet.custom.cnt_metrics import extract_metrics
import json
from cntfet.custom.cnt_vs_model import vs_terminal_current

FIDELITY = ('F1 (VS_MINIMAL compact model): every signal figure of '
            'merit is a central difference of the model\'s own Id at '
            'the device\'s derived parameters; shape scale lengths '
            'other than the CNT GAA branch are DATA (formulas as '
            'text, priors cited), not evaluated models')
PROVENANCE = 'FET_CELL_POWER_SILICON_PLAN §fp-3'
SIGNAL_CONCEPT = 'fet-signal-quality'
SIGNAL_CATEGORY = 'fet-signal-figures-of-merit'
TAXONOMY_CITATIONS = {
    '[EKV95]': {'citation': 'Enz, Krummenacher, Vittoz, "An analytical '
                'MOS transistor model valid in all regions of operation '
                'and dedicated to low-voltage and low-current '
                'applications", Analog Integr. Circuits Signal Process. '
                '8:83-114 (1995)', 'doi': '10.1007/BF01239381',
                'used_for': 'gm/Id weak-inversion limit 1/(n φt)'},
    '[SIL96]': {'citation': 'Silveira, Flandre, Jespers, "A gm/ID based '
                'methodology for the design of CMOS analog circuits and '
                'its application to the synthesis of a silicon-on-'
                'insulator micropower OTA", IEEE JSSC 31(9):1314-1319 '
                '(1996)', 'doi': '10.1109/4.535416',
                'used_for': 'gm/Id as THE analog design variable'},
    '[RAZ01]': {'citation': 'Razavi, "Design of Analog CMOS Integrated '
                'Circuits", McGraw-Hill (2001; 2nd ed. 2017), ch. 2-3 '
                '(intrinsic gain gm·ro, headroom Vds ≥ Vdsat)',
                'doi': '', 'isbn': '978-0072380323'},
    '[SAN06]': {'citation': 'Sansen, "Analog Design Essentials", '
                'Springer (2006), ch. 1-2 (gm/Id, gain, Vdsat)',
                'doi': '10.1007/b135783'},
    '[TN09]': {'citation': 'Taur & Ning, "Fundamentals of Modern VLSI '
               'Devices", 2nd ed., Cambridge Univ. Press (2009), §3.2 '
               '(short-channel scale length), §4 (CMOS)',
               'doi': '10.1017/CBO9781139195065'},
    '[YAN92]': {'citation': 'Yan, Ourmazd, Lee, "Scaling the Si MOSFET: '
                'from bulk to SOI to bulk", IEEE TED 39(7):1704-1710 '
                '(1992)', 'doi': '10.1109/16.141237',
                'used_for': 'natural length λ for single/double gate'},
    '[FTW98]': {'citation': 'Frank, Taur, Wong, "Generalized scale '
                'length for two-dimensional effects in MOSFETs", IEEE '
                'EDL 19(10):385-387 (1998)', 'doi': '10.1109/55.720194',
                'used_for': 'generalized scale length (ε ratio)'},
    '[AP97]': {'citation': 'Auth & Plummer, "Scaling theory for '
               'cylindrical, fully-depleted, surrounding-gate '
               'MOSFET\'s", IEEE EDL 18(2):74-76 (1997)',
               'doi': '10.1109/55.553049',
               'used_for': 'GAA nanowire scale length',
               'status': 'to verify (formula transcribed from memory)'},
    '[COL08]': {'citation': 'Colinge (ed.), "FinFETs and Other '
                'Multi-Gate Transistors", Springer (2008), ch. 1 '
                '(natural length per gate count)',
                'doi': '10.1007/978-0-387-71752-4'},
    '[HIS00]': {'citation': 'Hisamoto et al., "FinFET — a self-aligned '
                'double-gate MOSFET scalable to 20 nm", IEEE TED '
                '47(12):2320-2325 (2000)', 'doi': '10.1109/16.887014'},
    '[LOU17]': {'citation': 'Loubet et al., "Stacked nanosheet '
                'gate-all-around transistor to enable scaling beyond '
                'FinFET", VLSI Technology Symp. (2017) T230-T231',
                'doi': '10.23919/VLSIT.2017.7998183',
                'status': 'to verify (page numbers)'},
    '[IR11]': {'citation': 'Ionescu & Riel, "Tunnel field-effect '
               'transistors as energy-efficient electronic switches", '
               'Nature 479:329-337 (2011)', 'doi': '10.1038/nature10679',
               'used_for': 'TFET sub-60 mV/dec premise'},
}
SIGNAL_KNOBS = {
    'vdd_v': SCORE_KNOBS['vdd_v'],
    # the declared analog bias: Vgs = Vt(Vds) + vov_bias, Vds = Vdd/2
    'vov_bias_v': 0.15,
    'vds_fraction': 0.5,
    # saturation headroom the signal class wants: (Vds − Vdsat)/Vdd
    'headroom_margin': 0.1,
    # intrinsic-gain normalization range (min-max on gm/gds)
    'gain_lo': 1.0,
    'gain_hi': 100.0,
    # half-step for the central differences (gm, gds, d²Id/dVg²)
    'diff_step_v': REGIME_KNOBS['diff_step_v'],
    # |switching − signal| below which a device suits either class
    'tie_margin': 0.05,
}
PAIR_KNOBS = {
    'vdd_v': SCORE_KNOBS['vdd_v'],
    # | |Vt_n| − |Vt_p| | tolerance (V)
    'vt_tolerance_v': 0.05,
    # Ion_p / Ion_n window (drive match)
    'drive_ratio_lo': 0.7,
    'drive_ratio_hi': 1.4,
}
def _opt(figure, direction, why):
    return {'figure': figure, 'direction': direction, 'why': why}
SEED_FET_OPTIMIZATION_CLASSES = [
    {
        'name': 'switching-optimized',
        'display_name': 'Switching-optimized (digital)',
        'aliases_json': json.dumps(['digital', 'switching-optimized']),
        'description': 'A transistor built to be a good SWITCH: fully '
                       'off (tiny leakage) at Vgs = 0, fully on (large '
                       'drive) at Vgs = Vdd, and fast between the two. '
                       'It lives at the two ends of the transfer curve '
                       'and races through the middle.',
        'optimizes_json': json.dumps([
            _opt('Ion/Ioff', 'maximise', 'the off leg is the static '
                 'leakage (P_static = Vdd·Ioff), the on leg is the '
                 'drive that charges the next gate'),
            _opt('SS (subthreshold swing)', 'minimise', 'every decade '
                 'of off-current costs one SS of gate swing; a steeper '
                 'switch turns off in less Vdd'),
            _opt('DIBL', 'minimise', 'drain-induced Vt shift lowers the '
                 'off barrier at Vdd — leakage and noise-margin loss'),
            _opt('delay τ = C·Vdd/Ion', 'minimise', 'the switch must '
                 'charge its load inside the clock period'),
            _opt('leakage power Vdd·Ioff', 'minimise', 'idle cells still '
                 'burn Ioff (fp-1)'),
        ]),
        'preferred_region': 'off ↔ on-saturation (full swing: '
                            'subthreshold at Vgs = 0, on-saturation at '
                            'Vgs = Vdd; the transition band is crossed, '
                            'not lived in)',
        'score_concept': SWITCHING_CONCEPT,
        'design_rules_json': json.dumps([
            'centre Vt in [off_decades·SS, Vdd − vov_decades·SS] (the '
            'fi-2 Vt target)',
            'minimise λ/Lg (shape choice) for SS → 60 mV/dec and DIBL → 0',
            'size for drive: Ion sets delay, W_p/W_n balances rise/fall',
        ]),
        'notes': 'Scored by cnt_scoring FET_TERMS (fet-switching-'
                 'quality). Region names are fi-0 states.',
    },
    {
        'name': 'signal-optimized',
        'display_name': 'Signal-optimized (analog)',
        'aliases_json': json.dumps(['analog', 'signal-optimized']),
        'description': 'A transistor built to be a good AMPLIFIER: '
                       'biased ON in saturation at a chosen current, '
                       'it turns a small gate-voltage wiggle into a '
                       'faithful (linear), large (high gain) current '
                       'wiggle — it lives in the middle of the curve '
                       'and never switches.',
        'optimizes_json': json.dumps([
            _opt('gm/Id', 'maximise', 'transconductance per unit bias '
                 'current = gain per watt; bounded by the weak-'
                 'inversion limit 1/(n φt) [EKV95] [SIL96]'),
            _opt('gm/gds (intrinsic gain)', 'maximise', 'the maximum '
                 'voltage gain one device can deliver = gm·ro [RAZ01]'),
            _opt('Vdsat headroom', 'maximise', 'Vds must exceed Vdsat '
                 'by the signal swing or the device leaves saturation '
                 'and the gain collapses [SAN06]'),
            _opt('gm linearity |d²Id/dVg²|/gm', 'minimise', 'a gm that '
                 'changes with the signal makes distortion (HD2)'),
            _opt('noise, matching', 'minimise', 'named gaps at F1: no '
                 'flicker/thermal noise or mismatch model in this row '
                 'set — stated, not scored'),
        ]),
        'preferred_region': 'on-saturation with Vds ≥ Vdsat + '
                            'headroom_margin·Vdd (the velocity-'
                            'saturated / DIBL-tilted saturation regimes '
                            'of fv-1); moderate inversion (Vov ≈ 0.1-'
                            '0.2 V) for the gm/Id sweet spot',
        'score_concept': SIGNAL_CONCEPT,
        'design_rules_json': json.dumps([
            'pick the bias by gm/Id, not by W/L [SIL96]',
            'keep (Vds − Vdsat)/Vdd ≥ headroom_margin for the whole '
            'output swing',
            'prefer long Lg (lower gds / DIBL) — the opposite of the '
            'switching class',
        ]),
        'notes': 'Scored by cnt_taxonomy SIGNAL_TERMS (fet-signal-'
                 'quality) at the declared analog bias (SIGNAL_KNOBS).',
    },
]
SIGNAL_TERMS = {
    'fet-gm-over-id': {
        'raw': 'gm_over_id_per_v', 'ideal': 'gm_over_id_limit_per_v',
        'unit': '1/V',
        'equation': 'gm/Id = (dId/dVg)/Id at the analog bias',
        'ideal_why': '1/(n_ss·φt): the weak-inversion (exponential) '
                     'limit — no MOSFET converts bias current into '
                     'transconductance more efficiently [EKV95] '
                     '[SIL96]; ≈ 38.7 /V at 300 K, n = 1'},
    'fet-intrinsic-gain': {
        'raw': 'intrinsic_gain', 'ideal': 'gain_hi',
        'unit': 'V/V',
        'equation': 'A_v = gm/gds at the analog bias',
        'ideal_why': 'higher is better; the gain_hi knob is the top of '
                     'the normalization range (a long-channel device '
                     'with negligible DIBL) [RAZ01]'},
    'fet-vdsat-headroom': {
        'raw': 'headroom_fraction', 'ideal': 'headroom_margin',
        'unit': 'Vdd',
        'equation': '(Vds − Vdsat)/Vdd at the analog bias',
        'ideal_why': '≥ headroom_margin: the device sits in saturation '
                     'with room for the output swing; below 0 it is a '
                     'resistor, not an amplifier [SAN06]'},
    'fet-gm-linearity': {
        'raw': 'gm_nonlinearity_per_v', 'ideal': 0.0,
        'unit': '1/V',
        'equation': '|d²Id/dVg²| / gm at the analog bias',
        'ideal_why': '0: a transconductance that does not change with '
                     'the signal (no HD2); the exponential subthreshold '
                     'law gives the worst case 1/(n_ss·φt)'},
}
def _sterm(name, display, description, unit, positive, lo, hi,
           tags=()):
    row = _term(name, display, description, unit, positive, lo, hi,
                ('signal', *tags))
    row['category'] = SIGNAL_CATEGORY
    row['source'] = 'cntfet.cnt_taxonomy_basis (fp-3)'
    row['provenance_id'] = PROVENANCE
    return row
def _sdescribe(key):
    t = SIGNAL_TERMS[key]
    ideal = t['ideal'] if isinstance(t['ideal'], (int, float)) \
        else 'computed'
    return (f"{t['equation']}. Ideal: {ideal} ({t['ideal_why']}). "
            f"Raw frame key: {t['raw']}.")
_PHIT_300 = 8.617333262e-5 * 300.0
_GM_ID_LIMIT_300 = 1.0 / _PHIT_300   # ≈ 38.7 /V
SEED_SIGNAL_SCORE_TERMS = [
    _sterm('fet-gm-over-id', 'gm/Id',
           _sdescribe('fet-gm-over-id') + f' Range 0 → '
           f'{_GM_ID_LIMIT_300:.1f} /V (the n = 1, 300 K limit).',
           '1/V', True, 0.0, _GM_ID_LIMIT_300, ('efficiency',)),
    _sterm('fet-intrinsic-gain', 'Intrinsic gain gm/gds',
           _sdescribe('fet-intrinsic-gain') + ' Range 1 → 100 V/V '
           '(gain_lo/gain_hi knobs).',
           'V/V', True, SIGNAL_KNOBS['gain_lo'], SIGNAL_KNOBS['gain_hi'],
           ('gain',)),
    _sterm('fet-vdsat-headroom', 'Saturation headroom',
           _sdescribe('fet-vdsat-headroom') + ' Range 0 → 0.5 Vdd '
           '(a device biased at Vds = Vdd/2 cannot exceed 0.5).',
           'Vdd', True, 0.0, 0.5, ('headroom',)),
    _sterm('fet-gm-linearity', 'gm nonlinearity',
           _sdescribe('fet-gm-linearity') + f' Range 0 → '
           f'{_GM_ID_LIMIT_300:.1f} /V (linear → exponential).',
           '1/V', False, 0.0, _GM_ID_LIMIT_300, ('linearity',)),
]
SEED_SIGNAL_SCORE_CONCEPTS = [{
    'name': SIGNAL_CONCEPT,
    'display_name': 'FET signal quality',
    'description': 'Weighted mean of the ANALOG figures of merit at '
                   'the declared bias Vgs = Vt + vov_bias, Vds = '
                   'Vdd·vds_fraction (cntfet.cnt_taxonomy_basis SIGNAL_TERMS '
                   '/ SIGNAL_KNOBS), each normalized against its '
                   'characteristic-equation ideal. Weights are knobs '
                   '(equal by default). The fet-switching-quality '
                   'concept scores the same device as a SWITCH; '
                   'classify_optimization compares the two.',
    'subject_kind': 'fet-device',
    'subject_names_json': '[]',
    'term_weights_json': json.dumps(
        [{'term': k, 'weight': 1} for k in SIGNAL_TERMS]),
    'required_context_names_json': '[]',
    'aggregation': 'weighted-mean',
    'levelize': True,
    'abstract_tags_json': json.dumps(['fet', 'signal', 'analog',
                                      'device-figures-of-merit']),
    'provenance_id': PROVENANCE,
}]
def signal_frame(id_fn, p, temperature_k=300.0, knobs=None):
    """Every number a signal term may cite, at the declared analog
    bias. gm/gds/Id come from cnt_regimes.regime_frame (the same
    central differences fv-1 uses); d²Id/dVg² is one more."""
    k = {**SIGNAL_KNOBS, **(knobs or {})}
    vdd = k['vdd_v']
    vds = vdd * k['vds_fraction']
    vt = model_vt(p, vds)
    vgs = vt + k['vov_bias_v']
    f = regime_frame(p, vgs, vds, {'diff_step_v': k['diff_step_v']})
    h = k['diff_step_v']
    d2 = (id_fn(vgs + h, vds) - 2.0 * id_fn(vgs, vds)
          + id_fn(vgs - h, vds)) / (h * h)
    gm, gds, id_a = f['gm'], f['gds'], f['id_a']
    phit = p['phit_v']
    limit = 1.0 / (p['n_ss'] * phit)
    return {
        'bias': {'vgs_v': vgs, 'vds_v': vds, 'vt_v': vt,
                 'vov_v': k['vov_bias_v']},
        'id_ua': id_a * 1e6,
        'gm_us': gm * 1e6,
        'gds_us': gds * 1e6,
        'gm_over_id_per_v': gm / id_a if id_a > 0 else None,
        'gm_over_id_limit_per_v': limit,
        'gm_over_id_limit_n1_per_v': 1.0 / phit,
        'intrinsic_gain': gm / gds if gds > 0 else None,
        'gain_hi': k['gain_hi'],
        'vdsat_v': f['vdsat'],
        'headroom_fraction': (f['vdsi'] - f['vdsat']) / vdd,
        'headroom_margin': k['headroom_margin'],
        'gm_nonlinearity_per_v': abs(d2) / gm if gm > 0 else None,
        'fsat': f['fsat'],
        'n_ss': p['n_ss'],
        'temperature_k': temperature_k,
        'refusals': {
            **({} if id_a > 0 else {'gm_over_id_per_v': 'Id ≤ 0 at bias'}),
            **({} if gds > 0 else {'intrinsic_gain': 'gds ≤ 0 at bias'}),
            **({} if gm > 0 else {'gm_nonlinearity_per_v':
                                  'gm ≤ 0 at bias'}),
        },
        'knobs': k,
    }
def _rows_from_manager(manager, class_name):
    table = (getattr(manager, 'objectTables', {}) or {}).get(
        class_name) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)
def _signal_term_rows(manager):
    rows = {}
    for row in _rows_from_manager(manager, 'ScoreTerm'):
        if getattr(row, 'name', '') in SIGNAL_TERMS:
            rows[row.name] = {
                'name': row.name, 'display_name': row.display_name,
                'unit': row.unit, 'is_positive': row.is_positive,
                'normalization_json': row.normalization_json}
    for seed in SEED_SIGNAL_SCORE_TERMS:
        rows.setdefault(seed['name'], seed)
    return rows
def _signal_weights(manager):
    for row in _rows_from_manager(manager, 'ScoreConcept'):
        if getattr(row, 'name', '') == SIGNAL_CONCEPT:
            return json.loads(row.term_weights_json)
    return json.loads(SEED_SIGNAL_SCORE_CONCEPTS[0]['term_weights_json'])
def score_from_frame_registry(frame, registry, terms, weights):
    """cnt_scoring.score_from_frame with the term REGISTRY as a
    parameter (that function hard-codes FET_TERMS; the integrator can
    add `registry=FET_TERMS` there and point this at it). Same engine
    math: scoring_engine.normalize_value + weighted mean, missing
    terms at 0 in the denominator."""
    from scoring.custom.scoring_engine import AGGREGATION_NOTE, normalize_value
    rows, missing, weighted_sum = [], [], 0.0
    total_weight = sum(w.get('weight', 0) for w in weights) or 1
    for entry in weights:
        key = entry.get('term', '')
        reg, term = registry.get(key), terms.get(key)
        weight = entry.get('weight', 0)
        if reg is None or term is None:
            missing.append(key)
            rows.append({'term': key, 'weight': weight, 'found': False,
                         'error': 'no such term in the registry'})
            continue
        raw = frame.get(reg['raw'])
        ideal = (reg['ideal'] if isinstance(reg['ideal'], (int, float))
                 else frame.get(reg['ideal']))
        if raw is None:
            missing.append(key)
            rows.append({'term': key, 'label': term['display_name'],
                         'weight': weight, 'found': False,
                         'ideal': ideal, 'unit': term['unit'],
                         'equation': reg['equation'],
                         'error': frame.get('refusals', {}).get(
                             reg['raw'], f'{reg["raw"]} unmeasured')})
            continue
        spec = json.loads(term['normalization_json'])
        ok, normalized, applied = normalize_value(
            raw, spec, bool(term['is_positive']))
        if not ok:
            missing.append(key)
            rows.append({'term': key, 'weight': weight, 'found': False,
                         'raw': raw, **applied})
            continue
        weighted = normalized * weight
        weighted_sum += weighted
        rows.append({
            'term': key, 'label': term['display_name'],
            'weight': weight, 'found': True,
            'unit': term['unit'], 'equation': reg['equation'],
            'raw': raw, 'ideal': ideal,
            'distance': (abs(raw - ideal) if ideal is not None
                         else None),
            'ideal_why': reg['ideal_why'],
            'isPositive': bool(term['is_positive']),
            'normalized': round(normalized, 6),
            'weighted': round(weighted, 6),
            'normalization': applied,
        })
    return {'score': round(weighted_sum / total_weight, 6),
            'totalWeight': total_weight, 'termsMissing': missing,
            'terms': rows, 'aggregation': 'weighted-mean',
            'aggregationNote': AGGREGATION_NOTE}
def score_signal_from_model(id_fn, p, temperature_k=300.0,
                            manager=None, knobs=None):
    """Pure-model signal score with the FET validity gate (cnt_scoring
    .fet_validity): an unprovable FET scores 0, not low."""
    validity = fet_validity(id_fn, p, manager=manager)
    frame = signal_frame(id_fn, p, temperature_k, knobs)
    result = score_from_frame_registry(
        frame, SIGNAL_TERMS, _signal_term_rows(manager),
        _signal_weights(manager))
    if not validity['valid']:
        result['scoreIfValid'] = result['score']
        result['score'] = 0.0
    return {
        'ok': True, 'concept': SIGNAL_CONCEPT, 'fidelity': FIDELITY,
        'temperature_k': temperature_k, 'validity': validity,
        'knobs': frame['knobs'],
        'frame': {k: v for k, v in frame.items()
                  if k not in ('knobs', 'refusals')},
        'refusals': frame['refusals'],
        **result,
        'idealTable': [
            {'term': r['term'], 'label': r.get('label', r['term']),
             'unit': r.get('unit', ''), 'equation': r.get('equation', ''),
             'ideal': r.get('ideal'), 'actual': r.get('raw'),
             'distance': r.get('distance'),
             'normalized': r.get('normalized'),
             'why': r.get('ideal_why', r.get('error', ''))}
            for r in result['terms']],
    }
def score_signal(manager, device_name, knobs=None):
    """The /signal-score payload for one device."""
    from cntfet.cnt_device_viz_seed import device_model
    id_fn, p, device, refusal = device_model(manager, device_name)
    if refusal is not None:
        return {'ok': True, 'device': device_name,
                'concept': SIGNAL_CONCEPT, 'score': 0.0,
                'validity': {'valid': False, 'checks': [],
                             'failed': ['model-underivable'],
                             'reason': refusal['error']},
                'terms': [], 'termsMissing': list(SIGNAL_TERMS),
                'idealTable': [], 'unproven': True,
                'note': 'no derived model → nothing to prove → '
                        'score 0 (gate rule)'}
    out = score_signal_from_model(id_fn, p, device.temperature_k,
                                  manager, knobs)
    out['device'] = device_name
    return out
def classify_optimization(fet_score, signal_score, knobs=None):
    """Which class the device is better suited to, with the margin
    (signal − switching). Within tie_margin → 'either'."""
    k = {**SIGNAL_KNOBS, **(knobs or {})}
    margin = signal_score - fet_score
    if fet_score == 0.0 and signal_score == 0.0:
        suited = 'neither'
        why = 'both scores are 0 — the validity gate or an underived ' \
              'model; derive/repair before classifying'
    elif abs(margin) < k['tie_margin']:
        suited = 'either'
        why = (f'|signal − switching| = {abs(margin):.3f} < tie_margin '
               f'{k["tie_margin"]:g}: the device is about equally good '
               'as a switch and as an amplifier')
    elif margin > 0:
        suited = 'signal-optimized'
        why = (f'signal {signal_score:.3f} beats switching '
               f'{fet_score:.3f} by {margin:.3f}: better as an '
               'amplifier than as a switch')
    else:
        suited = 'switching-optimized'
        why = (f'switching {fet_score:.3f} beats signal '
               f'{signal_score:.3f} by {-margin:.3f}: better as a '
               'switch than as an amplifier')
    return {'suited_to': suited, 'margin': round(margin, 6),
            'switching_score': fet_score, 'signal_score': signal_score,
            'why': why, 'tie_margin': k['tie_margin'],
            'classes': [c['name'] for c in SEED_FET_OPTIMIZATION_CLASSES]}
SEED_FET_SHAPE_TYPES = [
    {
        'name': 'planar-bulk',
        'display_name': 'Planar bulk MOSFET',
        'description': 'The classic transistor: a gate on top of a '
                       'flat silicon surface, the channel a thin sheet '
                       'under the oxide, the body below it. One side '
                       'of the channel is gated; the drain reaches the '
                       'barrier through the body.',
        'gate_coupling': 'single',
        'scale_length_formula': 'λ ≈ sqrt((ε_si/ε_ox)·t_ox·W_dm) (W_dm '
                                '= max depletion width); generalized '
                                'form: tan(π t_ox/λ)·tan(π t_si/λ) = '
                                'ε_ox/ε_si... solved for λ',
        'scale_length_source': '[TN09] §3.2; [FTW98] (generalized)',
        'typical_n_ss': 1.4,
        'typical_dibl_mv_per_v': 100.0,
        'priors_source': '90-nm-class bulk: SS ≈ 85-100 mV/dec, DIBL ≈ '
                         '80-120 mV/V [TN09] (prior; to verify against '
                         'a named node)',
        'materials_json': json.dumps(['Si', 'SiO2/SiON', 'poly-Si or '
                                      'metal gate']),
        'complementary_capable': True,
        'complementary_how': 'n-well/p-well: NMOS in p-substrate, PMOS '
                             'in an n-well; W_p/W_n ≈ μ_n/μ_p ≈ 2-3 for '
                             'drive match',
        'notes': 'The fp-2 SiliconMOSFET "planar" shape maps here.',
    },
    {
        'name': 'soi',
        'display_name': 'Fully-depleted SOI',
        'description': 'A planar gate over a THIN silicon film on '
                       'buried oxide: the body is gone, so the drain '
                       'has less silicon to reach the barrier through.',
        'gate_coupling': 'single',
        'scale_length_formula': 'λ = sqrt((ε_si/ε_ox)·t_si·t_ox) '
                                '(single-gate thin film)',
        'scale_length_source': '[YAN92]',
        'typical_n_ss': 1.15,
        'typical_dibl_mv_per_v': 60.0,
        'priors_source': 'FD-SOI 28-nm-class: SS ≈ 70 mV/dec, DIBL ≈ '
                         '50-80 mV/V (prior, [TN09] [COL08]; to verify)',
        'materials_json': json.dumps(['Si film', 'buried SiO2',
                                      'HfO2', 'metal gate']),
        'complementary_capable': True,
        'complementary_how': 'same film, n/p by source/drain doping and '
                             'gate work function; back-bias tunes Vt',
        'notes': '',
    },
    {
        'name': 'finfet',
        'display_name': 'FinFET (tri-gate)',
        'description': 'The channel stands up as a thin fin and the '
                       'gate wraps three sides of it — the drain\'s '
                       'field must squeeze through a fin only a few '
                       'nm wide.',
        'gate_coupling': 'tri',
        'scale_length_formula': 'λ ≈ sqrt((ε_si/(2 ε_ox))·t_fin·t_ox) '
                                '(double-gate form; the top gate makes '
                                'it slightly shorter)',
        'scale_length_source': '[YAN92] (double gate); [COL08] ch.1; '
                               '[HIS00]',
        'typical_n_ss': 1.1,
        'typical_dibl_mv_per_v': 40.0,
        'priors_source': '14/16-nm-class FinFET: SS ≈ 65-70 mV/dec, '
                         'DIBL ≈ 30-50 mV/V (prior, [COL08]; to verify)',
        'materials_json': json.dumps(['Si fin (or SiGe for p)', 'HfO2',
                                      'TiN/W metal gate']),
        'complementary_capable': True,
        'complementary_how': 'n/p fins side by side; drive matched by '
                             'FIN COUNT (quantized W) and SiGe p-fins',
        'notes': 'The fp-2 SiliconMOSFET "finfet" shape maps here.',
    },
    {
        'name': 'gaa-nanowire',
        'display_name': 'GAA nanowire',
        'description': 'A round wire of silicon with the gate all the '
                       'way around it: the best electrostatic control '
                       'a gate can have, at the cost of tiny drive per '
                       'wire.',
        'gate_coupling': 'all-around',
        'scale_length_formula': 'λ = sqrt((2 ε_si t_si² ln(1 + 2 t_ox/'
                                't_si) + ε_ox t_si²)/(16 ε_ox))',
        'scale_length_source': '[AP97] (to verify)',
        'typical_n_ss': 1.05,
        'typical_dibl_mv_per_v': 25.0,
        'priors_source': 'Si NW GAA: SS ≈ 63-68 mV/dec, DIBL ≈ 20-40 '
                         'mV/V (prior, [COL08]; to verify)',
        'materials_json': json.dumps(['Si nanowire', 'HfO2', 'metal gate']),
        'complementary_capable': True,
        'complementary_how': 'n/p by S/D doping and gate work function; '
                             'drive matched by wire count',
        'notes': '',
    },
    {
        'name': 'gaa-nanosheet',
        'display_name': 'GAA nanosheet',
        'description': 'Stacked flat ribbons of silicon, each with the '
                       'gate around it: nanowire control with FinFET-'
                       'class drive (width is a design knob again).',
        'gate_coupling': 'all-around',
        'scale_length_formula': 'λ ≈ sqrt((ε_si/(2 ε_ox))·t_sheet·t_ox) '
                                '(double-gate limit of a wide sheet)',
        'scale_length_source': '[YAN92] limit; [LOU17]',
        'typical_n_ss': 1.08,
        'typical_dibl_mv_per_v': 30.0,
        'priors_source': 'stacked nanosheet: SS ≈ 65 mV/dec, DIBL ≈ 30 '
                         'mV/V [LOU17] (prior; to verify)',
        'materials_json': json.dumps(['Si sheets (SiGe sacrificial)',
                                      'HfO2', 'metal gate']),
        'complementary_capable': True,
        'complementary_how': 'n/p sheets, drive by sheet width and count',
        'notes': '',
    },
    {
        'name': 'cnt-gaa',
        'display_name': 'CNT gate-all-around',
        'description': 'One carbon nanotube (~1 nm) with a cylindrical '
                       'gate around it: the S1 device. The gate is as '
                       'close to every carrier as it can be.',
        'gate_coupling': 'all-around',
        'scale_length_formula': 'λ = (d + 2 t_ox)/(2 z0)·[1 + b(γ − 1)], '
                                'b = 0.41(ζ0/2 − ζ0³/16)(π ζ0/2), ζ0 = '
                                'z0 d/(d + 2 t_ox), γ = k_cnt/k_ox '
                                '(EVALUATED: cnt_bandstructure.'
                                'scale_length_nm)',
        'scale_length_source': '[VS1] eq.(7)',
        'typical_n_ss': 1.1,
        'typical_dibl_mv_per_v': 60.0,
        'priors_source': 'computed per device from [VS1] eq.(8) (cnt_'
                         'bandstructure.sce_parameters) — the numbers '
                         'here are the S1 Lg 15 nm order of magnitude',
        'materials_json': json.dumps(['semiconducting SWCNT', 'HfO2',
                                      'Pd (p) / Sc,Er (n) contacts']),
        'complementary_capable': True,
        'complementary_how': 'polarity by CONTACT work function (Pd → p, '
                             'Sc/Er → n) on the same tube — the twin is '
                             'mirror symmetric ([VS1] premise ii)',
        'notes': 'AlignedCNTFETDevice rows map here (shape_of).',
    },
    {
        'name': 'tfet',
        'display_name': 'Tunnel FET',
        'description': 'A gated p-i-n diode: carriers TUNNEL through the '
                       'band gap instead of climbing over a barrier, so '
                       'the swing can beat the 60 mV/dec thermionic '
                       'floor — but the on-current is small.',
        'gate_coupling': 'all-around',
        'scale_length_formula': 'same electrostatic λ as its shape '
                                '(usually GAA/DG); the SWING is set by '
                                'the tunnelling window, not by λ',
        'scale_length_source': '[IR11]; shape λ per [YAN92]/[AP97]',
        'typical_n_ss': 0.5,
        'typical_dibl_mv_per_v': 30.0,
        'priors_source': 'sub-60 mV/dec demonstrated over limited '
                         'decades [IR11]; n_ss < 1 here means "below the '
                         'thermionic floor", not a Boltzmann ideality '
                         '(prior; to verify)',
        'materials_json': json.dumps(['Si/SiGe', 'III-V heterojunction',
                                      'CNT']),
        'complementary_capable': True,
        'complementary_how': 'n- and p-TFETs by which side is the source; '
                             'asymmetric I-V makes drive match harder',
        'notes': 'The F1 VS model cannot represent a TFET (thermionic '
                 'only) — this row is taxonomy, not a model.',
    },
]
_SHAPE_ALIASES = {
    'planar': 'planar-bulk', 'bulk': 'planar-bulk',
    'planar-bulk': 'planar-bulk', 'soi': 'soi', 'fdsoi': 'soi',
    'fin': 'finfet', 'finfet': 'finfet', 'tri-gate': 'finfet',
    'nanowire': 'gaa-nanowire', 'gaa-nanowire': 'gaa-nanowire',
    'gaa': 'gaa-nanowire', 'nanosheet': 'gaa-nanosheet',
    'gaa-nanosheet': 'gaa-nanosheet', 'cnt-gaa': 'cnt-gaa',
    'gaa-cylindrical': 'cnt-gaa', 'tfet': 'tfet',
}
def _shape_rows(manager=None):
    rows = {}
    for row in _rows_from_manager(manager, 'FETShapeType'):
        rows[row.name] = {k: getattr(row, k) for k in
                          SEED_FET_SHAPE_TYPES[0] if hasattr(row, k)}
    for seed in SEED_FET_SHAPE_TYPES:
        rows.setdefault(seed['name'], dict(seed))
    return rows
def shape_of(device, manager=None):
    """The FETShapeType row for a device: AlignedCNTFETDevice rows →
    'cnt-gaa'; a SiliconMOSFET-like row → its `shape` field (aliases
    resolved); unknown → a refusal naming the affordance."""
    rows = _shape_rows(manager)
    cls = type(device).__name__
    shape_field = getattr(device, 'shape', None)
    if cls == 'AlignedCNTFETDevice' or (
            shape_field is None and getattr(device, 'material', '')
            .startswith('cnt')):
        key, how = 'cnt-gaa', 'AlignedCNTFETDevice rows are cnt-gaa'
    elif shape_field:
        key = _SHAPE_ALIASES.get(str(shape_field).lower())
        how = f'from the row\'s shape field "{shape_field}"'
        if key is None:
            # fp-2 SiliconMOSFET rows reference a SiliconFETShape ROW
            # by name ('planar-90nm-class'); its `kind` is the alias.
            for srow in _rows_from_manager(manager, 'SiliconFETShape'):
                if getattr(srow, 'name', '') == shape_field:
                    kind = getattr(srow, 'kind', '')
                    key = _SHAPE_ALIASES.get(str(kind).lower())
                    how = (f'SiliconFETShape row "{shape_field}" '
                           f'(kind "{kind}")')
                    break
        if key is None:
            return {'ok': False, 'shape': None,
                    'error': f'unknown shape "{shape_field}"',
                    'affordance': 'set shape to one of '
                                  + ', '.join(sorted(rows))}
    else:
        return {'ok': False, 'shape': None,
                'error': f'{cls} row carries no shape field',
                'affordance': 'add `shape` to the row (one of '
                              + ', '.join(sorted(rows)) + ')'}
    return {'ok': True, 'shape': key, 'how': how, 'row': rows[key]}
PAIR_LOGIC = ('The pull-up (p) conducts exactly when the pull-down (n) '
              'does not: the same gate voltage that turns one on turns '
              'the other off. So there is never a conducting path from '
              'Vdd to ground in a settled state (only leakage), the '
              'output is pulled all the way to a rail (rail-to-rail), '
              'and the switching point sits mid-supply with symmetric '
              'noise margins → CMOS.')
SEED_COMPLEMENTARY_PAIRS = [{
    'name': 'cnt-s1-pair',
    'n_device': 'cnt-aligned-s1',
    'p_device': 'cnt-aligned-s1-p',
    'logic': PAIR_LOGIC,
    'conditions_json': json.dumps([
        {'name': 'polarity', 'expr': 'polarity differs',
         'why': 'one must pull up and the other pull down'},
        {'name': 'vt-symmetry', 'expr': '| |Vt_n| − |Vt_p| | ≤ tol',
         'why': 'both switch at the same gate swing → the inverter '
                'threshold sits at Vdd/2 and noise margins are equal'},
        {'name': 'drive-match',
         'expr': 'Ion_p/Ion_n within [ratio_lo, ratio_hi] (W_p/W_n ≈ '
                 'μ_n/μ_p for Si; CNT twin = mirror symmetric)',
         'why': 'equal rise and fall → equal delays and a centred '
                'transfer curve'},
    ]),
    'how_it_helps': 'No static current in either logic state (static '
                    'power = leakage only, fp-1), full-swing outputs '
                    'that the next gate reads unambiguously, and a '
                    'symmetric transfer curve that tolerates noise '
                    'equally in both directions.',
    'status': 'declared (p twin is a LABEL today — see notes)',
    'notes': 'cnt-aligned-s1-p derives to the n numbers (build_vs_params '
             'pins ptype 0); check_pair applies the [VS1] premise-ii '
             'mirror explicitly, so the pair is exactly symmetric by '
             'construction. When derive consumes polarity, the same '
             'check reads real p numbers with zero code change.',
}]
_SI_PAIR_CONDITIONS = json.dumps([
    {'name': 'polarity', 'expr': 'polarity differs',
     'why': 'one must pull up and the other pull down'},
    {'name': 'vt-symmetry', 'expr': '| |Vt_n| − |Vt_p| | ≤ tol',
     'why': 'symmetric Vfb priors (±0.6 V) on mirrored 1e17 dopings '
            'give |Vt_n| = |Vt_p| by [SZE07] eq.6.28; a gate-metal '
            'asymmetry would show here first'},
    {'name': 'drive-match',
     'expr': 'Ion_p/Ion_n within [ratio_lo, ratio_hi]; at equal W the '
             'ratio ≈ μ_p/μ_n (rows carry mu_cm2_per_vs), so the '
             'matching width is W_p/W_n = Ion_n/Ion_p ≈ μ_n/μ_p',
     'why': 'equal rise and fall → equal delays and a centred transfer '
            'curve; silicon buys it with a wider (or more-fin) p device'},
])
SEED_COMPLEMENTARY_PAIRS += [{
    'name': 'si-planar-90-pair',
    'n_device': 'si-nmos-planar-90',
    'p_device': 'si-pmos-planar-90',
    'logic': PAIR_LOGIC,
    'conditions_json': _SI_PAIR_CONDITIONS,
    'how_it_helps': 'The planar-bulk CMOS pair: no static current in '
                    'either state, full-swing outputs, symmetric noise '
                    'margins — once the p device is widened by '
                    'μ_n/μ_p (≈ 2-3 at 1e17, [SZE07]/[CT67]).',
    'status': 'declared (real p device: n-well, hole mobility, own Vt)',
    'notes': 'Both rows are W = 1 um, so drive-match is expected to '
             'fail with ratio ≈ μ_p/μ_n; the evidence names the width '
             'ratio that would close it. Evaluate with knobs vdd_v = '
             'the rows\' vdd_v (1.0 V), not the CNT 0.6 V default.',
}, {
    'name': 'si-finfet-hfo2-pair',
    'n_device': 'si-nmos-finfet-solgel-hfo2',
    'p_device': 'si-pmos-finfet-solgel-hfo2',
    'logic': PAIR_LOGIC,
    'conditions_json': _SI_PAIR_CONDITIONS,
    'how_it_helps': 'The FinFET CMOS pair on the sol-gel HfO2 film: '
                    'fully-depleted bodies (n_ss → 1) on both sides; '
                    'drive is matched by FIN COUNT (W_eff quantized '
                    'at 90 nm per fin), so W_p/W_n ≈ μ_n/μ_p rounds '
                    'to the nearest whole fin.',
    'status': 'declared (real p device; one fin each)',
    'notes': 'One fin each → drive-match fails by ≈ μ_p/μ_n; the '
             'evidence ratio says how many p fins per n fin would '
             'match (ceil(Ion_n/Ion_p)). Evaluate at the rows\' '
             'vdd_v = 0.8 V.',
}]
def _pair_rows(manager=None):
    rows = {}
    for row in _rows_from_manager(manager, 'ComplementaryPair'):
        rows[row.name] = {k: getattr(row, k) for k in
                          SEED_COMPLEMENTARY_PAIRS[0] if hasattr(row, k)}
    for seed in SEED_COMPLEMENTARY_PAIRS:
        rows.setdefault(seed['name'], dict(seed))
    return rows
def _polarity_metrics(id_fn, p, device, vdd):
    """extract_metrics on the device as an n-type system plus the
    model Vt(Vdd). For a p-labelled device the mirror is applied
    explicitly: id_p(vg, vd) = −id_n(−vg, −vd) ([VS1] premise ii),
    and the metrics are taken on |id_p| at (−Vg, −Vd) — the mirror
    image, which is the n numbers by construction."""
    polarity = getattr(device, 'polarity', 'n')
    if polarity == 'p':
        p_mirror = {**p, 'ptype': 1}

        def id_p(vg, vd):
            return vs_terminal_current(vg, vd, p_mirror)['id_a']

        def as_n(vg, vd):          # measure the mirror image
            return -id_p(-vg, -vd)
        m = extract_metrics(as_n, {'vdd_v': vdd})
        vt = -model_vt(p, vdd)     # the p threshold is negative
        transform = ('mirror: id_p(Vg,Vd) = −id_n(−Vg,−Vd) applied '
                     'explicitly; the row\'s polarity is a LABEL today '
                     '(build_vs_params pins ptype 0), so the mirror '
                     'image equals the n numbers exactly')
    else:
        m = extract_metrics(id_fn, {'vdd_v': vdd})
        vt = model_vt(p, vdd)
        transform = 'none (n-type system as derived)'
    return {'polarity': polarity, 'vt_model_v': vt,
            'vt_cc_sat_v': m.get('vt_cc_sat_v'),
            'ion_a': m['ion_a'], 'ioff_a': m['ioff_a'],
            'transform': transform}
def check_pair(manager, pair_name, knobs=None):
    """Evaluate a ComplementaryPair's conditions with numbers."""
    from cntfet.cnt_device_viz_seed import device_model
    k = {**PAIR_KNOBS, **(knobs or {})}
    pair = _pair_rows(manager).get(pair_name)
    if pair is None:
        return {'ok': False, 'error': f'no pair named "{pair_name}"',
                'affordance': 'declare a ComplementaryPair row '
                              '(n_device, p_device, conditions_json)'}
    sides, refusals = {}, {}
    for side in ('n_device', 'p_device'):
        id_fn, p, dev, refusal = device_model(manager, pair[side])
        if refusal is not None:
            refusals[side] = refusal['error']
            continue
        sides[side] = _polarity_metrics(id_fn, p, dev, k['vdd_v'])
    if refusals:
        return {'ok': True, 'pair': pair_name, 'passed': False,
                'checks': [], 'refusals': refusals,
                'affordance': 'derive both devices first',
                'logic': pair['logic'], 'knobs': k}
    n, pp = sides['n_device'], sides['p_device']
    vt_gap = abs(abs(n['vt_model_v']) - abs(pp['vt_model_v']))
    ratio = pp['ion_a'] / n['ion_a'] if n['ion_a'] > 0 else float('inf')
    checks = []
    for c in json.loads(pair['conditions_json']):
        if c['name'] == 'polarity':
            passed = n['polarity'] != pp['polarity']
            evidence = {'n': n['polarity'], 'p': pp['polarity']}
        elif c['name'] == 'vt-symmetry':
            passed = vt_gap <= k['vt_tolerance_v']
            evidence = {'vt_n_v': n['vt_model_v'],
                        'vt_p_v': pp['vt_model_v'],
                        'gap_v': vt_gap, 'tol_v': k['vt_tolerance_v']}
        elif c['name'] == 'drive-match':
            passed = k['drive_ratio_lo'] <= ratio <= k['drive_ratio_hi']
            evidence = {'ion_n_ua': n['ion_a'] * 1e6,
                        'ion_p_ua': pp['ion_a'] * 1e6,
                        'ratio': ratio,
                        'window': [k['drive_ratio_lo'],
                                   k['drive_ratio_hi']]}
        else:
            passed, evidence = False, {'error': 'unknown condition'}
        checks.append({**c, 'passed': bool(passed), 'evidence': evidence})
    return {
        'ok': True, 'pair': pair_name, 'passed': all(c['passed']
                                                     for c in checks),
        'n_device': pair['n_device'], 'p_device': pair['p_device'],
        'checks': checks, 'sides': sides,
        'logic': pair['logic'], 'how_it_helps': pair['how_it_helps'],
        'status': pair['status'],
        'caveat': pp['transform'] if pp['polarity'] == 'p'
        else n['transform'],
        'knobs': k, 'fidelity': FIDELITY,
    }
def complementary_of(manager, device_name, knobs=None):
    """The device's declared partner + the pair check, or 'none
    declared' with the affordance."""
    for name, pair in _pair_rows(manager).items():
        if device_name in (pair['n_device'], pair['p_device']):
            partner = (pair['p_device'] if device_name == pair['n_device']
                       else pair['n_device'])
            return {'ok': True, 'device': device_name, 'partner': partner,
                    'role': 'pull-down (n)' if device_name
                    == pair['n_device'] else 'pull-up (p)',
                    'pair': name, 'check': check_pair(manager, name, knobs)}
    return {'ok': True, 'device': device_name, 'partner': None,
            'status': 'none declared',
            'affordance': 'declare a ComplementaryPair row with this '
                          'device as n_device or p_device (for a CNT the '
                          'twin is the same stack with the opposite '
                          'contact work function)'}
def regions_summary(id_fn, p, device, knobs=None):
    """Sub-threshold / Linear / Saturation with numeric boundaries,
    written for the average person; every number from cnt_states."""
    k = {**STATE_KNOBS, **SIGNAL_KNOBS, **(knobs or {})}
    vdd = k['vdd_v']
    vd_lin = SCORE_KNOBS['vd_lin_v']
    ss_v = subthreshold_swing_v(p)
    b_sat = transfer_boundaries(p, vdd, k)
    b_lin = transfer_boundaries(p, vd_lin, k)
    vt_sat, vt_on_sat = b_sat[0]['value_v'], b_sat[1]['value_v']
    vt_lin = b_lin[0]['value_v']
    vdsat_per_vg = []
    for vg in (0.3, 0.4, 0.5, 0.6):
        ob = output_boundary(p, vg, k)
        f = frame_at(p, vg, vdd, k)
        vdsat_per_vg.append({'vgs_v': vg, 'vdsat_v': f['vdsat'],
                             'vds_at_knee_v': ob['x'],
                             'refusal': ob.get('refusal')})
    regions = [
        {
            'name': 'sub-threshold',
            'display_name': 'Sub-threshold (off)',
            'meaning': 'The gate has not opened the channel: only a '
                       'thermal trickle of carriers leaks over the '
                       'barrier. Turning the gate down by one SS cuts '
                       'the current ten-fold.',
            'criteria': 'Vgs < Vt(Vds)  (state "off", cnt_states)',
            'boundaries': {'vt_at_vdd_v': vt_sat, 'vt_at_vd_lin_v': vt_lin,
                           'ss_mv_per_dec': ss_v * 1e3},
            'where': 'Id–Vg: the straight line on the log plot left of '
                     'Vt; Id–Vd: the flat near-zero curves',
            'used_by': ['switching-optimized (the OFF state; Ioff sets '
                        'leakage power)'],
            'states': ['off'], 'regimes': ['subthreshold-exponential'],
        },
        {
            'name': 'linear',
            'display_name': 'Linear / triode (on, resistive)',
            'meaning': 'The channel is open and the drain voltage is '
                       'small: current grows in proportion to Vds, like '
                       'a resistor whose value the gate sets.',
            'criteria': 'Vgs ≥ Vt + Vov_min and Vds < Vdsat  (state '
                        '"on-linear")',
            'boundaries': {'vt_on_v': vt_on_sat,
                           'vov_min_v': k['vov_decades'] * ss_v,
                           'vdsat_per_vg': vdsat_per_vg},
            'where': 'Id–Vd: the rising leg of each curve before the '
                     'knee; Id–Vg at small Vd',
            'used_by': ['switching-optimized (a closed switch at Vds → '
                        '0 — the on-resistance g_on)',
                        'signal-optimized avoids it (gain collapses)'],
            'states': ['on-linear'], 'regimes': ['linear-triode'],
        },
        {
            'name': 'saturation',
            'display_name': 'Saturation (on, current source)',
            'meaning': 'Beyond the knee the current stops rising with '
                       'Vds (carriers already leave the source as fast '
                       'as they can): the device is a gate-controlled '
                       'current source. BdSat / Vdsat is the knee.',
            'criteria': 'Vgs ≥ Vt + Vov_min and Vds ≥ Vdsat  (state '
                        '"on-saturation"; the fv-1 velocity-saturated / '
                        'DIBL-tilted regimes)',
            'boundaries': {'vdsat_per_vg': vdsat_per_vg,
                           'vdsat_strong_v': p['vxo_m_per_s'] * p['lg_m']
                           / p['mu_m2_per_vs'],
                           'analog_bias_vds_v': vdd * k['vds_fraction']},
            'where': 'Id–Vd: the flat plateau right of the knee; Id–Vg '
                     'at Vd = Vdd',
            'used_by': ['signal-optimized (the amplifier bias: Vds ≥ '
                        'Vdsat + margin)',
                        'switching-optimized (the ON state at Vgs = Vds '
                        '= Vdd — Ion)'],
            'states': ['on-saturation'],
            'regimes': ['velocity-saturated', 'dibl-tilted-saturation',
                        'square-law (unreachable in F1)'],
        },
    ]
    return {'ok': True, 'device': getattr(device, 'name', ''),
            'regions': regions,
            'equations': {'vt': 'Vt(Vds) = vt0 − dVt − DIBL·Vds [VS1] '
                                'eq.(8)',
                          'vov_min': 'Vov_min = vov_decades·SS, SS = '
                                     'n_ss·φt·ln10',
                          'vdsat': 'Vdsat = (v_xo Lg/μ)(1 − Ff) + φt Ff '
                                   '[VS1]'},
            'cites': ['cnt_states (fi-0)', 'cnt_regimes (fv-1)'],
            'knobs': {'vov_decades': k['vov_decades'],
                      'vdsat_criterion': k['vdsat_criterion'],
                      'vdd_v': vdd},
            'fidelity': FIDELITY}
def device_taxonomy_report(manager, device_name, knobs=None):
    from cntfet.cnt_device_viz_seed import device_model
    id_fn, p, device, refusal = device_model(manager, device_name)
    if refusal is not None:
        row = None
        for r in _rows_from_manager(manager, 'AlignedCNTFETDevice'):
            if getattr(r, 'name', '') == device_name:
                row = r
        return {'ok': True, 'device': device_name,
                'shape': shape_of(row, manager) if row else None,
                'optimization': classify_optimization(0.0, 0.0),
                'complementary': complementary_of(manager, device_name),
                'regions': None, 'refusal': refusal['error'],
                'fidelity': FIDELITY}
    sw = score_device(manager, device_name)
    sig = score_signal(manager, device_name, knobs)
    return {
        'ok': True, 'device': device_name,
        'shape': shape_of(device, manager),
        'optimization': {
            **classify_optimization(sw['score'], sig['score'], knobs),
            'switching': {'concept': SWITCHING_CONCEPT,
                          'score': sw['score'],
                          'terms': sw['idealTable']},
            'signal': {'concept': SIGNAL_CONCEPT, 'score': sig['score'],
                       'bias': sig['frame']['bias'],
                       'terms': sig['idealTable']},
            'classes': SEED_FET_OPTIMIZATION_CLASSES,
        },
        'complementary': complementary_of(manager, device_name, knobs),
        'regions': regions_summary(id_fn, p, device, knobs),
        'validity': sig['validity'],
        'fidelity': FIDELITY,
    }
def _device_graph(kind, description, x_label, y_label,
                  y_type='linear'):
    """Same wrapped {graphConfig} form as cnt_device_viz._device_graph
    (copied, not imported — private name)."""
    return {
        'name': f'cnt-device-{kind}',
        'description': description + ' — data: /api/cntfet/'
                       'device/{name}/points?curve=' + kind,
        'source_class': 'AlignedCNTFETDevice',
        'definition': json.dumps({'graphConfig': {
            'renderStyle': 'lineY',
            'xDimension': 'x',
            'yDimensions': ['y'],
            'seriesDimension': 'series',
            'styleDimension': 'style',
            'seriesColors': [],
            'options': {'showLegend': True, 'showGrid': True,
                        'xLabel': x_label, 'yLabel': y_label,
                        'yType': y_type},
            'aggregation': None,
        }}),
    }
SEED_CNT_TAXONOMY_GRAPHS = [
    _device_graph(
        'signal-terms',
        'ANALOG figures of merit at the declared bias (Vgs = Vt + '
        'vov_bias, Vds = Vdd/2), each normalized against its '
        'characteristic-equation ideal: gm/Id vs the 1/(nφt) limit, '
        'intrinsic gain gm/gds, saturation headroom, gm linearity; '
        'rule at 1.0 = ideal',
        'signal figure of merit', 'normalized (1 = ideal)'),
    _device_graph(
        'optimization-radar',
        'Switching terms and signal terms side by side (two series of '
        'categorical dots): which class the device is better suited '
        'to, term by term; rule at 1.0 = ideal',
        'figure of merit', 'normalized (1 = ideal)'),
]
def signal_term_rows(result):
    rows = [{'series': 'signal', 'style': 'dot', 'dash': False,
             'x': r['label'], 'y': r['normalized']}
            for r in result['terms'] if r.get('found')]
    rows.append({'series': 'ideal', 'style': 'hguide', 'dash': True,
                 'x': None, 'y': 1.0, 'label': 'ideal = 1.0'})
    return rows
def _build_signal(id_fn, p, device, manager, knobs):
    return signal_term_rows(score_signal(manager, device.name, knobs))
def _build_radar(id_fn, p, device, manager, knobs):
    sw = score_device(manager, device.name)
    sig = score_signal(manager, device.name, knobs)
    rows = [{'series': 'switching', 'style': 'dot', 'dash': False,
             'x': r['label'], 'y': r['normalized']}
            for r in sw['terms'] if r.get('found')]
    rows += [{'series': 'signal', 'style': 'dot', 'dash': False,
              'x': r['label'], 'y': r['normalized']}
             for r in sig['terms'] if r.get('found')]
    rows.append({'series': 'ideal', 'style': 'hguide', 'dash': True,
                 'x': None, 'y': 1.0, 'label': 'ideal = 1.0'})
    return rows
CURVE_BUILDERS = {
    'signal-terms': _build_signal,
    'optimization-radar': _build_radar,
}
assert not set(FET_TERMS) & set(SIGNAL_TERMS)
_ = (SWITCHING_CATEGORY, LN10)
