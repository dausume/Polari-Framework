"""
@cross-cutting
@module scoring.custom.scoring_engine
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
from scoring.custom.timeframes import (
    combine_over_frame, duration_days, frame_of_context,
    interpolate_at, overlap_days, term_temporal,
    timeframe_specificity,
)

AGGREGATION_NOTE = (
    'weighted-mean = sum(weight x normalized) / sum(all weights); '
    'missing terms contribute 0 and stay in the denominator (an '
    'absent measurement lowers the score rather than silently '
    'shrinking the basis). The legacy scorecard TS service divides '
    'by term count instead — a known divergence, not copied.'
)

#: Nesting depth cap (matches the msim subModel cap, msci-16 idiom).
MAX_NESTING_DEPTH = 8


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
    Location granularity dominates; timeframes grade by duration
    (shorter = more specific); other types use their base rank."""
    ctype = getattr(context_row, 'context_type', 'custom')
    base = CONTEXT_TYPES.get(ctype, 1)
    if ctype == 'location':
        value = _parse(getattr(context_row, 'value_json', '{}'), '{}')
        return LOCATION_SPECIFICITY.get(
            value.get('granularity', ''), base)
    if ctype == 'timeframe':
        frame = frame_of_context(context_row)
        return timeframe_specificity(frame) if frame else base
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


def expand_contexts(held, contexts_by_name):
    """A held context satisfies its ANCESTORS too (a value measured
    for state-california counts for country-usa) — the hierarchy is
    functional, not decorative. Cycle-safe, capped."""
    expanded = set(held)
    for name in held:
        node, hops = contexts_by_name.get(name), 0
        while node is not None and hops < 16:
            parent = getattr(node, 'parent_name', '')
            if not parent or parent in expanded:
                break
            expanded.add(parent)
            node = contexts_by_name.get(parent)
            hops += 1
    return expanded


def select_value(values, required_contexts, contexts_by_name):
    """Among a (term, subject)'s values, the one matching every
    required context (directly or through the context hierarchy),
    most specific first. Honest None when nothing matches."""
    required = set(required_contexts or [])
    candidates = []
    for row in values:
        held = set(_parse(getattr(row, 'context_names_json', '[]'),
                          '[]'))
        if not required <= expand_contexts(held, contexts_by_name):
            continue
        specificity = sum(
            context_specificity(contexts_by_name[c])
            for c in held if c in contexts_by_name)
        candidates.append((specificity, row))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: -pair[0])
    return candidates[0][1]


def _value_frame(value_row, contexts_by_name):
    """A value's most specific timeframe among its held contexts."""
    held = _parse(getattr(value_row, 'context_names_json', '[]'), '[]')
    frames = []
    for name in held:
        ctx = contexts_by_name.get(name)
        frame = frame_of_context(ctx) if ctx is not None else None
        if frame:
            frames.append(frame)
    if not frames:
        return None
    return min(frames, key=duration_days)


