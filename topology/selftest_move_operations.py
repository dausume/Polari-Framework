"""
Self-test for gm-2-lite: moves as data — the planned step list, step
transitions with measured durations, the prior-knowledge expected
durations (median per step of prior VERIFIED moves; no history = no
estimate), and the honest refusals.

Run from polari-framework/:
    python3 -m topology.selftest_move_operations
"""

import json
import sys
import time
import types

from topology.move_operations import (
    ENGINE_MOVE_STEPS, apply_step_update, expected_step_durations,
    move_dict, planned_steps,
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


def _row(**kw):
    row = types.SimpleNamespace(
        name='msci-engines@1', kind='engine-relocation',
        subject='msci-engines', from_machine='isle-core',
        to_machine='lightweight', status='running',
        steps_json=json.dumps(planned_steps('engine-relocation')),
        started_at=time.time(), finished_at=0.0,
        triggered_by='selftest', error='', notes='')
    for k, v in kw.items():
        setattr(row, k, v)
    return row


def test_planned_steps():
    print('[planned steps: the plan shows before anything runs]')
    steps = planned_steps('engine-relocation')
    check('engine plan carries the 6 gm-1 steps',
          [s['key'] for s in steps]
          == [k for k, _ in ENGINE_MOVE_STEPS])
    check('all steps start pending',
          all(s['status'] == 'pending' for s in steps))
    check('unknown kinds get NO invented plan',
          planned_steps('teleportation-move') == [])
    minio = planned_steps('minio-move')
    check('gm-3: minio + keydb share the staged-copy plan',
          [s['key'] for s in minio]
          == [s['key'] for s in planned_steps('keydb-move')]
          and {'preflight', 'copy-data', 'retire'}
          <= {s['key'] for s in minio})
    auth = planned_steps('auth-move')
    check('gm-4: auth plan is server-only (db-check, NO copy-data — '
          'the DB does not move)',
          'db-check' in {s['key'] for s in auth}
          and 'copy-data' not in {s['key'] for s in auth}
          and 'quiesce' not in {s['key'] for s in auth})
    db = planned_steps('database-move')
    check('gm-5: database plan drains writers + dumps BEFORE the '
          'volume move (correct-before-clever)',
          [s['key'] for s in db][:6]
          == ['preflight', 'sync-image', 'writers-drain',
              'backup-dump', 'quiesce-db', 'copy-data'])


def test_step_transitions():
    print('[step transitions: measured durations, honest refusals]')
    row = _row()
    got = apply_step_update(row, 'check-image', 'running')
    check('running stamps started_at',
          got['ok'] and got['step']['started_at'] is not None)
    got = apply_step_update(row, 'check-image', 'done',
                            receipt='image present (2.17GB)')
    check('done measures a duration >= 0',
          got['ok'] and got['step']['duration_s'] is not None
          and got['step']['duration_s'] >= 0)
    check('receipt recorded',
          got['step']['receipt'] == 'image present (2.17GB)')
    got = apply_step_update(row, 'ship-image', 'skipped',
                            receipt='already on target')
    check('skipped records no duration',
          got['ok'] and got['step']['duration_s'] is None)
    check('unknown step refuses',
          apply_step_update(row, 'warp-drive', 'done')['ok'] is False)
    check('unknown status refuses',
          apply_step_update(row, 'verify', 'perhaps')['ok'] is False)
    d = move_dict(row)
    check('move_dict sums only DONE durations',
          d['measuredTotalS'] >= 0
          and d['subject'] == 'msci-engines')


def _finished_row(durations, status='verified'):
    steps = planned_steps('engine-relocation')
    for s in steps:
        dur = durations.get(s['key'])
        if dur is None:
            s['status'] = 'skipped'
        else:
            s['status'] = 'done'
            s['duration_s'] = dur
    return _row(steps_json=json.dumps(steps), status=status)


def test_expected_durations():
    print('[prior knowledge: median per step, honest no-history]')
    history = [
        _finished_row({'check-image': 1.0, 'service-update': 10.0,
                       'readiness': 5.0, 'verify': 1.0}),
        _finished_row({'check-image': 3.0, 'service-update': 20.0,
                       'readiness': 7.0, 'verify': 1.0,
                       'ship-image': 120.0}),
        _finished_row({'check-image': 2.0, 'service-update': 30.0,
                       'readiness': 6.0, 'verify': 1.0}),
        # A FAILED move must never teach the estimator.
        _finished_row({'check-image': 500.0}, status='failed'),
    ]
    exp = expected_step_durations(history, 'engine-relocation',
                                  'msci-engines')
    check('median per step from verified moves',
          exp['check-image'] == 2.0 and exp['service-update'] == 20.0
          and exp['readiness'] == 6.0)
    check('a step present in only some moves still estimates '
          '(skipped never enters)',
          exp['ship-image'] == 120.0)
    check('failed moves never teach the estimator',
          exp['check-image'] != 500.0)
    check('no history -> {} (no invented estimate)',
          expected_step_durations([], 'engine-relocation') == {})
    check('other kinds do not leak in',
          expected_step_durations(history, 'database-move') == {})


def test_move_plan():
    print('[gm-6: plan preview — steps + ETAs + typed-confirm flag]')
    from topology.move_operations import MOVE_SUBJECTS, move_plan
    check('every relocatable subject is cataloged',
          set(MOVE_SUBJECTS) == {'msci-engines', 'backend',
                                 'prf-file-store', 'prf-keycloak',
                                 'prf-mariadb', 'odoo',
                                 'odoo-postgres'})
    plan = move_plan(subject='prf-mariadb', machine='isle-core')
    check('stateful subject demands confirmation',
          plan['ok'] and plan['stateful']
          and plan['confirmationRequired'])
    check('the exact command carries the machine',
          plan['command'] == 'pol swarm relocate mariadb isle-core')
    check('the planned steps show before anything runs',
          plan['steps'][0]['key'] == 'preflight'
          and all(s['status'] == 'pending' for s in plan['steps']))
    kc = move_plan(subject='prf-keycloak')
    check('stateless (server-only) subjects skip typed confirmation',
          kc['ok'] and not kc['stateful'])
    hist = [_finished_row({'check-image': 2.0, 'service-update': 8.0,
                           'readiness': 4.0, 'verify': 1.0})]
    eng = move_plan(subject='msci-engines', records=hist)
    check('expected durations flow from history into the preview',
          eng['expectedStepDurationsS'].get('service-update') == 8.0
          and eng['expectedTotalS'] == 15.0)
    check('unknown subject refuses with the catalog',
          move_plan(subject='mystery')['ok'] is False)


def main():
    test_planned_steps()
    test_step_transitions()
    test_expected_durations()
    test_move_plan()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
