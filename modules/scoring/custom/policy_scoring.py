"""
@cross-cutting
@module scoring.custom.policy_scoring
@tags @xc:bindings

Policy scoring (scr-5) — a policy subject's score for a concept is an
ASSERTION-WEIGHTED composition: confirmed assertions binding its text
spans to the concept (or to the concept's terms), each contributing
direction × strength × evidence-grade weight. Dustin 2026-07-08:
"Politician scoring through Policy Scoring via Score Assertions onto
policies".

Semantics, all explicit in the result:
  - Only CONFIRMED assertions score by default (include_statuses
    knob); everything excluded is listed with its status — an
    unconfirmed claim is visible, never silently counted or hidden.
  - Term-bound assertions weigh by the term's weight share within the
    concept (an assertion about a w8/21 term moves the policy more
    than one about a w2/21 term).
  - dependency assertions carry over the depended-on policy's score
    for the SAME concept (recursive, cycle-refused, depth-capped —
    the nested-concept idiom between policy subjects).
  - decorative assertions are listed and excluded — 'this span
    carries no weight' is itself an accountable claim.
  - stance ∈ [-1, 1] (weighted mean of ±1 directions), score =
    (stance + 1) / 2 ∈ [0, 1] so policy scores compose anywhere a
    normalized value does (politician scoring, scr-6).

@consumers
  - scoring.scoring_api (GET /api/scoring/policies/{name}/score)
@see /OVERLAP_MAP.md
"""

import json

from scoring.evidence_basis import evidence_weight

#: Dependency chain cap (matches concept nesting, msci-16 idiom).
MAX_DEPENDENCY_DEPTH = 8


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _parse(text, fallback):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)


def _term_share(concept_row, term_name):
    """A term's weight share within a concept (0 when absent)."""
    if concept_row is None or not term_name:
        return None
    entries = _parse(
        getattr(concept_row, 'term_weights_json', '[]'), '[]')
    total = sum(e.get('weight', 0) for e in entries) or 1
    for e in entries:
        if e.get('term') == term_name:
            return e.get('weight', 0) / total
    return None


