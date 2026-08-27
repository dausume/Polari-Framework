"""
@module cntfet.cnt_cell_scoring

fi-2 (cells): scoring the characterized STANDARD CELLS by their
characteristic equations, the same way cnt_scoring scores the FET.
Every cell figure of merit is a ratio to a limit the device's own
model sets, so the ranges are device-independent and the ideal is
computed, never typed:

  delay / τ_int      τ_int = Cgg·Vdd/Ion (the FET's intrinsic
                     FO1 delay, cnt_cells._tau_estimate — floored
                     at (Rs+Rd)·Cgg); ideal 1: a cell cannot switch
                     faster than the transistor that drives it
  transition / τ_int ideal 1 (same limit on the output edge)
  E_supply / (C_L·Vdd²)   supply energy per output transition over
                     the unavoidable load-charging energy at the
                     grid point; ideal 1: zero internal (short-
                     circuit + parasitic) energy
  FETs / FETs_min    transistor count over the x1 minimum for the
                     function; ideal 1 (area proxy — the plan's
                     parasitic grade-up will replace it with a
                     layout-backed area)

Raw values are read from the cell library's OWN Liberty (the text
stored on the CellCharacterizationRun row — parsed, so rows already
characterized on the live node score without a re-run) at the
MID-GRID point (slew index 1, load index 1: the FO-ish reference
the run report itself summarizes). Absent library → named refusal
(the characterize affordance), never zeros.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/device/{name}/cell-scores)
  - cntfet.cnt_device_viz (curve 'cell-scores')
  - polariServer (ScoreTerm / ScoreConcept / ScoreSubject seeds)
  - cntfet.selftest_cntfet
"""

import json
import re

FIDELITY = ('intrinsic-grade cell characterization (polari-own-loop '
            'ngspice transients over the F1 OSDI card, labeled '
            'standin parasitics) scored against the F1 device\'s own '
            'intrinsic limits')

CONCEPT_NAME = 'cell-switching-quality'
SUBJECT_KIND = 'cnt-cell'
CATEGORY = 'cell-figures-of-merit'

CELL_TERMS = {
    'cell-delay-over-tau': {
        'raw': 'delay_over_tau', 'ideal': 1.0, 'unit': 'τ_int',
        'equation': 'mean(cell_rise, cell_fall) over the arcs at '
                    'the mid-grid point / τ_int, τ_int = Cgg·Vdd/Ion',
        'ideal_why': '1: no cell switches faster than the intrinsic '
                     'FO1 delay of the transistor driving it'},
    'cell-transition-over-tau': {
        'raw': 'transition_over_tau', 'ideal': 1.0, 'unit': 'τ_int',
        'equation': 'mean(rise_transition, fall_transition) 20-80 '
                    'at the mid-grid point / τ_int',
        'ideal_why': '1: the output edge is bounded by the same '
                     'intrinsic limit'},
    'cell-energy-over-cv2': {
        'raw': 'energy_over_cv2', 'ideal': 1.0, 'unit': 'C_L·Vdd²',
        'equation': '(E_internal + C_L·Vdd²) / (C_L·Vdd²) at the '
                    'mid-grid load (rising-output arc)',
        'ideal_why': '1: every joule beyond charging the load is '
                     'short-circuit or parasitic energy'},
    'cell-fets-over-min': {
        'raw': 'fets_over_min', 'ideal': 1.0, 'unit': 'x',
        'equation': 'fet_count(cell, drive) / fet_count(cell, 1)',
        'ideal_why': '1: the x1 variant is the minimum transistor '
                     'count for the function (area proxy until '
                     'layout-backed area exists)'},
}


def _term(name, display, key, lo, hi, tags=()):
    t = CELL_TERMS[key]
    return {
        'name': name, 'display_name': display,
        'description': f"{t['equation']}. Ideal: {t['ideal']} "
                       f"({t['ideal_why']}). Range {lo} → {hi}. "
                       f"Raw frame key: {t['raw']}.",
        'category': CATEGORY, 'value_type': 'ratio', 'unit': t['unit'],
        'is_positive': False,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': lo, 'max': hi}),
        'temporal_json': json.dumps({'nature': 'stock',
                                     'resample': 'nearest'}),
        'abstract_tags_json': json.dumps(
            ['cell', 'switching', 'cell-figures-of-merit', *tags]),
        'source': 'cntfet.cnt_cell_scoring (fi-2 cells)',
        'provenance_id': 'FET_INTUITION_PLAN §fi-2 (cells)',
    }