def resolve_value_over_time(manager, values, required, contexts_by_name,
                            term, time_policy):
    """(ok, raw, meta) for one (term, subject) under the required
    contexts — the time-aware path (Dustin 2026-07-08: frames
    'coexisting and overlapping and interpolating').

    No required timeframe → the plain most-specific pick. With one:
    a single full-cover value wins (most specific); partial covers
    combine per the term's declared temporal nature (labeled, with
    coverage); a gap interpolates (stocks only, labeled, knob-gated);
    beyond the measured range refuses unless extrapolation is
    explicitly allowed."""
    # The TIME dimension matches by FRAME, not by name — a quarterly
    # value can serve a yearly request (combination) or a neighboring
    # frame (interpolation) that no name/ancestor chain would match.
    target, non_time = None, []
    for name in (required or []):
        ctx = contexts_by_name.get(name)
        frame = frame_of_context(ctx) if ctx is not None else None
        if frame and target is None:
            target = frame
        elif frame:
            pass  # one target frame per evaluation (first wins)
        else:
            non_time.append(name)

    if target is None:
        chosen = select_value(values, required, contexts_by_name)
        if chosen is None:
            return False, None, {'error': 'no value under the '
                                          'required contexts'}
        ok, raw, meta = resolve_raw_value(manager, chosen)
        if not ok:
            return False, None, meta
        return True, raw, {**meta,
                           'valueRow': getattr(chosen, 'name', ''),
                           'provenance':
                           getattr(chosen, 'provenance_id', '')}

    # Candidates satisfy the NON-time requirements (hierarchy applies
    # there); their own frames drive cover/combination/interpolation.
    candidates = []
    for row in values:
        held = set(_parse(getattr(row, 'context_names_json', '[]'),
                          '[]'))
        if set(non_time) <= expand_contexts(held, contexts_by_name):
            candidates.append(row)
    samples, full_cover = [], []
    for row in candidates:
        frame = _value_frame(row, contexts_by_name)
        if frame is None:
            continue
        ok, raw, _ = resolve_raw_value(manager, row)
        if not ok:
            continue
        name = getattr(row, 'name', '')
        samples.append((frame, raw, name))
        if overlap_days(frame, target) == duration_days(target):
            full_cover.append((frame, raw, row))
    if full_cover:
        frame, raw, row = min(full_cover,
                              key=lambda s: duration_days(s[0]))
        return True, raw, {'source': 'stored',
                           'valueRow': getattr(row, 'name', ''),
                           'provenance':
                           getattr(row, 'provenance_id', '')}
    if not samples:
        return False, None, {'error': 'no value under the required '
                                      'contexts'}

    nature, rule = term_temporal(term)
    if rule is None:
        return False, None, {
            'error': f"combining timeframes for "
                     f"'{getattr(term, 'name', '?')}' needs its "
                     'temporal nature declared',
            'suggestion': {'knob': 'ScoreTerm.temporal_json',
                           'action': "set {'nature': 'stock'|'flow'|"
                                     "'event'} so the engine knows "
                                     'how this metric resamples'}}
    overlapping = [s for s in samples if overlap_days(s[0], target)]
    if overlapping:
        ok, raw, meta = combine_over_frame(samples, target, rule)
        if not ok:
            return False, None, meta
        return True, raw, {**meta, 'source':
                           f"derived: {meta['derived']} over "
                           f"{len(meta['fromRows'])} rows "
                           f"(coverage {meta['coverage']})"}
    if not time_policy.get('allowInterpolation', True):
        return False, None, {
            'error': 'no value overlaps the frame and interpolation '
                     'is disabled on this concept',
            'suggestion': {'knob': 'time_policy_json.'
                                   'allowInterpolation',
                           'action': 'enable it, or ingest a value '
                                     'covering the frame'}}
    if nature != 'stock':
        return False, None, {
            'error': f"gap interpolation only applies to 'stock' "
                     f"metrics (this term is '{nature}')"}
    ok, raw, meta = interpolate_at(samples, target)
    if not ok and time_policy.get('allowExtrapolation', False) \
            and 'extrapolation' in meta.get('error', ''):
        frame, raw2, name = min(
            samples, key=lambda s: min(
                abs((s[0][0] - target[1]).days),
                abs((target[0] - s[0][1]).days)))
        return True, raw2, {'derived': 'extrapolated-nearest',
                            'fromRows': [name],
                            'source': 'derived: extrapolated-nearest '
                                      '(explicitly allowed)'}
    if not ok:
        return False, None, meta
    return True, raw, {**meta, 'source':
                       f"derived: interpolated between "
                       f"{' and '.join(meta['fromRows'])} "
                       f"(fraction {meta['fraction']})"}


