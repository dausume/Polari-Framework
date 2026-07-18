"""
@cross-cutting
@module scoring.specificity
@tags @xc:bindings

Specificity conformance + critical-context suggestions (scr-5).
Dustin 2026-07-08: "intelligent contextualization to ensure
specificity of our terms and that the terms match to the specificity
of the score itself".

check_concept_specificity — slot-by-slot findings (the
msim-conformance idiom): for each term × subject of a concept, does
the value that would actually be selected match the specificity the
concept asks for? Findings are evidence-bearing and name knobs; they
never block scoring (the engine already answers honestly — this is
the diagnosis of HOW honest that answer can be).

suggest_critical_contexts — the scorecard's designed-never-built
CriticalContext, as suggestions: a variance scan over context slices
finds the contexts under which a concept's raw values diverge most —
the slices worth requiring explicitly.

@consumers
  - scoring.scoring_api (GET /api/scoring/concepts/{name}/specificity
    + /critical-contexts)
@see /OVERLAP_MAP.md
"""

import json

from scoring.scoring_engine import (
    context_specificity, expand_contexts, resolve_value_over_time,
)
from scoring.timeframes import duration_days, frame_of_context


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


def _concept_subjects(manager, concept, subjects):
    picked_names = _parse(
        getattr(concept, 'subject_names_json', '[]'), '[]')
    kind = getattr(concept, 'subject_kind', '')
    if picked_names:
        return [subjects[n] for n in picked_names if n in subjects]
    return [s for s in subjects.values()
            if not kind or getattr(s, 'kind', '') == kind]


def check_concept_specificity(manager, concept_name):
    """Per term × subject: what value the ENGINE would actually serve
    (resolve_value_over_time is the oracle — no separate matching
    logic to diverge), at what specificity, versus what the concept
    requires. Finding kinds:

      missing-value        — the engine refuses (nothing satisfies
                             the required contexts); carries the
                             engine's own refusal.
      ancestor-only-match  — a non-time requirement is held only
                             through the hierarchy (MORE specific
                             than asked — fine, labeled).
      less-time-specific   — served directly from a frame LONGER than
                             the required one (a full-cover year
                             answering a quarter): honest, but a
                             finer series would be more specific.
      derived-timeframe    — the answer will be combined/interpolated
                             (labeled by the engine) instead of
                             measured.
      specificity-imbalance— subjects' served values for the same
                             term hold at different specificity
                             levels (the comparison is honest but
                             uneven).
      undeclared-temporal  — values carry timeframes but the term has
                             no temporal_json (cross-frame
                             combination will refuse until declared)."""
    concepts = _by_name(manager, 'ScoreConcept')
    concept = concepts.get(concept_name)
    if concept is None:
        return {'ok': False,
                'error': f"no ScoreConcept named '{concept_name}'",
                'knownConcepts': sorted(concepts)}
    terms = _by_name(manager, 'ScoreTerm')
    contexts = _by_name(manager, 'ScoreContext')
    subjects = _by_name(manager, 'ScoreSubject')
    required = _parse(
        getattr(concept, 'required_context_names_json', '[]'), '[]')
    term_weights = _parse(
        getattr(concept, 'term_weights_json', '[]'), '[]')
    picked = _concept_subjects(manager, concept, subjects)

    values_by_key = {}
    for row in _rows(manager, 'ContextualizedValue'):
        key = (getattr(row, 'term_name', ''),
               getattr(row, 'subject_name', ''))
        values_by_key.setdefault(key, []).append(row)

    # The first required timeframe is the engine's target frame; the
    # rest of the requirements match by name/ancestor.
    target = next(
        (frame_of_context(contexts[n]) for n in required
         if n in contexts and frame_of_context(contexts[n])), None)
    non_time = [n for n in required
                if not (n in contexts and frame_of_context(contexts[n]))]
    time_policy = {'allowInterpolation': True,
                   'allowExtrapolation': False}
    value_rows = {getattr(r, 'name', ''): r
                  for r in _rows(manager, 'ContextualizedValue')}
    findings = []
    for entry in term_weights:
        term_key = entry.get('term', '')
        if not term_key:
            continue  # nested concepts diagnose on their own report
        term = terms.get(term_key)
        served_specificities = {}
        for subject in picked:
            sname = getattr(subject, 'name', '')
            values = values_by_key.get((term_key, sname), [])
            ok, _, meta = resolve_value_over_time(
                manager, values, required, contexts, term,
                time_policy)
            if not ok:
                findings.append({
                    'kind': 'missing-value',
                    'term': term_key, 'subject': sname,
                    'evidence': f'{len(values)} value rows exist for '
                                f'this pair; engine refusal: '
                                f'{(meta or {}).get("error", "")}',
                    'suggestion': (meta or {}).get('suggestion') or {
                        'knob': 'POST /api/scoring/ingest',
                        'action': f"ingest '{term_key}' for "
                                  f"'{sname}' under the required "
                                  'contexts'}})
                continue
            if meta.get('derived') \
                    or str(meta.get('source', '')).startswith(
                        'derived'):
                findings.append({
                    'kind': 'derived-timeframe',
                    'term': term_key, 'subject': sname,
                    'evidence': {k: v for k, v in meta.items()
                                 if k in ('derived', 'fromRows',
                                          'coverage', 'fraction',
                                          'source')},
                    'suggestion': {
                        'knob': 'POST /api/scoring/ingest',
                        'action': f"ingest '{term_key}' measured at "
                                  'the required grain so the answer '
                                  'is measured, not derived'}})
                continue
            chosen = value_rows.get(meta.get('valueRow', ''))
            if chosen is None:
                continue
            held = _parse(
                getattr(chosen, 'context_names_json', '[]'), '[]')
            specificity = sum(
                context_specificity(contexts[c])
                for c in held if c in contexts)
            served_specificities[sname] = (specificity, held)
            direct = set(non_time) & set(held)
            via_hierarchy = set(non_time) - direct
            if via_hierarchy and set(non_time) <= expand_contexts(
                    set(held), contexts):
                findings.append({
                    'kind': 'ancestor-only-match',
                    'term': term_key, 'subject': sname,
                    'evidence': f'required {sorted(via_hierarchy)} '
                                f'satisfied through the hierarchy by '
                                f'{held} — the value is MORE specific '
                                'than asked (fine; labeled for the '
                                'reader)'})
            if target is not None:
                frames = [
                    frame_of_context(contexts[c]) for c in held
                    if c in contexts and frame_of_context(contexts[c])]
                if frames and min(
                        duration_days(f) for f in frames) \
                        > duration_days(target):
                    findings.append({
                        'kind': 'less-time-specific',
                        'term': term_key, 'subject': sname,
                        'evidence': f'served from a '
                                    f'{min(duration_days(f) for f in frames)}'
                                    f'-day frame covering the required '
                                    f'{duration_days(target)}-day one '
                                    '— honest, but coarser than asked',
                        'suggestion': {
                            'knob': 'POST /api/scoring/ingest',
                            'action': f"ingest '{term_key}' at the "
                                      'required grain'}})
        if len({spec for spec, _ in
                served_specificities.values()}) > 1:
            detail = {s: spec for s, (spec, _)
                      in served_specificities.items()}
            findings.append({
                'kind': 'specificity-imbalance',
                'term': term_key,
                'evidence': f'selected values hold at different '
                            f'specificity per subject: {detail}',
                'suggestion': {
                    'knob': 'ContextualizedValue',
                    'action': 'ingest the lagging subjects at the '
                              'same specificity so the comparison '
                              'is even'}})
        # Temporal declaration: frames on values, silence on the term.
        if term is not None:
            temporal = _parse(
                getattr(term, 'temporal_json', '{}'), '{}')
            any_frames = any(
                frame_of_context(contexts[c])
                for subject in picked
                for row in values_by_key.get(
                    (term_key, getattr(subject, 'name', '')), [])
                for c in _parse(
                    getattr(row, 'context_names_json', '[]'), '[]')
                if c in contexts)
            if any_frames and not temporal.get('nature'):
                findings.append({
                    'kind': 'undeclared-temporal',
                    'term': term_key,
                    'evidence': 'values carry timeframes but the term '
                                'declares no temporal nature — any '
                                'cross-frame combination will refuse',
                    'suggestion': {
                        'knob': 'ScoreTerm.temporal_json',
                        'action': "declare {'nature': 'stock'|'flow'|"
                                  "'event', 'resample': ...}"}})

    return {'ok': True, 'concept': concept_name,
            'requiredContexts': required,
            'subjects': [getattr(s, 'name', '') for s in picked],
            'findings': findings,
            'clean': not findings,
            'note': 'findings diagnose, never block — the engine '
                    'already answers honestly; these name what would '
                    'make the answer measured instead of derived'}


