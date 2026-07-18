"""
Selftest for testing-over-topology (tt-11).

Run from polari-framework/:  python3 -m topology.selftest_testing

Stdlib-only for the pure parts (parsing, protocol derivation,
module-state rollup, report aggregation over SimpleNamespace rows);
one real subprocess run of a fast suite proves the runner contract
end-to-end (the same invocation the API uses).
"""

import subprocess
import sys
import types

from topology.topology_testing import (
    discover_suites, module_test_state, parse_suite_output,
    protocol_of, testing_report,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _ns(**fields):
    return types.SimpleNamespace(**fields)


def _run(suite, status, passed, total, ran_at):
    return _ns(name=f'{suite}@{ran_at}', module_name=suite.split('.')[0],
               suite=suite, status=status, checks_passed=passed,
               checks_total=total, output_tail='', ran_at=ran_at,
               topology_name='staging-a')


def _ping(kind, subject, status, protocol='http', secured=False,
          checked_at='2026-07-18T01:00:00+00:00'):
    return _ns(name=f'{subject}@{checked_at}', kind=kind,
               subject=subject, target='http://x:9500',
               protocol=protocol, secured=secured,
               security_note='', status=status, evidence='',
               checked_at=checked_at, topology_name='staging-a')


if __name__ == '__main__':
    print('== suite: output parsing + protocol derivation ==')
    check('tally parsed from suite output',
          parse_suite_output('...\n52/52 checks passed\n') == (52, 52))
    check('last tally wins (nested suite output)',
          parse_suite_output('26/26 checks passed\n'
                             '3/9 checks passed') == (3, 9))
    check('no tally => None (caller treats as error)',
          parse_suite_output('Traceback ...') is None)
    check('https => secured TLS',
          protocol_of('https://a.b/c') == ('https', True, 'TLS'))
    proto, secured, note = protocol_of('http://192.168.0.210:9500')
    check('http => honest plaintext note',
          proto == 'http' and not secured and 'plaintext' in note)
    check('empty target => empty protocol',
          protocol_of('') == ('', False, ''))

    print('== suite: module state rollup ==')
    runs = {'m.selftest_a': _ns(status='pass'),
            'm.selftest_b': _ns(status='pass')}
    check('all suites pass => pass',
          module_test_state(['m.selftest_a', 'm.selftest_b'],
                            runs) == 'pass')
    runs['m.selftest_b'] = _ns(status='fail')
    check('any suite fails => fail',
          module_test_state(['m.selftest_a', 'm.selftest_b'],
                            runs) == 'fail')
    check('no runs => never-run',
          module_test_state(['m.selftest_a'], {}) == 'never-run')
    check('partially run => NOT pass (honest)',
          module_test_state(['m.selftest_a', 'm.selftest_c'],
                            {'m.selftest_a': _ns(status='pass')})
          == 'fail')
    check('no suites => no-suites',
          module_test_state([], {}) == 'no-suites')

    print('== suite: report aggregation ==')
    mgr = _ns(objectTables={
        'TopologyTestRun': {r.name: r for r in [
            _run('aqua.selftest_x', 'fail', 3, 9,
                 '2026-07-18T00:00:00+00:00'),
            # later run supersedes the failure
            _run('aqua.selftest_x', 'pass', 9, 9,
                 '2026-07-18T01:00:00+00:00'),
            _run('scoring.selftest_y', 'fail', 1, 2,
                 '2026-07-18T01:00:00+00:00'),
        ]},
        'IntegrationPing': {p.name: p for p in [
            _ping('machine', 'lightweight', 'ok', 'https', True),
            _ping('dep-edge', 'edge-1', 'failed'),
            _ping('connection', 'conn-1', 'static-artifact', 'file'),
        ]},
        'ModuleAssignment': {
            'aqua@prf-a': _ns(name='aqua@prf-a', module_name='aqua',
                              instance_name='prf-a', state='enabled',
                              topology_name='staging-a'),
            'scoring@prf-a': _ns(name='scoring@prf-a',
                                 module_name='scoring',
                                 instance_name='prf-a',
                                 state='enabled',
                                 topology_name='staging-a'),
            'aqua.sub@prf-b': _ns(name='aqua.sub@prf-b',
                                  module_name='aqua.sub',
                                  instance_name='prf-b',
                                  state='enabled',
                                  topology_name='staging-a'),
        },
        'InstanceDefinition': {
            'prf-a': _ns(name='prf-a', machine_name='staging-a',
                         topology_name='staging-a'),
            'prf-b': _ns(name='prf-b', machine_name='lightweight',
                         topology_name='staging-a'),
        },
    })
    fake_suites = {'aqua': ['aqua.selftest_x'],
                   'scoring': ['scoring.selftest_y']}
    report = testing_report(mgr, 'staging-a', suites=fake_suites)
    states = {m['module']: m['state'] for m in report['modules']}
    check('latest run wins (aqua recovered to pass)',
          states['aqua'] == 'pass', str(states))
    check('failing suite marks the module', states['scoring'] == 'fail')
    check('dotted assignment rides the top-level module '
          '(aqua covers prf-b)',
          sorted([m for m in report['modules']
                  if m['module'] == 'aqua'][0]['instances'])
          == ['prf-a', 'prf-b'])
    check('instance rollup: prf-a fails (scoring), prf-b passes',
          report['instances'] == {'prf-a': 'fail', 'prf-b': 'pass'},
          str(report['instances']))
    check('host rollup follows instances',
          report['hosts'] == {'staging-a': 'fail',
                              'lightweight': 'pass'},
          str(report['hosts']))
    check('links carry protocol + secured + status',
          any(l['subject'] == 'lightweight' and l['secured']
              and l['protocol'] == 'https' and l['status'] == 'ok'
              for l in report['links'])
          and any(l['subject'] == 'edge-1'
                  and l['status'] == 'failed'
                  for l in report['links'])
          and any(l['status'] == 'static-artifact'
                  for l in report['links']))

    print('== suite: suite discovery + one real run ==')
    suites = discover_suites()
    check('discovery finds topology + techtree suites',
          'topology.selftest_testing' in suites.get('topology', [])
          and suites.get('techtree'))
    proc = subprocess.run(
        [sys.executable, '-m', 'topology.selftest_module_graph'],
        capture_output=True, text=True, timeout=120)
    tally = parse_suite_output(proc.stdout + proc.stderr)
    check('real subprocess run parses to a full pass',
          proc.returncode == 0 and tally is not None
          and tally[0] == tally[1] > 0, str(tally))

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    raise SystemExit(1 if failed else 0)
