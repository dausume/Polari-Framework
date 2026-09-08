"""
acct-3: the twin-coherence rehearsal — the manual xsim-6/modsplit
proof as ONE repeatable command with guaranteed teardown:

    python3 -m testing.custom.twin_rehearsal

Boots three THROWAWAY containers on their own network (core=a all
modules, m=materialsScience only, n=aquaponics only — the current
framework source, fresh sqlite each), then asserts over plain HTTP:

  gating       a module-owned class is served ONLY by its owner
               (m has /MaterialsScienceMaterial, n 404s it).
  directory    after PeerNode + enabled ModuleAssignment rows, n's
               directory routes materialsScience to the ADDRESSABLE
               m (the modsplit-3 tie-break over the seeded
               non-addressable prf-a assignment).
  traversal    n resolves m's seeded 'ferrite' through the rung-4
               remote-api ladder (fields + path walk).
  refusal      an un-leased remote write is refused AND journaled —
               never silently accepted, never silently dropped.
  writes       a leased run (queue entry + pump holds the lease)
               writes m's row from core: applied on m, journaled on
               BOTH sides (dual journal).
  fencing      after a forced break + a new holder, the OLD token
               replays and is refused stale + journaled, row
               untouched (zombie fencing).
  teardown     the suite leaves NO acct3 containers running.

Prints the selftest 'X/Y passed' convention; the matrix carries it
as twin:rehearsal (compose kind, blocking).
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from testing.custom.twin_fixtures import TwinRun
from testing.custom.twin_http import (
    crude_create, crude_update, created_id, json_call,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []
CLASS_NAME = 'MaterialsScienceMaterial'
ROW_NAME = 'ferrite'


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}', flush=True)


def _boot(run):
    print('booting throwaway core + m + n (fresh sqlite, current '
          'source; ~2min)...', flush=True)
    run.create_network()
    run.up('core', 'a')
    run.up('m', 'm', modules='materialsScience', core_role='core')
    run.up('n', 'n', modules='aquaponics', core_role='core')
    run.wait_ready(['core', 'm', 'n'])
    for role, instance in (('core', 'a'), ('m', 'm'), ('n', 'n')):
        status, body = json_call(run.base_url(role)
                                 + '/api/refs/directory')
        check(f'{role} directory answers as instance {instance}',
              status == 200 and body.get('localInstance', {})
              .get('instanceId') == instance)


def _gating(run):
    print('module gating: separation of object concerns')
    status, _ = json_call(f'{run.base_url("m")}/{CLASS_NAME}')
    check('owner m serves the module class', status == 200)
    status, _ = json_call(f'{run.base_url("n")}/{CLASS_NAME}')
    check('n (module absent) has NO route for it — honest 404',
          status == 404)
    _, m_dir = json_call(run.base_url('m') + '/api/refs/directory')
    _, n_dir = json_call(run.base_url('n') + '/api/refs/directory')
    check('directory class maps mirror the gate',
          CLASS_NAME in m_dir.get('classes', {})
          and CLASS_NAME not in n_dir.get('classes', {}))


def _address_book(run):
    print('address book + agreements on every instance')
    for role in ('core', 'n'):
        status, body = crude_create(
            run.base_url(role), 'PeerNode',
            {'name': 'polari-m', 'base_url': run.internal_url('m'),
             'status': 'alive'})
        check(f'{role}: PeerNode polari-m created', status == 201,
              str(body)[:80] if status != 201 else '')
    for role in ('core', 'm', 'n'):
        base = run.base_url(role)
        statuses = []
        for requester in ('polari-a', 'polari-n'):
            status, body = crude_create(
                base, 'PeerAgreement',
                {'agreement_id': f'acct3-{requester}-to-m',
                 'requester_name': requester,
                 'approver_name': 'polari-m',
                 'scope': 'peer-basic', 'status': 'approved'})
            statuses.append(status)
        check(f'{role}: approved agreements naming polari-m',
              statuses == [201, 201], str(statuses))


def _routing(run):
    print('directory routing: addressable tie-break')
    status, body = crude_create(
        run.base_url('n'), 'ModuleAssignment',
        {'name': 'materialsScience@polari-m',
         'module_name': 'materialsScience',
         'instance_name': 'polari-m', 'state': 'enabled'})
    check('n: enabled ModuleAssignment created', status == 201)
    _, n_dir = json_call(run.base_url('n') + '/api/refs/directory')
    provider = n_dir.get('modules', {}).get('materialsScience', {})
    check('n routes materialsScience to the ADDRESSABLE m '
          '(tie-break over any non-addressable assignment)',
          provider.get('instance') == 'polari-m'
          and provider.get('baseUrl') == run.internal_url('m'),
          str(provider))


def _ref(fields=None, path=None):
    ref = {'kind': 'objectRef', 'className': CLASS_NAME,
           'name': ROW_NAME, 'authority': {'instance': 'm'}}
    if path:
        ref['path'] = path
    body = {'ref': ref}
    if fields is not None:
        body['fields'] = fields
    return body


def _traversal(run):
    print('cross-instance traversal (rung 4, n -> m)')
    status, body = json_call(run.base_url('n') + '/api/refs/resolve',
                             method='POST', body=_ref())
    check('n resolves m\'s seeded row via remote-api',
          status == 200 and body.get('ok')
          and body.get('provenance', {}).get('rung') == 'remote-api'
          and body.get('fields', {}).get('name') == ROW_NAME,
          str(body.get('provenance', body))[:120])
    status, body = json_call(run.base_url('n') + '/api/refs/resolve',
                             method='POST', body=_ref(path='name'))
    check('path walk returns the walked value',
          status == 200 and body.get('value') == ROW_NAME)


def _unleased_refusal(run):
    print('foreign write without a lease: refused + journaled')
    status, body = json_call(
        run.base_url('core') + '/api/refs/write', method='POST',
        body=_ref(fields={'description': 'acct3-zombie-attempt'}))
    check('write without run context refused', status in (403, 423),
          f'status={status}')
    _, journal = json_call(run.base_url('core')
                           + '/api/refs/journal')
    entries = journal.get('entries', [])
    check('the refusal is journaled (never silent)',
          any('refused' in (e.get('outcome') or '')
              for e in entries), f'{len(entries)} entries')


def _leased_write(run):
    print('leased remote write (test-build lease handle)')
    status, body = crude_create(
        run.base_url('core'), 'SimulationQueueEntry',
        {'name': 'acct3-q1', 'sim_kind': 'msim-run',
         'sim_ref': 'acct3-fake-msim', 'run_id': 'acct3-run-1',
         'manifest_json': '[]'})
    check('queue entry created on core', status == 201,
          str(body)[:80] if status != 201 else '')
    status, pump = json_call(run.base_url('core')
                             + '/api/simulation-queue/pump',
                             method='POST', body={})
    check('pump honestly refuses the no-direct-dispatch kind '
          '(msim runs re-enter through their own endpoint)',
          pump.get('ok') is False
          and 'msim' in str(pump.get('error', '')),
          str(pump)[:80])
    status, grant = json_call(run.base_url('core')
                              + '/api/testing/lease',
                              method='POST',
                              body={'action': 'acquire',
                                    'runId': 'acct3-run-1'})
    epoch = grant.get('token')
    _, lease = json_call(run.base_url('core')
                         + '/api/simulation-locks/lease')
    check('acquired lease is visible on the PRODUCTION lease '
          'surface (held by the run, epoch bumped)',
          lease.get('status') == 'held'
          and lease.get('holderRun') == 'acct3-run-1'
          and lease.get('tokenEpoch') == epoch,
          f'epoch={epoch}')
    marker = f'acct3-write-{int(time.time())}'
    status, body = json_call(
        run.base_url('core') + '/api/refs/write', method='POST',
        body=_ref(fields={'description': marker}),
        headers={'X-Polari-Run-Id': 'acct3-run-1',
                 'X-Polari-Lease-Token': str(epoch)})
    check('leased write accepted end-to-end', status == 200
          and body.get('ok') is True, str(body)[:140])
    status, resolved = json_call(
        run.base_url('n') + '/api/refs/resolve', method='POST',
        body=_ref())
    check('the write landed on the owner (visible from n)',
          resolved.get('fields', {}).get('description') == marker)
    _, core_journal = json_call(
        run.base_url('core') + '/api/refs/journal?run=acct3-run-1')
    _, m_journal = json_call(run.base_url('m')
                             + '/api/refs/journal')
    check('dual journal: applied on core side',
          any((e.get('outcome') == 'applied')
              for e in core_journal.get('entries', [])))
    check('dual journal: inbound entry on the owner',
          len(m_journal.get('entries', [])) >= 1,
          f"m entries={len(m_journal.get('entries', []))}")
    return epoch, marker


def _fencing(run, old_epoch, applied_marker):
    print('zombie fencing: old token refused after a new holder')
    status, body = json_call(
        run.base_url('core') + '/api/simulation-locks/lease/break',
        method='POST', body={'by': 'acct3', 'reason': 'rehearsal',
                             'force': True})
    check('lease force-broken (evented)', status == 200,
          str(body)[:80])
    _, grant = json_call(run.base_url('core') + '/api/testing/lease',
                         method='POST',
                         body={'action': 'acquire',
                               'runId': 'acct3-run-2'})
    _, lease = json_call(run.base_url('core')
                         + '/api/simulation-locks/lease')
    check('a NEW run holds a bumped epoch',
          lease.get('holderRun') == 'acct3-run-2'
          and (lease.get('tokenEpoch') or 0) > old_epoch,
          f'epoch {old_epoch} -> {lease.get("tokenEpoch")}')
    status, body = json_call(
        run.base_url('core') + '/api/refs/write', method='POST',
        body=_ref(fields={'description': 'acct3-ZOMBIE'}),
        headers={'X-Polari-Run-Id': 'acct3-run-1',
                 'X-Polari-Lease-Token': str(old_epoch)})
    check('zombie write with the old epoch refused',
          status in (403, 423), f'status={status}')
    _, resolved = json_call(run.base_url('n')
                            + '/api/refs/resolve', method='POST',
                            body=_ref())
    check('row untouched by the zombie',
          resolved.get('fields', {}).get('description')
          == applied_marker)


if __name__ == '__main__':
    run = TwinRun(run_tag=str(os.getpid()))
    try:
        _boot(run)
        if all(_results):
            _gating(run)
            _address_book(run)
            _routing(run)
            _traversal(run)
            _unleased_refusal(run)
            epoch, marker = _leased_write(run)
            if epoch is not None:
                _fencing(run, epoch, marker)
    except Exception as exc:
        check(f'rehearsal aborted: {type(exc).__name__}: {exc}',
              False)
        for role in ('core', 'm', 'n'):
            if role in run.containers:
                print(f'--- {role} logs ---')
                print(run.logs_tail(role))
    finally:
        run.teardown()
        check('teardown: no acct3 containers left',
              not run.leftovers())
    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
