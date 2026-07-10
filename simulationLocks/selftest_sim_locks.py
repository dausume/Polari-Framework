"""
Selftest — xsim-2: fencing-token lease + object locks + simulation
queue + the single-writer gate.

Run from polari-framework/:
    python3 -m simulationLocks.selftest_sim_locks

Covers the xsim-2 rows of the edge-case ledger: epoch bump + zombie
refusal, TTL lapse → breakable (evented break, never silent), queue
cancel (queued AND running), restart recovery, non-run write refusal
naming run + queue position, generated-object auto-lock via the
treeObject creation hook, quarantine on failure, selector overlap
(class-wide/range/id), tied children never re-acquiring.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from objectTreeDecorators import treeObject, treeObjectInit
from simulationLocks.gate import simulation_gate
from simulationLocks.lease import (
    LeaseBreakEvent, acquire_lease, break_lease, heartbeat_lease,
    lease_row, lease_status, release_lease, validate_token,
)
from simulationLocks.object_locks import (
    acquire_manifest, break_lock, check_write, escalate_lock,
    lock_generated, release_for_run, selectors_overlap,
)
from simulationLocks.run_context import current_run
from simulationLocks.sim_queue import (
    cancel_entry, finish_run_slot, promote_entry, queue_list,
    queue_position, reconcile_after_restart, request_run_slot,
    waiting_entries,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


class GeneratedThing(treeObject):
    """Stand-in for an object a simulation generates mid-run."""

    @treeObjectInit
    def __init__(self, name: str = '', manager=None):
        self.name = name


def _mgr():
    return SimpleNamespace(objectTables={}, idList=[], db=None,
                           dynamicClasses={}, objectTyping=[])


def _rows(manager, class_name):
    return list((manager.objectTables.get(class_name) or {}).values())


def _age(manager, seconds):
    lease = lease_row(manager)
    lease.heartbeat_at = (datetime.now(timezone.utc)
                          - timedelta(seconds=seconds)).isoformat()


if __name__ == '__main__':
    manager = _mgr()

    print('lease — fencing epochs')
    granted = acquire_lease(manager, 'run-A')
    check('acquire grants epoch 1',
          granted['ok'] and granted['token'] == 1)
    second = acquire_lease(manager, 'run-B')
    check('second acquire refused naming the holder',
          not second['ok'] and 'run-A' in second['error'])
    check('heartbeat with the live token', heartbeat_lease(
        manager, 'run-A', granted['token'])['ok'])
    zombie = validate_token(manager, 0)
    check('zombie epoch refused naming BOTH epochs',
          not zombie['ok'] and 'epoch 0' in zombie['error']
          and 'epoch 1' in zombie['error'])
    live_break = break_lease(manager, 'test', 'still live')
    check('live lease not breakable without force',
          not live_break['ok'] and 'force'
          in live_break['suggestion']['knob'])
    _age(manager, 999)
    check('TTL lapse flags breakable',
          lease_status(manager)['breakable'])
    broke = break_lease(manager, 'queue-head', 'ttl lapsed')
    check('breakable lease breaks + event recorded',
          broke['ok'] and broke['brokenRun'] == 'run-A'
          and any(e.broken_run == 'run-A'
                  for e in _rows(manager, 'LeaseBreakEvent')))
    regrant = acquire_lease(manager, 'run-B')
    check('re-acquire bumps the epoch (zombie fenced out)',
          regrant['ok'] and regrant['token'] == 2
          and not validate_token(manager, 1)['ok'])
    release_lease(manager, 'run-B', regrant['token'])

    print('object locks — selectors + refusals')
    check('class-wide overlaps everything',
          selectors_overlap('class-wide', '', 'id', 'X1'))
    check('disjoint ranges do not overlap',
          not selectors_overlap('range', '{"lo":"a","hi":"f"}',
                                'range', '{"lo":"g","hi":"z"}'))
    check('id vs name cannot prove disjoint (conservative)',
          selectors_overlap('id', 'X1', 'name', 'thing'))
    manifest = [{'className': 'MaterialScaleDefinition',
                 'selector': {'kind': 'name', 'value': 'steel-rod'}},
                {'className': 'SweepClass',
                 'selector': {'kind': 'class-wide', 'value': ''}}]
    locked = acquire_manifest(manager, 'run-C', 3, manifest)
    check('manifest locks acquired (one row per selector)',
          locked['ok'] and len(locked['locks']) == 2)
    clash = acquire_manifest(manager, 'run-D', 4, [
        {'className': 'SweepClass',
         'selector': {'kind': 'id', 'value': 'Z9'}}])
    check('overlapping manifest refused naming the holder',
          not clash['ok'] and 'run-C' in clash['error'])
    refusal = check_write(manager, 'MaterialScaleDefinition',
                          obj_name='steel-rod')
    check('non-run write refused naming the run',
          not refusal['allowed'] and refusal['lockedBy'] == 'run-C')
    check('the locking run itself may write',
          check_write(manager, 'MaterialScaleDefinition',
                      obj_name='steel-rod', run_id='run-C')['allowed'])
    check('unlocked object stays writable',
          check_write(manager, 'MaterialScaleDefinition',
                      obj_name='other-rod')['allowed'])
    lock_generated(manager, 'run-C', 3, 'ResultRow', 'GEN01')
    escalate_lock(manager, 'run-C', 3, 'TouchedClass', obj_id='T1')
    check('escalated lock notes the undeclared touch',
          any(lock.tag == 'escalated' and 'undeclared' in lock.notes
              for lock in _rows(manager, 'ObjectLockEntry')))
    released = release_for_run(manager, 'run-C', 'failed')
    check('failure quarantines generated, releases declared',
          len(released['quarantined']) == 1
          and len(released['released']) == 3)
    orphan = check_write(manager, 'ResultRow', obj_id='GEN01')
    check('quarantined orphan blocks writes naming the cleanup knob',
          not orphan['allowed'] and orphan['quarantined']
          and 'cleanup' in orphan['suggestion']['knob'])
    broke_lock = break_lock(manager, released['quarantined'][0],
                            'admin', 'cleanup decision: keep row')
    check('admin lock break evented',
          broke_lock['ok']
          and len(_rows(manager, 'LockBreakEvent')) == 1)

    print('queue — admission, cancel, promote, restart')
    slot_a = request_run_slot(manager, 'scale', 'sim-A',
                              submitted_by='selftest')
    check('first sim starts (lease + running entry)',
          slot_a['ok'] and slot_a['runContext']['lease_token'] == 3)
    slot_b = request_run_slot(manager, 'scale', 'sim-B',
                              submitted_by='selftest')
    check('second sim queues with an honest position (persisted row)',
          not slot_b['ok'] and slot_b['queued']
          and slot_b['position'] == 1)
    slot_c = request_run_slot(manager, 'model', 'sim-C')
    check('third sim queues behind the second',
          not slot_c['ok'] and slot_c['position'] == 2)
    promoted = promote_entry(manager, slot_c['entry'])
    check('promote moves it to the head',
          promoted['ok']
          and waiting_entries(manager)[0].name == slot_c['entry'])
    cancelled = cancel_entry(manager, slot_c['entry'])
    check('cancel queued entry',
          cancelled['ok']
          and waiting_entries(manager)[0].name == slot_b['entry'])
    finished = finish_run_slot(manager, slot_a['runContext'], 'done')
    check('finish releases lease atomically + suggests the pump',
          finished['ok'] and finished['nextHead'] == slot_b['entry']
          and finished['suggestion']['knob'] == 'pump')
    check('done entry recorded', any(
        e['state'] == 'done' and e['name'] == slot_a['entry']
        for e in queue_list(manager)))
    slot_b2 = request_run_slot(manager, 'scale', 'sim-B2')
    check('after release the head... new submission queues behind '
          'the waiting head (FIFO honesty)',
          not slot_b2['ok'] and slot_b2['position'] == 2)
    retry_b = request_run_slot(manager, 'scale', 'sim-B')
    check('resubmitting the queued head ADOPTS its entry and starts '
          '(retry-as-start, no duplicate)',
          retry_b['ok'] and retry_b['entry'] == slot_b['entry'])
    finish_run_slot(manager, retry_b['runContext'], 'done')
    running = cancel_entry(
        manager,
        next(e.name for e in waiting_entries(manager)))
    check('cancel of the queued head', running['ok'])
    # drain the queue so the next submission is the head
    for entry in list(waiting_entries(manager)):
        cancel_entry(manager, entry.name)
    # restart recovery: fabricate a running entry with a free lease
    slot_d = request_run_slot(manager, 'scale', 'sim-D')
    release_lease(manager, slot_d['runContext']['run_id'],
                  slot_d['runContext']['lease_token'])
    recovered = reconcile_after_restart(manager)
    check('restart reconciliation closes the stale running entry',
          slot_d['entry'] in recovered['closedStale'])

    print('gate — tied children + generated auto-lock + failure')
    with simulation_gate(manager, 'scale', 'outer-sim') as outer:
        check('gate admits and sets the ambient run context',
              outer['ok'] and current_run() is not None
              and current_run()['run_id']
              == outer['runContext']['run_id'])
        thing = GeneratedThing(name='made-mid-run', manager=manager)
        check('object created mid-run is auto-locked to the run',
              any(lock.tag == 'generated'
                  and lock.selector_value == str(thing.id)
                  and lock.run_id == outer['runContext']['run_id']
                  and lock.status == 'held'
                  for lock in _rows(manager, 'ObjectLockEntry')))
        with simulation_gate(manager, 'model', 'child-model') as child:
            check('tied child passes through on the parent token',
                  child['ok'] and child.get('tied')
                  and child['runContext']['lease_token']
                  == outer['runContext']['lease_token'])
        ext = check_write(manager, 'GeneratedThing',
                          obj_id=str(thing.id))
        check('external write to the generated object refused '
              'naming the run',
              not ext['allowed']
              and ext['lockedBy'] == outer['runContext']['run_id'])
    check('gate exit releases the generated lock + ambient context',
          current_run() is None
          and check_write(manager, 'GeneratedThing',
                          obj_id=str(thing.id))['allowed'])
    try:
        with simulation_gate(manager, 'scale', 'failing-sim') as slot:
            failing_ctx = slot['runContext']
            orphan_obj = GeneratedThing(name='orphan', manager=manager)
            raise RuntimeError('sim crashed')
    except RuntimeError:
        pass
    check('crash quarantines the generated object (orphaned-by-run)',
          any(lock.status == 'quarantined'
              and lock.selector_value == str(orphan_obj.id)
              for lock in _rows(manager, 'ObjectLockEntry')))
    check('crashed entry recorded as failed', any(
        e['state'] == 'failed' and e['runId'] == failing_ctx['run_id']
        for e in queue_list(manager)))
    check('lease free after the crash (released atomically)',
          lease_status(manager)['status'] == 'free')
    stub = SimpleNamespace(objectTables={})
    with simulation_gate(stub, 'model', 'unit-test') as slot:
        check('stub manager (no idList) passes ungated, honestly '
              'flagged', slot['ok'] and 'ungated' in slot)

    total, green = len(_results), sum(_results)
    print(f'\n{green}/{total} checks green')
    raise SystemExit(0 if green == total else 1)
