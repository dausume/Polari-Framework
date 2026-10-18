"""
@module cmod.custom.fsc_profiles

fsc-1/fsc-2: Firmware Score PROFILES, stored as `scoring.ScoreConcept` rows (no new class). A profile is a named, weighted set of terms:

  term_weights_json  [{"term": t, "weight": w}                         whole-solution weight (context hardware:<board>)
                      {"term": t, "weight": w, "purpose": P}           that term for ONE Purpose (context purpose:P) - per-Purpose weighting
                      ... "fallback": [{"term": t2, "weight": w2}]     used instead when the term has no cited value anywhere in the compared set (said on the breakdown)]
  time_policy_json   {"fsc": {normalization, accept_used, accept_local, hardware, alpha, compat_weights, bench_gate}}   (the engine ignores the key; see KNOWN_KNOBS)

Score = sum_p alpha_p x (sum_t w_t,p x norm(v_t,p) / sum_t w_t,p), then min-max across the compared set (top 100, bottom 0) - cmod.custom.fsc_score.
SEEDED profiles (provenance_id `fsc-seed`) are never edited in place: a person COPIES one and edits the copy (`create`). Today's two objectives are profiles too (`minimum-resources`,
`fastest-cycle`), with a stated `sol-0-compatible` normalization so sol-0's ranking is reproduced and proven; every profile defaults to competitive normalization.
"""
import json

from cmod.custom import fsc_terms as T

SEED_TAG = 'fsc-seed'
USER_TAG = 'fsc-user'
KNOWN_KNOBS = ('normalization', 'accept_used', 'accept_local', 'hardware', 'alpha', 'compat_weights', 'bench_gate')
KNOWN_BODY_KEYS = ('name', 'copy_of', 'display_name', 'description', 'weights', 'purpose_weights', 'alpha', 'knobs', 'hardware', 'remove')
COST_FALLBACK = [{'term': 'cost-to-build-now', 'weight': 0.5}, {'term': 'parts-to-acquire', 'weight': 0.5}]
UNO = 'arduino-uno-r3'
P_BUTTON, P_COMMAND, P_REPORT = 'ensure-button-controls-light', 'ensure-polari-can-control-light', 'ensure-polari-observes-hardware-state'


def _e(term, weight, purpose=None, fallback=None):
    e = {'term': term, 'weight': weight}
    if purpose:
        e['purpose'] = purpose
    if fallback:
        e['fallback'] = fallback
    return e


def _row(name, display, description, entries, knobs=None):
    return {'name': name, 'display_name': display, 'description': description, 'subject_kind': 'mission-solution', 'subject_names_json': '[]',
            'term_weights_json': json.dumps(entries), 'required_context_names_json': '[]', 'aggregation': 'weighted-mean', 'levelize': True,
            'abstract_tags_json': json.dumps(['firmware', 'score-profile']), 'time_policy_json': json.dumps({'fsc': dict(knobs or {})}), 'provenance_id': SEED_TAG,
            'notes': 'Seeded sample profile (FIRMWARE_SCORE_PROFILES_PLAN.md section 5; his answer D-fsc-4: "The sample profiles sound good"). His to rename and re-weight: copy it, then edit the copy.'}


