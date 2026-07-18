"""
Selftest — the GovSource registry (Dustin 2026-07-16).

Run from polari-framework/:
    python3 -m dmvdata.selftest_gov_sources

Covers: the acronym glossary (unique, expanded, official websites);
per-source API-key requirements naming ONLY env knobs (never literal
keys — repos are public); duplication attribution (SourceRetrieval:
date-time + group/individual origin, threaded through the census
ingest path with redacted provenance); and term-origin tracking
(terms_from_source matches acronym/full-name/official-domain against
REAL col-1 provenance strings, word-boundary pinned so 'MACROS'
never matches 'ACS').
"""

import json
import os
import re
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from dmvdata import census_pull as cp
from dmvdata import gov_sources as gs
from dmvdata.source_seed import DMV_JURISDICTIONS, SEED_API_ENDPOINTS
from scoring.dmv_col_seed import (SEED_DMV_GEO_CONTEXTS,
                                  SEED_DMV_TERMS,
                                  SEED_STATUTE_VALUES)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _mgr():
    tables = {name: {} for name in (
        'GovSource', 'SourceRetrieval', 'APIEndpoint', 'ScoreTerm',
        'ScoreContext', 'ScoreSubject', 'ContextualizedValue')}
    m = SimpleNamespace(objectTables=tables, idList=[], db=None)
    for seed in gs.SEED_GOV_SOURCES:
        tables['GovSource'][seed['name']] = SimpleNamespace(**seed)
    for seed in SEED_API_ENDPOINTS:
        tables['APIEndpoint'][seed['name']] = SimpleNamespace(**seed)
    for seed in SEED_DMV_TERMS:
        tables['ScoreTerm'][seed['name']] = SimpleNamespace(**seed)
    # The word-boundary poison: 'MACROS' must never match 'ACS'.
    tables['ScoreTerm']['macro-idx'] = SimpleNamespace(
        name='macro-idx', provenance_id='derived via the MACROS '
        'pipeline, no external source', source='internal')
    for seed in SEED_STATUTE_VALUES:
        tables['ContextualizedValue'][seed['name']] = (
            SimpleNamespace(**seed))
    for seed in SEED_DMV_GEO_CONTEXTS:
        tables['ScoreContext'][seed['name']] = SimpleNamespace(**seed)
    tables['ScoreContext']['acs-2023'] = SimpleNamespace(
        name='acs-2023')
    return m


def _glossary():
    print('the acronym glossary')
    m = _mgr()
    glossary = gs.source_glossary(m)
    check('every seeded source appears',
          len(glossary) == len(gs.SEED_GOV_SOURCES),
          f'{len(glossary)} entries')
    keys = [(e['acronym'] or e['fullName'], e['jurisdiction'])
            for e in glossary]
    check('(acronym, jurisdiction) pairs unique (DHCD exists in '
          'VA + MD + DC-adjacent forms legitimately)',
          len(keys) == len(set(keys)))
    check('sorted for lookup', keys == sorted(keys))
    check('every entry expands to a full name + agency + website',
          all(e['fullName'] and e['agency'] and e['website']
              for e in glossary))
    md_j = next(e for e in glossary
                if e['name'] == 'md-judiciary')
    check('a source with no real acronym carries none (never '
          'invented)', md_j['acronym'] == '')


def _key_hygiene():
    print('API-key requirements (env knobs only — repos public)')
    keyed = [s for s in gs.SEED_GOV_SOURCES if s['requires_api_key']]
    check('keyed sources exist (census/hud/eia family)',
          {'census-acs', 'hud-fmr', 'eia'}
          <= {s['name'] for s in keyed})
    check('every keyed source names a POLARI_* env knob',
          all(re.fullmatch(r'POLARI_[A-Z_]+', s['api_key_env'])
              for s in keyed))
    check('no source row carries anything but an env-knob pointer '
          'in its key field',
          all(re.fullmatch(r'|POLARI_[A-Z_]+', s['api_key_env'])
              for s in gs.SEED_GOV_SOURCES))
    check('BLS is honestly optional-key (works keyless, knob '
          'raises limits)',
          next(s for s in gs.SEED_GOV_SOURCES
               if s['name'] == 'bls')['requires_api_key'] is False)


def _referential_integrity():
    print('referential integrity')
    endpoint_names = {e['name'] for e in SEED_API_ENDPOINTS}
    bad = [(s['name'], n) for s in gs.SEED_GOV_SOURCES
           for n in json.loads(s['api_endpoint_names_json'])
           if n not in endpoint_names]
    check('every api_endpoint_names_json entry resolves to a real '
          'APIEndpoint seed', bad == [], str(bad[:3]))
    source_names = {s['name'] for s in gs.SEED_GOV_SOURCES}
    orphans = [s['name'] for s in gs.SEED_GOV_SOURCES
               if s['parent_source']
               and s['parent_source'] not in source_names]
    check('every parent_source resolves', orphans == [],
          str(orphans))


def _term_origins():
    print('term-origin tracking')
    m = _mgr()
    acs = gs.terms_from_source(m, 'census-acs')
    matched = {t['term']: t for t in acs['terms']}
    check('ACS terms found via acronym + census.gov domain',
          acs['ok'] and 'housing-stock-median-age' in matched
          and any('ACS' in e or 'census.gov' in e
                  for e in matched['housing-stock-median-age']
                  ['matchedBy']))
    check("word-boundary pin: 'MACROS' provenance never matches "
          "'ACS'", 'macro-idx' not in matched)
    cinch = gs.terms_from_source(m, 'hud-cinch')
    cinch_terms = {t['term'] for t in cinch['terms']}
    check('CINCH finds the demolition-turnover term',
          'demolition-turnover' in cinch_terms)
    statutes = gs.terms_from_source(m, 'md-dhcd')
    check('statute VALUES count toward a source when their '
          'provenance matches (values scanned, not just terms)',
          isinstance(statutes['valueCount'], int))
    unknown = gs.terms_from_source(m, 'nope')
    check('unknown source lists the known ones',
          not unknown['ok'] and 'census-acs'
          in unknown['knownSources'])


