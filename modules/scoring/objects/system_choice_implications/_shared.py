"""@module scoring.objects.system_choice_implications._shared — what the system_choice_implications row classes share (constants, seeds, helpers); split from system_choice_implications_basis.py (sap-2c)."""
from scoring.custom.scoring_engine import (
    _by_name, _rows, resolve_raw_value, select_value,
)
import json

def compare_outcomes_by_system_choice(manager, fork_name, outcome_term_name,
                                      required_context_names=None):
    """Groups jurisdictions currently deploying each criterion at
    `fork_name`, reports each jurisdiction's `outcome_term_name` value
    and a simple per-group average — the actual "review through
    history to see which systems work best" comparison Dustin asked
    for.

    Deliberately NOT a causal estimate: a raw grouped comparison,
    confounds are NOT controlled for (see module docstring — reported-
    rate metrics conflate incidence with reporting propensity). Real
    interpretation belongs in ScoreAssertion review (scr-5), not in
    this function's own math — the response says so explicitly rather
    than implying more certainty than the data supports."""
    choices = [c for c in _rows(manager, 'SystemChoiceInForce')
               if getattr(c, 'fork_name', '') == fork_name
               and not getattr(c, 'effective_to', '')]  # still in force
    if not choices:
        return {'ok': False,
                'error': f"no in-force SystemChoiceInForce rows for "
                         f"fork '{fork_name}'",
                'knownForks': sorted({
                    getattr(c, 'fork_name', '')
                    for c in _rows(manager, 'SystemChoiceInForce')})}

    contexts = _by_name(manager, 'ScoreContext')
    subjects = _by_name(manager, 'ScoreSubject')
    required = required_context_names or []

    values_by_subject = {}
    for row in _rows(manager, 'ContextualizedValue'):
        if getattr(row, 'term_name', '') == outcome_term_name:
            values_by_subject.setdefault(
                getattr(row, 'subject_name', ''), []).append(row)

    groups = {}
    for choice in choices:
        criterion = getattr(choice, 'criterion_name', '')
        subject_name = getattr(choice, 'jurisdiction_subject_name', '')
        subject = subjects.get(subject_name)
        display_name = getattr(subject, 'display_name', '') or subject_name
        candidates = values_by_subject.get(subject_name, [])
        chosen = select_value(candidates, required, contexts) \
            if candidates else None
        if chosen is None:
            entry = {'jurisdiction': subject_name,
                     'displayName': display_name, 'value': None,
                     'note': f'no {outcome_term_name} value on record '
                             'for this jurisdiction/context'}
        else:
            ok, raw, meta = resolve_raw_value(manager, chosen)
            entry = {'jurisdiction': subject_name,
                     'displayName': display_name,
                     'value': raw if ok else None,
                     'note': '' if ok else meta.get('error', '')}
        groups.setdefault(criterion, []).append(entry)

    report_groups = []
    for criterion, entries in groups.items():
        numeric = [e['value'] for e in entries if e['value'] is not None]
        report_groups.append({
            'criterion': criterion,
            'jurisdictions': entries,
            'jurisdictionCount': len(entries),
            'averageValue': (round(sum(numeric) / len(numeric), 4)
                             if numeric else None),
            'missingCount': len(entries) - len(numeric),
        })
    report_groups.sort(key=lambda g: g['criterion'])

    return {
        'ok': True,
        'fork': fork_name,
        'outcomeTerm': outcome_term_name,
        'groups': report_groups,
        'note': 'a RAW grouped comparison, not a controlled-for-'
                'confounds causal estimate — group averages differing '
                'does not by itself mean the system choice CAUSED the '
                'difference. See GET /api/scoring/assertions?subject='
                '<system-choice-subject> for the actual evidence-'
                'weighted implication claims and their contested '
                'review status before treating any difference as '
                "caused by the system choice itself.",
    }
_RATE_PROV = ('representative 2022 estimate, aligned with FBI UCR/'
             'NIBRS + BJS NCVS aggregate reporting styles — state-'
             'exact figure not individually cross-verified against a '
             'single primary source this session; flag for a live '
             'data-refresh pass (same honesty convention as this '
             "session's housing/labor demo data). CRITICAL "
             'methodological note, not a caveat to skip: this term '
             'measures REPORTED occurrence, which conflates true '
             'incidence with reporting propensity — see this term\'s '
             'own description.')
