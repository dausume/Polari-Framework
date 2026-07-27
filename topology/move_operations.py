"""
@module topology.move_operations

gm-2-lite (GRACEFUL_MOBILITY_PLAN): MOVES AS DATA.

Every graceful move (gm-1 engine relocation first; the stateful gm-3+
movers later) records a MoveOperation row: kind, subject, from -> to,
the PLANNED step list, then per-step status + receipts + measured
durations as the mover executes. The Topology surface reads these to
paint an in-progress move live, and — same discipline as the mlb
ModuleBootRecord history — prior completed moves of the same kind
yield EXPECTED per-step durations (median). No history = no estimate,
never a guess.

The mover itself runs on the HOST (pol CLI — docker/ssh live there,
not in the backend container); it reports steps through
/api/topology/move-operations. The backend is the ledger + the
broadcast, not the executor.

@consumers
  - topology.topology_api (/api/topology/move-operations*)
  - polariServer.defClassList (auto CRUDE + persistence)
  - topology.selftest_move_operations
"""

import json
import time

from objectTreeDecorators import treeObject, treeObjectInit

MOVE_KINDS = ('engine-relocation', 'keydb-move', 'minio-move',
              'auth-move', 'database-move', 'instance-move')
MOVE_STATUSES = ('planned', 'running', 'verified', 'failed',
                 'abandoned')
STEP_STATUSES = ('pending', 'running', 'done', 'failed', 'skipped')

#: gm-1 engine relocation — the canonical step plan (the mover may
#: mark 'ship-image' skipped when the target already has the image).
ENGINE_MOVE_STEPS = (
    ('check-image', 'image present on target?'),
    ('ship-image', 'docker save | ssh docker load'),
    ('ensure-label', 'target node labeled'),
    ('service-update', 'swarm update: start-first + constraint swap'),
    ('readiness', 'new task answers /capability through the mesh'),
    ('verify', 'capability + placement verified'),
)

#: gm-5 owned-sqlite instance move — QUIESCED, honest downtime
#: (stop-first: a stateful instance must never double-write).
INSTANCE_MOVE_STEPS = (
    ('preflight', 'target reachable + enough free space for the '
                  'data (fail EARLY, not mid-copy)'),
    ('sync-image', 'target runs the SAME image content (same tag != '
                   'same code — swarm ships config, not images)'),
    ('quiesce', 'write gate up + full flush (receipt = in-flight 0)'),
    ('snapshot', 'row counts recorded (the verify baseline)'),
    ('copy-data', 'STAGED: copy into .incoming-<move>/, verify the '
                  'staged file, journal both volumes — live target '
                  'data untouched until the verified swap'),
    ('service-update', 'constraint swap (stop-first — honest '
                       'downtime, no double-writes)'),
    ('boot-ready', 'relocated instance core-ready (/api/health)'),
    ('verify-data', 'row counts + marker row match the snapshot'),
    ('retire', 'journals cleared + .previous removed on target; the '
               'SOURCE volume is never deleted (rollback copy)'),
)


