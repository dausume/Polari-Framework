"""
Selftest — acct-0: the accountability spine.

Run from polari-framework/:
    python3 -m testing.selftest_testing

Covers: catalog discovery (every suite file + module selftest appears
exactly once, categories/criticalities per plan), runners parse real
counts from a selftest and a unittest file, live smoke skip-honests
with a suggestion when no server is reachable, run_matrix emits a
parseable versioned YAML whose blocking_green the exit code mirrors,
opt-in gating (normal env = disabled; POLARI_TEST_BUILD or explicit
POLARI_MODULES = enabled), a TEST build seeds + serves + runs the
matrix through /api/accountability with a persisted CheckRun, and a
NORMAL build's clean absence (testing.absence_probe subprocess).

NOTE: boots two in-process servers (~40s each) — the presence proof
and the absence probe are real boots, not mocks.
"""

import json
import os
import subprocess
import sys
import tempfile

import yaml

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _catalog():
    from testing.check_catalog import FRAMEWORK_ROOT, catalog_checks
    print('catalog discovery')
    entries = catalog_checks()
    names = [e['name'] for e in entries]
    check('names are unique', len(names) == len(set(names)))
    suite_files = [f for f in os.listdir(
        os.path.join(FRAMEWORK_ROOT, 'tests'))
        if f.startswith('test_') and f.endswith('.py')]
    check('every tests/test_*.py registered exactly once',
          sum(1 for n in names if n.startswith('suite:'))
          == len(suite_files), f'{len(suite_files)} suite files')
    selftest_count = sum(1 for n in names
                         if n.startswith('selftest:'))
    check('module selftests discovered (>= 90 incl. this one)',
          selftest_count >= 90, f'{selftest_count} selftests')
    check('this selftest is itself on the matrix',
          'selftest:testing.testing' in names)
    check('live + absence gate rows present',
          {'live:api-smoke', 'gate:normal-build-absence'}
          <= set(names))
    by_name = {e['name']: e for e in entries}
    check('turing litmus pinned under nocode',
          by_name['selftest:polariNoCode.turing']['category']
          == 'nocode')
    check('twin rows are blocking (plan §4)',
          by_name['selftest:polariRefs.directory']['criticality']
          == 'blocking')
    check('module rows are visible non-blocking debt',
          by_name['selftest:aquaponics.pot']['criticality']
          == 'informational')
    check('profiler override: informational (known drift)',
          by_name['suite:api-profiler']['criticality']
          == 'informational')
    check('absence gate is blocking',
          by_name['gate:normal-build-absence']['criticality']
          == 'blocking')
    return by_name


def _runners(by_name):
    from testing.check_runners import run_check
    print('runners parse real surfaces')
    row = run_check(by_name['selftest:waxsupply.wax'])
    check('selftest runner passes + parses counts',
          row['status'] == 'pass' and row['passed'] == row['total']
          and (row['total'] or 0) >= 10, row['evidence'])
    row = run_check(by_name['suite:modules-smoke'])
    check('unittest runner passes + parses counts',
          row['status'] == 'pass' and row['total'] == 3,
          row['evidence'])
    row = run_check(by_name['live:api-smoke'],
                    live_base_url='https://192.0.2.1:1')
    check('unreachable live server -> skip-honest',
          row['status'] == 'skip-honest')
    check('skip-honest evidence names the knob',
          'POLARI_SMOKE_BASE_URL' in row['evidence'])


def _matrix_and_report():
    from testing.matrix_runner import exit_code_for, run_matrix
    print('matrix run + YAML projection')
    results_dir = tempfile.mkdtemp(prefix='acct0-report-')
    record = run_matrix(
        names=['selftest:waxsupply.wax', 'suite:modules-smoke'],
        results_dir=results_dir, log=lambda *a: None)
    check('slice ran both checks',
          record['totals'] == {'pass': 2, 'fail': 0,
                               'skip_honest': 0})
    check('blocking_green true on a green slice',
          record['blocking_green'] is True)
    check('exit code mirrors blocking_green',
          exit_code_for(record) == 0)
    with open(os.path.join(results_dir, 'test-report.yaml')) as fh:
        report = yaml.safe_load(fh)
    check('report parses with report_version 1',
          report.get('report_version') == 1)
    check('report blocking_green matches the run',
          report['run']['blocking_green'] is True)
    check('report stamps environment db_dialect',
          report['run']['environment'].get('db_dialect')
          in ('sqlite', 'mariadb'))
    check('per-check rows carry status + evidence',
          all(r.get('status') and 'evidence' in r
              for r in report['checks'])
          and len(report['checks']) == 2)
    stamped = [f for f in os.listdir(results_dir)
               if f.startswith('test-report-')]
    check('timestamped copy written alongside', len(stamped) == 1)
    fake = dict(record)
    fake['results'] = [dict(record['results'][0],
                            status='fail', criticality='blocking')]
    fake['blocking_green'] = False
    check('exit code 1 when blocking_green false',
          exit_code_for(fake) == 1)


