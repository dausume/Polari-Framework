"""
Self-test for gm-2: the quiesce seam.

Through a real falcon App: engage gates mutations FIRST then flushes
(receipt carries flush time + in-flight report), reads always flow,
the open prefixes (quiesce/health/move-operations) stay writable,
double-engage 409s, release is idempotent, and a FAILED flush keeps
the gate up with the error as the receipt (data protected, move must
not proceed).

Run from polari-framework/:
    python3 -m polariApiServer.selftest_quiesce
"""

import sys
import types

import falcon
import falcon.testing as ft

from polariApiServer.quiesce import (
    QuiesceEndpoint, QuiesceMiddleware, QuiesceState,
)

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


class _Echo:
    def on_get(self, request, response):
        response.media = {'ok': True}

    def on_post(self, request, response):
        response.media = {'ok': True, 'wrote': True}


def _app(persist=None, has_db=True):
    state = QuiesceState()
    app = falcon.App(middleware=[QuiesceMiddleware(state)])
    calls = []

    def _persist():
        calls.append(1)
        if persist == 'boom':
            raise RuntimeError('disk exploded')

    manager = types.SimpleNamespace(
        db=object() if has_db else None,
        persistTree=_persist,
        objectTables={'MutationLease': {}, 'WriteJournalEntry': {}})
    polServer = types.SimpleNamespace(falconServer=app,
                                      manager=manager)
    QuiesceEndpoint(polServer, state)
    app.add_route('/api/DigitizedDataset', _Echo())
    app.add_route('/api/topology/move-operations/step', _Echo())
    return state, ft.TestClient(app), calls


def test_gate_semantics():
    print('[gate: mutations 423, reads flow, receipts flow]')
    state, client, calls = _app()
    got = client.simulate_post('/api/quiesce', json={
        'reason': 'test move', 'moveName': 'backend@1'})
    check('engage ok with flush receipt',
          got.status_code == 200 and got.json['ok']
          and got.json['receipt']['persisted'] is True
          and got.json['receipt']['inFlight'] == 0)
    check('persistTree ran exactly once', len(calls) == 1)
    check('mutation 423s while quiesced',
          client.simulate_post('/api/DigitizedDataset')
          .status_code == 423)
    check('the 423 names the move',
          'backend@1' in client.simulate_post(
              '/api/DigitizedDataset').json['description'])
    check('reads still answer',
          client.simulate_get('/api/DigitizedDataset')
          .status_code == 200)
    check('move-operation receipts stay writable (open prefix)',
          client.simulate_post(
              '/api/topology/move-operations/step')
          .status_code == 200)
    check('status reports quiesced',
          client.simulate_get('/api/quiesce/status')
          .json['quiesced'] is True)
    got = client.simulate_post('/api/quiesce', json={})
    check('double engage 409s (two moves must not interleave)',
          got.status_code == 409)
    got = client.simulate_post('/api/quiesce/release')
    check('release drops the gate', got.json['released'] is True)
    check('mutations flow again after release',
          client.simulate_post('/api/DigitizedDataset')
          .status_code == 200)
    check('release is idempotent',
          client.simulate_post('/api/quiesce/release')
          .json['released'] is False)


def test_failed_flush():
    print('[failed flush: gate STAYS UP, error is the receipt]')
    state, client, calls = _app(persist='boom')
    got = client.simulate_post('/api/quiesce', json={})
    check('engage reports failure', got.status_code == 500
          and got.json['ok'] is False)
    check('the error is the receipt',
          'disk exploded' in got.json['receipt']['error'])
    check('gate stays UP (data protected — the move must not '
          'proceed)',
          client.simulate_post('/api/DigitizedDataset')
          .status_code == 423)


def test_stateless():
    print('[stateless instance: nothing to flush, still gates]')
    state, client, calls = _app(has_db=False)
    got = client.simulate_post('/api/quiesce', json={})
    check('no-DB engage is ok with the honest note',
          got.status_code == 200 and got.json['ok']
          and 'stateless' in got.json['receipt']['error'])
    check('gate up regardless',
          client.simulate_post('/api/DigitizedDataset')
          .status_code == 423)


def main():
    test_gate_semantics()
    test_failed_flush()
    test_stateless()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