class MoveOperation(treeObject):
    """One graceful move of one subject between machines."""

    @treeObjectInit
    def __init__(
        self,
        # '<subject>@<epoch>' — one row per attempt.
        name: str = '',
        kind: str = 'engine-relocation',
        # What is moving ('msci-engines', 'prf-keycloak'…).
        subject: str = '',
        from_machine: str = '',
        to_machine: str = '',
        status: str = 'planned',
        # JSON list [{key,label,status,started_at,finished_at,
        # duration_s,receipt}] — receipts carry sizes/paths/counts.
        steps_json: str = '[]',
        started_at: float = 0.0,
        finished_at: float = 0.0,
        # Who/what triggered it ('pol allocate --graceful', UI…).
        triggered_by: str = '',
        error: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.kind = kind
        self.subject = subject
        self.from_machine = from_machine
        self.to_machine = to_machine
        self.status = status
        self.steps_json = steps_json
        self.started_at = started_at
        self.finished_at = finished_at
        self.triggered_by = triggered_by
        self.error = error
        self.notes = notes


def _get(row, key, default=None):
    return (row.get(key, default) if isinstance(row, dict)
            else getattr(row, key, default))


def _steps(row):
    raw = _get(row, 'steps_json', '[]') or '[]'
    try:
        steps = raw if isinstance(raw, list) else json.loads(raw)
    except Exception:
        steps = []
    return steps if isinstance(steps, list) else []


def planned_steps(kind):
    """The canonical step plan for a move kind — shown BEFORE anything
    runs (gm-6 discipline: the user sees the plan first)."""
    plans = {'engine-relocation': ENGINE_MOVE_STEPS,
             'instance-move': INSTANCE_MOVE_STEPS}
    return [{'key': k, 'label': label, 'status': 'pending',
             'started_at': None, 'finished_at': None,
             'duration_s': None, 'receipt': ''}
            for k, label in plans.get(kind, ())]


def expected_step_durations(records, kind, subject=None):
    """Median duration per step key from prior VERIFIED moves of this
    kind (same-subject moves preferred). {} when no history — the
    honest 'no estimate'. Skipped steps never enter the median."""
    done = [r for r in records
            if _get(r, 'kind') == kind
            and _get(r, 'status') == 'verified']
    if subject:
        scoped = [r for r in done if _get(r, 'subject') == subject]
        done = scoped or done
    by_key = {}
    for r in done:
        for s in _steps(r):
            if s.get('status') == 'done' \
                    and (s.get('duration_s') or 0) > 0:
                by_key.setdefault(s['key'], []).append(
                    float(s['duration_s']))
    out = {}
    for key, values in by_key.items():
        values.sort()
        mid = len(values) // 2
        out[key] = (values[mid] if len(values) % 2
                    else (values[mid - 1] + values[mid]) / 2.0)
    return out


def move_dict(row, expected=None):
    steps = _steps(row)
    total = sum(s.get('duration_s') or 0 for s in steps
                if s.get('status') == 'done')
    return {
        'name': _get(row, 'name', ''),
        'kind': _get(row, 'kind', ''),
        'subject': _get(row, 'subject', ''),
        'fromMachine': _get(row, 'from_machine', ''),
        'toMachine': _get(row, 'to_machine', ''),
        'status': _get(row, 'status', ''),
        'steps': steps,
        'startedAt': _get(row, 'started_at', 0.0) or None,
        'finishedAt': _get(row, 'finished_at', 0.0) or None,
        'measuredTotalS': round(total, 3),
        'expectedStepDurationsS': expected or {},
        'triggeredBy': _get(row, 'triggered_by', ''),
        'error': _get(row, 'error', ''),
    }


def apply_step_update(row, step_key, status, receipt=None):
    """Mark one step's transition on a MoveOperation row (mutates the
    row's steps_json; caller persists). Durations are measured here so
    every mover reports the same way. Returns the updated step dict or
    an honest refusal."""
    if status not in STEP_STATUSES:
        return {'ok': False,
                'refusal': f'unknown step status {status!r}',
                'suggestion': f'one of {STEP_STATUSES}'}
    steps = _steps(row)
    target = None
    for s in steps:
        if s.get('key') == step_key:
            target = s
            break
    if target is None:
        return {'ok': False,
                'refusal': f'step {step_key!r} is not in this '
                           "move's plan",
                'suggestion': 'steps are declared at creation '
                              '(planned_steps)'}
    now = time.time()
    target['status'] = status
    if status == 'running' and not target.get('started_at'):
        target['started_at'] = now
    if status in ('done', 'failed', 'skipped'):
        target['finished_at'] = now
        if target.get('started_at') and status == 'done':
            target['duration_s'] = round(now - target['started_at'], 3)
    if receipt is not None:
        target['receipt'] = str(receipt)
    row.steps_json = json.dumps(steps)
    return {'ok': True, 'step': dict(target)}
