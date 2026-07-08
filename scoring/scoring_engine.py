"""
@cross-cutting
@module scoring.scoring_engine
@tags @xc:bindings

The context-based scoring MATH — the Political Scorecard's pipeline
(normalize → context-match by specificity → weighted aggregation →
levelize) as pure functions over manager.objectTables. Everything the
score claims is inspectable: every normalized value travels with the
spec that produced it, every absent term is named (absence is data),
and arbitrary-data values resolve through the SAME objectRef binding
contract the engine models use.

Known divergence, stated not hidden: the scorecard's live TS service
divides the weighted sum by term COUNT; its spreadsheet/sample divides
by TOTAL WEIGHT. We implement the documented spreadsheet behavior
(weighted-mean) and stamp `aggregationNote` on every result.

@consumers
  - scoring.scoring_api (HTTP surface)
@see /OVERLAP_MAP.md
"""

import json

from materialsScience.component_binding import resolve_binding
from scoring.scoring_basis import (
    CONTEXT_TYPES, LOCATION_SPECIFICITY,
)

AGGREGATION_NOTE = (
    'weighted-mean = sum(weight x normalized) / sum(all weights); '
    'missing terms contribute 0 and stay in the denominator (an '
    'absent measurement lowers the score rather than silently '
    'shrinking the basis). The legacy scorecard TS service divides '
    'by term count instead — a known divergence, not copied.'
)


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _by_name(manager, class_name):
    return {getattr(r, 'name', ''): r for r in _rows(manager, class_name)}


def _parse(text, fallback):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)


def context_specificity(context_row):
    """Scorecard idiom: the most specific matching value wins.
    Location granularity dominates; other types use their base rank."""
    ctype = getattr(context_row, 'context_type', 'custom')
    base = CONTEXT_TYPES.get(ctype, 1)
    if ctype == 'location':
        value = _parse(getattr(context_row, 'value_json', '{}'), '{}')
        return LOCATION_SPECIFICITY.get(
            value.get('granularity', ''), base)
    return base


def normalize_value(raw, spec, is_positive, value_pool=None):
    """One raw value → [0, 1] under an EXPLICIT spec.

    spec: {'method': 'min-max', 'min': x, 'max': y} or
          {'method': 'min-max-auto'} (range from value_pool).
    Returns (ok, normalized|None, applied_spec|refusal)."""
    method = (spec or {}).get('method', 'min-max-auto')
    if method not in ('min-max', 'min-max-auto'):
        return False, None, {
            'error': f"unknown normalization method '{method}'",
            'suggestion': {'knob': 'normalization_json',
                           'action': "use 'min-max' (explicit range) "
                                     "or 'min-max-auto'"}}
    if method == 'min-max-auto':
        pool = [v for v in (value_pool or []) if v is not None]
        if len(pool) < 2 or min(pool) == max(pool):
            return False, None, {
                'error': 'min-max-auto needs >= 2 distinct values '
                         f'across subjects (have {len(pool)})',
                'suggestion': {'knob': 'normalization_json',
                               'action': 'set an explicit min/max on '
                                         'the term'}}
        lo, hi = min(pool), max(pool)
    else:
        lo, hi = spec.get('min'), spec.get('max')
        if lo is None or hi is None or lo == hi:
            return False, None, {
                'error': f'min-max spec needs distinct min/max, got '
                         f'min={lo} max={hi}'}
    normalized = (float(raw) - lo) / (hi - lo)
    clamped = min(1.0, max(0.0, normalized))
    if not is_positive:
        clamped = 1.0 - clamped
    return True, clamped, {'method': method, 'min': lo, 'max': hi,
                           'inverted': not is_positive,
                           'clamped': clamped != normalized
                           if is_positive else
                           (1.0 - clamped) != normalized}


def resolve_raw_value(manager, value_row):
    """A value's raw number: stored pre_normalized_value, or resolved
    live through its objectRef data_ref (the arbitrary-data seam)."""
    stored = getattr(value_row, 'pre_normalized_value', None)
    if stored is not None and stored != '':
        try:
            return True, float(stored), {'source': 'stored'}
        except (TypeError, ValueError):
            return False, None, {
                'error': f"pre_normalized_value '{stored}' is not a "
                         'number'}
    ref = _parse(getattr(value_row, 'data_ref_json', ''), 'null')
    if not ref:
        return False, None, {
            'error': 'no stored value and no data_ref',
            'suggestion': {'knob': 'ContextualizedValue',
                           'action': 'set pre_normalized_value or a '
                                     'data_ref objectRef binding'}}
    ok, value, refusal = resolve_binding(manager, ref)
    if not ok:
        return False, None, refusal
    try:
        return True, float(value), {
            'source': f"objectRef {ref.get('className', '')}"
                      f"/{ref.get('name', '')}"
                      + (f".{ref['path']}" if ref.get('path') else '')}
    except (TypeError, ValueError):
        return False, None, {
            'error': f"objectRef resolved to non-numeric "
                     f"'{value}' ({type(value).__name__})"}


def select_value(values, required_contexts, contexts_by_name):
    """Among a (term, subject)'s values, the one matching every
    required context, most specific first. Honest None when nothing
    matches."""
    required = set(required_contexts or [])
    candidates = []
    for row in values:
        held = set(_parse(getattr(row, 'context_names_json', '[]'),
                          '[]'))
        if not required <= held:
            continue
        specificity = sum(
            context_specificity(contexts_by_name[c])
            for c in held if c in contexts_by_name)
        candidates.append((specificity, row))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: -pair[0])
    return candidates[0][1]


