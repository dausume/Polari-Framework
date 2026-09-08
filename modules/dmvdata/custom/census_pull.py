"""
@module dmvdata.custom.census_pull

col-2's end-to-end slice: pull one ACS table for the 11 DMV
jurisdictions from the official Census API and hand it to the
scoring engine through the EXISTING ingest bridge
(scoring.custom.data_ingestion.ingest_records) — geography as subject,
[geography-context, acs-vintage] as contexts, the full API URL as
provenance. No key needed at this volume (plan Appendix B1).

Honesty: network unreachable -> ok:False naming the URL (callers
treat as skip-honest); unexpected response shape -> ok:False with
the leading bytes; a jurisdiction missing from the response is a
NAMED gap, never silently dropped.
"""

import json
import os
import urllib.error
import urllib.request

from dmvdata.source_seed import DMV_JURISDICTIONS

ACS_BASE = 'https://api.census.gov/data/{year}/acs/acs5'
#: The Census API refuses keyless requests (observed live
#: 2026-07-16: HTTP 200 'Missing Key' HTML). Keys are FREE:
#: https://api.census.gov/data/key_signup.html
CENSUS_KEY_ENV = 'POLARI_CENSUS_API_KEY'
_KEY_REDACTED = f'&key=<env:{CENSUS_KEY_ENV}>'


def build_acs_url(table, year, state, counties, key=None):
    """The exact documented Census API URL (pinned by selftest).
    The key is appended only for the live request — provenance and
    logs always carry the REDACTED form (repos are public)."""
    url = (f'{ACS_BASE.format(year=year)}'
           f'?get=NAME,{table}_001E'
           f'&for=county:{",".join(counties)}'
           f'&in=state:{state}')
    return url + (f'&key={key}' if key else '')


def _redact(url):
    key = (os.environ.get(CENSUS_KEY_ENV) or '').strip()
    return url.replace(f'&key={key}', _KEY_REDACTED) if key else url


