"""
@module cntfet.cnt_scoring

fi-2 (2026-08-26, FET_INTUITION_PLAN §fi-2): scoring a FET by its
CHARACTERISTIC EQUATIONS. Every figure of merit is a ScoreTerm row
whose description states the governing equation and the IDEAL /
limit value it is measured against; the ideal itself is computed
from the same model frame the device's curves come from, never a
typed-in number:

  SS          = n_ss φt ln10           ideal n_ss = 1 → φt ln10
                                       (59.5 mV/dec at 300 K); lower better
  log10(Ion/Ioff)                      ceiling = Vdd / SS_ideal (the
                                       thermionic limit at this Vdd —
                                       reaching it means Vt = Vdd, i.e.
                                       no drive: a trade-off, stated)
  DIBL        = -dVt/dVds              ideal 0 (perfect gate control)
  gm_pk / G0                           ideal 1: one ballistic 1-D channel
                                       (4 modes) cannot exceed G0 = 4e²/h
  |g_on/G0 - 0.7|                      ideal 0: the [FC10] best-measured
                                       on-conductance fraction
  |Vt - Vt_target|                     ideal 0; Vt_target = midpoint of
                                       the feasible window
                                       [off_decades·SS, Vdd - vov_decades·SS]
                                       (off floor vs on headroom — both
                                       from the fi-0 state criteria)

Normalization ranges are EXPLICIT min-max on physically motivated
spans (knobs on the ScoreTerm rows); weights are knobs on the
ScoreConcept row; the aggregation is the generic scoring engine's
weighted-mean (scoring_engine.normalize_value / AGGREGATION_NOTE —
the SAME math the political scorecard and the materials concepts
use, so a FET score is comparable in kind, not a bespoke formula).

Two consumers of the same numbers:
  * `score_device` — the per-device endpoint (raw → normalized with
    spec → weighted; plus the ideal-vs-actual table with distances).
  * the GENERIC engine — seeded ScoreSubject (object_ref → the device
    row) + ContextualizedValue rows bound by objectRef to
    `AlignedCNTFETDevice.figures_of_merit.<key>` (a live property,
    cnt_basis) so `score_concept(manager, 'fet-switching-quality')`
    levelizes devices against each other with no stored numbers.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/device/{name}/score)
  - cntfet.cnt_montecarlo (fi-3: per-sample scores → best/worst)
  - cntfet.cnt_device_viz (curve 'score-terms')
  - cntfet.cnt_basis (AlignedCNTFETDevice.figures_of_merit)
  - polariServer (ScoreTerm / ScoreConcept / ScoreSubject /
    ContextualizedValue seed passes)
  - cntfet.selftest_cntfet
"""

import json
import math

from cntfet.cnt_metrics import G0_FC10_S, extract_metrics
from cntfet.cnt_states import (
    LN10, STATE_KNOBS, model_vt, subthreshold_swing_v,
)

FIDELITY = ('F1 (VS_MINIMAL compact model): every raw value is the '
            'cnt_metrics family on the model at the device\'s '
            'derived parameters; every ideal is the same model\'s '
            'characteristic limit, computed, not typed')

CONCEPT_NAME = 'fet-switching-quality'
SUBJECT_KIND = 'fet-device'
CATEGORY = 'fet-figures-of-merit'

#: Explicit knobs (every result echoes what it used).
SCORE_KNOBS = {
    # decades of Ion/Ioff a device must hold to count as "off" at
    # Vgs = 0 — the S3 yield criterion (min_on_off_ratio 1e4)
    'off_decades': 4.0,
    # decades above Vt before "on" — shared with the fi-0 states
    'vov_decades': STATE_KNOBS['vov_decades'],
    # [FC10] best-measured on-conductance fraction of G0
    'g_on_target_over_g0': 0.7,
    # which Vt the target term compares: 'model' = Vt(Vdd) from the
    # VS parameters (the fi-0 state boundary — default, so the
    # score and the states agree); 'constant-current' = the
    # cnt_metrics 1 nA crossing (on a device whose Ioff is already
    # ~1 nA that crossing sits at Vgs ≈ 0 — a definition, not a
    # defect, and the frame carries both)
    'vt_definition': 'model',
    'vdd_v': 0.6,
    'vd_lin_v': 0.05,
}

