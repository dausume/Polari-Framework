"""@module dmvdata.objects.cross_validation._shared — what the cross_validation row classes share (constants, seeds, helpers); split from cross_validation_basis.py (sap-2c)."""
from scoring.survival_costs_basis import SMALL_SAMPLE
import json
import threading
from polariApiProfiler.schema_drift import verify_continuity

CONTRADICTED_SHARE = 0.2
MISMATCH_DETAIL_CAP = 20
CREDIBILITY_PRIOR = 1.0
VERDICT_WEIGHTS = {'confirmed': 1.0, 'partial': 0.5,
                   'contradicted': 0.0}
_CONFIRMATION_LOCK = threading.Lock()
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
     'provenance_id': 'dmvdata.cross_validation_basis provider terms',
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
     'provenance_id': 'dmvdata.cross_validation_basis provider terms',
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
     'provenance_id': 'dmvdata.cross_validation_basis provider terms',
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
     'provenance_id': 'dmvdata.cross_validation_basis provider concept',
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