SEED_CELL_SCORE_TERMS = [
    _term('cell-delay-over-tau', 'Delay / τ_int',
          'cell-delay-over-tau', 1.0, 20.0, ('speed',)),
    _term('cell-transition-over-tau', 'Output transition / τ_int',
          'cell-transition-over-tau', 1.0, 20.0, ('speed',)),
    _term('cell-energy-over-cv2', 'Energy / C_L·Vdd²',
          'cell-energy-over-cv2', 1.0, 5.0, ('energy',)),
    _term('cell-fets-over-min', 'FET count / minimum',
          'cell-fets-over-min', 1.0, 4.0, ('area',)),
]

SEED_CELL_SCORE_CONCEPTS = [{
    'name': CONCEPT_NAME,
    'display_name': 'Cell switching quality',
    'description': 'Weighted mean of the standard-cell figures of '
                   'merit, each a ratio to the driving FET\'s own '
                   'intrinsic limit (cntfet.cnt_cell_scoring '
                   'CELL_TERMS). Weights are knobs; raw values come '
                   'from the characterized Liberty on the cell '
                   'library run row.',
    'subject_kind': SUBJECT_KIND,
    'subject_names_json': '[]',
    'term_weights_json': json.dumps(
        [{'term': k, 'weight': 1} for k in CELL_TERMS]),
    'required_context_names_json': '[]',
    'aggregation': 'weighted-mean',
    'levelize': True,
    'abstract_tags_json': json.dumps(['cell', 'switching',
                                      'cell-figures-of-merit']),
    'provenance_id': 'FET_INTUITION_PLAN §fi-2 (cells)',
}]


def seed_cell_subjects(cell_names):
    """ScoreSubject rows per CNTCellDefinition name (object_ref →
    the cell row; object coherence)."""
    return [{
        'name': f'cell-{n}', 'display_name': n, 'kind': SUBJECT_KIND,
        'object_ref_json': json.dumps(
            {'kind': 'objectRef', 'className': 'CNTCellDefinition',
             'name': n}),
        'description': 'The generated cell-variant row IS the '
                       'subject; scores come from the device\'s '
                       'cell-scores surface.',
    } for n in cell_names]


# ── our own Liberty, read back ─────────────────────────────────────

_NUM = r'[-+0-9.eE]+'


def parse_liberty(text):
    """{cellName: {'inputCap_ff', 'arcs': {pin: {kind: rows}}},
    'index_1': [...], 'index_2': [...]} from the cnt_cell_library
    emitter's format (and only that format — stated)."""
    idx1 = re.search(r'index_1 \("([^"]*)"\)', text)
    idx2 = re.search(r'index_2 \("([^"]*)"\)', text)
    index_1 = [float(v) for v in idx1.group(1).split(',')] if idx1 \
        else []
    index_2 = [float(v) for v in idx2.group(1).split(',')] if idx2 \
        else []
    cells = {}
    # lookahead keeps the separating newline for the NEXT cell block
    for m in re.finditer(r'\n  cell \(([^)]+)\) \{\n(.*?)\n  \}(?=\n)',
                         text, re.S):
        name, body = m.group(1), m.group(2)
        cap = re.search(r'capacitance : (' + _NUM + ')', body)
        arcs = {}
        for blk in re.finditer(
                r'(timing|internal_power) \(\) \{\n\s*related_pin : '
                r'"([^"]+)";(.*?)\n      \}', body, re.S):
            pin = blk.group(2)
            tables = arcs.setdefault(pin, {})
            for tb in re.finditer(
                    r'(cell_rise|cell_fall|rise_transition|'
                    r'fall_transition|rise_power|fall_power) '
                    r'\([^)]*\) \{.*?values \((.*?)\);', blk.group(3),
                    re.S):
                rows = [[float(v) for v in row.split(',')]
                        for row in re.findall(r'"([^"]*)"',
                                              tb.group(2))]
                tables.setdefault(tb.group(1), rows)
        cells[name] = {'inputCap_ff': float(cap.group(1)) if cap
                       else None, 'arcs': arcs}
    return {'index_1_ps': index_1, 'index_2_ff': index_2,
            'cells': cells}


