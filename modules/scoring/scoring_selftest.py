"""
Selftest — context-based scoring (the Political Scorecard generalized).

Run from polari-framework/:
    python3 -m scoring.scoring_selftest

Covers: PARITY with the scorecard's Labor Quality spreadsheet sample
(same 2022 data, ranges, weights → same initialScores, same ranking,
DC on top at levelized 100); inversion for anti-competitive terms;
context matching by specificity; the arbitrary-data seam (objectRef
into another class's JSON blob resolves live; a dangling ref is an
honest absence, and missing terms stay in the denominator); honest
errors for unknown concepts and empty subject selections.
"""

from types import SimpleNamespace

from scoring.custom.scoring_engine import (
    normalize_value, score_concept, select_value,
)
from scoring.agreement_policy_basis import (
    SEED_AGREEMENT_POLICIES, classify_max,
)
from scoring.custom.group_aggregation import (
    aggregate_group, all_groups_consensus, compare_groups,
)
from scoring.scoring_seed import (
    SEED_CONTEXTUALIZED_VALUES, SEED_SCORE_CONCEPTS,
    SEED_SCORE_CONTEXTS, SEED_SCORE_GROUPS, SEED_SCORE_SUBJECTS,
    SEED_SCORE_TERMS,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**{'pre_normalized_value': None, **r})
            for i, r in enumerate(seed_list)}


def _mgr(with_beeswax_result=True):
    tables = {
        'ScoreTerm': _rows(SEED_SCORE_TERMS),
        'ScoreContext': _rows(SEED_SCORE_CONTEXTS),
        'ScoreSubject': _rows(SEED_SCORE_SUBJECTS),
        'ContextualizedValue': _rows(SEED_CONTEXTUALIZED_VALUES),
        'ScoreConcept': _rows(SEED_SCORE_CONCEPTS),
        'ScoreGroup': _rows(SEED_SCORE_GROUPS),
        'AgreementPolicy': _rows(SEED_AGREEMENT_POLICIES),
        'FEMModelDefinition': {},
        'MaterialScaleDefinition': {},
    }
    if with_beeswax_result:
        tables['FEMModelDefinition'] = {0: SimpleNamespace(
            name='wax-thermal-continuum',
            last_result_json='{"effectiveK": 0.2593}')}
    return SimpleNamespace(objectTables=tables)


#: Expected initialScores, hand-computed from the scorecard sample's
#: exact formula (weightedSum / 21).
EXPECTED = {
    'washington-dc': 0.924732,
    'california': 0.720064,
    'idaho': 0.438120,
    'texas': 0.157559,
    'alabama': 0.114809,
}


