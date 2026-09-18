"""
@module polariRefs.write_journal

The write journal (xsim-4, design pillar 4): EVERY remote mutation —
applied OR refused — appends a WriteJournalEntry. The audit trail that
makes "each simulation handles its data intelligently" verifiable:
post-run review, external-mutation detection, and (later, explicit
knob) rollback all read this ledger. Refused zombie writes are
journaled too — a fenced-out worker leaves evidence, never silence.

ct-1 GENERALISES it into **Ledger B, the effect journal**
(CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §2): the same row now carries
`trace_id`, `cause_ref`, `verb`, `origin` (local | remote), `actor` and
`target`, so a LOCAL write recorded under an armed `TraceTarget` lands
here beside the remote ones. Every existing field is kept and every
existing caller is unchanged — a caller that says nothing about origin
is a remote write, which is what all of them are.

  * `origin='remote'` — a cross-instance write (xsim-4, unchanged).
  * `origin='local'`  — this instance's own create/update/delete,
    written ONLY while a `TraceTarget` is armed, and only in dev
    posture. `security.custom.security_trace.record_effect` is the one
    caller; the anonymised-class rule (design §5) is applied there,
    before the row is built.

The journal is a RING (`POLARI_TRACE_JOURNAL_ROWS`, default 20 000):
`prune_journal` drops the oldest rows by `at` once the table is over the
ceiling, so evidence for the current question cannot grow without bound.
"""

import os
from datetime import datetime, timezone
from typing import Dict, List

from objectTreeDecorators import treeObject, treeObjectInit

#: the ring ceiling (design §2). 0 or a bad value = the default.
JOURNAL_ROWS_ENV = 'POLARI_TRACE_JOURNAL_ROWS'
DEFAULT_JOURNAL_ROWS = 20000

#: where a write came from
ORIGINS = ('local', 'remote')


class WriteJournalEntry(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', run_id: str = '',
                 authority: str = '', class_name: str = '',
                 object_id: str = '', fields_changed_json: str = '[]',
                 token_epoch: int = 0, at: str = '',
                 outcome: str = 'applied', notes: str = '',
                 trace_id: str = '', cause_ref: str = '', verb: str = '',
                 origin: str = 'remote', actor: str = '', target: str = '',
                 manager=None):
        self.name = name
        self.run_id = run_id
        self.authority = authority          # 'instance:b'
        self.class_name = class_name
        self.object_id = object_id
        self.fields_changed_json = fields_changed_json
        self.token_epoch = token_epoch
        self.at = at
        # applied | refused-stale-token | refused-no-agreement |
        # refused-write-failed
        self.outcome = outcome
        self.notes = notes
        # ---- ct-1: the effect journal's columns (design §2) ----
        self.trace_id = trace_id            # the chain this write belongs to ('' outside dev posture)
        self.cause_ref = cause_ref          # the door the chain started at: 'PUT /api/X/{id}', 'trigger:daily'
        self.verb = verb                    # create | update | delete (a remote write leaves it '')
        self.origin = origin                # local | remote
        self.actor = actor                  # the causing person's Keycloak `sub` ALONE (D18-1), '' when nobody
        self.target = target                # the TraceTarget (class) armed when this row was written


def journal_rows_limit() -> int:
    raw = (os.environ.get(JOURNAL_ROWS_ENV) or '').strip()
    try:
        n = int(raw)
        return n if n > 0 else DEFAULT_JOURNAL_ROWS
    except ValueError:
        return DEFAULT_JOURNAL_ROWS


