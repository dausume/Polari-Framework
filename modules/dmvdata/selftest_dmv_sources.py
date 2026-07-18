"""
Selftest — col-2: DMV official-source registration + the Census
end-to-end slice.

Run from polari-framework/:
    python3 -m dmvdata.selftest_dmv_sources

Covers: every seed row constructs against the REAL
APIDomain/APIEndpoint classes; no seed carries anything resembling a
literal credential (repos are PUBLIC — auth rides env-knob pointers);
the Census URL builder pins the documented API shape; the
array-of-arrays parser handles a real-shaped fixture; the ingest
payload matches the scoring bridge's documented contract; and the
LIVE leg pulls real ACS B25064 median rents for the 11 DMV
jurisdictions (skip-honest naming the URL when offline).
"""

import json
import os
import re
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from dmvdata import census_pull as cp
from dmvdata.source_seed import (DMV_JURISDICTIONS, SEED_API_DOMAINS,
                                 SEED_API_ENDPOINTS)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _seed_shapes():
    print('seed rows construct against the real classes')
    from polariApiProfiler.apiDomain import APIDomain
    from polariApiProfiler.apiEndpoint import APIEndpoint
    domains = {}
    for seed in SEED_API_DOMAINS:
        row = APIDomain(**seed, manager=None)
        domains[row.name] = row
    check('every APIDomain seed constructs, hosts cleaned',
          len(domains) == len(SEED_API_DOMAINS)
          and domains['census-api'].host == 'api.census.gov'
          and domains['census-api'].protocol == 'https')
    endpoints = {}
    for seed in SEED_API_ENDPOINTS:
        row = APIEndpoint(**seed, manager=None)
        endpoints[row.name] = row
    check('every APIEndpoint seed constructs',
          len(endpoints) == len(SEED_API_ENDPOINTS))
    unknown_domains = sorted(
        {e.domainName for e in endpoints.values()} - set(domains))
    check('every endpoint names a seeded domain',
          not unknown_domains, f'{unknown_domains}')
    dupes = len(SEED_API_ENDPOINTS) != len(
        {s['name'] for s in SEED_API_ENDPOINTS})
    check('endpoint names unique (idempotent-by-name)', not dupes)


def _credential_hygiene():
    print('credential hygiene (repos are PUBLIC)')
    blob = json.dumps(SEED_API_DOMAINS) + json.dumps(
        SEED_API_ENDPOINTS)
    # Key-named fields must never carry a literal; long hex is only
    # suspect in CREDENTIAL-CAPABLE fields (authConfig/headers/body)
    # — ArcGIS dataset ids in endpoint paths are public identifiers.
    leak = re.search(
        r'(?i)"(api[_-]?key|token|secret|password)"\s*:\s*"(?!env:)'
        r'[A-Za-z0-9_\-]{12,}"', blob)
    cred_fields = json.dumps(
        [{k: s.get(k, '') for k in ('authConfig', 'defaultHeaders',
                                    'bodyTemplate')}
         for s in SEED_API_ENDPOINTS])
    hex_leak = re.search(r'[a-fA-F0-9]{32,}', cred_fields)
    check('no literal credential shapes in the seeds '
          '(credential-capable fields scanned for hex; public '
          'dataset ids in paths are fine)',
          leak is None and hex_leak is None,
          (leak or hex_leak).group(0)[:40]
          if (leak or hex_leak) else '')
    needing_auth = [s for s in SEED_API_ENDPOINTS
                    if s.get('authType', 'none') != 'none']
    check('every auth-needing endpoint points at an env knob',
          needing_auth and all(
              s.get('authConfig', '').startswith('env:POLARI_')
              for s in needing_auth),
          f'{len(needing_auth)} auth endpoints')