def score_policy(manager, policy_name, concept_name,
                 include_statuses=('confirmed',),
                 evidence_policy='', _path=()):
    """One policy subject's assertion-composed score for one concept.

    Returns the score with every contribution itemized (span quote,
    direction, strength, evidence grade, weight) and every exclusion
    named (status, decorative, unbound)."""
    if policy_name in _path:
        cycle = ' → '.join(_path + (policy_name,))
        return {'ok': False,
                'error': f'policy dependency cycle refused: {cycle}',
                'cyclePath': list(_path + (policy_name,))}
    if len(_path) >= MAX_DEPENDENCY_DEPTH:
        return {'ok': False,
                'error': f'policy dependency chain deeper than '
                         f'{MAX_DEPENDENCY_DEPTH} refused '
                         f'(path: {" → ".join(_path)})'}
    subjects = {getattr(s, 'name', ''): s
                for s in _rows(manager, 'ScoreSubject')}
    subject = subjects.get(policy_name)
    if subject is None:
        return {'ok': False,
                'error': f"no ScoreSubject named '{policy_name}'"}
    concepts = {getattr(c, 'name', ''): c
                for c in _rows(manager, 'ScoreConcept')}
    concept = concepts.get(concept_name)
    if concept is None:
        return {'ok': False,
                'error': f"no ScoreConcept named '{concept_name}'",
                'knownConcepts': sorted(concepts)}
    concept_terms = {e.get('term') for e in _parse(
        getattr(concept, 'term_weights_json', '[]'), '[]')
        if e.get('term')}

    assertions = [a for a in _rows(manager, 'ScoreAssertion')
                  if getattr(a, 'subject_name', '') == policy_name]
    used, excluded = [], []
    weighted_stance, total_weight = 0.0, 0.0
    for a in assertions:
        aname = getattr(a, 'name', '')
        atype = getattr(a, 'assertion_type', 'score-impact')
        status = getattr(a, 'status', 'asserted')
        bound_concept = getattr(a, 'concept_name', '')
        bound_term = getattr(a, 'term_name', '')
        span = _parse(getattr(a, 'span_json', ''), 'null') or {}
        base = {'assertion': aname,
                'type': atype, 'status': status,
                'intent': getattr(a, 'intent', ''),
                'quote': span.get('quote', ''),
                'assertedBy': getattr(a, 'asserted_by', '')}
        if atype == 'decorative':
            excluded.append({**base,
                             'reason': 'decorative — asserted to '
                                       'carry no score weight'})
            continue
        # Relevance to THIS concept: bound to it directly, or to one
        # of its terms; dependency assertions are concept-agnostic
        # (the child is scored for the same concept).
        term_share = _term_share(concept, bound_term)
        relevant = (bound_concept == concept_name
                    or (bound_term and bound_term in concept_terms)
                    or atype == 'dependency')
        if not relevant:
            if bound_concept or bound_term:
                continue  # bound elsewhere — not this concept's story
            excluded.append({**base,
                             'reason': 'unbound — no concept_name/'
                                       'term_name set',
                             'suggestion': {
                                 'knob': 'GET /api/scoring/assertions/'
                                         f'{aname}/suggestions',
                                 'action': 'run abstraction matching '
                                           'and bind the assertion'}})
            continue
        if status not in include_statuses:
            excluded.append({**base,
                             'reason': f"status '{status}' not in "
                                       f'{list(include_statuses)}'})
            continue

        strength = float(getattr(a, 'strength', 0.5) or 0)
        sign = -1.0 if getattr(a, 'direction', 'supports') == 'harms' \
            else 1.0
        eweight, edetail = evidence_weight(
            manager,
            _parse(getattr(a, 'evidence_names_json', '[]'), '[]'),
            evidence_policy)

        if atype == 'dependency':
            depends_on = getattr(a, 'depends_on_subject', '')
            child = score_policy(
                manager, depends_on, concept_name,
                include_statuses, evidence_policy,
                _path + (policy_name,))
            if not child.get('ok'):
                excluded.append({**base,
                                 'reason': f"dependency "
                                           f"'{depends_on}' did not "
                                           'score',
                                 'error': child.get('error', '')})
                continue
            # The child's stance carries over, scaled by strength ×
            # evidence × direction (a harmful dependency inverts).
            stance = sign * child['stance']
            weight = strength * eweight
            used.append({**base, 'dependsOn': depends_on,
                         'childScore': child['score'],
                         'stance': round(stance, 6),
                         'strength': strength,
                         'evidence': edetail,
                         'weight': round(weight, 6)})
        else:
            weight = strength * eweight * (
                term_share if term_share is not None else 1.0)
            stance = sign
            entry = {**base, 'direction':
                     getattr(a, 'direction', 'supports'),
                     'stance': stance,
                     'strength': strength,
                     'evidence': edetail,
                     'weight': round(weight, 6)}
            if bound_term:
                entry['term'] = bound_term
                entry['termShare'] = round(term_share, 6) \
                    if term_share is not None else None
            used.append(entry)
        weighted_stance += stance * weight
        total_weight += weight

    if not used:
        return {'ok': False,
                'policy': policy_name,
                'concept': concept_name,
                'error': f"no {list(include_statuses)} assertions "
                         f"bind '{policy_name}' to "
                         f"'{concept_name}'",
                'excluded': excluded,
                'suggestion': {
                    'knob': 'ScoreAssertion',
                    'action': 'assert spans of this policy onto the '
                              'concept (or its terms) and confirm '
                              'them through validity review'}}

    stance = weighted_stance / total_weight if total_weight else 0.0
    return {
        'ok': True,
        'policy': policy_name,
        'displayName': getattr(subject, 'display_name', '')
        or policy_name,
        'kind': getattr(subject, 'kind', ''),
        'concept': concept_name,
        'stance': round(stance, 6),
        'score': round((stance + 1.0) / 2.0, 6),
        'totalWeight': round(total_weight, 6),
        'includeStatuses': list(include_statuses),
        'assertionsUsed': used,
        'excluded': excluded,
        'note': 'score = (weighted mean stance + 1) / 2; stance per '
                'assertion is ±direction, weighted by strength × '
                'evidence grade × term share; dependency assertions '
                "carry the depended-on policy's stance",
    }