def seed_rows():
    cheap = _e('bom-cost', 1.0, fallback=COST_FALLBACK)
    return [
        _row('fsc-fastest', 'Fastest', 'Only the Mission cycle time counts: the quickest solution wins.', [_e('mission-cycle', 1.0)]),
        _row('fsc-cheapest', 'Cheapest', 'Only money counts: the cheapest cited offers for every part, the board included. Until a price is cited for the parts it falls back to cost-to-build-now and parts-to-acquire, and says so.', [cheap]),
        _row('fsc-build-it-today', 'Build it today', 'What it costs to build with what is on the bench now, how few wires, and how much of the picture is evidenced.',
             [_e('cost-to-build-now', 0.5), _e('wires', 0.3), _e('confidence', 0.2)]),
        _row('fsc-balanced', 'Balanced', 'Cycle 0.3, cost 0.3, headroom 0.2 (flash, RAM, pins, blocks), robustness 0.2 (open risks, shared resources).',
             [_e('mission-cycle', 0.3), _e('bom-cost', 0.3), _e('flash-free', 0.05), _e('ram-free', 0.05), _e('pins-free', 0.05), _e('blocks-free', 0.05), _e('risk-points', 0.1), _e('shared-resources', 0.1)]),
        _row('fsc-battery', 'Battery', 'Running current 0.5 (UNDETERMINED until current figures are cited: scored at the midpoint and said), can-sleep 0.4, cycle 0.1.',
             [_e('active-current', 0.5), _e('sleep-capable', 0.4), _e('mission-cycle', 0.1)]),
        _row('fsc-room-to-grow', 'Room to grow', 'Flash, RAM, pins and chip blocks left, a quarter each.', [_e('flash-free', 0.25), _e('ram-free', 0.25), _e('pins-free', 0.25), _e('blocks-free', 0.25)]),
        _row('fsc-most-trustworthy', 'Most trustworthy', 'How much of the picture is measured, how far the Purposes are proven, and how few open risks.',
             [_e('confidence', 0.4), _e('proof-level', 0.4), _e('risk-points', 0.2)]),
        _row('minimum-resources', 'Minimum resources (sol-0)', 'Today\'s first objective, sol-0\'s equation as a profile: pins 3, chip blocks 2, parts to get 3, part classes 0.5, flash 1, RAM 1, CPU 1. The "sol-0-compatible" normalization reproduces sol-0 order exactly.',
             [_e('pins-free', 3.0), _e('blocks-free', 2.0), _e('parts-to-acquire', 3.0), _e('part-count', 0.5), _e('flash-free', 1.0), _e('ram-free', 1.0), _e('cpu-idle', 1.0)],
             {'compat_weights': {'pins-free': 3.0, 'blocks-free': 2.0, 'parts-to-acquire': 30.0, 'part-count': 0.5, 'flash-free': 1.0, 'ram-free': 1.0, 'cpu-idle': 1.0}}),
        _row('fastest-cycle', 'Fastest cycle (sol-0)', 'Today\'s second objective: the Mission cycle time. In "sol-0-compatible" mode a solution that needs a part the bench lacks ranks after every buildable one, as sol-0 does.',
             [_e('mission-cycle', 1.0)], {'bench_gate': True}),
        _row('fsc-uno-r3-per-purpose', 'UNO R3, weighted per Purpose',
             'Unique to the arduino-uno-r3 hardware, weighting speed against cost per Purpose: button-controls-light latency 0.8 / cost 0.2; Polari-controls-light latency 0.5 / cost 0.5; Polari-observes-state cost 0.8 / latency 0.2. '
             'Each Purpose counts in proportion to its importance weight; a shared route\'s cost is split the same way.',
             [_e('worst-purpose-latency', 0.8, P_BUTTON), _e('bom-cost', 0.2, P_BUTTON, COST_FALLBACK),
              _e('worst-purpose-latency', 0.5, P_COMMAND), _e('bom-cost', 0.5, P_COMMAND, COST_FALLBACK),
              _e('worst-purpose-latency', 0.2, P_REPORT), _e('bom-cost', 0.8, P_REPORT, COST_FALLBACK)],
             {'hardware': UNO, 'alpha': {P_BUTTON: 3.0, P_COMMAND: 3.0, P_REPORT: 3.0}}),
    ]


def _get(row, key, default=''):
    return row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)


def parse(row):
    """A ScoreConcept row (dict or object) -> {name, display_name, description, seeded, entries, knobs}."""
    try:
        entries = json.loads(_get(row, 'term_weights_json') or '[]')
    except ValueError:
        entries = []
    try:
        tp = json.loads(_get(row, 'time_policy_json') or '{}')
    except ValueError:
        tp = {}
    knobs = dict({'normalization': 'competitive', 'accept_used': T.PRICE_KNOBS['accept_used'], 'accept_local': T.PRICE_KNOBS['accept_local']}, **(tp.get('fsc') or {}))
    return {'name': _get(row, 'name'), 'display_name': _get(row, 'display_name') or _get(row, 'name'), 'description': _get(row, 'description'),
            'seeded': _get(row, 'provenance_id') == SEED_TAG, 'entries': entries, 'knobs': knobs, 'hardware': knobs.get('hardware', '')}


def all_profiles(manager=None):
    """Seeded profiles first, then every ScoreConcept row tagged as a firmware profile (live rows win over the seed of the same name)."""
    out = {r['name']: parse(r) for r in seed_rows()}
    for row in ((getattr(manager, 'objectTables', None) or {}).get('ScoreConcept') or {}).values():
        if _get(row, 'provenance_id') in (SEED_TAG, USER_TAG) and 'firmware' in (_get(row, 'abstract_tags_json') or ''):
            out[_get(row, 'name')] = parse(row)
    return out


