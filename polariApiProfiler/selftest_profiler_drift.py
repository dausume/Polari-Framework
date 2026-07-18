"""
Selftest — API-profiler schema drift + relocation discovery
(Dustin 2026-07-16).

Run from polari-framework/:
    python3 -m polariApiProfiler.selftest_profiler_drift

An EMULATED EXTERNAL API (in-process HTTP server, OS-assigned port)
serves a consistent data profile long enough to be SOLID, then
completely changes its formatting (renamed fields, same values) —
the tracker must call that DRIFT of the same API, the fuzzy matcher
must propose the old->new field migration from name-token AND
value-overlap evidence, and continuity must be PROVEN (old ids +
locally stored values match up after migration). Then the API
RELOCATES: /data 404s, an RFC 9727 api-catalog advertises the new
location, discovery finds it, and drift-aware matching identifies it
as the API we wanted even under the renamed fields.
"""

import http.server
import json
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from polariApiProfiler import api_discovery as disco
from polariApiProfiler import schema_drift as drift
from polariApiProfiler.profileMatcher import ProfileMatcher

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


PHASE_A_ROWS = [
    {'household_id': 'hh-001', 'county_name': 'Fairfax',
     'median_rent': 2150, 'year_built': 1987},
    {'household_id': 'hh-002', 'county_name': 'Arlington',
     'median_rent': 2400, 'year_built': 1975},
    {'household_id': 'hh-003', 'county_name': 'Montgomery',
     'median_rent': 1975, 'year_built': 1992},
    {'household_id': 'hh-004', 'county_name': 'Prince Georges',
     'median_rent': 1830, 'year_built': 2003},
]
PHASE_B_ROWS = [
    {'hhId': r['household_id'], 'jurisdiction': r['county_name'],
     'rentMedian': r['median_rent'],
     'constructionYear': r['year_built']} for r in PHASE_A_ROWS]

#: Mutable behavior switch for the emulated API.
STATE = {'phase': 'A', 'relocated': False, 'advertise': True}


