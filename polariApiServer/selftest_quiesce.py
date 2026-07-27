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

    def _persist(progress=None):
        calls.append(1)
        if persist == 'boom':
            raise RuntimeError('disk exploded')
        if progress is not None:
            progress({'module': '(core)', 'className': 'Widget',
                      'rows': 3, 'batched': True, 'batchError': '',
                      'classesDone': 1, 'classesTotal': 2,
                      'rowsDone': 3})

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
        'reason': 'test move', 'moveName': 'backend@1',
        'wait': True})
    check('engage (wait) ok with flush receipt',
          got.status_code == 200 and got.json['ok']
          and got.json['receipt']['persisted'] is True
          and got.json['receipt']['inFlight'] == 0)
    check('persistTree ran exactly once', len(calls) == 1)
    check('per-class progress streamed into the receipt (mlb-5b)',
          got.json['receipt'].get('classesDone') == 1
          and got.json['receipt'].get('currentClass') == 'Widget')
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
    got = client.simulate_post('/api/quiesce', json={
        'moveName': 'backend@1'})
    check('re-engage for the SAME move is idempotent (crash-resume, '
          'gm-safety)',
          got.status_code == 200 and got.json.get('resumed') is True)
    got = client.simulate_post('/api/quiesce', json={
        'moveName': 'other@9'})
    check('engage for a DIFFERENT move 409s (no interleaving)',
          got.status_code == 409)
    got = client.simulate_post('/api/quiesce', json={})
    check('anonymous double engage 409s too',
          got.status_code == 409)
    got = client.simulate_post('/api/quiesce/release')
    check('release drops the gate', got.json['released'] is True)
    check('mutations flow again after release',
          client.simulate_post('/api/DigitizedDataset')
          .status_code == 200)
    check('release is idempotent',
          client.simulate_post('/api/quiesce/release')
          .json['released'] is False)


def test_async_engage():
    print('[async engage: gate up immediately, status streams]')
    state, client, calls = _app()
    got = client.simulate_post('/api/quiesce', json={
        'moveName': 'backend@2'})
    check('async engage returns immediately with flushing note',
          got.status_code == 200 and got.json.get('flushing'))
    check('gate is up before the flush finishes (gate-first)',
          client.simulate_post('/api/DigitizedDataset')
          .status_code == 423)
    import time as _t
    for _ in range(50):
        st = client.simulate_get('/api/quiesce/status').json
        if st['receipt'].get('persisted'):
            break
        _t.sleep(0.1)
    check('status reaches persisted with flush seconds',
          st['receipt'].get('persisted') is True
          and st['receipt'].get('flushSeconds') is not None)
    client.simulate_post('/api/quiesce/release')


def test_failed_flush():
    print('[failed flush: gate STAYS UP, error is the receipt]')
    state, client, calls = _app(persist='boom')
    got = client.simulate_post('/api/quiesce', json={'wait': True})
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
    got = client.simulate_post('/api/quiesce', json={'wait': True})
    check('no-DB engage is ok with the honest note',
          got.status_code == 200 and got.json['ok']
          and 'stateless' in got.json['receipt']['error'])
    check('gate up regardless',
          client.simulate_post('/api/DigitizedDataset')
          .status_code == 423)


def test_stale_move_artifacts():
    print('[gm-safety: interrupted transfers are discoverable]')
    import json as _json
    import os
    import tempfile

    from polariApiServer.quiesce import stale_move_artifacts
    tmp = tempfile.mkdtemp(prefix='stale-move-')
    check('clean volume -> no findings',
          stale_move_artifacts(tmp) == [])
    _json.dump({'move': 'backend@9', 'from': 'a', 'to': 'b',
                'phase': 'copying'},
               open(os.path.join(tmp, '.move-journal.json'), 'w'))
    os.makedirs(os.path.join(tmp, '.incoming-backend@9'))
    os.makedirs(os.path.join(tmp, '.previous-backend@9'))
    found = stale_move_artifacts(tmp)
    kinds = {f['kind'] for f in found}
    check('journal + staged + previous all surface',
          kinds == {'move-journal', 'incoming', 'previous'})
    journal = next(f for f in found if f['kind'] == 'move-journal')
    check('the journal names the move and phase',
          journal['journal']['move'] == 'backend@9'
          and journal['journal']['phase'] == 'copying')
    check('every finding carries meaning + action (honest, not '
          'just a path)',
          all(f.get('meaning') and f.get('action') for f in found))
    # /api/health surfaces them (the boot-time awareness).
    old = os.environ.get('POLARI_DATA_DIR')
    os.environ['POLARI_DATA_DIR'] = tmp
    try:
        from polariApiServer.lazy_boot import HealthEndpoint
        stub = types.SimpleNamespace(falconServer=falcon.App(),
                                     bootRegistry=None)
        HealthEndpoint(stub)
        got = ft.TestClient(stub.falconServer) \
            .simulate_get('/api/health')
        check('health carries staleMoveArtifacts',
              len(got.json.get('staleMoveArtifacts', [])) == 3)
    finally:
        if old is None:
            os.environ.pop('POLARI_DATA_DIR', None)
        else:
            os.environ['POLARI_DATA_DIR'] = old


def main():
    test_gate_semantics()
    test_async_engage()
    test_failed_flush()
    test_stateless()
    test_stale_move_artifacts()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
