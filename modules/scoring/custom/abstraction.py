"""
@cross-cutting
@module scoring.custom.abstraction
@tags @xc:bindings

Abstraction mapping (scr-5) — generic intents → SUGGESTED score
bindings. Dustin 2026-07-08: "map to more abstract concepts so that we
can more easily assign scores via assertions of generic intents and
then suggestions of scores that should apply".

An assertion's free-text intent is matched against the abstract-tag
vocabularies on ScoreTerm/ScoreConcept rows (abstract_tags_json), plus
display names/descriptions, expanded through equivalent_terms_json
(the scorecard's purpose-equivalence, finally consumed). The output is
a RANKED SUGGESTION LIST naming the knob (concept_name / term_name on
the assertion) — never auto-bound (knobs-and-suggestions).

@consumers
  - scoring.scoring_api
    (GET /api/scoring/assertions/{name}/suggestions)
@see /OVERLAP_MAP.md
"""

import json
import re

#: Words too generic to carry a match on their own.
_STOPWORDS = {
    'the', 'a', 'an', 'of', 'for', 'and', 'or', 'to', 'in', 'on',
    'by', 'with', 'this', 'that', 'is', 'are', 'be', 'it', 'as',
    'at', 'from', 'into', 'more', 'less', 'improves', 'improve',
    'raises', 'raise', 'lowers', 'lower', 'increases', 'increase',
    'decreases', 'decrease', 'weakens', 'weaken', 'strengthens',
    'strengthen',
}

#: Crude suffix folding so 'wages' matches 'wage', 'unions' 'union'.
def _stem(token):
    for suffix in ('ing', 'es', 's'):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            return token[:-len(suffix)]
    return token


def _tokens(text):
    raw = re.split(r'[^a-z0-9]+', (text or '').lower())
    return {_stem(t) for t in raw
            if t and t not in _STOPWORDS and len(t) > 2}


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _parse_list(row, attr):
    try:
        loaded = json.loads(getattr(row, attr, '') or '[]')
        return loaded if isinstance(loaded, list) else []
    except Exception:
        return []


def _match(intent_tokens, row):
    """(score, matched) for one candidate row: tag hits weigh 2 (tags
    are the curated vocabulary), name/description token hits weigh 1."""
    matched, score = [], 0.0
    for tag in _parse_list(row, 'abstract_tags_json'):
        tag_tokens = _tokens(tag)
        hits = tag_tokens & intent_tokens
        if hits:
            score += 2.0 * len(hits) / len(tag_tokens)
            matched.append({'tag': tag, 'via': sorted(hits)})
    name_tokens = _tokens(
        f"{getattr(row, 'display_name', '')} "
        f"{getattr(row, 'name', '')} "
        f"{getattr(row, 'description', '')}")
    plain = intent_tokens & name_tokens
    if plain:
        score += float(len(plain))
        matched.append({'text': sorted(plain)})
    return score, matched


def suggest_scores_for_assertion(manager, assertion_name):
    """Ranked concept/term suggestions for one assertion's intent.
    Terms found directly also pull in their equivalent_terms_json
    partners (labeled 'equivalent-to'), so purpose-equivalence works
    without the intent naming the exact metric."""
    assertion = next(
        (a for a in _rows(manager, 'ScoreAssertion')
         if getattr(a, 'name', '') == assertion_name), None)
    if assertion is None:
        return {'ok': False,
                'error': f"no ScoreAssertion named '{assertion_name}'"}
    intent = getattr(assertion, 'intent', '')
    intent_tokens = _tokens(intent)
    if not intent_tokens:
        return {'ok': False,
                'error': 'assertion has no matchable intent text',
                'suggestion': {'knob': 'ScoreAssertion.intent',
                               'action': 'state the generic intent '
                                         '(what the span does), then '
                                         're-run suggestions'}}

    suggestions = []
    terms = {getattr(t, 'name', ''): t
             for t in _rows(manager, 'ScoreTerm')}
    for name, term in terms.items():
        score, matched = _match(intent_tokens, term)
        if score > 0:
            suggestions.append({
                'kind': 'term', 'name': name,
                'displayName': getattr(term, 'display_name', '')
                or name,
                'matchScore': round(score, 4),
                'evidence': matched,
                'knob': 'ScoreAssertion.term_name',
                'action': f"set term_name = '{name}' to bind this "
                          'assertion'})
    # Purpose-equivalence expansion: a directly-matched term vouches
    # for its declared equivalents at reduced score.
    direct = {s['name']: s for s in suggestions if s['kind'] == 'term'}
    for name, sugg in list(direct.items()):
        for equivalent in _parse_list(terms.get(name),
                                      'equivalent_terms_json'):
            if equivalent in terms and equivalent not in direct:
                suggestions.append({
                    'kind': 'term', 'name': equivalent,
                    'displayName': getattr(
                        terms[equivalent], 'display_name', '')
                    or equivalent,
                    'matchScore': round(sugg['matchScore'] * 0.5, 4),
                    'evidence': [{'equivalent-to': name}],
                    'knob': 'ScoreAssertion.term_name',
                    'action': f"set term_name = '{equivalent}' "
                              f"(purpose-equivalent of '{name}')"})
    for concept in _rows(manager, 'ScoreConcept'):
        score, matched = _match(intent_tokens, concept)
        if score > 0:
            cname = getattr(concept, 'name', '')
            suggestions.append({
                'kind': 'concept', 'name': cname,
                'displayName': getattr(concept, 'display_name', '')
                or cname,
                'matchScore': round(score, 4),
                'evidence': matched,
                'knob': 'ScoreAssertion.concept_name',
                'action': f"set concept_name = '{cname}' to bind "
                          'this assertion'})

    suggestions.sort(key=lambda s: -s['matchScore'])
    bound = getattr(assertion, 'concept_name', '') \
        or getattr(assertion, 'term_name', '')
    return {'ok': True,
            'assertion': assertion_name,
            'intent': intent,
            'intentTokens': sorted(intent_tokens),
            'alreadyBound': bound or None,
            'suggestions': suggestions[:8],
            'note': 'suggestions only — binding happens by setting '
                    'the named knob on the assertion row, never '
                    'automatically'}