def _retrievals():
    print('duplication attribution (group/individual origin)')
    m = _mgr()
    result = gs.record_retrieval(
        m, 'census-acs', endpoint_name='census-acs5-b25064',
        what='B25064 acs-2023', retrieved_by='analyst-a',
        retrieved_by_group='housing-data-collective', row_count=11,
        retrieved_at='2026-07-16T20:00:00+00:00')
    check('a group retrieval records date-time + group origin',
          result['ok']
          and result['retrieval']['retrievedAt']
          == '2026-07-16T20:00:00+00:00'
          and result['retrieval']['origin']
          == 'group:housing-data-collective')
    solo = gs.record_retrieval(
        m, 'census-acs', what='B25031 acs-2023',
        retrieved_by='analyst-b',
        retrieved_at='2026-07-16T21:00:00+00:00')
    check('an individual retrieval reads back as individual origin',
          solo['retrieval']['origin'] == 'individual:analyst-b')
    listed = gs.retrievals_for(m, 'census-acs')
    check('retrievals_for returns both, time-ordered',
          [r['origin'] for r in listed]
          == ['group:housing-data-collective',
              'individual:analyst-b'])
    dup = gs.record_retrieval(
        m, 'census-acs', what='B25064 acs-2023',
        retrieved_by='analyst-a',
        retrieved_at='2026-07-16T20:00:00+00:00')
    check('same-stamp re-record stays unique (suffixed, never '
          'overwritten)', dup['ok']
          and dup['retrieval']['name']
          != result['retrieval']['name'])
    check('unattributed retrieval refused (the origin IS the '
          'point)',
          not gs.record_retrieval(m, 'census-acs',
                                  what='x')['ok'])
    check('unknown source refused with the known list',
          not gs.record_retrieval(m, 'nope', retrieved_by='a')['ok'])


def _report():
    print('the source card')
    m = _mgr()
    gs.record_retrieval(m, 'census-acs', what='B25064 acs-2023',
                        retrieved_by='analyst-a',
                        retrieved_by_group='housing-data-collective',
                        retrieved_at='2026-07-16T20:00:00+00:00')
    report = gs.source_report(m, 'census-acs')
    check('composes expansion + website + key knob + endpoints + '
          'retrievals + originating terms',
          report['ok'] and report['acronym'] == 'ACS'
          and report['requiresApiKey']
          and report['apiKeyEnv'] == 'POLARI_CENSUS_API_KEY'
          and all(e['registered'] for e in report['endpoints'])
          and len(report['retrievals']) == 1
          and any(t['term'] == 'housing-stock-median-age'
                  for t in report['originatingTerms']))


def _census_threading():
    print('census ingest threads the attribution (redacted URL)')
    m = _mgr()
    fixture = [
        ['NAME', 'B25064_001E', 'state', 'county'],
        ['District of Columbia, District of Columbia', '1817',
         '11', '001'],
        ['Fairfax County, Virginia', '2117', '51', '059'],
    ]
    juris = [j for j in DMV_JURISDICTIONS
             if j['context'] in ('dc', 'va-fairfax')]
    def state_aware(url):
        # One request per state (the real API's shape) — return
        # only that state's rows, like Census does.
        state = url.split('in=state:')[1].split('&')[0]
        return 200, [fixture[0]] + [r for r in fixture[1:]
                                    if r[2] == state]

    os.environ[cp.CENSUS_KEY_ENV] = 'FAKEKEY1234567890'
    try:
        pull = cp.pull_acs_table('B25064', 2023,
                                 jurisdictions=juris,
                                 fetcher=state_aware)
        ingest = cp.ingest_acs_to_scoring(
            m, pull, 'median-gross-rent',
            retrieved_by='analyst-a',
            retrieved_by_group='housing-data-collective')
        rows = list(m.objectTables['SourceRetrieval'].values())
        check('a successful attributed ingest records EXACTLY one '
              'retrieval', ingest.get('ok') and len(rows) == 1,
              str(ingest.get('error', ''))[:120])
        row = rows[0] if rows else SimpleNamespace()
        check('the retrieval carries group origin + row count',
              getattr(row, 'retrieved_by_group', '')
              == 'housing-data-collective'
              and getattr(row, 'row_count', 0) == 2)
        check('the recorded provenance URL is the REDACTED form',
              'FAKEKEY1234567890'
              not in getattr(row, 'provenance_url', 'x')
              and f'<env:{cp.CENSUS_KEY_ENV}>'
              in getattr(row, 'provenance_url', ''))
        m2 = _mgr()
        ingest2 = cp.ingest_acs_to_scoring(m2, pull,
                                           'median-gross-rent')
        check('no retrieved_by -> ingest succeeds with NO '
              'attribution row (attribution is opt-in per call)',
              ingest2.get('ok')
              and not m2.objectTables['SourceRetrieval'])
    finally:
        del os.environ[cp.CENSUS_KEY_ENV]


def main():
    _glossary()
    _key_hygiene()
    _referential_integrity()
    _term_origins()
    _retrievals()
    _report()
    _census_threading()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