def score_concept(manager, concept_name):
    """The full pipeline for one concept: per-subject breakdowns +
    (knob-gated) levelized comparison."""
    concepts = _by_name(manager, 'ScoreConcept')
    concept = concepts.get(concept_name)
    if concept is None:
        return {'ok': False,
                'error': f"no ScoreConcept named '{concept_name}'",
                'knownConcepts': sorted(concepts)}

    terms = _by_name(manager, 'ScoreTerm')
    contexts = _by_name(manager, 'ScoreContext')
    subjects = _by_name(manager, 'ScoreSubject')

    term_weights = _parse(
        getattr(concept, 'term_weights_json', '[]'), '[]')
    required = _parse(
        getattr(concept, 'required_context_names_json', '[]'), '[]')
    picked_names = _parse(
        getattr(concept, 'subject_names_json', '[]'), '[]')
    kind = getattr(concept, 'subject_kind', '')
    picked = [subjects[n] for n in picked_names if n in subjects] \
        if picked_names else \
        [s for s in subjects.values()
         if not kind or getattr(s, 'kind', '') == kind]
    if not picked:
        return {'ok': False,
                'error': 'concept selects no subjects',
                'suggestion': {'knob': 'subject_names_json / '
                                       'subject_kind',
                               'action': 'name subjects or set a kind '
                                         'that has ScoreSubject rows'}}

    # Values indexed by (term, subject); raw pools per term feed
    # min-max-auto so every subject normalizes against the same range.
    values_by_key = {}
    for row in _rows(manager, 'ContextualizedValue'):
        key = (getattr(row, 'term_name', ''),
               getattr(row, 'subject_name', ''))
        values_by_key.setdefault(key, []).append(row)

    raw_cache, pools = {}, {}
    for entry in term_weights:
        term_key = entry.get('term', '')
        for subject in picked:
            sname = getattr(subject, 'name', '')
            chosen = select_value(
                values_by_key.get((term_key, sname), []),
                required, contexts)
            if chosen is None:
                raw_cache[(term_key, sname)] = (
                    False, None, {'error': 'no value under the '
                                           'required contexts'})
                continue
            ok, raw, meta = resolve_raw_value(manager, chosen)
            raw_cache[(term_key, sname)] = (ok, raw, meta) if ok else \
                (False, None, meta)
            if ok:
                pools.setdefault(term_key, []).append(raw)
                raw_cache[(term_key, sname)] = (
                    True, raw, {**meta, 'valueRow':
                                getattr(chosen, 'name', ''),
                                'provenance':
                                getattr(chosen, 'provenance_id', '')})

    total_weight = sum(e.get('weight', 0) for e in term_weights) or 1
    results = []
    for subject in picked:
        sname = getattr(subject, 'name', '')
        breakdown, weighted_sum, missing = [], 0.0, []
        for entry in term_weights:
            term_key = entry.get('term', '')
            weight = entry.get('weight', 0)
            term = terms.get(term_key)
            if term is None:
                missing.append(term_key)
                breakdown.append({'term': term_key, 'weight': weight,
                                  'found': False,
                                  'error': 'no such ScoreTerm'})
                continue
            ok, raw, meta = raw_cache.get(
                (term_key, sname), (False, None, {'error': 'unseen'}))
            if not ok:
                missing.append(term_key)
                breakdown.append({'term': term_key, 'weight': weight,
                                  'found': False, **(meta or {})})
                continue
            spec = _parse(getattr(term, 'normalization_json', ''),
                          '{"method": "min-max-auto"}')
            nok, normalized, applied = normalize_value(
                raw, spec, bool(getattr(term, 'is_positive', True)),
                pools.get(term_key, []))
            if not nok:
                missing.append(term_key)
                breakdown.append({'term': term_key, 'weight': weight,
                                  'found': False, 'raw': raw,
                                  **(applied or {})})
                continue
            weighted = normalized * weight
            weighted_sum += weighted
            breakdown.append({
                'term': term_key,
                'label': getattr(term, 'display_name', term_key),
                'weight': weight,
                'isPositive': bool(getattr(term, 'is_positive', True)),
                'raw': raw, 'unit': getattr(term, 'unit', ''),
                'normalized': round(normalized, 6),
                'weighted': round(weighted, 6),
                'normalization': applied,
                'found': True,
                **{k: v for k, v in (meta or {}).items()
                   if k in ('source', 'valueRow', 'provenance')},
            })
        initial = weighted_sum / total_weight
        results.append({
            'subject': sname,
            'displayName': getattr(subject, 'display_name', '') or sname,
            'kind': getattr(subject, 'kind', ''),
            'weightedSum': round(weighted_sum, 6),
            'initialScore': round(initial, 6),
            'termsMissing': missing,
            'breakdown': breakdown,
        })

    max_initial = max((r['initialScore'] for r in results), default=0)
    levelize = bool(getattr(concept, 'levelize', True))
    for r in results:
        r['levelizedScore'] = (
            round(100.0 * r['initialScore'] / max_initial, 4)
            if levelize and max_initial > 0 else None)
    results.sort(key=lambda r: -r['initialScore'])

    return {
        'ok': True,
        'concept': concept_name,
        'displayName': getattr(concept, 'display_name', '')
        or concept_name,
        'description': getattr(concept, 'description', ''),
        'aggregation': getattr(concept, 'aggregation', 'weighted-mean'),
        'aggregationNote': AGGREGATION_NOTE,
        'totalWeight': total_weight,
        'requiredContexts': required,
        'levelized': levelize,
        'subjects': results,
    }