SEED_IMPLICATION_SCORE_TERMS = [{
    'name': 'rape-occurrence-rate',
    'display_name': 'Reported Rape/Sexual Assault Rate',
    'description': 'Reported forcible rape/sexual assault incidents '
                   'per 100,000 population — a standard UCR/NCVS-'
                   'style criminology metric. METHODOLOGICAL '
                   'HONESTY: this measures REPORTED occurrence, not '
                   'true incidence. More survivor-friendly '
                   'evidentiary/consent standards can RAISE reported '
                   'rates even as true incidence FALLS, because '
                   'people trust the system more to report — a '
                   'well-documented criminological confound. Any '
                   'comparison using this term must be read with '
                   'that confound in mind, not as a direct safety '
                   'measure.',
    'category': 'public-safety', 'value_type': 'rate',
    'unit': 'per 100,000',
    'is_positive': False,
    'normalization_json': json.dumps(
        {'method': 'min-max', 'min': 15.0, 'max': 50.0}),
    'temporal_json': json.dumps(
        {'nature': 'flow', 'resample': 'mean'}),
    'abstract_tags_json': json.dumps(
        ['public-safety', 'criminal-justice', 'reported-crime']),
    'provenance_id': _RATE_PROV,
}]
_RATE_DATA = {
    'alabama': 38.2,
    'california': 27.4,
    'idaho': 33.6,
    'texas': 41.8,
    'washington-dc': 45.3,
}
SEED_IMPLICATION_CONTEXTUALIZED_VALUES = [
    {
        'name': f'rape-occurrence-rate@{state}-2022',
        'term_name': 'rape-occurrence-rate',
        'subject_name': state,
        'context_names_json': json.dumps([f'state-{state}', 'year-2022']),
        'pre_normalized_value': value,
        'source': 'FBI UCR/NIBRS + BJS NCVS aggregate reporting',
        'provenance_id': _RATE_PROV,
    }
    for state, value in _RATE_DATA.items()
]
SEED_SYSTEM_CHOICES_IN_FORCE = [
    {
        'name': 'in-force-california-consent',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'consent-determination-fork',
        'criterion_name': 'affirmative-consent-standard',
        'jurisdiction_subject_name': 'california',
        'effective_from': '2015-01-01', 'effective_to': '',
        'source': 'representative demo reflecting CA\'s affirmative-'
                  'consent policy direction (e.g. SB 967)',
        'provenance_id': 'Phase D implications seed',
    },
    {
        'name': 'in-force-dc-consent',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'consent-determination-fork',
        'criterion_name': 'affirmative-consent-standard',
        'jurisdiction_subject_name': 'washington-dc',
        'effective_from': '2019-01-01', 'effective_to': '',
        'source': 'representative demo reflecting DC\'s criminal-code '
                  'reform direction',
        'provenance_id': 'Phase D implications seed',
    },
    {
        'name': 'in-force-texas-consent',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'consent-determination-fork',
        'criterion_name': 'force-based-consent-standard',
        'jurisdiction_subject_name': 'texas',
        'effective_from': '', 'effective_to': '',
        'source': 'representative demo reflecting TX\'s statutory '
                  'baseline',
        'provenance_id': 'Phase D implications seed',
    },
    {
        'name': 'in-force-alabama-consent',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'consent-determination-fork',
        'criterion_name': 'force-based-consent-standard',
        'jurisdiction_subject_name': 'alabama',
        'effective_from': '', 'effective_to': '',
        'source': 'representative demo reflecting AL\'s statutory '
                  'baseline',
        'provenance_id': 'Phase D implications seed',
    },
    {
        'name': 'in-force-idaho-consent',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'consent-determination-fork',
        'criterion_name': 'force-based-consent-standard',
        'jurisdiction_subject_name': 'idaho',
        'effective_from': '', 'effective_to': '',
        'source': 'representative demo reflecting ID\'s statutory '
                  'baseline',
        'provenance_id': 'Phase D implications seed',
    },
]
SEED_IMPLICATION_SUBJECTS = [
    {
        'name': 'system-choice-affirmative-consent',
        'display_name': 'Affirmative-Consent Standard (System Choice)',
        'kind': 'judicial-system-choice',
        'object_ref_json': json.dumps(
            {'kind': 'objectRef', 'className': 'LogicForkCriterion',
             'name': 'affirmative-consent-standard'}),
        'description': 'The affirmative-consent-standard criterion, '
                       'as a scored subject implication assertions '
                       'about its real-world effects can anchor to.',
    },
    {
        'name': 'system-choice-force-based-consent',
        'display_name': 'Force-Based Consent Standard (System Choice)',
        'kind': 'judicial-system-choice',
        'object_ref_json': json.dumps(
            {'kind': 'objectRef', 'className': 'LogicForkCriterion',
             'name': 'force-based-consent-standard'}),
        'description': 'The force-based-consent-standard criterion, '
                       'as a scored subject implication assertions '
                       'about its real-world effects can anchor to.',
    },
]
SEED_IMPLICATION_ASSERTIONS = [
    {
        'name': 'assert-affirmative-consent-safety-improvement',
        'display_name': "Affirmative-consent adoption's asserted "
                        'safety-improvement effect',
        'subject_name': 'system-choice-affirmative-consent',
        'target_ref_json': json.dumps(
            {'kind': 'objectRef', 'className': 'LogicForkCriterion',
             'name': 'affirmative-consent-standard'}),
        'intent': 'Adopting the affirmative-consent standard '
                  'improves real-world safety outcomes over time '
                  '(deterrence + accountability effects), which '
                  'this demo\'s reported-rate comparison (CA 27.4, '
                  'DC 45.3 vs. TX 41.8, AL 38.2, ID 33.6 per 100k) '
                  'is offered as partial, contested evidence for — '
                  'NOT a settled finding.',
        'assertion_type': 'score-impact',
        'direction': 'supports',
        'strength': 0.35,
        'term_name': 'rape-occurrence-rate',
        'evidence_names_json': '[]',
        'asserted_by': 'demo-victim-advocacy-coalition',
        'status': 'under-review',
        'provenance_id': 'Phase D implications seed',
        'notes': 'CONTESTED — see assert-reporting-propensity-rival-'
                 'explanation for the leading rival hypothesis. This '
                 "demo has neither the panel-data history nor the "
                 'jurisdiction count to distinguish a true-incidence '
                 'effect from a reporting-propensity effect; treat '
                 'the strength value as reflecting that genuine '
                 'uncertainty, not a considered confidence estimate.',
    },
    {
        'name': 'assert-reporting-propensity-rival-explanation',
        'display_name': 'Reporting-propensity rival explanation for '
                        'the observed rate difference',
        'subject_name': 'system-choice-affirmative-consent',
        'target_ref_json': json.dumps(
            {'kind': 'objectRef', 'className': 'LogicForkCriterion',
             'name': 'affirmative-consent-standard'}),
        'intent': 'The higher reported rate observed in affirmative-'
                  'consent jurisdictions in this demo more '
                  'parsimoniously reflects increased REPORTING '
                  'PROPENSITY (survivors trusting the system more '
                  'following evidentiary reform) than a change in '
                  'true incidence — a well-documented criminological '
                  'confound. This is NOT a claim that affirmative-'
                  'consent standards are bad policy, only that raw '
                  'reported-rate comparisons cannot isolate a true-'
                  'incidence effect from this confound.',
        'assertion_type': 'score-impact',
        'direction': 'harms',
        'strength': 0.5,
        'term_name': 'rape-occurrence-rate',
        'evidence_names_json': '[]',
        'asserted_by': 'demo-forensic-psychology-panel',
        'status': 'under-review',
        'provenance_id': 'Phase D implications seed',
        'notes': 'Complementary/competing with '
                 'assert-affirmative-consent-safety-improvement, not '
                 'necessarily contradictory — both effects could be '
                 'real simultaneously; this demo cannot separate '
                 'them.',
    },
]
SEED_IMPLICATION_VALIDITY_VOTES = [
    {
        'name': 'validity-safety-vote-victim-advocacy',
        'assertion_name': 'assert-affirmative-consent-safety-improvement',
        'voter': 'demo-victim-advocacy-coalition',
        'round_number': 1, 'vote': 'valid',
        'rationale': 'Consistent with the coalition\'s policy '
                     'position, though we agree more data is needed.',
        'cast_date': '2026-07-12',
    },
    {
        'name': 'validity-safety-vote-forensic-panel',
        'assertion_name': 'assert-affirmative-consent-safety-improvement',
        'voter': 'demo-forensic-psychology-panel',
        'round_number': 1, 'vote': 'invalid',
        'rationale': 'The comparison as presented cannot rule out '
                     'the reporting-propensity confound — see our '
                     'companion assertion.',
        'cast_date': '2026-07-12',
    },
    {
        'name': 'validity-safety-vote-judicial-conference',
        'assertion_name': 'assert-affirmative-consent-safety-improvement',
        'voter': 'demo-judicial-conference',
        'round_number': 1, 'vote': 'abstain',
        'rationale': 'Outside the judiciary\'s expertise to assess '
                     'the underlying criminological claim.',
        'cast_date': '2026-07-13',
    },
    {
        'name': 'validity-confound-vote-forensic-panel',
        'assertion_name': 'assert-reporting-propensity-rival-explanation',
        'voter': 'demo-forensic-psychology-panel',
        'round_number': 1, 'vote': 'valid',
        'rationale': 'A well-established confound in this literature.',
        'cast_date': '2026-07-12',
    },
    {
        'name': 'validity-confound-vote-victim-advocacy',
        'assertion_name': 'assert-reporting-propensity-rival-explanation',
        'voter': 'demo-victim-advocacy-coalition',
        'round_number': 1, 'vote': 'valid',
        'rationale': 'Agreed the confound is real — we hold both '
                     'effects can be true simultaneously.',
        'cast_date': '2026-07-13',
    },
]
SEED_INTERPRETATION_SCORE_CONCEPTS = [
    {
        'name': 'interpretation-safety-improvement-effect',
        'display_name': 'Interpretation: Genuine Safety-Improvement '
                        'Effect',
        'description': 'Weights the observed rate difference as '
                       'substantially attributable to a genuine '
                       'safety-improvement effect from affirmative-'
                       'consent adoption (deterrence + '
                       'accountability).',
        'subject_kind': 'judicial-system-choice',
        'term_weights_json': json.dumps([
            {'term': 'rape-occurrence-rate', 'weight': 1}]),
        'required_context_names_json': '[]',
        'aggregation': 'weighted-mean',
        'levelize': False,
        'provenance_id': 'Phase D implications correction seed',
    },
    {
        'name': 'interpretation-reporting-propensity-effect',
        'display_name': 'Interpretation: Reporting-Propensity Effect',
        'description': 'Weights the observed rate difference as '
                       'substantially attributable to increased '
                       'reporting propensity (survivor trust) rather '
                       'than a true-incidence change.',
        'subject_kind': 'judicial-system-choice',
        'term_weights_json': json.dumps([
            {'term': 'rape-occurrence-rate', 'weight': 1}]),
        'required_context_names_json': '[]',
        'aggregation': 'weighted-mean',
        'levelize': False,
        'provenance_id': 'Phase D implications correction seed',
    },
]
SEED_INTERPRETATION_SCORE_GROUPS = [{
    'name': 'rape-occurrence-interpretation-assembly',
    'display_name': 'Rape-Occurrence-Rate Interpretation Assembly',
    'group_type': 'civic',
    'member_concept_names_json': json.dumps([
        'interpretation-safety-improvement-effect',
        'interpretation-reporting-propensity-effect']),
    'member_contributor_names_json': json.dumps([
        'demo-victim-advocacy-coalition', 'demo-forensic-psychology-panel',
        'demo-judicial-conference', 'demo-prosecutors-association',
        'demo-defense-bar-association']),
    'description': 'Democratically weights how much each competing '
                   'explanation should count, rather than forcing a '
                   'single-winner valid/invalid verdict on either.',
}]
SEED_INTERPRETATION_ELECTIONS = [{
    'name': 'rape-occurrence-interpretation-election',
    'display_name': 'How much should each explanation count?',
    'description': 'Approval vote — voters may approve either '
                   'explanation, or both, expressing that multiple '
                   'explanations can carry real weight '
                   'simultaneously rather than picking one as "the" '
                   'true account.',
    'group_name': 'rape-occurrence-interpretation-assembly',
    'mode': 'approval',
    'status': 'closed',
    'opens_date': '2026-07-14', 'closes_date': '2026-07-14',
    'provenance_id': 'Phase D implications correction seed',
}]
SEED_INTERPRETATION_BALLOTS = [
    {
        'name': 'interpretation-ballot-victim-advocacy',
        'election_name': 'rape-occurrence-interpretation-election',
        'voter': 'demo-victim-advocacy-coalition',
        'approvals_json': json.dumps(
            ['interpretation-safety-improvement-effect']),
        'cast_date': '2026-07-14',
    },
    {
        'name': 'interpretation-ballot-forensic-panel',
        'election_name': 'rape-occurrence-interpretation-election',
        'voter': 'demo-forensic-psychology-panel',
        'approvals_json': json.dumps(
            ['interpretation-reporting-propensity-effect']),
        'cast_date': '2026-07-14',
    },
    {
        # Approves BOTH — "both are valid but should be weighted".
        'name': 'interpretation-ballot-judicial-conference',
        'election_name': 'rape-occurrence-interpretation-election',
        'voter': 'demo-judicial-conference',
        'approvals_json': json.dumps([
            'interpretation-safety-improvement-effect',
            'interpretation-reporting-propensity-effect']),
        'cast_date': '2026-07-14',
    },
    {
        # Approves BOTH.
        'name': 'interpretation-ballot-prosecutors',
        'election_name': 'rape-occurrence-interpretation-election',
        'voter': 'demo-prosecutors-association',
        'approvals_json': json.dumps([
            'interpretation-safety-improvement-effect',
            'interpretation-reporting-propensity-effect']),
        'cast_date': '2026-07-14',
    },
    {
        'name': 'interpretation-ballot-defense-bar',
        'election_name': 'rape-occurrence-interpretation-election',
        'voter': 'demo-defense-bar-association',
        'approvals_json': json.dumps(
            ['interpretation-reporting-propensity-effect']),
        'cast_date': '2026-07-14',
    },
]
