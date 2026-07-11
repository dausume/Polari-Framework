"""
@module polariRefs.remote_writes

xsim-4: AUTOMATED remote writes — under a valid fencing token there
are no confirmation prompts inside a running simulation (Dustin
directive 3: "that is the whole point of multiscale simulations").

The shared-DB write rung: direct parameterized UPDATE with the
OWNER's _instance_id, token checked against core FIRST, lock coverage
checked (an undeclared target lazy-escalates a lock — journaled
evidence for the overlap advisor), and EVERY attempt journaled:
applied, refused-stale-token (the zombie), refused-no-agreement,
refused-write-failed. A refused write is an honest error naming the
epochs/knobs — never a silent divergence. No cross-object
transactions in v1 (the journal detects partial-write windows —
documented limitation).
"""

from typing import Dict, Optional

from polariRefs.ref_format import parse_ref
from polariRefs.remote_hydration import peer_agreement_allows
from polariRefs.write_journal import journal_write
from simulationLocks.lease import validate_token
from simulationLocks.object_locks import (
    escalate_lock, held_locks, selector_matches,
)
from simulationLocks.run_context import current_run


def _run_lock_covers(manager, run_id: str, class_name: str,
                     obj_id: str, obj_name: str) -> bool:
    for lock in held_locks(manager):
        if lock.run_id == run_id and lock.class_name == class_name \
                and selector_matches(lock, obj_id=obj_id,
                                     obj_name=obj_name):
            return True
    return False


def write_remote(manager, raw_ref, fields: Dict,
                 run_context: Optional[Dict] = None) -> Dict:
    """Apply `fields` to the object a remote-authority ref names.
    Policy order: token → agreement → lock coverage (escalate if
    undeclared) → mechanical UPDATE → journal. Every exit journals."""
    ok, ref, refusal = parse_ref(raw_ref)
    if not ok:
        return {'ok': False, 'refusal': refusal}
    authority = ref['authority'] or {}
    target = authority.get('instance', '')
    if not target:
        return {'ok': False, 'refusal': {
            'error': 'write_remote is the REMOTE rung — local writes '
                     'go through their own object/CRUDE paths',
            'suggestion': {'knob': 'binding.authority',
                           'action': "carry {'instance': <owner>}"}}}
    run = run_context or current_run() or {}
    run_id = run.get('run_id', '')
    token = int(run.get('lease_token', 0) or 0)
    object_key = ref['id'] or ref['name']
    fenced = validate_token(manager, token)
    if not fenced['ok']:
        journal_write(manager, run_id, f'instance:{target}',
                      ref['className'], object_key,
                      list(fields or {}), token,
                      'refused-stale-token', notes=fenced['error'])
        return {'ok': False, 'refusal': {
            'error': f"remote write fenced out: {fenced['error']}",
            'journaled': True,
            'suggestion': {'knob': 'the simulation queue',
                           'action': 'only the lease-holding run may '
                                     'mutate — zombie workers stop '
                                     'here'}}}
    allowed = peer_agreement_allows(manager, target)
    if not allowed['ok']:
        journal_write(manager, run_id, f'instance:{target}',
                      ref['className'], object_key,
                      list(fields or {}), token,
                      'refused-no-agreement', notes=allowed['error'])
        return {'ok': False, 'refusal': {**allowed, 'journaled': True}}
    escalated = ''
    if not _run_lock_covers(manager, run_id, ref['className'],
                            ref['id'], ref['name']):
        result = escalate_lock(manager, run_id, token,
                               ref['className'], obj_id=ref['id'],
                               obj_name=ref['name'])
        escalated = result.get('lock', '')
    # resolve the concrete row id when the ref names by name
    row_id = ref['id']
    if not row_id:
        probe = manager.db.getAllInTableForInstance(
            ref['className'], target)
        if probe.get('ok'):
            for row in probe['rows']:
                row_fields = dict(zip(probe['columns'], row))
                if str(row_fields.get('name', '')) == ref['name']:
                    row_id = str(row_fields.get('id', ''))
                    break
    if not row_id:
        journal_write(manager, run_id, f'instance:{target}',
                      ref['className'], object_key,
                      list(fields or {}), token,
                      'refused-write-failed',
                      notes='target row not found on the owner')
        return {'ok': False, 'refusal': {
            'error': f"instance '{target}' has no {ref['className']} "
                     f"'{object_key}' to write", 'journaled': True}}
    written = manager.db.updateRowForInstance(
        ref['className'], row_id, fields, target)
    if not written.get('ok'):
        journal_write(manager, run_id, f'instance:{target}',
                      ref['className'], row_id, list(fields or {}),
                      token, 'refused-write-failed',
                      notes=written.get('error', ''))
        return {'ok': False, 'refusal': {
            'error': written.get('error'), 'journaled': True,
            'blockedState': 'run should pause honestly — retry/skip '
                            'knobs (never diverge silently)'}}
    entry = journal_write(manager, run_id, f'instance:{target}',
                          ref['className'], row_id,
                          written['fieldsChanged'], token, 'applied',
                          notes=f'escalated lock {escalated}'
                          if escalated else '')
    return {'ok': True, 'rowsAffected': written['rowsAffected'],
            'fieldsChanged': written['fieldsChanged'],
            'journal': entry.name,
            'escalatedLock': escalated or None,
            'tokenEpoch': token}
