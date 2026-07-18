"""
@module dmvdata.cross_validation

Cross-validation of duplicated source data (Dustin 2026-07-16):
more users assert duplicate data as REAL by pulling the same source
on their own Polari instance and comparing — each comparison is a
RetrievalConfirmation row tying the validator's own independent
SourceRetrieval to the one being validated, with a computed
per-key/per-field comparison and group-or-individual attribution.
Confirmations by DISTINCT confirmers raise the sourcing-credibility
READING; contradictions lower it. Groups that PROVIDE data become
scoreable subjects through the standard engine (ScoreTerms + a
'data-provider-reliability' ScoreConcept whose weights are
mechanism-B votable).

Honesty stances baked in:
  * Credibility is a READING with evidence, never a truth
    declaration — the reading text says so.
  * Self-confirmation is refused (independence is the point).
  * Small samples are flagged (the scr-12a SMALL_SAMPLE idiom).
  * Verdict thresholds and the credibility prior are module
    constants — knobs, not hidden policy.

@consumers
  - dmvdata.selftest_cross_validation
  - scoring engine (via SEED_PROVIDER_TERMS / SEED_PROVIDER_CONCEPT
    + push_provider_scores)
"""

import json
import threading
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit
from polariApiProfiler.schema_drift import verify_continuity
from scoring.survival_costs import SMALL_SAMPLE

#: Verdict knobs: a mismatch (or missing-key) SHARE above this is a
#: contradiction; zero mismatches AND zero missing originals is a
#: confirmation; between = partial.
CONTRADICTED_SHARE = 0.2
#: Mismatch detail is evidence, not a data dump.
MISMATCH_DETAIL_CAP = 20
#: Credibility prior: score = Σ(verdict weights of DISTINCT
#: confirmers) / (distinct confirmers + PRIOR). One clean
#: confirmation = 0.5; each additional distinct confirmer raises it;
#: a contradiction adds a confirmer with weight 0, lowering it.
CREDIBILITY_PRIOR = 1.0
VERDICT_WEIGHTS = {'confirmed': 1.0, 'partial': 0.5,
                   'contradicted': 0.0}

_CONFIRMATION_LOCK = threading.Lock()