def journal_fields(run_id: str, authority: str, class_name: str,
                   object_id: str, fields: List[str], token_epoch: int,
                   outcome: str, notes: str = '', verb: str = '',
                   origin: str = 'remote', actor: str = '', target: str = '',
                   trace_id=None, cause_ref=None) -> Dict:
    """The row's fields, built once so the remote path and the effect
    journal cannot drift apart. `trace_id`/`cause_ref` default to the
    CURRENT cause (ct-0) — '' when there is none, so a row always has
    the columns and never a None."""
    import json
    if trace_id is None or cause_ref is None:
        try:
            from accessControl.cause_context import current_cause, trace_ids
            cause = current_cause() or {}
            ids = trace_ids()
        except Exception:               # noqa: BLE001 — a journal must never fail on bookkeeping
            cause, ids = {}, {'trace_id': ''}
        if trace_id is None:
            trace_id = ids.get('trace_id', '')
        if cause_ref is None:
            cause_ref = str(cause.get('entry_ref') or '')[:400]
    return {
        'name': f'wj-{run_id}-{class_name}-{object_id}-'
                f'{datetime.now(timezone.utc).strftime("%H%M%S%f")}',
        'run_id': run_id, 'authority': authority, 'class_name': class_name,
        'object_id': object_id,
        'fields_changed_json': json.dumps(sorted(fields or [])),
        'token_epoch': int(token_epoch or 0),
        'at': datetime.now(timezone.utc).isoformat(), 'outcome': outcome,
        'notes': notes,
        'trace_id': trace_id or '', 'cause_ref': cause_ref or '',
        'verb': verb, 'origin': origin if origin in ORIGINS else 'remote',
        'actor': actor, 'target': target,
    }


def journal_write(manager, run_id: str, authority: str,
                  class_name: str, object_id: str, fields: List[str],
                  token_epoch: int, outcome: str,
                  notes: str = '', verb: str = '', origin: str = 'remote',
                  actor: str = '', target: str = '',
                  trace_id=None, cause_ref=None) -> WriteJournalEntry:
    entry = WriteJournalEntry(
        manager=manager,
        **journal_fields(run_id, authority, class_name, object_id, fields,
                         token_epoch, outcome, notes=notes, verb=verb,
                         origin=origin, actor=actor, target=target,
                         trace_id=trace_id, cause_ref=cause_ref))
    try:
        manager.db.saveInstanceInDB(entry)
    except Exception:
        pass
    return entry


def prune_journal(manager, limit: int = 0) -> int:
    """Drop the oldest rows by `at` once the table is over the ring
    ceiling. Returns how many were dropped. Never raises: an unprunable
    journal is a big journal, not a broken instance."""
    limit = int(limit or 0) or journal_rows_limit()
    try:
        table = (getattr(manager, 'objectTables', None) or {}).get('WriteJournalEntry', None)
        if not isinstance(table, dict) or len(table) <= limit:
            return 0
        ordered = sorted(table.items(), key=lambda kv: getattr(kv[1], 'at', '') or '')
        drop = len(table) - limit
        for key, _row in ordered[:drop]:
            table.pop(key, None)
            try:
                manager.noteTreeDeletion('WriteJournalEntry', key)
            except Exception:
                pass
        return drop
    except Exception:
        return 0


ROW_KEYS = ('name', 'run_id', 'authority', 'class_name', 'object_id',
            'fields_changed_json', 'token_epoch', 'at', 'outcome', 'notes',
            'trace_id', 'cause_ref', 'verb', 'origin', 'actor', 'target')


def journal_rows(manager, run_filter: str = '', trace_id: str = '',
                 class_name: str = '', origin: str = '') -> List[Dict]:
    table = (getattr(manager, 'objectTables', None) or {}).get(
        'WriteJournalEntry', {}) or {}
    rows = table.values() if isinstance(table, dict) else table
    out = [{'name': e.name, 'runId': e.run_id,
            'authority': e.authority, 'className': e.class_name,
            'objectId': e.object_id,
            'fieldsChanged': e.fields_changed_json,
            'tokenEpoch': e.token_epoch, 'at': e.at,
            'outcome': e.outcome, 'notes': e.notes,
            'traceId': getattr(e, 'trace_id', ''),
            'causeRef': getattr(e, 'cause_ref', ''),
            'verb': getattr(e, 'verb', ''),
            'origin': getattr(e, 'origin', 'remote'),
            'actor': getattr(e, 'actor', ''),
            'target': getattr(e, 'target', '')}
           for e in sorted(rows, key=lambda e: e.at or '')
           if not run_filter or e.run_id == run_filter]
    if trace_id:
        out = [r for r in out if r['traceId'] == trace_id]
    if class_name:
        out = [r for r in out if r['className'] == class_name]
    if origin:
        out = [r for r in out if r['origin'] == origin]
    return out