def suggest_critical_contexts(manager, concept_name):
    """Contexts under which this concept's raw values diverge most —
    the slices worth requiring explicitly (the scorecard's designed
    CriticalContext, as evidence-bearing suggestions). Per (term,
    context): the slice's spread as a fraction of the term's full
    spread; high ratio = the context carries real variation."""
    concepts = _by_name(manager, 'ScoreConcept')
    concept = concepts.get(concept_name)
    if concept is None:
        return {'ok': False,
                'error': f"no ScoreConcept named '{concept_name}'",
                'knownConcepts': sorted(concepts)}
    term_keys = [e.get('term', '') for e in _parse(
        getattr(concept, 'term_weights_json', '[]'), '[]')
        if e.get('term')]
    contexts = _by_name(manager, 'ScoreContext')

    per_context = {}
    full_pool = {}
    for row in _rows(manager, 'ContextualizedValue'):
        term = getattr(row, 'term_name', '')
        if term not in term_keys:
            continue
        raw = getattr(row, 'pre_normalized_value', None)
        if raw is None or raw == '':
            continue
        raw = float(raw)
        full_pool.setdefault(term, []).append(raw)
        for ctx in _parse(
                getattr(row, 'context_names_json', '[]'), '[]'):
            per_context.setdefault((term, ctx), []).append(raw)

    suggestions = []
    for (term, ctx), pool in per_context.items():
        if len(pool) < 2:
            continue
        full = full_pool.get(term, [])
        full_spread = max(full) - min(full) if len(full) > 1 else 0
        if not full_spread:
            continue
        spread = max(pool) - min(pool)
        ratio = spread / full_spread
        if ratio >= 0.5:
            ctx_row = contexts.get(ctx)
            suggestions.append({
                'context': ctx,
                'displayName': getattr(ctx_row, 'display_name', '')
                if ctx_row is not None else ctx,
                'term': term,
                'sliceSpread': round(spread, 6),
                'fullSpread': round(full_spread, 6),
                'divergenceRatio': round(ratio, 4),
                'sampleCount': len(pool),
                'knob': 'ScoreConcept.required_context_names_json',
                'action': f"scores for '{term}' vary almost as much "
                          f"WITHIN '{ctx}' as overall — slicing by a "
                          'sibling of this context (or requiring it '
                          'explicitly) would separate real variation'})
    suggestions.sort(key=lambda s: -s['divergenceRatio'])
    return {'ok': True, 'concept': concept_name,
            'suggestions': suggestions[:10],
            'note': 'suggestions only — requiring a context is an '
                    'explicit edit to the concept row'}