#: The characteristic-equation registry: term → how its raw value
#: and its ideal are read from the frame. `ideal` is a frame key
#: (computed) or a number (a true constant such as 0).
FET_TERMS = {
    'fet-ss': {
        'raw': 'ss_mv_per_dec', 'ideal': 'ss_ideal_mv_per_dec',
        'unit': 'mV/dec',
        'equation': 'SS = n_ss·φt·ln10',
        'ideal_why': 'n_ss = 1 (perfect gate control): φt·ln10 = '
                     '59.5 mV/dec at 300 K — the thermionic floor '
                     '(a tunnel FET could beat it; this model '
                     'cannot)'},
    'fet-on-off-decades': {
        'raw': 'on_off_decades', 'ideal': 'on_off_decades_ceiling',
        'unit': 'decades',
        'equation': 'log10(Ion/Ioff), Ion = Id(Vdd,Vdd), '
                    'Ioff = Id(0,Vdd)',
        'ideal_why': 'ceiling = Vdd/SS_ideal: with Ioff on the '
                     'subthreshold tail, every decade costs one SS of '
                     'gate swing; reaching the ceiling means Vt = Vdd '
                     '(no overdrive left) — the drive/leakage '
                     'trade-off made explicit'},
    'fet-dibl': {
        'raw': 'dibl_mv_per_v', 'ideal': 0.0, 'unit': 'mV/V',
        'equation': 'DIBL = (Vt(Vd_lin) - Vt(Vdd)) / (Vdd - Vd_lin)',
        'ideal_why': '0: the drain does not reach the barrier '
                     '(λ ≪ Lg, [VS1] eq.(7))'},
    'fet-gm-over-g0': {
        'raw': 'gm_peak_over_g0', 'ideal': 1.0, 'unit': 'G0',
        'equation': 'gm_pk = max dId/dVg at Vd = Vdd; G0 = 4e²/h',
        'ideal_why': '1: a single ballistic 1-D channel (4 modes) '
                     'cannot exceed G0 = 155 µS of transconductance'},
    'fet-g-on-distance': {
        'raw': 'g_on_target_distance', 'ideal': 0.0, 'unit': 'G0',
        'equation': '|g_on/G0 - target|, g_on = Id(Vdd,Vd_lin)/Vd_lin',
        'ideal_why': '0: the [FC10] best measured 0.7·G0 (contact + '
                     'channel resistance at the quantum floor)'},
    'fet-vt-distance': {
        'raw': 'vt_target_distance_v', 'ideal': 0.0, 'unit': 'V',
        'equation': '|Vt(Vdd) - Vt_target|, Vt_target = '
                    '(off_decades·SS + Vdd - vov_decades·SS)/2 '
                    '(Vt per the vt_definition knob: model | '
                    'constant-current)',
        'ideal_why': '0: Vt centred in the window where the device '
                     'is both OFF at Vgs = 0 (off_decades of margin) '
                     'and fully ON at Vgs = Vdd (vov_decades of '
                     'overdrive) — the fi-0 state criteria as a '
                     'target'},
}


def _term(name, display, description, unit, positive, lo, hi,
          tags=()):
    return {
        'name': name, 'display_name': display,
        'description': description,
        'category': CATEGORY, 'value_type': 'custom', 'unit': unit,
        'is_positive': positive,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': lo, 'max': hi}),
        'temporal_json': json.dumps({'nature': 'stock',
                                     'resample': 'nearest'}),
        'abstract_tags_json': json.dumps(
            ['fet', 'switching', 'device-figures-of-merit',
             *tags]),
        'source': 'cntfet.cnt_scoring (fi-2)',
        'provenance_id': 'FET_INTUITION_PLAN §fi-2',
    }


def _describe(key):
    t = FET_TERMS[key]
    ideal = t['ideal'] if isinstance(t['ideal'], (int, float)) \
        else 'computed'
    return (f"{t['equation']}. Ideal: {ideal} ({t['ideal_why']}). "
            f"Raw frame key: {t['raw']}.")


