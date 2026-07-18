"""
Selftest — the legal source types (Dustin 2026-07-16: NonProfit /
Company / PoliticalGroup / Individual siblings of GovSource).

Run from polari-framework/:
    python3 -m dmvdata.selftest_legal_sources

Covers: the four classes construct standalone; ONE machinery spans
all five source tables (glossary labeled by kind, find_source,
source_report with per-type legal identity + the non-government
framing note); cross-type name uniqueness across every seed; the
retrieval/cross-validation machinery is type-agnostic (a nonprofit
retrieval records, reports, and survives a confirm_retrieval
round-trip); GovSource reports are byte-for-byte unchanged in their
existing fields (regression); and no seed carries anything
key-looking (repos are public).
"""

import json
import os
import re
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from dmvdata import cross_validation as cv
from dmvdata import gov_sources as gs
from dmvdata import legal_sources as ls
from dmvdata.source_seed import SEED_API_ENDPOINTS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


_ALL_SEEDS = {
    'GovSource': gs.SEED_GOV_SOURCES,
    'NonProfitSource': ls.SEED_NONPROFIT_SOURCES,
    'CompanySource': ls.SEED_COMPANY_SOURCES,
    'PoliticalGroupSource': ls.SEED_POLITICAL_SOURCES,
    'IndividualSource': ls.SEED_INDIVIDUAL_SOURCES,
}


def _mgr():
    tables = {name: {} for name in (
        list(gs.SOURCE_TABLES) + ['SourceRetrieval',
                                  'RetrievalConfirmation',
                                  'APIEndpoint', 'ScoreTerm',
                                  'ContextualizedValue'])}
    m = SimpleNamespace(objectTables=tables, idList=[], db=None)
    for class_name, seeds in _ALL_SEEDS.items():
        for seed in seeds:
            tables[class_name][seed['name']] = SimpleNamespace(**seed)
    for seed in SEED_API_ENDPOINTS:
        tables['APIEndpoint'][seed['name']] = SimpleNamespace(**seed)
    # A term whose provenance cites LSC's data portal — the
    # cross-type term-origin case.
    tables['ScoreTerm']['eviction-filings-proxy'] = SimpleNamespace(
        name='eviction-filings-proxy',
        provenance_id='PROXY series from civilcourtdata.lsc.gov '
                      '(Legal Services Corporation) — not official',
        source='nonprofit proxy')
    return m


def _classes():
    print('the four legal source classes')
    rows = {
        'nonprofit': ls.NonProfitSource(
            name='t-np', short_name='TNP', full_name='Test NP',
            ein='', manager=None),
        'company': ls.CompanySource(
            name='t-co', legal_name='Test Co LLC', manager=None),
        'political-group': ls.PoliticalGroupSource(
            name='t-pg', group_kind='pac', manager=None),
        'individual': ls.IndividualSource(
            name='t-in', person_name='Test Person',
            contributor_name='contrib-1', manager=None),
    }
    check('all four construct standalone with their SOURCE_KIND',
          all(type(row).SOURCE_KIND == kind
              for kind, row in rows.items()))
    check('per-type verification registries point at official '
          'lookup tools',
          'irs.gov' in rows['nonprofit'].irs_lookup_url
          and 'sec.gov' in rows['company'].registry_url
          and 'fec.gov' in rows['political-group'].fec_lookup_url)
    check('individual sources bridge to Contributor rows',
          rows['individual'].contributor_name == 'contrib-1')


def _seeds_hygiene():
    print('seed hygiene (one namespace, no invented identifiers, '
          'no keys)')
    m = _mgr()
    check('cross-type name uniqueness across ALL seeds',
          gs.validate_source_names(m) == {},
          str(gs.validate_source_names(m)))
    non_gov = (ls.SEED_NONPROFIT_SOURCES + ls.SEED_POLITICAL_SOURCES
               + ls.SEED_COMPANY_SOURCES
               + ls.SEED_INDIVIDUAL_SOURCES)
    check('every non-government seed carries the NOT-official '
          'framing in its description',
          all('NOT an official government source'
              in seed['description'] for seed in non_gov))
    check('no invented registry identifiers (unknown EIN/FEC ids '
          'stay empty, lookup URL supplied)',
          all(seed.get('ein', '') == ''
              and 'irs.gov' in seed.get('irs_lookup_url', '')
              for seed in ls.SEED_NONPROFIT_SOURCES)
          and all(seed.get('fec_committee_id', '') == ''
                  and 'fec.gov' in seed.get('fec_lookup_url', '')
                  for seed in ls.SEED_POLITICAL_SOURCES))
    key_pattern = re.compile(r'[A-Za-z0-9]{24,}')
    suspicious = [seed['name'] for seeds in _ALL_SEEDS.values()
                  for seed in seeds
                  for v in seed.values()
                  if isinstance(v, str) and '://' not in v
                  and key_pattern.search(v)]
    check('nothing key-looking in any seed (repos are public)',
          suspicious == [], str(suspicious[:3]))
    check('company + individual seeds are honestly EMPTY (nothing '
          'referenced by the plan yet; runtime data)',
          ls.SEED_COMPANY_SOURCES == []
          and ls.SEED_INDIVIDUAL_SOURCES == [])


