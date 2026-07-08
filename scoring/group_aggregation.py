"""
@cross-cutting
@module scoring.group_aggregation
@tags @xc:bindings

Group-aggregate AGREEMENT over member worldviews — per term and per
group (Dustin 2026-07-08): is a term divisive or consensus for the
group (direction agreement, classified through the editable
AgreementPolicy bands)? Do members weight it similarly? What is the
group's aggregate definition, and do two GROUPS share a definition of
good performance?

Every classification travels with its evidence numbers — the label is
a reading of the fractions, never a replacement for them.

Pure functions over manager.objectTables.

@consumers
  - scoring.scoring_api (group endpoints)
@see /OVERLAP_MAP.md
"""

import json
import math

from scoring.agreement_policy import (
    classify_max, classify_min, policy_bands,
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


def member_definition(concept_row, terms_by_name):
    """One member worldview as {key: {'share', 'stance'}} — weight
    share of the member's total, stance +1/-1 (entry override, else
    the term's is_positive). Nested concept entries key as
    'concept:<name>'."""
    entries = _parse(
        getattr(concept_row, 'term_weights_json', '[]'), '[]')
    total = sum(abs(e.get('weight', 0)) for e in entries) or 1
    definition = {}
    for entry in entries:
        if entry.get('concept'):
            key = f"concept:{entry['concept']}"
            positive = bool(entry.get('isPositive', True))
        else:
            key = entry.get('term', '')
            term = terms_by_name.get(key)
            positive = bool(entry.get(
                'isPositive',
                getattr(term, 'is_positive', True) if term else True))
        if not key:
            continue
        definition[key] = {
            'share': abs(entry.get('weight', 0)) / total,
            'stance': 1 if positive else -1,
        }
    return definition


def _resolve_policy(manager, policy_name):
    policies = _by_name(manager, 'AgreementPolicy')
    policy = policies.get(policy_name or 'default-agreement')
    if policy is None:
        return None, {
            'ok': False,
            'error': f"no AgreementPolicy named "
                     f"'{policy_name or 'default-agreement'}'",
            'knownPolicies': sorted(policies),
            'suggestion': {'knob': 'AgreementPolicy',
                           'action': 'create the policy row (bands '
                                     'are settings, not code)'}}
    return policy, None


def _aggregate_members(manager, member_names, policy):
    """The shared core: per-term agreement classification + the
    aggregate definition over a list of member concept names."""
    concepts = _by_name(manager, 'ScoreConcept')
    terms = _by_name(manager, 'ScoreTerm')
    bands = policy_bands(policy)

    members, missing_members = [], []
    for name in member_names:
        row = concepts.get(name)
        if row is None:
            missing_members.append(name)
        else:
            members.append((name, member_definition(row, terms)))
    if not members:
        return None, {
            'ok': False,
            'error': 'no member concepts resolved',
            'missingMembers': missing_members}

    total = len(members)
    keys = sorted({k for _, d in members for k in d})
    term_reports, definition = [], {}
    agreement_num, agreement_den = 0.0, 0.0
    for key in keys:
        holders = [(name, d[key]) for name, d in members if key in d]
        positive = [n for n, e in holders if e['stance'] > 0]
        negative = [n for n, e in holders if e['stance'] < 0]
        dominant_count = max(len(positive), len(negative))
        dominant_fraction = dominant_count / len(holders)
        # An exact tie is a SPLIT — the group takes no side, and its
        # aggregate definition carries stance 0 for this term.
        if len(positive) == len(negative):
            dominant_stance = 'split'
        elif len(positive) > len(negative):
            dominant_stance = 'positive'
        else:
            dominant_stance = 'negative'
        direction_label = classify_max(
            dominant_fraction, bands['direction'])

        shares = [e['share'] for _, e in holders]
        mean_share = sum(shares) / len(shares)
        mad = (sum(abs(s - mean_share) for s in shares)
               / len(shares))
        spread = (mad / mean_share) if mean_share > 0 else 0.0
        weight_label = classify_max(spread, bands['weight'])

        participation = len(holders) / total
        agreement_num += dominant_fraction * participation
        agreement_den += participation

        term = terms.get(key)
        term_reports.append({
            'key': key,
            'label': getattr(term, 'display_name', key)
            if term else key,
            'participation': round(participation, 4),
            'holders': len(holders),
            'positiveMembers': positive,
            'negativeMembers': negative,
            'dominantStance': dominant_stance,
            'dominantFraction': round(dominant_fraction, 4),
            'directionClass': direction_label,
            'meanWeightShare': round(mean_share, 4),
            'weightShareSpread': round(spread, 4),
            'weightClass': weight_label,
        })
        definition[key] = {
            'meanShare': round(mean_share, 6),
            'stanceSign': {'positive': 1, 'negative': -1,
                           'split': 0}[dominant_stance],
            'participation': round(participation, 6),
        }

    report = {
        'ok': True,
        'members': [n for n, _ in members],
        'missingMembers': missing_members,
        'memberCount': total,
        'policy': getattr(policy, 'name', ''),
        'terms': term_reports,
        'definition': definition,
        'agreementIndex': round(
            agreement_num / agreement_den, 4) if agreement_den else None,
    }
    return report, None


def aggregate_group(manager, group_name, policy_name=''):
    """One group's per-term agreement + aggregate definition."""
    groups = _by_name(manager, 'ScoreGroup')
    group = groups.get(group_name)
    if group is None:
        return {'ok': False,
                'error': f"no ScoreGroup named '{group_name}'",
                'knownGroups': sorted(groups)}
    policy, refusal = _resolve_policy(manager, policy_name)
    if refusal:
        return refusal
    member_names = _parse(
        getattr(group, 'member_concept_names_json', '[]'), '[]')
    report, refusal = _aggregate_members(manager, member_names, policy)
    if refusal:
        return {**refusal, 'group': group_name}
    return {**report, 'group': group_name,
            'displayName': getattr(group, 'display_name', '')
            or group_name,
            'groupType': getattr(group, 'group_type', '')}


def all_groups_consensus(manager, policy_name=''):
    """(a) All groups — Consensus: the union of every group's members
    aggregated as one body."""
    policy, refusal = _resolve_policy(manager, policy_name)
    if refusal:
        return refusal
    union, seen = [], set()
    for group in _rows(manager, 'ScoreGroup'):
        for name in _parse(
                getattr(group, 'member_concept_names_json', '[]'),
                '[]'):
            if name not in seen:
                seen.add(name)
                union.append(name)
    if not union:
        return {'ok': False,
                'error': 'no ScoreGroup rows with members',
                'suggestion': {'knob': 'ScoreGroup',
                               'action': 'create groups whose '
                                         'member_concept_names_json '
                                         'lists worldview concepts'}}
    report, refusal = _aggregate_members(manager, union, policy)
    if refusal:
        return refusal
    return {**report, 'group': '(all groups)',
            'displayName': 'All groups — consensus',
            'groupType': 'all'}


def compare_groups(manager, group_names, policy_name=''):
    """Do groups share a definition of good performance? Cosine
    similarity between aggregate-definition vectors (share × stance ×
    participation), classified through the policy's similarity bands,
    with the biggest per-term disagreements named."""
    policy, refusal = _resolve_policy(manager, policy_name)
    if refusal:
        return refusal
    if not group_names or len(group_names) < 2:
        return {'ok': False,
                'error': 'compare needs at least two group names'}
    aggregates = {}
    for name in group_names:
        report = aggregate_group(manager, name, policy_name)
        if not report.get('ok'):
            return {'ok': False,
                    'error': f"group '{name}' failed to aggregate: "
                             f"{report.get('error')}"}
        aggregates[name] = report

    bands = policy_bands(policy)
    pairs = []
    names = list(group_names)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = aggregates[names[i]], aggregates[names[j]]
            keys = sorted(set(a['definition']) | set(b['definition']))

            def vec(agg):
                return [
                    (agg['definition'].get(k, {}).get('meanShare', 0.0)
                     * agg['definition'].get(k, {}).get('stanceSign', 1)
                     * agg['definition'].get(k, {}).get(
                         'participation', 0.0))
                    for k in keys]
            va, vb = vec(a), vec(b)
            dot = sum(x * y for x, y in zip(va, vb))
            mag = (math.sqrt(sum(x * x for x in va))
                   * math.sqrt(sum(y * y for y in vb)))
            similarity = dot / mag if mag else 0.0
            gaps = sorted(
                ({'key': k, 'gap': round(abs(x - y), 4),
                  'a': round(x, 4), 'b': round(y, 4)}
                 for k, x, y in zip(keys, va, vb)),
                key=lambda g: -g['gap'])
            pairs.append({
                'groups': [names[i], names[j]],
                'similarity': round(similarity, 4),
                'similarityClass': classify_min(
                    similarity, bands['similarity']),
                'topDisagreements': gaps[:5],
            })
    return {'ok': True, 'policy': getattr(policy, 'name', ''),
            'pairs': pairs,
            'note': 'similarity = cosine over share×stance×'
                    'participation vectors; the label reads the '
                    'number, the number stays authoritative'}