#: ScoreTerm seeds — ranges are the knobs (edit on the scoring page).
SEED_FET_SCORE_TERMS = [
    _term('fet-ss', 'Subthreshold swing',
          _describe('fet-ss') + ' Range 59.5 → 200 mV/dec (thermionic '
          'floor → a poorly gated device).',
          'mV/dec', False, 59.5, 200.0, ('leakage',)),
    _term('fet-on-off-decades', 'On/off decades',
          _describe('fet-on-off-decades') + ' Range 0 → 10 decades '
          '(the 0.6 V / 59.5 mV ceiling).',
          'decades', True, 0.0, 10.0, ('leakage',)),
    _term('fet-dibl', 'DIBL',
          _describe('fet-dibl') + ' Range 0 → 150 mV/V.',
          'mV/V', False, 0.0, 150.0, ('short-channel',)),
    _term('fet-gm-over-g0', 'Peak transconductance / G0',
          _describe('fet-gm-over-g0') + ' Range 0 → 1.',
          'G0', True, 0.0, 1.0, ('drive',)),
    _term('fet-g-on-distance', 'On-conductance distance to 0.7·G0',
          _describe('fet-g-on-distance') + ' Range 0 → 0.7 (an open '
          'channel).',
          'G0', False, 0.0, 0.7, ('drive', 'contacts')),
    _term('fet-vt-distance', 'Threshold distance to target',
          _describe('fet-vt-distance') + ' Range 0 → 0.3 V.',
          'V', False, 0.0, 0.3, ('threshold',)),
]

SEED_FET_SCORE_CONCEPTS = [{
    'name': CONCEPT_NAME,
    'display_name': 'FET switching quality',
    'description': 'Weighted mean of the FET figures of merit, each '
                   'normalized against its characteristic-equation '
                   'ideal (cntfet.cnt_scoring FET_TERMS). Weights '
                   'default to equal — a knob; per-device numbers '
                   'resolve LIVE through objectRef bindings into '
                   'AlignedCNTFETDevice.figures_of_merit.',
    'subject_kind': SUBJECT_KIND,
    'subject_names_json': '[]',
    'term_weights_json': json.dumps(
        [{'term': k, 'weight': 1} for k in FET_TERMS]),
    'required_context_names_json': '[]',
    'aggregation': 'weighted-mean',
    'levelize': True,
    'abstract_tags_json': json.dumps(['fet', 'switching',
                                      'device-figures-of-merit']),
    'provenance_id': 'FET_INTUITION_PLAN §fi-2',
}]


def _subject(device_name):
    return {
        'name': f'fet-{device_name}',
        'display_name': device_name,
        'kind': SUBJECT_KIND,
        'object_ref_json': json.dumps(
            {'kind': 'objectRef', 'className': 'AlignedCNTFETDevice',
             'name': device_name}),
        'description': 'The device row IS the subject (object '
                       'coherence); its figures of merit resolve live.',
    }


def _values(device_name):
    return [{
        'name': f'{k}@fet-{device_name}',
        'term_name': k,
        'subject_name': f'fet-{device_name}',
        'context_names_json': '[]',
        'pre_normalized_value': None,
        'data_ref_json': json.dumps(
            {'kind': 'objectRef', 'className': 'AlignedCNTFETDevice',
             'name': device_name,
             'path': f'figures_of_merit.{FET_TERMS[k]["raw"]}'}),
        'source': 'live: AlignedCNTFETDevice.figures_of_merit '
                  '(cnt_scoring.figures_of_merit)',
        'provenance_id': 'FET_INTUITION_PLAN §fi-2',
    } for k in FET_TERMS]


def seed_subjects_and_values(device_names):
    """ScoreSubject + ContextualizedValue seeds for the given
    device names (polariServer passes the seeded device names)."""
    subjects, values = [], []
    for name in device_names:
        subjects.append(_subject(name))
        values.extend(_values(name))
    return subjects, values


# ── the frame: raw values + computed ideals ────────────────────────

