"""
@module polariApiProfiler.api_discovery

API relocation discovery (Dustin 2026-07-16): when a known API's
location changes, ask "hey, what are your APIs?" at the STANDARD
advertising locations, then search the advertised APIs for something
matching what we want (the known profile) — drift-aware, because a
relocated API may ALSO have changed its formatting.

Standard advertising locations probed (each named by its standard):
  /.well-known/api-catalog      RFC 9727 (api-catalog linkset)
  /openapi.json                 OpenAPI description at the root
  /.well-known/openapi.json     OpenAPI via RFC 8615 well-known
  /swagger.json                 legacy Swagger 2.x convention
  /api-docs                     springdoc/swagger-ui convention
  /api                          plain JSON listing fallback
                                ({'apis': [{'name','url'}...]})

Honesty: no advertisement found -> ok False naming every path
checked; no candidate above threshold -> ok False WITH the ranking.

@consumers
  - polariApiProfiler.selftest_profiler_drift
"""

import json
import ssl
import urllib.error
import urllib.request
from urllib.parse import urljoin

from polariApiProfiler.schema_drift import (fields_with_samples,
                                            profile_consistency,
                                            propose_field_migration)

STANDARD_ADVERTISING_PATHS = (
    ('/.well-known/api-catalog', 'RFC 9727 api-catalog'),
    ('/openapi.json', 'OpenAPI root description'),
    ('/.well-known/openapi.json', 'OpenAPI well-known'),
    ('/swagger.json', 'Swagger 2.x root description'),
    ('/api-docs', 'api-docs convention'),
    ('/api', 'plain JSON api listing'),
)

DEFAULT_TIMEOUT_S = 5


def default_fetcher(url, timeout=DEFAULT_TIMEOUT_S):
    """(status, parsed_json_or_None). Never raises."""
    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(url, timeout=timeout,
                                    context=context) as response:
            body = response.read()
            try:
                return response.status, json.loads(body)
            except (ValueError, UnicodeDecodeError):
                return response.status, None
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except Exception:
        return 0, None


def _parse_api_catalog(base_url, doc):
    """RFC 9727 linkset -> advertised API urls (anchor + item +
    service-desc hrefs, resolved against the base)."""
    advertised = []
    for entry in doc.get('linkset', []) or []:
        anchor = entry.get('anchor')
        if anchor:
            advertised.append({'url': urljoin(base_url, anchor),
                               'source': 'RFC 9727 api-catalog '
                                         'anchor'})
        for relation in ('item', 'service-desc', 'service-doc'):
            for link in entry.get(relation, []) or []:
                href = link.get('href') if isinstance(link, dict) \
                    else None
                if href:
                    advertised.append(
                        {'url': urljoin(base_url, href),
                         'source': f'RFC 9727 api-catalog '
                                   f'{relation}'})
    return advertised


def _parse_openapi(base_url, doc, source):
    servers = doc.get('servers') or []
    server = (servers[0].get('url') if servers
              and isinstance(servers[0], dict) else '') or base_url
    advertised = []
    for path, operations in (doc.get('paths') or {}).items():
        name = None
        if isinstance(operations, dict):
            for operation in operations.values():
                if isinstance(operation, dict) \
                        and operation.get('summary'):
                    name = operation['summary']
                    break
        advertised.append({'url': urljoin(server + '/',
                                          path.lstrip('/')),
                           'source': source,
                           **({'name': name} if name else {})})
    return advertised


def _parse_plain_listing(base_url, doc):
    advertised = []
    for api in doc.get('apis', []) or []:
        if isinstance(api, dict) and api.get('url'):
            advertised.append(
                {'url': urljoin(base_url, api['url']),
                 'source': 'plain JSON api listing',
                 **({'name': api['name']} if api.get('name')
                    else {})})
    return advertised


