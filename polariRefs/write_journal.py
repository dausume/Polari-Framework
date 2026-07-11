"""
@module polariRefs.write_journal

The write journal (xsim-4, design pillar 4): EVERY remote mutation —
applied OR refused — appends a WriteJournalEntry. The audit trail that
makes "each simulation handles its data intelligently" verifiable:
post-run review, external-mutation detection, and (later, explicit
knob) rollback all read this ledger. Refused zombie writes are
journaled too — a fenced-out worker leaves evidence, never silence.
"""

from datetime import datetime, timezone
from typing import Dict, List

from objectTreeDecorators import treeObject, treeObjectInit


class WriteJournalEntry(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', run_id: str = '',
                 authority: str = '', class_name: str = '',
                 object_id: str = '', fields_changed_json: str = '[]',
                 token_epoch: int = 0, at: str = '',
                 outcome: str = 'applied', notes: str = '',
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


def journal_write(manager, run_id: str, authority: str,
                  class_name: str, object_id: str, fields: List[str],
                  token_epoch: int, outcome: str,
                  notes: str = '') -> WriteJournalEntry:
    import json
    entry = WriteJournalEntry(
        name=f'wj-{run_id}-{class_name}-{object_id}-'
             f'{datetime.now(timezone.utc).strftime("%H%M%S%f")}',
        run_id=run_id, authority=authority, class_name=class_name,
        object_id=object_id,
        fields_changed_json=json.dumps(sorted(fields or [])),
        token_epoch=int(token_epoch or 0),
        at=datetime.now(timezone.utc).isoformat(), outcome=outcome,
        notes=notes, manager=manager)
    try:
        manager.db.saveInstanceInDB(entry)
    except Exception:
        pass
    return entry


def journal_rows(manager, run_filter: str = '') -> List[Dict]:
    table = (getattr(manager, 'objectTables', None) or {}).get(
        'WriteJournalEntry', {}) or {}
    rows = table.values() if isinstance(table, dict) else table
    return [{'name': e.name, 'runId': e.run_id,
             'authority': e.authority, 'className': e.class_name,
             'objectId': e.object_id,
             'fieldsChanged': e.fields_changed_json,
             'tokenEpoch': e.token_epoch, 'at': e.at,
             'outcome': e.outcome, 'notes': e.notes}
            for e in sorted(rows, key=lambda e: e.at or '')
            if not run_filter or e.run_id == run_filter]