def score_frame(id_fn, p, temperature_k=300.0, knobs=None,
                metrics=None):
    """Every number a term may cite, from ONE model. `metrics` may
    be passed when already extracted (the MC loop)."""
    k = {**SCORE_KNOBS, **(knobs or {})}
    vdd, vd_lin = k['vdd_v'], k['vd_lin_v']
    m = metrics or extract_metrics(id_fn, {'vdd_v': vdd,
                                           'vd_lin_v': vd_lin})
    phit = p['phit_v']
    ss_ideal_v = phit * LN10
    ss_model_v = subthreshold_swing_v(p)
    ratio = m.get('on_off_ratio')
    decades = math.log10(ratio) if ratio and ratio > 0 else None
    vt_cc = m.get('vt_cc_sat_v')
    vt_model = model_vt(p, vdd)
    vt_used = vt_model if k['vt_definition'] == 'model' else vt_cc
    vt_lo = k['off_decades'] * ss_model_v
    vt_hi = vdd - k['vov_decades'] * ss_model_v
    vt_target = 0.5 * (vt_lo + vt_hi)
    g_on_over_g0 = m['g_on_s'] / G0_FC10_S
    frame = {
        'ss_mv_per_dec': m.get('ss_mv_per_dec'),
        'ss_ideal_mv_per_dec': ss_ideal_v * 1e3,
        'on_off_decades': decades,
        'on_off_decades_ceiling': vdd / ss_ideal_v,
        'dibl_mv_per_v': m.get('dibl_mv_per_v'),
        'gm_peak_over_g0': m['gm_peak_s'] / G0_FC10_S,
        'g_on_over_g0': g_on_over_g0,
        'g_on_target_distance': abs(g_on_over_g0
                                    - k['g_on_target_over_g0']),
        'vt_cc_sat_v': vt_cc,
        'vt_model_v': vt_model,
        'vt_used_v': vt_used,
        'vt_target_v': vt_target,
        'vt_window_v': [vt_lo, vt_hi],
        'vt_target_distance_v': (abs(vt_used - vt_target)
                                 if vt_used is not None else None),
        'ion_ua': m['ion_a'] * 1e6,
        'ioff_na': m['ioff_a'] * 1e9,
        'temperature_k': temperature_k,
        'refusals': m.get('refusals', {}),
        'knobs': k,
    }
    return frame


def device_knobs(device, knobs=None):
    """Score/validity knobs scaled to THIS device's supply: a
    SiliconMOSFET row carries vdd_v (1.0 / 0.8 V); CNT rows use the
    S1 0.6 V window. Explicit knobs still win."""
    vdd = getattr(device, 'vdd_v', None)
    base = {'vdd_v': float(vdd)} if vdd else {}
    return {**base, **(knobs or {})}


def figures_of_merit(manager, device_name, knobs=None):
    """The dict the device row's `figures_of_merit` property (and
    the generic engine's objectRef bindings) read — raw values +
    ideals. Refusals ride along as data."""
    from cntfet.cnt_device_viz import device_model
    id_fn, p, device, refusal = device_model(manager, device_name)
    if refusal is not None:
        return {'refusal': refusal['error'], 'fet_valid': 0}
    knobs = device_knobs(device, knobs)
    validity = fet_validity(id_fn, p, knobs={'vdd_v': knobs['vdd_v']}
                            if 'vdd_v' in knobs else None, manager=manager)
    if not validity['valid']:
        # every binding resolves to a NAMED absence → the generic
        # engine scores 0 (missing terms contribute 0), same verdict
        # as score_device — never a "low" score for a non-FET
        return {'refusal': 'not provably a FET: failed '
                           + ', '.join(validity['failed']),
                'fet_valid': 0, 'validity': validity}
    return {**score_frame(id_fn, p, device.temperature_k, knobs),
            'fet_valid': 1}


# ── the FET-validity gate (Dustin 2026-08-27) ──────────────────────
#
# "if it fails to meet the conditions of being a FET at all (cannot be
# proven to have valid characteristic equations that show switching
# state transitions) the score will always be 0." The proof is the
# fi-0 machinery itself: the same criteria-as-data that classify
# states must, on THIS device, actually produce the transitions. Every
# check below is a characteristic-equation statement with its numbers;
# ALL must pass, an underivable model fails by construction (nothing to
# prove), and the score is then 0 — not "low", zero — with the failed
# proofs named.

VALIDITY_KNOBS = {
    # decades of gate modulation the device must show (Ion/Ioff) for
    # the gate to count as controlling the channel at all
    'min_modulation_decades': 1.0,
    'vdd_v': 0.6,
}