def discover_apis(base_url, fetcher=None):
    """Probe every standard advertising location on base_url ->
    {'ok', 'advertised': [{'url','source','name'?}], 'checked',
    'errors'}."""
    fetcher = fetcher or default_fetcher
    base = base_url.rstrip('/')
    advertised, checked, errors = [], [], []
    seen_urls = set()
    for path, standard in STANDARD_ADVERTISING_PATHS:
        url = base + path
        checked.append(path)
        status, doc = fetcher(url)
        if status == 0:
            errors.append(f'{path}: unreachable')
            continue
        if status != 200 or not isinstance(doc, dict):
            continue
        if 'linkset' in doc:
            found = _parse_api_catalog(base, doc)
        elif 'paths' in doc:
            found = _parse_openapi(base, doc, standard)
        elif 'apis' in doc:
            found = _parse_plain_listing(base, doc)
        else:
            errors.append(f'{path}: 200 but not a recognized '
                          f'advertisement shape ({standard})')
            continue
        for item in found:
            if item['url'] not in seen_urls:
                seen_urls.add(item['url'])
                advertised.append(item)
    if not advertised:
        return {'ok': False, 'advertised': [], 'checked': checked,
                'errors': errors,
                'error': 'no API advertisement found at any '
                         'standard location — checked: '
                         + ', '.join(checked)}
    return {'ok': True, 'advertised': advertised,
            'checked': checked, 'errors': errors}


def _rows_of(data):
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list) and value \
                    and isinstance(value[0], dict):
                return value
        return [data]
    return []


def find_matching_api(manager, candidates, wanted_profile,
                      wanted_samples, fetcher=None, threshold=0.5,
                      matcher=None):
    """Search advertised candidate APIs for the one matching the
    wanted profile. DRIFT-AWARE: when exact field names score low,
    the candidate is retried through propose_field_migration (a
    relocated API may also have renamed its fields) and scored by
    the mapped confidence. Returns ranked candidates with evidence
    and the migration used, or an honest refusal with the ranking."""
    fetcher = fetcher or default_fetcher
    if matcher is None:
        from polariApiProfiler.profileMatcher import ProfileMatcher
        matcher = ProfileMatcher(manager=manager)
    old_fields = fields_with_samples(wanted_samples)
    ranked = []
    for candidate in candidates or []:
        url = candidate['url'] if isinstance(candidate, dict) \
            else candidate
        status, data = fetcher(url)
        if status != 200 or data is None:
            ranked.append({'url': url, 'score': 0.0,
                           'evidence': f'unreachable or non-JSON '
                                       f'(status {status})'})
            continue
        analysis = matcher.analyze_structure(data)
        exact = profile_consistency(wanted_profile, analysis)
        entry = {'url': url,
                 'score': exact['overall'],
                 'evidence': f'exact-name field consistency '
                             f"{exact['fieldConfidence']:.2f}"}
        if exact['fieldConfidence'] < threshold and old_fields:
            rows = _rows_of(data)
            migration = propose_field_migration(
                old_fields, fields_with_samples(rows))
            mapped_confidence = (
                sum(m['confidence']
                    for m in migration['mapping'].values())
                / len(old_fields)) if old_fields else 0.0
            if mapped_confidence > entry['score']:
                entry.update({
                    'score': mapped_confidence,
                    'migration': migration,
                    'evidence': f'drift-aware match: '
                                f'{len(migration["mapping"])}'
                                f'/{len(old_fields)} old fields '
                                f'mapped, mean confidence '
                                f'{mapped_confidence:.2f} (exact '
                                f'names scored only '
                                f"{exact['fieldConfidence']:.2f})"})
        entry['score'] = round(entry['score'], 4)
        ranked.append(entry)
    ranked.sort(key=lambda e: -e['score'])
    if not ranked or ranked[0]['score'] < threshold:
        return {'ok': False, 'ranking': ranked,
                'error': 'no advertised API matches the wanted '
                         f'profile at threshold {threshold}',
                'suggestion': {
                    'knob': 'threshold / wanted profile',
                    'action': 'widen the search (more advertising '
                              'hosts) or refresh the wanted profile '
                              'if the data legitimately changed'}}
    return {'ok': True, 'best': ranked[0], 'ranking': ranked}
