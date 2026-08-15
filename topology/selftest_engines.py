"""
sep-4 selftest: engine metering + the engine data-page report.
Function-level, no server — a stub manager injected through
provider_registry.set_manager (the same seam the boot uses).
Run: python topology/selftest_engines.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'modules'))

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    from topology import provider_registry
    from topology.engine_metering import (
        binding_url, record, usage_report)
    from topology.engines_api import ENGINES, engine_report
    from topology.topology_modules import EngineProviderBinding

    mgr = type('M', (), {'objectTables': {
        'EngineUsageWindow': {}, 'EngineProviderBinding': {},
    }, 'idList': []})()
    mgr.db = type('D', (), {'saveInstanceInDB':
                            staticmethod(lambda row: None)})()
    provider_registry.set_manager(mgr)

    print('== suite: metering (rows, never logs) ==')
    started = time.time() - 0.05
    ok1 = record('msci', True, started, bytes_out=100, bytes_in=900)
    ok2 = record('msci', False, started, bytes_out=50, bytes_in=0)
    rows = [r for r in mgr.objectTables['EngineUsageWindow'].values()
            if getattr(r, 'engine', '') == 'msci']
    check('two calls accumulate into ONE hour window row',
          ok1 and ok2 and len(rows) == 1)
    row = rows[0]
    check('window row: calls/errors/bytes/latency accumulated',
          row.calls == 2 and row.errors == 1
          and row.bytes_out == 150 and row.bytes_in == 900
          and row.latency_ms_sum >= 100
          and row.latency_ms_max >= 50)
    report = usage_report(mgr, 'msci')
    check('usage_report: tracked with derived averages',
          report['tracked'] and len(report['windows']) == 1
          and report['windows'][0]['calls'] == 2
          and report['windows'][0]['latencyMsAvg'] >= 50)
    untracked = usage_report(mgr, 'cad')
    check('usage_report: never an empty chart pretending to be '
          'zero — untracked says so',
          not untracked['tracked']
          and 'no traffic recorded' in untracked['note'])

    print('== suite: never breaks the call path ==')
    provider_registry.set_manager(None)
    check('record without a manager degrades to not-tracked',
          record('msci', True, time.time()) is False)
    bare = type('M', (), {'objectTables': {}, 'idList': []})()
    provider_registry.set_manager(bare)
    check('record without the class registered degrades too',
          record('msci', True, time.time()) is False)
    provider_registry.set_manager(mgr)

    print('== suite: the binding rung ==')
    EngineProviderBinding(name='cad', url='http://cad.isle:9600/',
                          bound_from='cad-engines', manager=mgr)
    check('binding_url reads the row (trailing slash stripped)',
          binding_url('cad') == 'http://cad.isle:9600')
    check('binding_url: unbound engine answers empty',
          binding_url('livekit') == '')
    saved_env = os.environ.pop('CAD_ENGINES_URL', None)
    try:
        from mathshapes.cad_remote import engines_url_for
        check('cad ladder rung 2: binding row answers when the env '
              'knob is unset',
              engines_url_for() == 'http://cad.isle:9600')
    finally:
        if saved_env is not None:
            os.environ['CAD_ENGINES_URL'] = saved_env

    print('== suite: the engine data page ==')
    check('all five engines registered with natures + apps',
          set(ENGINES) == {'msci', 'cad', 'business-ops',
                           'livekit', 'reticulum'}
          and ENGINES['msci']['nature'] == 'engine-only'
          and ENGINES['business-ops']['nature'] == 'engine+app'
          and ENGINES['business-ops']['app'] == 'app-business')
    check('unknown engine refused honestly, naming the known set',
          not engine_report(mgr, 'nope').get('ok'))
    saved_env = os.environ.pop('MSCI_ENGINES_URL', None)
    try:
        rep = engine_report(mgr, 'msci')
        rungs = rep['reachability']['ladder']
        check('msci report: 3-rung ladder, each half stated',
              rep['ok'] and len(rungs) == 3
              and rungs[0]['name'] == 'MSCI_ENGINES_URL'
              and rungs[0]['set'] is False
              and rungs[1]['bound'] is False
              and rungs[2]['resolved'] is False)
        check('msci report: placement lists BOTH module seams with '
              'refusals stated',
              [p['module'] for p in rep['placement']]
              == ['materialsScience.dft', 'materialsScience.fem']
              and all(not p['resolved'] and p['refusal']
                      for p in rep['placement']))
        check('msci report: usage tracked from the earlier calls',
              rep['usage']['tracked'])
        check('capability absence is a stated note, not a guess',
              rep['reachability']['capability'] is None
              and 'no live capability' in
                  rep['reachability']['capabilityNote'])
    finally:
        if saved_env is not None:
            os.environ['MSCI_ENGINES_URL'] = saved_env

    failed = [label for label, passed in _results if not passed]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} '
          'checks passed')
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