def fet_validity(id_fn, p, knobs=None, manager=None):
    """{valid, checks: [{name, equation, passed, evidence, why}],
    failed: [...]} — the proof that this model IS a FET."""
    from cntfet.cnt_states import (
        output_boundary, transitions_on_sweep,
    )
    k = {**VALIDITY_KNOBS, **(knobs or {})}
    vdd = k['vdd_v']
    checks = []

    # the sweep and grids span THIS device's supply (a 1.0 V silicon
    # device is not judged on a 0.6 V window)
    events = transitions_on_sweep(p, vdd, 'rising', manager=manager,
                                  vgs_max=vdd)
    order = [e['to'] for e in events]
    on_states = [s for s in order if s and s.startswith('on')]
    traversed = ('off' in order and 'transition-on' in order
                 and bool(on_states)
                 and order.index('off') < order.index('transition-on')
                 < order.index(on_states[0]))
    checks.append({
        'name': 'states-traversed',
        'equation': 'rising Vgs sweep at Vd = Vdd crosses Vt(Vds) then '
                    'Vt + Vov_min: off → transition-on → on',
        'passed': traversed,
        'evidence': [(e['vgs'], e['to']) for e in events],
        'why': 'a FET must leave the subthreshold tail and reach an '
               'on state inside its supply window — the switching '
               'event the states define'})

    ion, ioff = id_fn(vdd, vdd), id_fn(0.0, vdd)
    decades = (math.log10(ion / ioff) if ion > 0 and ioff > 0
               else float('-inf'))
    checks.append({
        'name': 'gate-modulation',
        'equation': 'log10(Id(Vdd,Vdd)/Id(0,Vdd)) ≥ '
                    f"{k['min_modulation_decades']:g}",
        'passed': decades >= k['min_modulation_decades'],
        'evidence': {'ion_a': ion, 'ioff_a': ioff, 'decades': decades},
        'why': 'the gate must actually modulate the channel — no '
               'modulation, no transistor (a wire or an open)'})

    grid = [i * vdd / 30.0 for i in range(31)]
    ids = [id_fn(vg, vdd) for vg in grid]
    monotone = all(ids[i + 1] >= ids[i] * (1 - 1e-9)
                   for i in range(len(ids) - 1))
    checks.append({
        'name': 'gate-monotone',
        'equation': 'dId/dVg ≥ 0 on [0, Vdd] at Vd = Vdd (n-type)',
        'passed': monotone,
        'evidence': {'min_id_a': min(ids), 'max_id_a': max(ids)},
        'why': 'the transfer characteristic of an n-FET rises with '
               'gate bias; a non-monotone Id(Vg) is not the '
               'equation set the states are built on'})

    m = extract_metrics(id_fn, {'vdd_v': vdd})
    ss = m.get('ss_mv_per_dec')
    checks.append({
        'name': 'subthreshold-measurable',
        'equation': 'SS = dVg/dlog10(Id) exists over [1e-6,1e-3]·Ion',
        'passed': ss is not None and math.isfinite(ss) and ss > 0,
        'evidence': {'ss_mv_per_dec': ss,
                     'refusal': m['refusals'].get('ss_mv_per_dec')},
        'why': 'the subthreshold equation Id ∝ 10^((Vgs-Vt)/SS) must '
               'be measurable on the device, or the off state has '
               'no characteristic equation'})

    bounds = [output_boundary(p, vg * vdd, vds_max=vdd)
              for vg in (0.5, 0.667, 0.833, 1.0)]
    found = [b for b in bounds if b['x'] is not None]
    checks.append({
        'name': 'output-saturation',
        'equation': 'some Vg ≥ Vt+Vov_min has Vds ≥ Vdsat inside '
                    '[0, Vdd]: on-linear → on-saturation',
        'passed': bool(found),
        'evidence': [{'vgs': b['vgs'], 'vdsat_at_x': b['x']}
                     for b in bounds],
        'why': 'the on state must split into its linear and '
               'velocity-saturated legs (Fsat knee) — otherwise the '
               'output characteristic is a resistor, not a FET'})

    failed = [c['name'] for c in checks if not c['passed']]
    return {'valid': not failed, 'checks': checks, 'failed': failed,
            'knobs': k,
            'rule': 'ALL proofs must pass; an unprovable model scores '
                    '0 — not low, zero'}


# ── scoring ────────────────────────────────────────────────────────

def _term_rows(manager):
    """Seeded ScoreTerm rows for the FET category (manager rows win
    so range edits on the scoring page change the score with zero
    code)."""
    rows = {}
    if manager is not None:
        table = getattr(manager, 'objectTables', {}).get(
            'ScoreTerm') or {}
        for row in (table.values() if isinstance(table, dict)
                    else table):
            if getattr(row, 'name', '') in FET_TERMS:
                rows[row.name] = {
                    'name': row.name,
                    'display_name': row.display_name,
                    'unit': row.unit,
                    'is_positive': row.is_positive,
                    'normalization_json': row.normalization_json}
    for seed in SEED_FET_SCORE_TERMS:
        rows.setdefault(seed['name'], seed)
    return rows


