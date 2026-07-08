"""
@cross-cutting
@module scoring.group_bias
@tags @xc:bindings

Per-group bias analysis (scr-16) — Dustin 2026-07-08: "per group bias
analysis". Four independent reads per group, every label traveling
with its numbers, bands = editable BiasPolicy rows:

  stance skew      — the group's aggregate definition vs the
                     all-groups consensus, per term (opposed stances
                     and emphasis gaps named).
  one-sidedness    — supports-vs-harms fractions of the members'
                     assertions per target subject kind (a group that
                     only ever harms one kind of target is visible).
  vote alignment   — the confirmation-bias read: how often member
                     validity votes go the way the group's own stance
                     would prefer (self-serving) vs against it
                     (evidence-driven). Small samples flagged, never
                     over-read.
  source quality   — evidence grades + scr-15 outlet accuracy over
                     what the group's assertions actually cite.

Bias here is a READING of behavior against the group's own recorded
stances — evidence-bearing, recomputable, never a verdict on people.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (GET /api/scoring/groups/{name}/bias)
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.agreement_policy import classify_max
from scoring.group_aggregation import (
    aggregate_group, all_groups_consensus,
)
from scoring.media_accuracy import outlet_accuracy

#: Below this many decisive data points a band is a hint, not a
#: reading — flagged on the result.
SMALL_SAMPLE = 3


class BiasPolicy(treeObject):
    """Editable bands for the bias reads."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # Bands over the dominant supports/harms fraction (0.5-1.0).
        onesidedness_bands_json: str = '[]',
        # Bands over the self-serving vote fraction (0-1).
        alignment_bands_json: str = '[]',
        # Bands over |group share − consensus share| per term.
        emphasis_bands_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.onesidedness_bands_json = onesidedness_bands_json
        self.alignment_bands_json = alignment_bands_json
        self.emphasis_bands_json = emphasis_bands_json
        self.notes = notes


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


def _bias_bands(manager, policy_name):
    policies = _rows(manager, 'BiasPolicy')
    wanted = policy_name or 'default-bias'
    row = next((p for p in policies
                if getattr(p, 'name', '') == wanted),
               policies[0] if policies else None)
    if row is None:
        return {'onesidedness': [], 'alignment': [],
                'emphasis': []}, None
    return {
        'onesidedness': _parse(
            getattr(row, 'onesidedness_bands_json', '[]'), '[]'),
        'alignment': _parse(
            getattr(row, 'alignment_bands_json', '[]'), '[]'),
        'emphasis': _parse(
            getattr(row, 'emphasis_bands_json', '[]'), '[]'),
    }, getattr(row, 'name', '')


def _stance_skew(group_agg, consensus_agg, emphasis_bands):
    """Group definition vs the all-groups consensus, per term."""
    group_def = group_agg.get('definition', {})
    consensus_def = consensus_agg.get('definition', {})
    skew, opposed = [], 0
    for key in sorted(set(group_def) | set(consensus_def)):
        g = group_def.get(key, {})
        c = consensus_def.get(key, {})
        g_stance = g.get('stanceSign', 0)
        c_stance = c.get('stanceSign', 0)
        gap = (g.get('meanShare', 0.0) or 0.0) \
            - (c.get('meanShare', 0.0) or 0.0)
        if g_stance and c_stance and g_stance != c_stance:
            reading = 'opposed'
            opposed += 1
        elif key not in group_def:
            reading = 'absent-from-group'
        elif key not in consensus_def:
            reading = 'group-only'
        else:
            reading = classify_max(abs(gap), emphasis_bands) \
                if emphasis_bands else 'unclassified'
        skew.append({'key': key,
                     'groupStance': g_stance,
                     'consensusStance': c_stance,
                     'groupShare': round(
                         g.get('meanShare', 0.0) or 0.0, 4),
                     'consensusShare': round(
                         c.get('meanShare', 0.0) or 0.0, 4),
                     'shareGap': round(gap, 4),
                     'reading': reading})
    return skew, opposed