def _latest_library_row(manager, device_name):
    table = (getattr(manager, 'objectTables', {}) or {}).get(
        'CellCharacterizationRun') or {}
    rows = [r for r in (table.values() if isinstance(table, dict)
                        else table)
            if getattr(r, 'device', '') == device_name
            and str(getattr(r, 'cell', '')).startswith('library:')
            and getattr(r, 'liberty_text', '')]
    if not rows:
        return None
    return max(rows, key=lambda r: getattr(r, 'ran_at', ''))


def _liberty_to_cell(liberty_name):
    """INVX1 → ('cinv', 1) via the library's own naming."""
    from cntfet.cnt_cell_library import (
        CELL_LIBRARY, DRIVES, liberty_cell_name,
    )
    for key in CELL_LIBRARY:
        for drive in DRIVES:
            if liberty_cell_name(key, drive) == liberty_name:
                return key, drive
    return None, None


def cell_frames(parsed, tau_s, vdd):
    """Per-cell raw figures at the mid-grid point + the ideals."""
    from cntfet.cnt_cell_library import fet_count
    i1 = len(parsed['index_1_ps']) // 2
    i2 = len(parsed['index_2_ff']) // 2
    load_f = (parsed['index_2_ff'][i2] * 1e-15
              if parsed['index_2_ff'] else None)
    cv2 = load_f * vdd * vdd if load_f else None
    tau_ps = tau_s * 1e12
    frames = {}
    for name, cell in parsed['cells'].items():
        key, drive = _liberty_to_cell(name)
        delays, trans, energies = [], [], []
        for pin, tables in cell['arcs'].items():
            try:
                delays.append(0.5 * (tables['cell_rise'][i1][i2]
                                     + tables['cell_fall'][i1][i2]))
                trans.append(0.5 * (tables['rise_transition'][i1][i2]
                                    + tables['fall_transition'][i1][i2]))
                energies.append(tables['rise_power'][i1][i2])
            except (KeyError, IndexError):
                continue
        if not delays:
            frames[name] = {'refusal': 'no complete arc table'}
            continue
        delay_ps = sum(delays) / len(delays)
        tran_ps = sum(trans) / len(trans)
        e_int_aj = sum(energies) / len(energies)
        fets = fet_count(key, drive) if key else None
        fets_min = fet_count(key, 1) if key else None
        frames[name] = {
            'cell': key, 'drive': drive,
            'delay_ps': delay_ps, 'transition_ps': tran_ps,
            'energy_internal_aJ': e_int_aj,
            'energy_supply_aJ': (e_int_aj + cv2 * 1e18) if cv2 else None,
            'load_cv2_aJ': cv2 * 1e18 if cv2 else None,
            'tau_int_ps': tau_ps,
            'fet_count': fets, 'fet_count_min': fets_min,
            'delay_over_tau': delay_ps / tau_ps if tau_ps else None,
            'transition_over_tau': tran_ps / tau_ps if tau_ps else None,
            'energy_over_cv2': ((e_int_aj + cv2 * 1e18) / (cv2 * 1e18)
                                if cv2 else None),
            'fets_over_min': (fets / fets_min
                              if fets and fets_min else None),
            'gridPoint': {'slew_ps': parsed['index_1_ps'][i1],
                          'load_ff': parsed['index_2_ff'][i2]},
        }
    return frames


def _term_rows(manager):
    rows = {}
    if manager is not None:
        table = getattr(manager, 'objectTables', {}).get(
            'ScoreTerm') or {}
        for row in (table.values() if isinstance(table, dict)
                    else table):
            if getattr(row, 'name', '') in CELL_TERMS:
                rows[row.name] = {
                    'name': row.name, 'display_name': row.display_name,
                    'unit': row.unit, 'is_positive': row.is_positive,
                    'normalization_json': row.normalization_json}
    for seed in SEED_CELL_SCORE_TERMS:
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
    return json.loads(SEED_CELL_SCORE_CONCEPTS[0]['term_weights_json'])