def _weights(manager):
    if manager is not None:
        table = getattr(manager, 'objectTables', {}).get(
            'ScoreConcept') or {}
        for row in (table.values() if isinstance(table, dict)
                    else table):
            if getattr(row, 'name', '') == CONCEPT_NAME:
                return json.loads(row.term_weights_json)
    return json.loads(SEED_FET_SCORE_CONCEPTS[0]['term_weights_json'])


def score_from_frame(frame, manager=None, terms=None, weights=None):
    """Pure: frame → per-term (raw, ideal, distance, normalized with
    its spec, weighted) → weighted-mean score. Missing terms stay in
    the denominator at 0 (the engine's stated rule)."""
    from scoring.scoring_engine import AGGREGATION_NOTE, normalize_value
    terms = terms or _term_rows(manager)
    weights = weights or _weights(manager)
    rows, missing, weighted_sum = [], [], 0.0
    total_weight = sum(w.get('weight', 0) for w in weights) or 1
    for entry in weights:
        key = entry.get('term', '')
        reg, term = FET_TERMS.get(key), terms.get(key)
        weight = entry.get('weight', 0)
        if reg is None or term is None:
            missing.append(key)
            rows.append({'term': key, 'weight': weight,
                         'found': False, 'error': 'no such FET term'})
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
    score = weighted_sum / total_weight
    return {'score': round(score, 6), 'totalWeight': total_weight,
            'termsMissing': missing, 'terms': rows,
            'aggregation': 'weighted-mean',
            'aggregationNote': AGGREGATION_NOTE}


def score_device(manager, device_name, knobs=None):
    """The /score payload for one device."""
    from cntfet.cnt_device_viz import device_model
    id_fn, p, device, refusal = device_model(manager, device_name)
    if refusal is not None:
        # unprovable = not a FET yet: score 0 with the affordance named
        return {'ok': True, 'device': device_name,
                'concept': CONCEPT_NAME, 'score': 0.0,
                'validity': {'valid': False, 'checks': [],
                             'failed': ['model-underivable'],
                             'reason': refusal['error']},
                'terms': [], 'termsMissing': list(FET_TERMS),
                'idealTable': [], 'unproven': True,
                'note': 'no derived model → no characteristic '
                        'equations to prove → score 0 (gate rule)'}
    knobs = device_knobs(device, knobs)
    validity = fet_validity(id_fn, p, knobs={'vdd_v': knobs['vdd_v']}
                            if 'vdd_v' in knobs else None, manager=manager)
    frame = score_frame(id_fn, p, device.temperature_k, knobs)
    result = score_from_frame(frame, manager)
    if not validity['valid']:
        result['scoreIfValid'] = result['score']
        result['score'] = 0.0
    return {
        'ok': True, 'device': device_name, 'concept': CONCEPT_NAME,
        'fidelity': FIDELITY, 'temperature_k': device.temperature_k,
        'validity': validity,
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
        'genericEngine': f"score_concept(manager, '{CONCEPT_NAME}') "
                         'levelizes every fet-device subject with the '
                         'same terms via objectRef bindings',
    }


# ── long-form rows for the fi-2/fi-3 graph ─────────────────────────

def score_term_rows(result, spread=None, best=None, worst=None):
    """Rows for `cnt-device-score-terms`: one dot per term (x = the
    term label — categorical), y = normalized; lo/hi = the MC
    p05/p95 per term when a spread is given; best/worst-case dots as
    their own series; a horizontal guide at 1.0 = ideal."""
    rows = []
    for r in result['terms']:
        if not r.get('found'):
            continue
        row = {'series': 'nominal', 'style': 'dot', 'dash': False,
               'x': r['label'], 'y': r['normalized']}
        if spread and r['term'] in spread:
            row['lo'] = spread[r['term']]['p05']
            row['hi'] = spread[r['term']]['p95']
        rows.append(row)
    for label, case in (('best case (MC)', best),
                        ('worst case (MC)', worst)):
        for r in (case or {}).get('terms', []):
            if r.get('found'):
                rows.append({'series': label, 'style': 'dot',
                             'dash': True, 'x': r['label'],
                             'y': r['normalized']})
    rows.append({'series': 'ideal', 'style': 'hguide', 'dash': True,
                 'x': None, 'y': 1.0, 'label': 'ideal = 1.0'})
    return rows
