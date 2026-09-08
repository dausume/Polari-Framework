"""
Selftest — acct-3: twin coherence phase wiring.

Run from polari-framework/:
    python3 -m testing.twin_selftest

Covers the wiring + honesty ladder cheaply (the coherence PROOF
itself is the twin:rehearsal matrix row — a ~5min three-container
run; set POLARI_TWIN_SELFTEST_FULL=1 to run it inside this selftest
too): the row is registered compose-kind + blocking in the twin
category, missing docker/image skip-honestly naming the fix, and
the rehearsal command + fixtures + lease adapter import cleanly.
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


def _catalog_row():
    from testing.check_catalog import catalog_by_name
    print('catalog: the twin rehearsal row')
    row = catalog_by_name().get('twin:rehearsal')
    check('twin:rehearsal registered', row is not None)
    check('compose kind, twin category, blocking',
          row and row['kind'] == 'compose'
          and row['category'] == 'twin'
          and row['criticality'] == 'blocking')
    return row


def _honesty():
    from testing.custom.twin_checks import check_twin_rehearsal
    print('environment honesty')
    saved = os.environ.get('POLARI_TWIN_IMAGE')
    os.environ['POLARI_TWIN_IMAGE'] = 'acct3-no-such-image:none'
    try:
        row = check_twin_rehearsal()
        check('missing image -> skip-honest naming the image knob',
              row['status'] == 'skip-honest'
              and 'POLARI_TWIN_IMAGE' in row['evidence'],
              row['evidence'][:80])
    finally:
        if saved is None:
            os.environ.pop('POLARI_TWIN_IMAGE', None)
        else:
            os.environ['POLARI_TWIN_IMAGE'] = saved


def _imports():
    print('rehearsal machinery imports')
    from testing.custom.twin_http import crude_create, json_call
    from testing.twin_lease_api import TwinLeaseAPI
    from testing.custom.twin_rehearsal import _ref
    body = _ref(fields={'x': 1}, path='name')
    check('ref shape carries authority + className + path',
          body['ref']['authority'] == {'instance': 'm'}
          and body['ref']['path'] == 'name'
          and body['fields'] == {'x': 1})
    api = TwinLeaseAPI(polServer=None)
    check('lease adapter constructs without a server (no routes)',
          api.apiName == '/api/testing/lease')
    check('http helpers importable',
          callable(crude_create) and callable(json_call))


def _full_rehearsal():
    from testing.check_catalog import catalog_by_name
    from testing.custom.check_runners import run_check
    print('FULL rehearsal (POLARI_TWIN_SELFTEST_FULL=1; ~5min)')
    row = run_check(catalog_by_name()['twin:rehearsal'])
    check('twin:rehearsal green', row['status'] == 'pass',
          row['evidence'][:120])


if __name__ == '__main__':
    _catalog_row()
    _honesty()
    _imports()
    if (os.environ.get('POLARI_TWIN_SELFTEST_FULL') or '') == '1':
        _full_rehearsal()
    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