def _one_sidedness(manager, members, bands):
    """supports/harms split of member assertions per target kind."""
    subjects = _by_name(manager, 'ScoreSubject')
    per_kind = {}
    for a in _rows(manager, 'ScoreAssertion'):
        if getattr(a, 'asserted_by', '') not in members:
            continue
        if getattr(a, 'assertion_type', '') != 'score-impact':
            continue
        target = subjects.get(getattr(a, 'subject_name', ''))
        kind = getattr(target, 'kind', 'unknown') \
            if target is not None else 'unknown'
        entry = per_kind.setdefault(
            kind, {'supports': 0, 'harms': 0, 'assertions': []})
        direction = getattr(a, 'direction', 'supports')
        entry[direction if direction in ('supports', 'harms')
              else 'supports'] += 1
        entry['assertions'].append(getattr(a, 'name', ''))
    readings = []
    for kind, entry in sorted(per_kind.items()):
        total = entry['supports'] + entry['harms']
        dominant = max(entry['supports'], entry['harms']) / total \
            if total else 0.5
        readings.append({
            'targetKind': kind,
            'supports': entry['supports'],
            'harms': entry['harms'],
            'dominantFraction': round(dominant, 4),
            'band': classify_max(dominant, bands) if bands
            else 'unclassified',
            'smallSample': total < SMALL_SAMPLE,
            'assertions': sorted(entry['assertions']),
        })
    return readings


def _vote_alignment(manager, members, group_def, bands):
    """The confirmation-bias read: member validity votes vs the
    group's own stances. favorable = the assertion is good news for
    what the group values; aligned = voting the way that favor
    points (valid on favorable / invalid on unfavorable)."""
    assertions = _by_name(manager, 'ScoreAssertion')
    votes, skipped = [], []
    self_serving = 0
    for v in _rows(manager, 'AssertionValidityVote'):
        voter = getattr(v, 'voter', '')
        if voter not in members:
            continue
        kind = getattr(v, 'vote', 'abstain')
        if kind not in ('valid', 'invalid'):
            continue  # abstentions carry no direction to align
        a = assertions.get(getattr(v, 'assertion_name', ''))
        term = getattr(a, 'term_name', '') if a is not None else ''
        stance = group_def.get(term, {}).get('stanceSign', 0)
        if a is None or not term or not stance:
            skipped.append({
                'vote': getattr(v, 'name', ''),
                'reason': 'assertion unbound to a term, or the '
                          'group holds no stance on it'})
            continue
        direction = getattr(a, 'direction', 'supports')
        favorable = (direction == 'supports') == (stance > 0)
        aligned = (kind == 'valid') == favorable
        if aligned:
            self_serving += 1
        votes.append({'vote': getattr(v, 'name', ''),
                      'voter': voter,
                      'assertion': getattr(a, 'name', ''),
                      'direction': direction,
                      'term': term,
                      'groupStance': stance,
                      'favorableToGroup': favorable,
                      'castVote': kind,
                      'selfServing': aligned})
    decisive = len(votes)
    rate = self_serving / decisive if decisive else None
    return {
        'decisiveVotes': decisive,
        'selfServing': self_serving,
        'counterStance': decisive - self_serving,
        'alignmentRate': round(rate, 4) if rate is not None else None,
        'band': classify_max(rate, bands)
        if bands and rate is not None else 'unclassified',
        'smallSample': decisive < SMALL_SAMPLE,
        'votes': votes,
        'skipped': skipped,
        'reading': 'counter-stance votes are the evidence-driven '
                   'signal; a high alignment rate over a real sample '
                   'is the confirmation-bias smell, not proof',
    }