def score_concept(manager, concept_name, _path=()):
    """The full pipeline for one concept: per-subject breakdowns +
    (knob-gated) levelized comparison.

    Concepts NEST: a term_weights entry {'concept': <name>, 'weight':
    w} scores the child concept per subject and uses its initialScore
    (already 0-1) as the normalized value. Cycles refuse naming the
    path; depth caps at MAX_NESTING_DEPTH (the msci-16 subModel
    idiom). A broken child entry is an honest absence on the parent,
    never a crash."""
    if concept_name in _path:
        cycle = ' → '.join(_path + (concept_name,))
        return {'ok': False,
                'error': f'concept nesting cycle refused: {cycle}',
                'cyclePath': list(_path + (concept_name,))}
    if len(_path) >= MAX_NESTING_DEPTH:
        return {'ok': False,
                'error': f'concept nesting deeper than '
                         f'{MAX_NESTING_DEPTH} refused '
                         f'(path: {" → ".join(_path)})'}
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

    # Nested concepts: each unique child scored ONCE, subjects looked
    # up per parent subject afterwards.
    child_reports = {}
    for entry in term_weights:
        child_name = entry.get('concept', '')
        if child_name and child_name not in child_reports:
            child_reports[child_name] = score_concept(
                manager, child_name, _path + (concept_name,))

    time_policy = _parse(
        getattr(concept, 'time_policy_json', ''),
        '{"allowInterpolation": true, "allowExtrapolation": false}')

    raw_cache, pools = {}, {}
    for entry in term_weights:
        if entry.get('concept'):
            continue
        term_key = entry.get('term', '')
        for subject in picked:
            sname = getattr(subject, 'name', '')
            ok, raw, meta = resolve_value_over_time(
                manager, values_by_key.get((term_key, sname), []),
                required, contexts, terms.get(term_key), time_policy)
            raw_cache[(term_key, sname)] = (ok, raw, meta)
            if ok:
                pools.setdefault(term_key, []).append(raw)

    total_weight = sum(e.get('weight', 0) for e in term_weights) or 1
    results = []
    for subject in picked:
        sname = getattr(subject, 'name', '')
        breakdown, weighted_sum, missing = [], 0.0, []
        for entry in term_weights:
            weight = entry.get('weight', 0)
            child_name = entry.get('concept', '')
            if child_name:
                child = child_reports.get(child_name) or {}
                if not child.get('ok'):
                    missing.append(child_name)
                    breakdown.append({
                        'concept': child_name, 'kind': 'concept',
                        'weight': weight, 'found': False,
                        'error': child.get(
                            'error', 'child concept failed')})
                    continue
                scored = next(
                    (s for s in child['subjects']
                     if s['subject'] == sname), None)
                if scored is None:
                    missing.append(child_name)
                    breakdown.append({
                        'concept': child_name, 'kind': 'concept',
                        'weight': weight, 'found': False,
                        'error': f"child concept '{child_name}' did "
                                 f"not score subject '{sname}'"})
                    continue
                normalized = scored['initialScore']
                weighted = normalized * weight
                weighted_sum += weighted
                breakdown.append({
                    'concept': child_name, 'kind': 'concept',
                    'label': child.get('displayName', child_name),
                    'weight': weight,
                    'normalized': round(normalized, 6),
                    'weighted': round(weighted, 6),
                    'found': True,
                    'source': f"nested concept '{child_name}' "
                              '(initialScore, already 0-1)',
                    'childTermsMissing': scored['termsMissing'],
                })
                continue
            term_key = entry.get('term', '')
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
            # Stance is per-ENTRY when given (a concept may hold a
            # term good that another holds bad — the scorecard's
            # per-ballot isPositive; feeds group divisiveness).
            is_positive = bool(entry.get(
                'isPositive', getattr(term, 'is_positive', True)))
            nok, normalized, applied = normalize_value(
                raw, spec, is_positive, pools.get(term_key, []))
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
                'isPositive': is_positive,
                'raw': raw, 'unit': getattr(term, 'unit', ''),
                'normalized': round(normalized, 6),
                'weighted': round(weighted, 6),
                'normalization': applied,
                'found': True,
                **{k: v for k, v in (meta or {}).items()
                   if k in ('source', 'valueRow', 'provenance',
                            'derived', 'fromRows', 'coverage',
                            'fraction')},
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
        'nestedConcepts': sorted(child_reports),
        'subjects': results,
    }