def _spanning_machinery():
    print('one machinery, five tables')
    m = _mgr()
    glossary = gs.source_glossary(m)
    total = sum(len(seeds) for seeds in _ALL_SEEDS.values())
    check('glossary spans every kind and labels it',
          len(glossary) == total
          and {e['kind'] for e in glossary}
          == {'government', 'nonprofit', 'political-group'},
          f'{len(glossary)} entries')
    keys = [(e['acronym'] or e['fullName'], e['jurisdiction'])
            for e in glossary]
    check('glossary stays sorted with the mixed kinds',
          keys == sorted(keys))
    row, kind = gs.find_source(m, 'legal-services-corp')
    check('find_source resolves a nonprofit',
          row is not None and kind == 'nonprofit')
    row, kind = gs.find_source(m, 'census-acs')
    check('find_source resolves a government source',
          row is not None and kind == 'government')
    check('find_source is honest about unknowns',
          gs.find_source(m, 'nope') == (None, None))


def _reports():
    print('source cards across kinds')
    m = _mgr()
    lsc = gs.source_report(m, 'legal-services-corp')
    check("nonprofit card: kind + EIN field + IRS lookup + the "
          'non-government framing note',
          lsc['ok'] and lsc['kind'] == 'nonprofit'
          and 'ein' in lsc['legalIdentity']
          and 'irs.gov' in lsc['legalIdentity']['irs_lookup_url']
          and lsc['framing']
          == 'non-government source — not an official statistic '
             'origin')
    check('nonprofit term-origin: the LSC-proxy term traces to it',
          any(t['term'] == 'eviction-filings-proxy'
              for t in lsc['originatingTerms']))
    acs = gs.source_report(m, 'census-acs')
    check('government card regression: existing fields unchanged, '
          'no framing note, kind labeled',
          acs['ok'] and acs['kind'] == 'government'
          and acs['acronym'] == 'ACS'
          and acs['apiKeyEnv'] == 'POLARI_CENSUS_API_KEY'
          and 'framing' not in acs
          and 'legalIdentity' not in acs)
    pg = gs.source_report(m, 'democratic-party-platform')
    check('political-group card carries group_kind + FEC lookup',
          pg['ok']
          and pg['legalIdentity']['group_kind'] == 'party'
          and 'fec.gov' in pg['legalIdentity']['fec_lookup_url'])


def _retrievals_cross_type():
    print('retrieval + cross-validation machinery is type-agnostic')
    m = _mgr()
    first = gs.record_retrieval(
        m, 'legal-services-corp', what='eviction-proxy va 2025',
        retrieved_by='analyst-a', retrieved_by_group='group-alpha',
        row_count=3, retrieved_at='2026-07-16T22:00:00+00:00')
    check('a retrieval records against a nonprofit source',
          first['ok']
          and first['retrieval']['origin'] == 'group:group-alpha')
    report = gs.source_report(m, 'legal-services-corp')
    check("the retrieval appears on the nonprofit's card",
          len(report['retrievals']) == 1)
    second = gs.record_retrieval(
        m, 'legal-services-corp', what='eviction-proxy va 2025',
        retrieved_by='analyst-b', retrieved_by_group='group-beta',
        row_count=3, retrieved_at='2026-07-16T23:00:00+00:00')
    rows = [{'id': 'r1', 'filings': 10}, {'id': 'r2', 'filings': 20},
            {'id': 'r3', 'filings': 30}]
    confirmation = cv.confirm_retrieval(
        m, first['retrieval']['name'], second['retrieval']['name'],
        original_rows=rows, independent_rows=[dict(r) for r in rows],
        key_field='id', confirmed_by='analyst-b',
        confirmed_by_group='group-beta',
        compared_at='2026-07-16T23:30:00+00:00')
    check('confirm_retrieval round-trips against nonprofit-source '
          'retrievals (verdict confirmed)',
          confirmation.get('ok', False)
          and confirmation.get('comparison', {}).get('verdict')
          == 'confirmed',
          str(confirmation)[:120])
    missing = gs.record_retrieval(m, 'no-such-source',
                                  retrieved_by='x')
    check('an unknown source refusal names the five legal kinds',
          not missing['ok']
          and all(kind in missing['error'] for kind in
                  ('government', 'nonprofit', 'company',
                   'political-group', 'individual')))


def main():
    _classes()
    _seeds_hygiene()
    _spanning_machinery()
    _reports()
    _retrievals_cross_type()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