def _source_quality(manager, members):
    """Grades + outlet accuracy over what member assertions cite."""
    evidence = _by_name(manager, 'MediaEvidence')
    grades, outlets, uncited = {}, {}, 0
    for a in _rows(manager, 'ScoreAssertion'):
        if getattr(a, 'asserted_by', '') not in members:
            continue
        names = _parse(
            getattr(a, 'evidence_names_json', '[]'), '[]')
        if not names:
            uncited += 1
            continue
        for name in names:
            row = evidence.get(name)
            if row is None:
                continue
            grade = getattr(row, 'evidence_grade', 'secondhand')
            grades[grade] = grades.get(grade, 0) + 1
            outlet = getattr(row, 'outlet_name', '')
            if outlet:
                outlets[outlet] = outlets.get(outlet, 0) + 1
    outlet_reports = {}
    for outlet in sorted(outlets):
        record = outlet_accuracy(manager, outlet)
        outlet_reports[outlet] = {
            'citations': outlets[outlet],
            'meanRelativeError': record.get('meanRelativeError')
            if record.get('ok') else None,
            'verdicts': record.get('verdicts')
            if record.get('ok') else None,
            'note': None if record.get('ok')
            else record.get('error'),
        }
    return {'gradeDistribution': grades,
            'unevidencedAssertions': uncited,
            'outletsCited': outlet_reports}


def group_bias_report(manager, group_name, policy_name='',
                      agreement_policy=''):
    """The four bias reads for one group."""
    groups = _by_name(manager, 'ScoreGroup')
    group = groups.get(group_name)
    if group is None:
        return {'ok': False,
                'error': f"no ScoreGroup named '{group_name}'",
                'knownGroups': sorted(groups)}
    members = _parse(
        getattr(group, 'member_contributor_names_json', '[]'), '[]')
    if not members:
        return {'ok': False,
                'error': f"group '{group_name}' names no member "
                         'contributors',
                'suggestion': {
                    'knob': 'ScoreGroup.member_contributor_names_json',
                    'action': 'list the Contributor rows belonging '
                              'to this group — bias reads follow '
                              'their assertions, votes and '
                              'citations'}}
    bands, policy = _bias_bands(manager, policy_name)

    group_agg = aggregate_group(manager, group_name, agreement_policy)
    consensus = all_groups_consensus(manager, agreement_policy)
    if group_agg.get('ok') and consensus.get('ok'):
        skew, opposed = _stance_skew(group_agg, consensus,
                                     bands['emphasis'])
    else:
        skew, opposed = [], 0

    group_def = group_agg.get('definition', {}) \
        if group_agg.get('ok') else {}
    return {
        'ok': True,
        'group': group_name,
        'displayName': getattr(group, 'display_name', '')
        or group_name,
        'memberContributors': members,
        'biasPolicy': policy,
        'stanceSkew': {'terms': skew, 'opposedTerms': opposed,
                       'vsConsensusOf': consensus.get('memberCount')
                       if consensus.get('ok') else None},
        'oneSidedness': _one_sidedness(manager, set(members),
                                       bands['onesidedness']),
        'voteAlignment': _vote_alignment(manager, set(members),
                                         group_def,
                                         bands['alignment']),
        'sourceQuality': _source_quality(manager, set(members)),
        'note': 'four independent reads of recorded behavior against '
                "the group's own stances — labels travel with their "
                'numbers, small samples are flagged, and every input '
                'row is citable',
    }


SEED_BIAS_POLICIES = [{
    'name': 'default-bias',
    'display_name': 'Default bias bands',
    'description': 'First-cut bands for the bias reads — edit this '
                   'row to recalibrate. One-sidedness/alignment: '
                   '≤0.6 balanced · ≤0.8 leaning · ≤0.95 one-sided · '
                   'above = echo-chamber. Emphasis gap vs consensus: '
                   '≤0.05 aligned-emphasis · ≤0.15 emphasis-gap · '
                   'above = strong-emphasis-gap.',
    'onesidedness_bands_json': json.dumps([
        {'label': 'balanced', 'max': 0.6},
        {'label': 'leaning', 'max': 0.8},
        {'label': 'one-sided', 'max': 0.95},
        {'label': 'echo-chamber', 'max': 1.0},
    ]),
    'alignment_bands_json': json.dumps([
        {'label': 'balanced', 'max': 0.6},
        {'label': 'leaning', 'max': 0.8},
        {'label': 'one-sided', 'max': 0.95},
        {'label': 'echo-chamber', 'max': 1.0},
    ]),
    'emphasis_bands_json': json.dumps([
        {'label': 'aligned-emphasis', 'max': 0.05},
        {'label': 'emphasis-gap', 'max': 0.15},
        {'label': 'strong-emphasis-gap', 'max': 1.0},
    ]),
}]
