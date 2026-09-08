"""
Selftest — acct-2: transports + formats phase wiring.

Run from polari-framework/:
    python3 -m testing.transports_selftest

Covers: the acct-2 rows are on the matrix with the right categories
and criticalities (format golden shapes blocking; grpc-3
placeholders informational + skip-honest naming grpc-3), the two
in-process proofs pass as subprocess rows (formats golden shapes,
STOMP wire round-trip), and — when staging is reachable — the live
sidecar probes: STOMP CONNECT->CONNECTED and gRPC reflection.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _catalog_rows():
    from testing.check_catalog import catalog_by_name
    print('catalog: transport + format rows')
    by_name = catalog_by_name()
    check('live sidecar rows registered',
          {'transport:stomp-live-connect',
           'transport:grpc-sidecar-reachability'}
          <= set(by_name))
    check('format selftest recategorized as format + blocking',
          by_name['selftest:testing.formats']['category'] == 'format'
          and by_name['selftest:testing.formats']['criticality']
          == 'blocking')
    check('stomp selftest recategorized as transport + blocking',
          by_name['selftest:testing.stomp']['category']
          == 'transport'
          and by_name['selftest:testing.stomp']['criticality']
          == 'blocking')
    check('grpc-3 placeholders informational (visible debt, '
          'non-gating)',
          by_name['transport:grpc-parity-measurement']['criticality']
          == 'informational'
          and by_name['transport:grpc-peer-watch']['criticality']
          == 'informational')
    return by_name


def _in_process_proofs(by_name):
    from testing.custom.check_runners import run_check
    print('in-process round-trip proofs (subprocess rows)')
    row = run_check(by_name['selftest:testing.formats'])
    check('format golden shapes green',
          row['status'] == 'pass'
          and row['passed'] == row['total'], row['evidence'][:80])
    row = run_check(by_name['selftest:testing.stomp'])
    check('STOMP wire round-trip green',
          row['status'] == 'pass'
          and row['passed'] == row['total'], row['evidence'][:80])


def _grpc3_placeholders(by_name):
    from testing.custom.check_runners import run_check
    print('grpc-3 placeholders')
    for name in ('transport:grpc-parity-measurement',
                 'transport:grpc-peer-watch'):
        row = run_check(by_name[name])
        check(f'{name} skip-honest naming grpc-3',
              row['status'] == 'skip-honest'
              and 'grpc-3' in row['evidence'])


def _live_probes(by_name):
    from testing.custom.check_runners import run_check
    from testing.custom.transport_checks import _resolve_backend
    reachable = _resolve_backend('POLARI_STOMP_WS_URL',
                                 3001)['host'] is not None
    print(f'live sidecar probes (staging reachable: {reachable})')
    for name in ('transport:stomp-live-connect',
                 'transport:grpc-sidecar-reachability'):
        row = run_check(by_name[name])
        if reachable:
            check(f'{name} green against staging',
                  row['status'] == 'pass', row['evidence'][:110])
        else:
            check(f'{name} honest without staging',
                  row['status'] in ('skip-honest', 'fail'),
                  row['status'])


if __name__ == '__main__':
    by_name = _catalog_rows()
    _in_process_proofs(by_name)
    _grpc3_placeholders(by_name)
    _live_probes(by_name)
    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