def _gating():
    from polariApiServer.module_gating import module_enabled
    print('opt-in gating (the test-build knob)')
    saved = {k: os.environ.pop(k, None)
             for k in ('POLARI_TEST_BUILD', 'POLARI_MODULES')}
    try:
        check('normal env: testing disabled',
              not module_enabled('testing'))
        os.environ['POLARI_MODULES'] = 'materialsScience,aquaponics'
        check('POLARI_MODULES without testing: still disabled',
              not module_enabled('testing'))
        check('other modules unaffected by the opt-in set',
              module_enabled('aquaponics'))
        os.environ['POLARI_MODULES'] = 'aquaponics,testing'
        check('explicit POLARI_MODULES entry enables',
              module_enabled('testing'))
        del os.environ['POLARI_MODULES']
        os.environ['POLARI_TEST_BUILD'] = 'true'
        check('POLARI_TEST_BUILD enables', module_enabled('testing'))
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _test_build_presence():
    print('TEST build: seeded matrix served + run via the API '
          '(booting in-process server...)')
    os.environ['POLARI_TEST_BUILD'] = 'true'
    from falcon import inspect as falcon_inspect
    from falcon import testing as falcon_testing

    from objectTreeManagerDecorators import managerObject
    manager = managerObject(hasServer=True)
    client = falcon_testing.TestClient(manager.polServer.falconServer)

    check('CapabilityCheck registered in objectTypingDict',
          'CapabilityCheck' in manager.objectTypingDict)
    routes = [r.path for r in falcon_inspect.inspect_app(
        manager.polServer.falconServer).routes]
    check('CapabilityCheck has a CRUDE route',
          any('CapabilityCheck' in p for p in routes))

    matrix = client.simulate_get('/api/accountability').json
    check('GET /api/accountability serves the seeded matrix',
          matrix.get('ok') and matrix['count'] >= 95)
    check('seeded rows are honest never-run',
          matrix['statusTotals'].get('never-run', 0)
          == matrix['count'])

    filtered = client.simulate_get(
        '/api/accountability', params={'category': 'nocode'}).json
    check('?category= filters the matrix',
          filtered['count'] >= 8 and all(
              c['category'] == 'nocode' for c in filtered['checks']))

    run = client.simulate_post(
        '/api/accountability/run',
        json={'checks': ['selftest:waxsupply.wax']}).json
    check('POST run executes a slice and reports',
          run.get('ok') and run['blockingGreen'] is True
          and run['totals'] == {'pass': 1, 'fail': 0,
                                'skip_honest': 0})

    matrix = client.simulate_get('/api/accountability').json
    wax = next(c for c in matrix['checks']
               if c['name'] == 'selftest:waxsupply.wax')
    check('matrix row updated from the CheckRun',
          wax['lastStatus'] == 'pass' and wax['lastRunAt'] != '')

    runs = client.simulate_get('/api/accountability/runs').json
    check('CheckRun persisted and listed',
          runs.get('ok') and runs['count'] >= 1
          and runs['runs'][0]['blockingGreen'] is True)

    refused = client.simulate_post('/api/accountability/run',
                                   json={'checks': ['no:such']})
    check('unknown check filter refuses honestly',
          refused.status_code == 404
          and refused.json.get('ok') is False)

    bare = client.simulate_post('/api/accountability/run', json={})
    check('bare POST refuses (full run must be explicit — the '
          'api-sweep must never recurse into a nested matrix)',
          bare.status_code == 400
          and 'all' in bare.json.get('suggestion', ''))


def _normal_build_absence():
    print('NORMAL build absence probe (subprocess, real boot...)')
    from testing.check_catalog import FRAMEWORK_ROOT
    env = dict(os.environ, PYTHONUNBUFFERED='1')
    env.pop('POLARI_TEST_BUILD', None)
    env.pop('POLARI_MODULES', None)
    proc = subprocess.run(
        ['python3', '-m', 'testing.absence_probe'],
        cwd=FRAMEWORK_ROOT, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, timeout=600)
    tail = '\n'.join(proc.stdout.strip().splitlines()[-3:])
    check('absence probe green on a normal build',
          proc.returncode == 0, tail)


if __name__ == '__main__':
    by_name = _catalog()
    _runners(by_name)
    _matrix_and_report()
    _gating()
    _test_build_presence()
    _normal_build_absence()
    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