def _default_fetcher(url, timeout=20):
    """(status, parsed_json_or_none). Never raises."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            try:
                return resp.status, json.loads(body)
            except ValueError:
                return resp.status, body
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except Exception as exc:  # URLError, timeout, DNS…
        return 0, f'unreachable: {exc}'


def parse_acs_response(payload, table, jurisdictions_by_fips):
    """Census array-of-arrays -> [{geography, name, value, state,
    county}]. Header row names the columns; rows follow."""
    if not (isinstance(payload, list) and payload
            and isinstance(payload[0], list)):
        head = json.dumps(payload)[:200] if payload is not None \
            else 'None'
        raise ValueError(f'unexpected Census response shape '
                         f'(want array-of-arrays): {head}')
    header = payload[0]
    try:
        name_i = header.index('NAME')
        value_i = header.index(f'{table}_001E')
        state_i = header.index('state')
        county_i = header.index('county')
    except ValueError as exc:
        raise ValueError(f'Census header missing a column: {header} '
                         f'({exc})')
    rows = []
    for raw in payload[1:]:
        fips = (raw[state_i], raw[county_i])
        meta = jurisdictions_by_fips.get(fips)
        if meta is None:
            continue  # a county we did not ask about
        value_raw = raw[value_i]
        rows.append({
            'geography': meta['context'],
            'name': raw[name_i],
            'value': (float(value_raw)
                      if value_raw not in (None, '', 'null')
                      else None),
            'state': fips[0], 'county': fips[1],
        })
    return rows


def pull_acs_table(table='B25064', year=2023, jurisdictions=None,
                   fetcher=None):
    """One ACS table across the DMV -> {'ok', 'rows', 'provenance',
    'missing'}. One request per state (the `in=state:` clause is
    single-state)."""
    fetcher = fetcher or _default_fetcher
    jurisdictions = jurisdictions or DMV_JURISDICTIONS
    key = (os.environ.get(CENSUS_KEY_ENV) or '').strip() or None
    by_state = {}
    for j in jurisdictions:
        by_state.setdefault(j['state'], []).append(j)
    by_fips = {(j['state'], j['county']): j for j in jurisdictions}
    rows, urls, errors = [], [], []
    for state, members in sorted(by_state.items()):
        url = build_acs_url(table, year, state,
                            [m['county'] for m in members], key=key)
        urls.append(_redact(url))
        status, payload = fetcher(url)
        if status != 200 or payload is None \
                or isinstance(payload, str):
            # Redact the body as well — error pages can echo the
            # request URL (key included) back at us.
            body = _redact(str(payload)) \
                if isinstance(payload, str) else 'no body'
            if 'Missing Key' in str(body):
                body = (f'the Census API requires a key — set env '
                        f'{CENSUS_KEY_ENV} (free signup: '
                        f'https://api.census.gov/data/'
                        f'key_signup.html)')
            errors.append(f'{_redact(url)} -> HTTP {status} '
                          f'({str(body)[:160]})')
            continue
        try:
            rows.extend(parse_acs_response(payload, table, by_fips))
        except ValueError as exc:
            errors.append(f'{url} -> {exc}')
    if errors and not rows:
        return {'ok': False,
                'error': 'no Census data retrieved: '
                         + ' | '.join(errors),
                'urls': urls}
    got = {r['geography'] for r in rows}
    missing = sorted(j['context'] for j in jurisdictions
                     if j['context'] not in got)
    vintage = f'acs-{year}'
    provenance = (f'U.S. Census Bureau, American Community Survey '
                  f'5-year estimates, table {table}, vintage {year}, '
                  f'retrieved from ' + ' ; '.join(urls))
    result = {'ok': True, 'table': table, 'vintage': vintage,
              'rows': rows, 'provenance': provenance, 'urls': urls,
              'missing': missing}
    if errors:
        result['partialErrors'] = errors
    return result


def build_ingest_payload(pull_result, term_name):
    """The EXACT scoring ingest_records payload (data_ingestion.py):
    geography context + subject per jurisdiction, vintage context,
    provenance carried through."""
    if not pull_result.get('ok'):
        raise ValueError('cannot build an ingest payload from a '
                         'failed pull: '
                         + pull_result.get('error', '?'))
    records = [{'subject': r['geography'],
                'value': r['value'],
                'contexts': [r['geography']]}
               for r in pull_result['rows']
               if r['value'] is not None]
    return {
        'term': term_name,
        'records': records,
        'contexts': [pull_result['vintage']],
        'source': 'api.census.gov',
        'provenance': pull_result['provenance'],
        'subject_kind': 'jurisdiction',
        'create_missing_subjects': True,
    }


def ingest_acs_to_scoring(manager, pull_result, term_name,
                          retrieved_by='', retrieved_by_group=''):
    """Build the payload and run it through the real bridge. When
    `retrieved_by` names the Contributor (optionally acting for a
    ScoreGroup), a SourceRetrieval row records the duplication —
    date-time + group/individual origin (GovSource registry)."""
    from scoring.custom.data_ingestion import ingest_records
    payload = build_ingest_payload(pull_result, term_name)
    result = ingest_records(manager, payload)
    if result.get('ok') and retrieved_by:
        from dmvdata.gov_sources_basis import record_retrieval
        table = pull_result.get('table', '?')
        retrieval = record_retrieval(
            manager, 'census-acs',
            endpoint_name=f'census-acs5-{table.lower()}',
            what=f'{table} {pull_result.get("vintage", "")}',
            retrieved_by=retrieved_by,
            retrieved_by_group=retrieved_by_group,
            row_count=len(payload['records']),
            # urls are already the REDACTED form (never a live key).
            provenance_url=' ; '.join(pull_result.get('urls', [])))
        result['retrieval'] = retrieval.get('retrieval',
                                            retrieval)
    return result