if __name__ == '__main__':
    print('\nContext-based scoring (scorecard generalization)\n')

    print('normalization')
    ok, v, spec = normalize_value(
        13.5, {'method': 'min-max', 'min': 5.0, 'max': 15.0}, False)
    check('anti-competitive inversion (13.5% poverty -> 0.15)',
          ok and abs(v - 0.15) < 1e-9, f'{v}')
    ok, v, spec = normalize_value(
        16.0, {'method': 'min-max', 'min': 7.25, 'max': 17.50}, True)
    check('min-max ($16 wage -> 0.853659)',
          ok and abs(v - 0.8536585) < 1e-6)
    ok, _, refusal = normalize_value(1.0, {'method': 'z-score'}, True)
    check('unknown method refused naming the knob',
          not ok and refusal['suggestion']['knob']
          == 'normalization_json')
    ok, _, refusal = normalize_value(
        1.0, {'method': 'min-max-auto'}, True, value_pool=[1.0])
    check('min-max-auto with a degenerate pool refused honestly',
          not ok and '>= 2 distinct' in refusal['error'])

    print('\nparity with the scorecard Labor Quality sample')
    report = score_concept(_mgr(), 'labor-quality')
    check('scores computed for all 5 states',
          report['ok'] and len(report['subjects']) == 5)
    by_name = {s['subject']: s for s in report['subjects']}
    for state, expected in EXPECTED.items():
        got = by_name[state]['initialScore']
        check(f'{state} initialScore parity ({expected})',
              abs(got - expected) < 1e-4, f'got {got}')
    ranking = [s['subject'] for s in report['subjects']]
    check('ranking DC > CA > ID > TX > AL',
          ranking == list(EXPECTED))
    check('DC levelized to 100',
          by_name['washington-dc']['levelizedScore'] == 100.0)
    check('total weight 21 + the count-divergence note travels',
          report['totalWeight'] == 21
          and 'divides by term count' in report['aggregationNote'])
    dc = by_name['washington-dc']
    check('breakdown carries raw + normalized + weighted + spec',
          all(('raw' in b and 'normalized' in b and 'weighted' in b
               and b['normalization']['method'] == 'min-max')
              for b in dc['breakdown'] if b['found']))
    check('no terms missing in the parity model',
          not dc['termsMissing'])

    print('\narbitrary-data seam (objectRef values)')
    report = score_concept(_mgr(), 'demo-material-conductivity')
    subjects = {s['subject']: s for s in report['subjects']}
    bee = subjects['beeswax-material']
    check('beeswax scores from the LIVE FEM result through the '
          'objectRef',
          not bee['termsMissing']
          and abs(bee['breakdown'][0]['raw'] - 0.2593) < 1e-9)
    check('objectRef source travels in the breakdown',
          'FEMModelDefinition/wax-thermal-continuum'
          in bee['breakdown'][0]['source'])
    car = subjects['carnauba-material']
    check('carnauba honestly missing (no executed L1 row)',
          car['termsMissing'] == ['thermal-conductivity-score']
          and car['initialScore'] == 0.0)
    report = score_concept(_mgr(with_beeswax_result=False),
                           'demo-material-conductivity')
    bee = {s['subject']: s for s in report['subjects']}[
        'beeswax-material']
    check('dangling objectRef -> absence with the refusal, not a '
          'guess',
          bee['termsMissing'] and not bee['breakdown'][0]['found'])

    print('\ncontext selection')
    contexts = {getattr(r, 'name', ''): r
                for r in _mgr().objectTables['ScoreContext'].values()}
    broad = SimpleNamespace(context_names_json='["year-2022"]')
    specific = SimpleNamespace(
        context_names_json='["state-california", "year-2022"]')
    chosen = select_value([broad, specific], ['year-2022'], contexts)
    check('most specific value wins (state beats bare year)',
          chosen is specific)
    check('required context not held -> no match',
          select_value([broad], ['state-texas'], contexts) is None)
    check('hierarchy is functional: state value satisfies required '
          'country-usa via parent chain',
          select_value([specific], ['country-usa'], contexts)
          is specific)
    check('hierarchy does not invent downward matches (country value '
          'never satisfies a required state)',
          select_value(
              [SimpleNamespace(context_names_json='["country-usa"]')],
              ['state-california'], contexts) is None)

    print('\nnesting (scores inside scores)')
    report = score_concept(_mgr(), 'nested-labor-demo')
    by_name = {s['subject']: s for s in report['subjects']}
    # parent initial = (3*child_initial + 1*wage_normalized) / 4
    expected_dc = (3 * 0.924732 + 1 * 1.0) / 4
    check('nested parity: DC = (3*labor + 1*wage)/4',
          abs(by_name['washington-dc']['initialScore']
              - expected_dc) < 1e-4,
          f"got {by_name['washington-dc']['initialScore']}")
    expected_al = (3 * 0.114809 + 1 * 0.0) / 4
    check('nested parity: Alabama',
          abs(by_name['alabama']['initialScore'] - expected_al) < 1e-4)
    entry = by_name['washington-dc']['breakdown'][0]
    check("concept entry kind='concept' w/ child initialScore as "
          'normalized',
          entry.get('kind') == 'concept'
          and abs(entry['normalized'] - 0.924732) < 1e-4
          and entry['childTermsMissing'] == [])
    check('nestedConcepts named on the report',
          report['nestedConcepts'] == ['labor-quality'])

    mgr = _mgr()
    mgr.objectTables['ScoreConcept'][99] = SimpleNamespace(
        name='ouroboros', display_name='Ouroboros',
        subject_kind='state', subject_names_json='["texas"]',
        term_weights_json='[{"concept": "ouroboros", "weight": 1}]',
        required_context_names_json='[]',
        aggregation='weighted-mean', levelize=False)
    report = score_concept(mgr, 'ouroboros')
    entry = report['subjects'][0]['breakdown'][0]
    check('self-nesting cycle refused, named in the entry',
          report['ok'] and not entry['found']
          and 'cycle' in entry['error'])

    print('\ningestion (records + any-class series)')
    import scoring.custom.data_ingestion as ingestion_mod

    def _factory(class_name, mgr):
        def make(manager=None, **fields):
            row = SimpleNamespace(**fields)
            table = mgr.objectTables.setdefault(class_name, {})
            table[f'ing-{len(table)}'] = row
            return row
        return make

    mgr = _mgr()
    orig = (ingestion_mod.ContextualizedValue, ingestion_mod.ScoreSubject)
    ingestion_mod.ContextualizedValue = _factory(
        'ContextualizedValue', mgr)
    ingestion_mod.ScoreSubject = _factory('ScoreSubject', mgr)
    try:
        from scoring.custom.data_ingestion import (
            ingest_from_class, ingest_records,
        )
        bad = ingestion_mod.ingest_records(mgr, {
            'term': 'rainfall', 'records': [{'subject': 'x',
                                             'value': 1}]})
        check('unknown term refused naming the ScoreTerm knob',
              not bad['ok'] and bad['suggestion']['knob'] == 'ScoreTerm')
        bad = ingestion_mod.ingest_records(mgr, {
            'term': 'minimum-wage',
            'records': [{'subject': 'Oregon', 'value': 14.2}]})
        check('unknown subject refused w/ wouldCreate + the knob',
              not bad['ok'] and bad['wouldCreate'] == ['oregon']
              and bad['suggestion']['knob']
              == 'create_missing_subjects')
        bad = ingestion_mod.ingest_records(mgr, {
            'term': 'minimum-wage', 'contexts': ['year-2099'],
            'records': [{'subject': 'texas', 'value': 7.25}]})
        check('unknown context refused (contexts never auto-invented)',
              not bad['ok'] and 'year-2099' in bad['error'])
        result = ingestion_mod.ingest_records(mgr, {
            'term': 'minimum-wage', 'subject_kind': 'state',
            'contexts': ['year-2022'],
            'create_missing_subjects': True,
            'records': [{'subject': 'Oregon', 'value': 14.2}]})
        check('create_missing_subjects knob creates subject + value',
              result['ok'] and result['createdSubjects'] == ['oregon']
              and len(result['created']) == 1)
        again = ingestion_mod.ingest_records(mgr, {
            'term': 'minimum-wage', 'contexts': ['year-2022'],
            'records': [{'subject': 'Oregon', 'value': 15.0}]})
        check('re-ingest skips existing rows (idempotent by name)',
              again['ok'] and again['skipped'] == result['created']
              and not again['created'])
        forced = ingestion_mod.ingest_records(mgr, {
            'term': 'minimum-wage', 'contexts': ['year-2022'],
            'overwrite': True,
            'records': [{'subject': 'Oregon', 'value': 15.0}]})
        check('overwrite knob updates explicitly',
              forced['ok'] and forced['updated'] == result['created'])

        mgr.objectTables['WeatherStation'] = {
            0: SimpleNamespace(name='st-tx', state='texas',
                               rainfall=32.1),
            1: SimpleNamespace(name='st-ca', state='california',
                               rainfall=18.4),
            2: SimpleNamespace(name='st-broken', state=None,
                               rainfall=None),
        }
        mgr.objectTables['ScoreTerm'][99] = SimpleNamespace(
            name='rainfall', display_name='Rainfall',
            is_positive=True, unit='in/yr',
            normalization_json='{"method": "min-max-auto"}')
        result = ingestion_mod.ingest_from_class(mgr, {
            'term': 'rainfall', 'source_class': 'WeatherStation',
            'mapping': {'subjectField': 'state',
                        'valueField': 'rainfall'}})
        check('ANY class as a data series (2 values from '
              'WeatherStation rows)',
              result['ok'] and len(result['created']) == 2
              and result['rowsRead'] == 3)
        check('unusable rows reported, not silently dropped',
              any('st-broken' in str(r.get('row', ''))
                  for r in result['refused']))
        bad = ingestion_mod.ingest_from_class(mgr, {
            'term': 'rainfall', 'source_class': 'NoSuchClass',
            'mapping': {'subjectField': 'a', 'valueField': 'b'}})
        check('unknown class refused w/ classes that have rows',
              not bad['ok'] and 'WeatherStation'
              in bad['classesWithRows'])
    finally:
        ingestion_mod.ContextualizedValue = orig[0]
        ingestion_mod.ScoreSubject = orig[1]

    print("\nagreement bands (Dustin's settings, classify_max)")
    import json as _json
    bands = _json.loads(
        SEED_AGREEMENT_POLICIES[0]['direction_bands_json'])
    for value, label in ((0.5, 'divisive'), (0.6, 'slight-majority'),
                         (0.75, 'large-majority'),
                         (0.9, 'near-consensus'), (1.0, 'consensus')):
        check(f'{value} -> {label}',
              classify_max(value, bands) == label,
              classify_max(value, bands))

    print('\ngroup aggregation')
    mgr = _mgr()
    political = aggregate_group(mgr, 'demo-political-group')
    terms_pol = {t['key']: t for t in political['terms']}
    check('political group: minimum-wage consensus (2/2 positive)',
          terms_pol['minimum-wage']['directionClass'] == 'consensus'
          and terms_pol['minimum-wage']['dominantFraction'] == 1.0)
    check('political group: aligned weighting on minimum-wage '
          '(identical shares)',
          terms_pol['minimum-wage']['weightClass']
          == 'aligned-weighting'
          and terms_pol['minimum-wage']['weightShareSpread'] == 0.0)

    professional = aggregate_group(mgr, 'demo-professional-group')
    terms_pro = {t['key']: t for t in professional['terms']}
    check('professional group: minimum-wage DIVISIVE (carol + / '
          'dan −, 50/50)',
          terms_pro['minimum-wage']['directionClass'] == 'divisive'
          and terms_pro['minimum-wage']['negativeMembers']
          == ['member-labor-dan'])
    check('evidence numbers travel with the label',
          terms_pro['minimum-wage']['dominantFraction'] == 0.5
          and terms_pro['minimum-wage']['holders'] == 2)

    consensus = all_groups_consensus(mgr)
    terms_all = {t['key']: t for t in consensus['terms']}
    check('all-groups consensus: 4 members, minimum-wage '
          'large-majority (3/4)',
          consensus['memberCount'] == 4
          and terms_all['minimum-wage']['dominantFraction'] == 0.75
          and terms_all['minimum-wage']['directionClass']
          == 'large-majority')
    check('unsplit terms reach consensus in the union',
          terms_all['union-participation']['directionClass']
          == 'consensus')
    check('agreementIndex present',
          0.0 < consensus['agreementIndex'] <= 1.0,
          str(consensus['agreementIndex']))

    compared = compare_groups(
        mgr, ['demo-political-group', 'demo-professional-group'])
    pair = compared['pairs'][0]
    check('group comparison classified via similarity bands',
          compared['ok'] and pair['similarityClass'] in (
              'shared-definition', 'broadly-aligned',
              'partially-aligned', 'divergent'),
          f"{pair['similarity']} -> {pair['similarityClass']}")
    check('biggest disagreement named: minimum-wage (stance flip)',
          pair['topDisagreements'][0]['key'] == 'minimum-wage')

    # Settings are SETTINGS: a different policy reclassifies.
    mgr.objectTables['AgreementPolicy'][9] = SimpleNamespace(
        name='everything-is-fine',
        direction_bands_json='[{"label": "fine", "max": 1.0}]',
        weight_bands_json='[{"label": "fine", "max": 10.0}]',
        similarity_bands_json='[{"label": "fine", "min": -1.0}]')
    relaxed = aggregate_group(
        mgr, 'demo-professional-group', 'everything-is-fine')
    check('editing the policy changes the classification (knob, '
          'not code)',
          {t['key']: t for t in relaxed['terms']}[
              'minimum-wage']['directionClass'] == 'fine')

    print('\nper-entry stance (isPositive override)')
    dan = score_concept(mgr, 'member-labor-dan')
    dc = {s['subject']: s for s in dan['subjects']}['washington-dc']
    wage = next(b for b in dc['breakdown']
                if b.get('term') == 'minimum-wage')
    check("dan's inverted minimum-wage: DC ($17.50, best) "
          'normalizes to 0',
          wage['isPositive'] is False and wage['normalized'] == 0.0)

    print('\ntime-specific scoring (scr-4)')
    from scoring.custom.timeframes import parse_frame, timeframe_specificity

    def _concept(mgr, name, term, required, time_policy=''):
        mgr.objectTables['ScoreConcept'][f'fix-{name}'] = \
            SimpleNamespace(
                name=name, display_name=name, subject_kind='state',
                subject_names_json='["texas"]',
                term_weights_json=_json.dumps(
                    [{'term': term, 'weight': 1}]),
                required_context_names_json=_json.dumps(required),
                aggregation='weighted-mean', levelize=False,
                time_policy_json=time_policy)

    def _ctx(mgr, name, start, end):
        mgr.objectTables['ScoreContext'][f'fix-{name}'] = \
            SimpleNamespace(name=name, display_name=name,
                            context_type='timeframe', parent_name='',
                            value_json=_json.dumps(
                                {'start': start, 'end': end}))

    def _lfpr(subjects):
        return next(b for b in subjects[0]['breakdown'])

    check('quarter frames grade more specific than the year',
          timeframe_specificity(parse_frame(
              '{"start": "2022-04-01", "end": "2022-06-30"}')) == 7
          and timeframe_specificity(parse_frame(
              '{"start": "2022-01-01", "end": "2022-12-31"}')) == 6)

    mgr = _mgr()
    check('parity guard: yearly full-cover still wins for texas '
          '(quarterly rows present)',
          abs({s['subject']: s for s in score_concept(
              mgr, 'labor-quality')['subjects']}['texas'][
                  'initialScore'] - EXPECTED['texas']) < 1e-4)

    _concept(mgr, 'fix-q2', 'labor-force-participation-rate',
             ['q2-2022'])
    entry = _lfpr(score_concept(mgr, 'fix-q2')['subjects'])
    check('quarter-specific request serves the quarter directly '
          '(63.0)', entry['found'] and entry['raw'] == 63.0)

    # Remove the yearly texas LFPR row: the year must now be SERVED
    # by combining the quarters (day-weighted mean).
    mgr2 = _mgr()
    mgr2.objectTables['ContextualizedValue'] = {
        k: v for k, v in
        mgr2.objectTables['ContextualizedValue'].items()
        if getattr(v, 'name', '')
        != 'labor-force-participation-rate@texas-2022'}
    _concept(mgr2, 'fix-year', 'labor-force-participation-rate',
             ['year-2022'])
    entry = _lfpr(score_concept(mgr2, 'fix-year')['subjects'])
    expected_mean = (62.8 * 90 + 63.0 * 91 + 63.4 * 92
                     + 63.6 * 92) / 365
    check('coexisting scales: quarters combine day-weighted to serve '
          'the year',
          entry['found'] and abs(entry['raw'] - expected_mean) < 1e-3
          and entry['derived'] == 'time-weighted-mean'
          and len(entry['fromRows']) == 4,
          f"raw {entry.get('raw')}")

    # Undeclared temporal nature -> refusal naming the knob.
    mgr3 = _mgr()
    mgr3.objectTables['ContextualizedValue'] = \
        mgr2.objectTables['ContextualizedValue']
    for row in mgr3.objectTables['ScoreTerm'].values():
        if getattr(row, 'name', '') \
                == 'labor-force-participation-rate':
            row.temporal_json = '{}'
    _concept(mgr3, 'fix-undeclared',
             'labor-force-participation-rate', ['year-2022'])
    entry = _lfpr(score_concept(mgr3, 'fix-undeclared')['subjects'])
    check('combining without declared temporal nature refused w/ '
          'the knob',
          not entry['found'] and 'temporal' in entry['error']
          and entry['suggestion']['knob'] == 'ScoreTerm.temporal_json')

    # Gap interpolation between measured frames, labeled.
    mgr4 = _mgr()
    _ctx(mgr4, 'q2-2023', '2023-04-01', '2023-06-30')
    mgr4.objectTables['ContextualizedValue']['fix-q4-2023'] = \
        SimpleNamespace(
            name='lfpr@texas-q4-2023',
            term_name='labor-force-participation-rate',
            subject_name='texas',
            context_names_json='["state-texas", "q4-2023"]',
            pre_normalized_value=64.4, data_ref_json='',
            provenance_id='fixture')
    _ctx(mgr4, 'q4-2023', '2023-10-01', '2023-12-31')
    _concept(mgr4, 'fix-interp', 'labor-force-participation-rate',
             ['q2-2023'])
    entry = _lfpr(score_concept(mgr4, 'fix-interp')['subjects'])
    check('gap interpolates between neighboring frames, LABELED',
          entry['found'] and abs(entry['raw'] - 64.0) < 0.05
          and entry['derived'] == 'interpolated'
          and len(entry['fromRows']) == 2,
          f"raw {entry.get('raw')}")

    # Beyond the measured range: refusal, then the explicit knob.
    mgr5 = _mgr()
    _ctx(mgr5, 'year-2025', '2025-01-01', '2025-12-31')
    _concept(mgr5, 'fix-extrap', 'labor-force-participation-rate',
             ['year-2025'])
    entry = _lfpr(score_concept(mgr5, 'fix-extrap')['subjects'])
    check('extrapolation refused by default, frontier named',
          not entry['found'] and 'extrapolation'
          in entry['error'] and entry.get('frontierRow'))
    _concept(mgr5, 'fix-extrap-on',
             'labor-force-participation-rate', ['year-2025'],
             time_policy='{"allowExtrapolation": true}')
    entry = _lfpr(score_concept(mgr5, 'fix-extrap-on')['subjects'])
    check('explicit allowExtrapolation serves nearest, LABELED',
          entry['found'] and entry['derived'] == 'extrapolated-nearest')

    print('\nhonest errors')
    bad = score_concept(_mgr(), 'no-such-concept')
    check('unknown concept named + known list',
          not bad['ok'] and 'labor-quality' in bad['knownConcepts'])
    bad = aggregate_group(_mgr(), 'no-such-group')
    check('unknown group named + known groups',
          not bad['ok'] and 'demo-political-group'
          in bad['knownGroups'])
    bad = aggregate_group(_mgr(), 'demo-political-group',
                          'no-such-policy')
    check('unknown policy refused w/ the AgreementPolicy knob',
          not bad['ok']
          and bad['suggestion']['knob'] == 'AgreementPolicy')
    bad = compare_groups(_mgr(), ['demo-political-group'])
    check('compare needs two groups',
          not bad['ok'] and 'two group names' in bad['error'])

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed\n')
    raise SystemExit(1 if failed else 0)