class _EmulatedApi(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        base = f'http://{self.headers.get("Host", "")}'
        if self.path == '/data':
            if STATE['relocated']:
                self._json(404, {'error': 'gone'})
            elif STATE['phase'] == 'A':
                self._json(200, PHASE_A_ROWS)
            else:
                self._json(200, PHASE_B_ROWS)
        elif self.path == '/.well-known/api-catalog' \
                and STATE['advertise'] and STATE['relocated']:
            self._json(200, {'linkset': [{
                'anchor': f'{base}/v2/households',
                'item': [{'href': '/v2/households'}]}]})
        elif self.path == '/v2/households' and STATE['relocated']:
            self._json(200, PHASE_B_ROWS)
        else:
            self._json(404, {'error': 'not found'})


def _fetch(url):
    return disco.default_fetcher(url, timeout=5)


def _tracker_and_drift(base):
    print('the profile becomes solid, then the SAME api drifts')
    tracker = drift.ProfileStabilityTracker(f'{base}/data',
                                            stable_after=5)
    for i in range(4):
        _, data = _fetch(f'{base}/data')
        result = tracker.observe(data)
    check('4 consistent samples: solid NOT yet declared',
          result['status'] == 'observing'
          and result['consecutive'] == 4)
    _, data = _fetch(f'{base}/data')
    result = tracker.observe(data)
    check('5th consistent sample: profile is SOLID',
          result['status'] == 'solid'
          and 'SOLID' in result['evidence'])

    STATE['phase'] = 'B'
    _, drifted_data = _fetch(f'{base}/data')
    result = tracker.observe(drifted_data)
    check('renamed fields on the SAME url = DRIFT (never a new API)',
          result['status'] == 'drifted'
          and 'changed its formatting' in result['evidence']
          and 'not a new API' in result['evidence'])
    check('drift evidence carries the compare confidence',
          'fieldConfidence' in result['evidence'])
    return tracker, drifted_data


def _migration(drifted_data):
    print('fuzzy adaptation: word formatting + data formatting')
    old_fields = drift.fields_with_samples(PHASE_A_ROWS)
    new_fields = drift.fields_with_samples(drifted_data)
    migration = drift.propose_field_migration(old_fields, new_fields)
    expected = {'household_id': 'hhId', 'county_name': 'jurisdiction',
                'median_rent': 'rentMedian',
                'year_built': 'constructionYear'}
    mapped = {old: entry['newField']
              for old, entry in migration['mapping'].items()}
    check('all four renames mapped correctly',
          mapped == expected, f'{mapped}')
    check('nothing unmatched, no false ambiguity',
          migration['unmatchedOld'] == []
          and migration['unmatchedNew'] == []
          and migration['ambiguous'] == [])
    check('every mapping meets the confidence threshold',
          all(entry['confidence'] >= drift.DEFAULT_MIGRATION_THRESHOLD
              for entry in migration['mapping'].values()))
    all_evidence = ' | '.join(
        ' '.join(entry['evidence'])
        for entry in migration['mapping'].values())
    check('evidence cites name-token reasoning',
          'name token' in all_evidence or 'name tokens'
          in all_evidence)
    check('evidence cites value-overlap reasoning',
          'exact overlap' in all_evidence)
    verdict = drift.drift_verdict(migration, len(old_fields))
    check("the drift verdict is explicitly 'adaptable'",
          verdict['verdict'] == 'adaptable'
          and verdict['mappedFraction'] == 1.0)
    return migration


def _continuity(drifted_data, migration):
    print('continuity: old ids + locally stored values match up')
    migrated = drift.apply_migration(drifted_data,
                                     migration['mapping'])
    result = drift.verify_continuity(PHASE_A_ROWS, migrated,
                                     'household_id')
    check('every stored id matched, zero value mismatches',
          result['ok'] and len(result['matchedIds']) == 4
          and result['valueMismatches'] == []
          and result['missingIds'] == [])
    corrupted = [dict(row) for row in migrated]
    corrupted[0]['median_rent'] += 100
    negative = drift.verify_continuity(PHASE_A_ROWS, corrupted,
                                       'household_id')
    check('a corrupted value is reported as EXACTLY that mismatch',
          not negative['ok']
          and len(negative['valueMismatches']) == 1
          and negative['valueMismatches'][0]['field']
          == 'median_rent'
          and negative['valueMismatches'][0]['id'] == 'hh-001')


def _honest_matching():
    print('ambiguity + incompatibility honesty')
    ambiguous = drift.propose_field_migration(
        {'user_id': ['u1', 'u2', 'u3']},
        {'userId': ['u1', 'u2', 'u3'],
         'user_identifier': ['u1', 'u2', 'u3']})
    check('near-tied candidates are SURFACED as ambiguous, not '
          'silently picked',
          ambiguous['mapping'] == {}
          and len(ambiguous['ambiguous']) == 1
          and len(ambiguous['ambiguous'][0]['candidates']) == 2)

    incompatible = drift.propose_field_migration(
        drift.fields_with_samples(PHASE_A_ROWS),
        {'foo': ['x', 'y', 'z', 'w'], 'bar': [9.5, 3.3, 1.1, 7.7]})
    verdict = drift.drift_verdict(incompatible, 4)
    check("a totally different API is 'incompatible', mostly "
          'unmatched',
          verdict['verdict'] == 'incompatible'
          and len(incompatible['unmatchedOld']) >= 3)


def _relocation(base, tracker):
    print('relocation: standard advertising locations + drift-aware '
          'search')
    STATE['relocated'] = True
    status, _ = _fetch(f'{base}/data')
    check('the old location is really gone (404)', status == 404)

    found = disco.discover_apis(base, fetcher=_fetch)
    check('the api-catalog advertises the new location',
          found['ok'] and any(
              entry['url'] == f'{base}/v2/households'
              and 'RFC 9727' in entry['source']
              for entry in found['advertised']))

    matcher = ProfileMatcher(manager=None)
    wanted_profile = tracker.profile
    result = disco.find_matching_api(
        None, found['advertised'], wanted_profile, PHASE_A_ROWS,
        fetcher=_fetch, matcher=matcher)
    check('drift-aware matching ranks the relocated API best',
          result['ok']
          and result['best']['url'] == f'{base}/v2/households'
          and result['best']['score'] >= 0.5)
    check('the match carries the migration it needed',
          'migration' in result['best']
          and len(result['best']['migration']['mapping']) == 4
          and 'drift-aware' in result['best']['evidence'])

    _, new_data = _fetch(result['best']['url'])
    migrated = drift.apply_migration(
        new_data, result['best']['migration']['mapping'])
    continuity = drift.verify_continuity(PHASE_A_ROWS, migrated,
                                         'household_id')
    check('end to end: rows from the NEW location still match the '
          'local store', continuity['ok']
          and len(continuity['matchedIds']) == 4)


def _honest_refusals(base):
    print('honest refusals')
    STATE['advertise'] = False
    STATE['relocated'] = False
    STATE['phase'] = 'A'
    silent = disco.discover_apis(base, fetcher=_fetch)
    check('no advertisement anywhere -> ok:False naming every '
          'checked path',
          not silent['ok'] and len(silent['checked'])
          == len(disco.STANDARD_ADVERTISING_PATHS)
          and '/.well-known/api-catalog' in silent['error'])

    matcher = ProfileMatcher(manager=None)
    unrelated_rows = [{'zzz_alpha': 'qq', 'zzz_beta': 123456.7}]
    unrelated_profile = matcher.analyze_structure(unrelated_rows)
    result = disco.find_matching_api(
        None, [f'{base}/data'], unrelated_profile, unrelated_rows,
        fetcher=_fetch, matcher=matcher)
    check('no candidate above threshold -> ok:False WITH the '
          'ranking + suggestion',
          not result['ok'] and len(result['ranking']) == 1
          and result['suggestion']['knob'])


def main():
    server = http.server.HTTPServer(('127.0.0.1', 0), _EmulatedApi)
    port = server.server_address[1]
    base = f'http://127.0.0.1:{port}'
    thread = threading.Thread(target=server.serve_forever,
                              daemon=True)
    thread.start()
    try:
        status = 0
        for _ in range(100):
            status, _data = _fetch(f'{base}/data')
            if status == 200:
                break
        if status != 200:
            print('emulated API never came up — cannot test')
            return 1
        tracker, drifted_data = _tracker_and_drift(base)
        migration = _migration(drifted_data)
        _continuity(drifted_data, migration)
        _honest_matching()
        _relocation(base, tracker)
        _honest_refusals(base)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