class RetrievalConfirmation(treeObject):
    """One independent re-pull compared against a recorded
    retrieval — the cross-validation unit."""

    @treeObjectInit
    def __init__(self, name: str = '',
                 subject_retrieval_name: str = '',
                 confirming_retrieval_name: str = '',
                 confirmed_by: str = '',
                 confirmed_by_group: str = '',
                 compared_at: str = '',
                 rows_compared: int = 0, matches: int = 0,
                 mismatches: int = 0,
                 mismatch_detail_json: str = '[]',
                 verdict: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.subject_retrieval_name = subject_retrieval_name
        self.confirming_retrieval_name = confirming_retrieval_name
        self.confirmed_by = confirmed_by
        self.confirmed_by_group = confirmed_by_group
        self.compared_at = compared_at
        self.rows_compared = rows_compared
        self.matches = matches
        self.mismatches = mismatches
        self.mismatch_detail_json = mismatch_detail_json
        self.verdict = verdict
        self.notes = notes


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _retrieval(manager, name):
    return next((r for r in _rows(manager, 'SourceRetrieval')
                 if getattr(r, 'name', '') == name), None)


def _known_retrievals(manager):
    return sorted(getattr(r, 'name', '')
                  for r in _rows(manager, 'SourceRetrieval'))


def compare_duplicate_data(original_rows, independent_rows,
                           key_field):
    """Per-key, per-field comparison of a duplicate pull against the
    original — verify_continuity's proof, translated into the
    confirmation vocabulary. Extra rows in the independent pull
    (newIds) do not count against the original rows' validity but
    are reported."""
    continuity = verify_continuity(original_rows, independent_rows,
                                   key_field)
    matched = continuity['matchedIds']
    mismatch_rows = {m['id'] for m in continuity['valueMismatches']}
    detail = continuity['valueMismatches'][:MISMATCH_DETAIL_CAP]
    truncated = (len(continuity['valueMismatches'])
                 > MISMATCH_DETAIL_CAP)
    if truncated:
        detail = detail + [{'truncated': True,
                            'totalMismatches':
                                len(continuity['valueMismatches'])}]
    original_count = len(original_rows or [])
    mismatch_share = (len(mismatch_rows) / len(matched)
                      if matched else 1.0)
    missing_share = (len(continuity['missingIds']) / original_count
                     if original_count else 1.0)
    if not continuity['valueMismatches'] \
            and not continuity['missingIds'] and original_count:
        verdict = 'confirmed'
    elif (mismatch_share > CONTRADICTED_SHARE
          or missing_share > CONTRADICTED_SHARE):
        verdict = 'contradicted'
    else:
        verdict = 'partial'
    return {'rowsCompared': len(matched),
            'matches': len(matched) - len(mismatch_rows),
            'mismatches': len(mismatch_rows),
            'mismatchDetail': detail,
            'missingIds': continuity['missingIds'],
            'newIds': continuity['newIds'],
            'mismatchShare': round(mismatch_share, 4),
            'missingShare': round(missing_share, 4),
            'verdict': verdict}


def confirm_retrieval(manager, subject_retrieval_name,
                      confirming_retrieval_name, original_rows,
                      independent_rows, key_field, confirmed_by,
                      confirmed_by_group='', compared_at=None,
                      notes=''):
    """Record one cross-validation. Both retrieval rows must exist;
    the confirmer must be INDEPENDENT of the subject retrieval's
    origin (same person AND same group = self-confirmation,
    refused)."""
    subject = _retrieval(manager, subject_retrieval_name)
    if subject is None:
        return {'ok': False,
                'error': f'no SourceRetrieval named '
                         f"'{subject_retrieval_name}'",
                'knownRetrievals': _known_retrievals(manager)}
    confirming = _retrieval(manager, confirming_retrieval_name)
    if confirming is None:
        return {'ok': False,
                'error': f'no SourceRetrieval named '
                         f"'{confirming_retrieval_name}' — record "
                         f'the validator\'s own pull first '
                         f'(record_retrieval)',
                'knownRetrievals': _known_retrievals(manager)}
    if not confirmed_by:
        return {'ok': False,
                'error': 'confirmed_by must name the Contributor '
                         'doing the validation'}
    same_person = (confirmed_by
                   == getattr(subject, 'retrieved_by', ''))
    same_group = (confirmed_by_group
                  == getattr(subject, 'retrieved_by_group', ''))
    if same_person and same_group:
        return {'ok': False,
                'error': 'self-confirmation refused: the subject '
                         'retrieval was recorded by the same '
                         'person and group — cross-validation '
                         'requires an INDEPENDENT puller'}
    comparison = compare_duplicate_data(original_rows,
                                        independent_rows, key_field)
    stamp = compared_at or datetime.now(timezone.utc).isoformat()
    with _CONFIRMATION_LOCK:
        table = manager.objectTables.setdefault(
            'RetrievalConfirmation', {})
        taken = {getattr(r, 'name', '') for r in table.values()}
        base = (f'{subject_retrieval_name}--by-'
                f'{confirmed_by_group or confirmed_by}')
        row_name, suffix = base, 2
        while row_name in taken:
            row_name = f'{base}-{suffix}'
            suffix += 1
        row = RetrievalConfirmation(
            name=row_name,
            subject_retrieval_name=subject_retrieval_name,
            confirming_retrieval_name=confirming_retrieval_name,
            confirmed_by=confirmed_by,
            confirmed_by_group=confirmed_by_group,
            compared_at=stamp,
            rows_compared=comparison['rowsCompared'],
            matches=comparison['matches'],
            mismatches=comparison['mismatches'],
            mismatch_detail_json=json.dumps(
                comparison['mismatchDetail']),
            verdict=comparison['verdict'], notes=notes,
            manager=manager)
        if not any(existing is row for existing in table.values()):
            table[row_name] = row
    db = getattr(manager, 'db', None)
    persisted = True
    if db is not None:
        try:
            db.saveInstanceInDB(row)
        except Exception as exc:
            persisted = False
            print(f'[CrossValidation] save FAILED for {row_name}: '
                  f'{exc}', flush=True)
    result = {'ok': True, 'confirmation': row_name,
              'comparison': comparison}
    if not persisted:
        result['persistWarning'] = ('the DB save FAILED — this '
                                    'confirmation exists in memory '
                                    'only')
    return result


def _confirmations_for_retrievals(manager, retrieval_names):
    return [c for c in _rows(manager, 'RetrievalConfirmation')
            if getattr(c, 'subject_retrieval_name', '')
            in retrieval_names]


def sourcing_credibility(manager, name, subject='retrieval'):
    """The credibility READING for one retrieval (or every retrieval
    of a source). Formula (documented, a future mechanism-C
    criterion): score = Σ(verdict weights of DISTINCT confirmers,
    latest confirmation each) / (distinct confirmers +
    CREDIBILITY_PRIOR). Confirmed=1, partial=0.5, contradicted=0 —
    so each additional independent confirmation RAISES the score
    and each contradiction LOWERS it. Never a truth declaration."""
    if subject == 'retrieval':
        wanted = {name}
        if _retrieval(manager, name) is None:
            return {'ok': False,
                    'error': f"no SourceRetrieval named '{name}'",
                    'knownRetrievals': _known_retrievals(manager)}
    elif subject == 'source':
        wanted = {getattr(r, 'name', '')
                  for r in _rows(manager, 'SourceRetrieval')
                  if getattr(r, 'source_name', '') == name}
        if not wanted:
            return {'ok': False,
                    'error': f'no SourceRetrieval rows for source '
                             f"'{name}'"}
    else:
        return {'ok': False,
                'error': "subject must be 'retrieval' or 'source'"}
    confirmations = _confirmations_for_retrievals(manager, wanted)
    if not confirmations:
        return {'ok': True, 'score': None, 'confirmationCount': 0,
                'reading': 'no independent confirmations yet — '
                           'credibility unrated, not zero',
                'suggestion': {
                    'knob': 'confirm_retrieval',
                    'action': 'pull the same data on another '
                              'instance and record the comparison'}}
    latest_by_confirmer = {}
    for c in sorted(confirmations,
                    key=lambda r: getattr(r, 'compared_at', '')):
        confirmer = (getattr(c, 'confirmed_by_group', '')
                     or f'individual:{getattr(c, "confirmed_by", "")}')
        latest_by_confirmer[confirmer] = c
    weights = {confirmer: VERDICT_WEIGHTS.get(
                   getattr(c, 'verdict', ''), 0.0)
               for confirmer, c in latest_by_confirmer.items()}
    score = (sum(weights.values())
             / (len(weights) + CREDIBILITY_PRIOR))
    verdicts = [getattr(c, 'verdict', '') for c in confirmations]
    distinct_groups = {getattr(c, 'confirmed_by_group', '')
                       for c in confirmations
                       if getattr(c, 'confirmed_by_group', '')}
    evidence = [f'{confirmer}: {getattr(c, "verdict", "")} '
                f'({getattr(c, "matches", 0)}/'
                f'{getattr(c, "rows_compared", 0)} rows matched)'
                for confirmer, c in
                sorted(latest_by_confirmer.items())]
    return {'ok': True, 'score': round(score, 4),
            'confirmationCount': len(confirmations),
            'distinctConfirmers': len(latest_by_confirmer),
            'distinctGroups': len(distinct_groups),
            'confirmedCount': verdicts.count('confirmed'),
            'partialCount': verdicts.count('partial'),
            'contradictedCount': verdicts.count('contradicted'),
            'smallSample': len(confirmations) < SMALL_SAMPLE,
            'reading': 'a credibility READING with evidence, not a '
                       'truth declaration',
            'evidence': evidence}


def provider_reliability(manager, group_name):
    """Reliability reading for a GROUP that provides data: its
    retrievals, how the rest of the network's independent re-pulls
    judged them, and any additional score-term values on the group
    subject (the 'other factors' extension point)."""
    retrievals = [r for r in _rows(manager, 'SourceRetrieval')
                  if getattr(r, 'retrieved_by_group', '')
                  == group_name]
    if not retrievals:
        return {'ok': False,
                'error': f"no SourceRetrieval rows attribute group "
                         f"'{group_name}'"}
    stamps = sorted(getattr(r, 'retrieved_at', '')
                    for r in retrievals)
    statuses = {}
    for retrieval in retrievals:
        r_name = getattr(retrieval, 'name', '')
        # Only OTHERS' judgments count toward reliability.
        confirms = [c for c in _confirmations_for_retrievals(
                        manager, {r_name})
                    if getattr(c, 'confirmed_by_group', '')
                    != group_name]
        verdicts = {getattr(c, 'verdict', '') for c in confirms}
        if 'contradicted' in verdicts:
            statuses[r_name] = 'contradicted'
        elif 'confirmed' in verdicts:
            statuses[r_name] = 'confirmed'
        elif 'partial' in verdicts:
            statuses[r_name] = 'partial'
        else:
            statuses[r_name] = 'unconfirmed'
    volume = len(retrievals)
    confirmed = sum(1 for s in statuses.values() if s == 'confirmed')
    contradicted = sum(1 for s in statuses.values()
                       if s == 'contradicted')
    other_factors = [
        {'term': getattr(v, 'term_name', ''),
         'value': getattr(v, 'pre_normalized_value', None),
         'provenance': getattr(v, 'provenance_id', '')}
        for v in _rows(manager, 'ContextualizedValue')
        if getattr(v, 'subject_name', '') == group_name
        and getattr(v, 'term_name', '')
        not in {t['name'] for t in SEED_PROVIDER_TERMS}]
    return {'ok': True, 'group': group_name, 'volume': volume,
            'span': {'first': stamps[0], 'last': stamps[-1]},
            'confirmedRetrievals': confirmed,
            'contradictedRetrievals': contradicted,
            'unconfirmedRetrievals': sum(
                1 for s in statuses.values() if s == 'unconfirmed'),
            'confirmationRate': round(confirmed / volume, 4),
            'contradictionRate': round(contradicted / volume, 4),
            'perRetrieval': statuses,
            'smallSample': volume < SMALL_SAMPLE,
            'otherFactors': other_factors,
            'reading': 'a reliability READING with evidence, not a '
                       'truth declaration'}


_PROVIDER_PROVENANCE = ('derived from RetrievalConfirmation rows — '
                        'independent re-pull comparisons, never '
                        'self-attested')

SEED_PROVIDER_TERMS = [
    {'name': 'data-confirmation-rate',
     'display_name': 'Data Confirmation Rate',
     'description': 'Share of a provider group\'s recorded '
                    'retrievals independently CONFIRMED by other '
                    'groups/individuals re-pulling the same source.',
     'category': 'data-provenance', 'value_type': 'custom',
     'unit': 'ratio', 'is_positive': True,
     'abstract_tags_json': json.dumps(
         ['data-trust', 'reliability', 'provenance']),
     'source': _PROVIDER_PROVENANCE,
     'provenance_id': 'dmvdata.cross_validation provider terms',
     'notes': ''},
    {'name': 'data-contradiction-rate',
     'display_name': 'Data Contradiction Rate',
     'description': 'Share of a provider group\'s retrievals that '
                    'independent re-pulls CONTRADICTED.',
     'category': 'data-provenance', 'value_type': 'custom',
     'unit': 'ratio', 'is_positive': False,
     'abstract_tags_json': json.dumps(
         ['data-trust', 'reliability', 'provenance']),
     'source': _PROVIDER_PROVENANCE,
     'provenance_id': 'dmvdata.cross_validation provider terms',
     'notes': ''},
    {'name': 'data-retrieval-volume',
     'display_name': 'Data Retrieval Volume',
     'description': 'How many attributed retrievals the group has '
                    'recorded — experience, flagged small-sample '
                    'below the scr-12a threshold.',
     'category': 'data-provenance', 'value_type': 'custom',
     'unit': 'count', 'is_positive': True,
     'abstract_tags_json': json.dumps(
         ['data-trust', 'reliability', 'volume']),
     'source': _PROVIDER_PROVENANCE,
     'provenance_id': 'dmvdata.cross_validation provider terms',
     'notes': ''},
]

SEED_PROVIDER_CONCEPT = [
    {'name': 'data-provider-reliability',
     'display_name': 'Data Provider Reliability',
     'description': 'How reliable a data-providing group has proven '
                    'under independent cross-validation. The '
                    'starter weights below are a DEFAULT, not a '
                    'ruling — mechanism-B worldview elections can '
                    'reweight them (and add other factors as more '
                    'terms).',
     'subject_kind': 'group',
     'subject_names_json': '[]',
     'term_weights_json': json.dumps([
         {'term': 'data-confirmation-rate', 'weight': 6},
         {'term': 'data-contradiction-rate', 'weight': 6},
         {'term': 'data-retrieval-volume', 'weight': 2},
     ]),
     'required_context_names_json': '[]',
     'aggregation': 'weighted-mean', 'levelize': True,
     'abstract_tags_json': json.dumps(
         ['data-trust', 'reliability', 'provenance']),
     'provenance_id': 'dmvdata.cross_validation provider concept',
     'notes': ''},
]


def push_provider_scores(manager, group_name, timeframe_context):
    """Materialize a group's reliability reading as
    ContextualizedValue rows under the provider terms so the
    STANDARD scoring engine can score the concept. Idempotent by
    name; provenance counts the confirmations behind the numbers."""
    reading = provider_reliability(manager, group_name)
    if not reading.get('ok'):
        return reading
    confirmation_count = sum(
        1 for c in _rows(manager, 'RetrievalConfirmation')
        if getattr(c, 'subject_retrieval_name', '')
        in reading['perRetrieval'])
    provenance = (f'{_PROVIDER_PROVENANCE}; '
                  f'{confirmation_count} confirmations over '
                  f"{reading['volume']} retrievals")
    values = [
        ('data-confirmation-rate', reading['confirmationRate']),
        ('data-contradiction-rate', reading['contradictionRate']),
        ('data-retrieval-volume', float(reading['volume'])),
    ]
    from scoring.scoring_basis import ContextualizedValue
    table = manager.objectTables.setdefault('ContextualizedValue',
                                            {})
    written = []
    for term_name, value in values:
        row_name = f'{term_name}@{group_name}-{timeframe_context}'
        existing = next((v for v in table.values()
                         if getattr(v, 'name', '') == row_name),
                        None)
        if existing is not None:
            existing.pre_normalized_value = value
            existing.provenance_id = provenance
        else:
            row = ContextualizedValue(
                name=row_name, term_name=term_name,
                subject_name=group_name,
                context_names_json=json.dumps([timeframe_context]),
                pre_normalized_value=value,
                source='cross-validation derivation',
                provenance_id=provenance, notes='',
                manager=manager)
            if not any(v is row for v in table.values()):
                table[row_name] = row
        written.append(row_name)
    return {'ok': True, 'written': written,
            'smallSample': reading['smallSample'],
            'provenance': provenance}