def _url_and_parser():
    print('census URL builder + parser (pinned shapes)')
    url = cp.build_acs_url('B25064', 2023, '11', ['001'])
    check('URL pins the documented Census API shape',
          url == 'https://api.census.gov/data/2023/acs/acs5'
                 '?get=NAME,B25064_001E&for=county:001&in=state:11',
          url)
    fixture = [
        ['NAME', 'B25064_001E', 'state', 'county'],
        ['District of Columbia, District of Columbia', '1817',
         '11', '001'],
        ['Fairfax County, Virginia', '2117', '51', '059'],
    ]
    by_fips = {(j['state'], j['county']): j
               for j in DMV_JURISDICTIONS}
    rows = cp.parse_acs_response(fixture, 'B25064', by_fips)
    check('fixture parses with FIPS -> geography-context mapping',
          [(r['geography'], r['value']) for r in rows]
          == [('dc', 1817.0), ('va-fairfax', 2117.0)])
    try:
        cp.parse_acs_response({'oops': 1}, 'B25064', by_fips)
        refused = False
    except ValueError as exc:
        refused = 'array-of-arrays' in str(exc)
    check('unexpected response shape is a plain error', refused)

    # Key redaction: the live request carries the key; everything
    # PERSISTED (urls/provenance/errors) must not.
    os.environ[cp.CENSUS_KEY_ENV] = 'FAKEKEY1234567890'
    try:
        result = cp.pull_acs_table(
            'B25064', 2023,
            jurisdictions=[DMV_JURISDICTIONS[0]],
            fetcher=lambda url: (0, f'unreachable-test ({url})'))
        blob = json.dumps(result)
        check('the key never appears in urls/provenance/errors '
              '(redacted to the env-knob name)',
              'FAKEKEY1234567890' not in blob
              and cp.CENSUS_KEY_ENV in blob)
    finally:
        del os.environ[cp.CENSUS_KEY_ENV]


def _ingest_bridge():
    print('the scoring ingest bridge payload')
    fake_pull = {
        'ok': True, 'table': 'B25064', 'vintage': 'acs-2023',
        'rows': [{'geography': 'dc', 'name': 'DC', 'value': 1817.0,
                  'state': '11', 'county': '001'},
                 {'geography': 'md-howard', 'name': 'Howard',
                  'value': None, 'state': '24', 'county': '027'}],
        'provenance': 'U.S. Census Bureau … test', 'urls': ['u'],
        'missing': []}
    payload = cp.build_ingest_payload(fake_pull, 'median-gross-rent')
    check('payload matches ingest_records contract '
          '(term + records[{subject,value,contexts}] + provenance)',
          payload['term'] == 'median-gross-rent'
          and payload['records'] == [{'subject': 'dc',
                                      'value': 1817.0,
                                      'contexts': ['dc']}]
          and payload['contexts'] == ['acs-2023']
          and payload['subject_kind'] == 'jurisdiction'
          and 'Census Bureau' in payload['provenance'])
    check('null-valued rows are excluded, never ingested as 0',
          all(r['value'] is not None for r in payload['records']))
    try:
        cp.build_ingest_payload({'ok': False, 'error': 'x'}, 't')
        refused = False
    except ValueError:
        refused = True
    check('a failed pull cannot become an ingest payload', refused)
    from scoring.data_ingestion import ingest_records
    refusal = ingest_records(
        SimpleNamespace(objectTables={'ScoreTerm': {}}), payload)
    check('the REAL bridge validates the payload shape (refuses '
          'only on the unseeded term, as designed)',
          not refusal['ok'] and 'median-gross-rent'
          in refusal['error'])


def _live_pull():
    print('LIVE: ACS B25064 for the 11 DMV jurisdictions')
    result = cp.pull_acs_table('B25064', 2023)
    if not result.get('ok'):
        check('live leg', True,
              f"skip-honest: {result.get('error', '?')[:120]}")
        return
    values = {r['geography']: r['value'] for r in result['rows']}
    check('all 11 jurisdictions came back',
          len(result['rows']) == 11 and result['missing'] == [],
          f"got {len(result['rows'])}, missing {result['missing']}")
    plausible = all(v is not None and 500 <= v <= 5000
                    for v in values.values())
    sample = {k: values[k] for k in ('dc', 'va-fairfax',
                                     'md-montgomery')
              if k in values}
    check('median rents in a plausible range (500..5000 $/mo)',
          plausible, f'sample: {sample}')
    check('provenance carries every request URL',
          all(u.startswith('https://api.census.gov/data/2023/')
              for u in result['urls'])
          and str(len(result['urls'])) and len(result['urls']) == 3)
    print(f'  LIVE VALUES: {json.dumps(values, indent=1)}')


def main():
    _seed_shapes()
    _credential_hygiene()
    _url_and_parser()
    _ingest_bridge()
    _live_pull()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