def score_cell_frame(frame, manager=None):
    """Same shape as cnt_scoring.score_from_frame, over CELL_TERMS."""
    from scoring.scoring_engine import AGGREGATION_NOTE, normalize_value
    terms, weights = _term_rows(manager), _weights(manager)
    rows, missing, weighted_sum = [], [], 0.0
    total_weight = sum(w.get('weight', 0) for w in weights) or 1
    for entry in weights:
        key = entry.get('term', '')
        reg, term = CELL_TERMS.get(key), terms.get(key)
        weight = entry.get('weight', 0)
        if reg is None or term is None:
            missing.append(key)
            rows.append({'term': key, 'weight': weight, 'found': False,
                         'error': 'no such cell term'})
            continue
        raw = frame.get(reg['raw'])
        if raw is None:
            missing.append(key)
            rows.append({'term': key, 'label': term['display_name'],
                         'weight': weight, 'found': False,
                         'error': f'{reg["raw"]} unmeasured'})
            continue
        ok, normalized, applied = normalize_value(
            raw, json.loads(term['normalization_json']),
            bool(term['is_positive']))
        if not ok:
            missing.append(key)
            rows.append({'term': key, 'weight': weight, 'found': False,
                         'raw': raw, **applied})
            continue
        weighted_sum += normalized * weight
        rows.append({'term': key, 'label': term['display_name'],
                     'weight': weight, 'found': True,
                     'unit': term['unit'], 'equation': reg['equation'],
                     'raw': raw, 'ideal': reg['ideal'],
                     'distance': abs(raw - reg['ideal']),
                     'ideal_why': reg['ideal_why'],
                     'isPositive': bool(term['is_positive']),
                     'normalized': round(normalized, 6),
                     'weighted': round(normalized * weight, 6),
                     'normalization': applied})
    return {'score': round(weighted_sum / total_weight, 6),
            'totalWeight': total_weight, 'termsMissing': missing,
            'terms': rows, 'aggregation': 'weighted-mean',
            'aggregationNote': AGGREGATION_NOTE}


def score_cells(manager, device_name, liberty_text=None):
    """The /cell-scores payload: every characterized cell of the
    device's latest library run, scored; refuses by name without a
    run."""
    from cntfet.cnt_cells import _tau_estimate
    from cntfet.cnt_device_viz import device_model
    id_fn, p, device, refusal = device_model(manager, device_name)
    if refusal is not None:
        return refusal
    run_name, vdd = None, 0.6
    if liberty_text is None:
        row = _latest_library_row(manager, device_name)
        if row is None:
            return {'ok': False,
                    'error': f'no cell-library characterization run '
                             f'for "{device_name}" — POST '
                             f'{{"action": "characterize-cells"}} to '
                             f'/api/cntfet/devices/{device_name} '
                             f'first (ngspice + OSDI on the engines '
                             f'worker)'}
        liberty_text, run_name = row.liberty_text, row.name
        vdd = getattr(row, 'vdd_v', 0.6) or 0.6
    parsed = parse_liberty(liberty_text)
    if not parsed['cells']:
        return {'ok': False, 'error': 'library text holds no cell '
                                      'blocks (not the '
                                      'cnt_cell_library format?)'}
    tau = _tau_estimate({**p, 'ptype': 0}, vdd)
    frames = cell_frames(parsed, tau, vdd)
    cells = []
    for name in sorted(frames):
        frame = frames[name]
        if 'refusal' in frame:
            cells.append({'cell': name, 'ok': False,
                          'error': frame['refusal']})
            continue
        cells.append({'cell': name, 'ok': True, 'frame': frame,
                      **score_cell_frame(frame, manager)})
    scored = [c for c in cells if c['ok']]
    return {
        'ok': True, 'device': device_name, 'concept': CONCEPT_NAME,
        'fidelity': FIDELITY, 'run': run_name, 'vdd_v': vdd,
        'tau_int_ps': tau * 1e12,
        'gridPoint': next((c['frame']['gridPoint'] for c in scored),
                          None),
        'cells': cells,
        'ranking': [{'cell': c['cell'], 'score': c['score']}
                    for c in sorted(scored, key=lambda c: -c['score'])],
        'idealTable': [
            {'term': k, 'equation': v['equation'], 'ideal': v['ideal'],
             'why': v['ideal_why'], 'unit': v['unit']}
            for k, v in CELL_TERMS.items()],
    }


def cell_score_rows(report):
    """Rows for `cnt-device-cell-scores`: x = cell (categorical),
    one series per term (normalized) + the overall score, hguide at
    1.0."""
    rows = []
    for c in report.get('cells', []):
        if not c.get('ok'):
            continue
        rows.append({'series': 'score', 'style': 'dot', 'dash': False,
                     'x': c['cell'], 'y': c['score']})
        for t in c['terms']:
            if t.get('found'):
                rows.append({'series': t['label'], 'style': 'dot',
                             'dash': True, 'x': c['cell'],
                             'y': t['normalized']})
    rows.append({'series': 'ideal', 'style': 'hguide', 'dash': True,
                 'x': None, 'y': 1.0, 'label': 'ideal = 1.0'})
    return rows