def public(p):
    purposes = sorted({e['purpose'] for e in p['entries'] if e.get('purpose')})
    return {'name': p['name'], 'display_name': p['display_name'], 'description': p['description'], 'seeded': p['seeded'], 'editable': not p['seeded'], 'hardware': p['hardware'],
            'normalization': p['knobs'].get('normalization', 'competitive'), 'accept_used': p['knobs']['accept_used'], 'accept_local': p['knobs']['accept_local'],
            'terms': [dict(e) for e in p['entries']], 'purposes': purposes, 'alpha': p['knobs'].get('alpha') or {}}


def validate_body(body, known_purposes=()):
    """-> list of refusal strings naming what is known (empty = fine)."""
    errs = []
    bad = sorted(k for k in body if k not in KNOWN_BODY_KEYS)
    if bad:
        errs.append('unknown key(s) %s (known: %s)' % (', '.join(bad), ', '.join(KNOWN_BODY_KEYS)))
    for tname in list((body.get('weights') or {}).keys()):
        if tname not in T.TERM_NAMES:
            errs.append('unknown term %r in weights (known terms: %s)' % (tname, ', '.join(T.TERM_NAMES)))
    for pn, d in (body.get('purpose_weights') or {}).items():
        if known_purposes and pn not in known_purposes:
            errs.append('unknown Purpose %r in purpose_weights (known: %s)' % (pn, ', '.join(sorted(known_purposes))))
        for tname in (d or {}):
            if tname not in T.TERM_NAMES:
                errs.append('unknown term %r for Purpose %s (known terms: %s)' % (tname, pn, ', '.join(T.TERM_NAMES)))
    for k in (body.get('knobs') or {}):
        if k not in KNOWN_KNOBS:
            errs.append('unknown knob %r (known: %s)' % (k, ', '.join(KNOWN_KNOBS)))
    n = (body.get('knobs') or {}).get('normalization')
    if n is not None and n not in T.NORMALIZATIONS:
        errs.append('unknown normalization %r (one of %s)' % (n, ', '.join(T.NORMALIZATIONS)))
    for w in list((body.get('weights') or {}).values()) + [x for d in (body.get('purpose_weights') or {}).values() for x in (d or {}).values()]:
        if not isinstance(w, (int, float)) or isinstance(w, bool) or w < 0:
            errs.append('a weight must be a number >= 0, got %r' % (w,))
            break
    return errs


def apply_body(base, body):
    """The new (entries, knobs, description, display) from a base profile dict and a validated body. Weights REPLACE the entry of the same (term, purpose); a weight 0 removes it."""
    entries = [dict(e) for e in base['entries']]
    knobs = dict(base['knobs'])
    idx = {(e['term'], e.get('purpose', '')): i for i, e in enumerate(entries)}

    def put(term, w, purpose=''):
        k = (term, purpose)
        if k in idx:
            entries[idx[k]]['weight'] = w
        else:
            e = {'term': term, 'weight': w}
            if purpose:
                e['purpose'] = purpose
            entries.append(e)
            idx[k] = len(entries) - 1
    for t, w in (body.get('weights') or {}).items():
        put(t, w)
    for pn, d in (body.get('purpose_weights') or {}).items():
        for t, w in (d or {}).items():
            put(t, w, pn)
    entries = [e for e in entries if e['weight'] > 0]
    if body.get('alpha'):
        knobs['alpha'] = dict(body['alpha'])
    knobs.update(body.get('knobs') or {})
    if body.get('hardware') is not None:
        knobs['hardware'] = body['hardware']
    return entries, knobs


def save(manager, name, base, entries, knobs, display='', description=''):
    """Create or update the user's ScoreConcept row. -> the row (or a plain dict when the manager holds no ScoreConcept class)."""
    fields = dict(name=name, display_name=display or base['display_name'], description=description or base['description'], subject_kind='mission-solution',
                  term_weights_json=json.dumps(entries), aggregation='weighted-mean', levelize=True, abstract_tags_json=json.dumps(['firmware', 'score-profile']),
                  time_policy_json=json.dumps({'fsc': knobs}), provenance_id=USER_TAG,
                  notes='Copied from %s' % base['name'] if base.get('name') != name else '')
    table = (manager.objectTables or {}).setdefault('ScoreConcept', {}) if manager is not None else {}
    row = next((r for r in table.values() if getattr(r, 'name', '') == name), None)
    if row is not None:
        for k, v in fields.items():
            setattr(row, k, v)
    else:
        from scoring.score_concept_basis import ScoreConcept
        row = ScoreConcept(manager=manager, **fields)
    db = getattr(manager, 'db', None)
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        try:
            db.saveInstanceInDB(row)
        except Exception:  # noqa: BLE001 - logged by the DB layer; the row stays in the tree
            pass
    return row
