"""
@module polariApiServer.quiesce

gm-2 (GRACEFUL_MOBILITY_PLAN): the QUIESCE seam — the enforceable
"no active actions between backends, no data loss" gate every
stateful move calls before touching data.

POST /api/quiesce            engage: the write gate goes up FIRST
                             (mutating requests 423 immediately),
                             then the whole object tree flushes to
                             the DB (persistTree), then the in-flight
                             report (leases + journal) — by
                             construction nothing can mutate after
                             the receipt returns.
GET  /api/quiesce/status     the current state + receipt.
POST /api/quiesce/release    the gate comes down (a mover that moved
                             the instance never calls this — the NEW
                             instance boots unquiesced; release is
                             for aborted moves).

The gate is a WRITE gate: GET/HEAD/OPTIONS flow freely (reads stay
honest during a move), mutations get 423 Locked with the move name.
The quiesce/health/status/move-operation surfaces stay open — move
receipts MUST flow while quiesced.

State is in-process (deliberate: a restarted/relocated instance must
never come up frozen by a stale flag — the plan's cutover semantics).

@consumers
  - polariApiServer.polariServer (middleware + endpoint registration)
  - pol CLI stateful movers (gm-3..5)
  - polariApiServer.selftest_quiesce
"""

import threading
import time

import falcon

_MUTATING = ('POST', 'PUT', 'PATCH', 'DELETE')

#: Path prefixes that stay open while quiesced (receipts + honesty).
OPEN_PREFIXES = (
    '/api/quiesce',
    '/api/health',
    '/api/modules/status',
    '/api/topology/move-operations',
    '/api/topology/providers/reprobe',
)


class QuiesceState:
    """In-process quiesce truth. Thread-safe."""

    def __init__(self):
        self._lock = threading.Lock()
        self.engaged = False
        self.reason = ''
        self.move_name = ''
        self.engaged_at = None
        self.receipt = {}

    def engage(self, reason, move_name):
        with self._lock:
            self.engaged = True
            self.reason = reason
            self.move_name = move_name
            self.engaged_at = time.time()
            self.receipt = {}

    def release(self):
        with self._lock:
            was = self.engaged
            self.engaged = False
            self.reason = ''
            self.move_name = ''
            self.engaged_at = None
            self.receipt = {}
            return was

    def snapshot(self):
        with self._lock:
            return {
                'quiesced': self.engaged,
                'reason': self.reason,
                'moveName': self.move_name,
                'engagedAt': self.engaged_at,
                'receipt': dict(self.receipt),
            }


class QuiesceMiddleware:
    """423-Locked for mutations while quiesced. Reads always flow."""

    def __init__(self, state):
        self._state = state

    def process_request(self, req, resp):
        if not self._state.engaged:
            return
        if req.method not in _MUTATING:
            return
        path = req.path or ''
        if any(path.startswith(p) for p in OPEN_PREFIXES):
            return
        snap = self._state.snapshot()
        raise falcon.HTTPLocked(
            title='instance quiesced',
            description=(
                'mutations are gated for a graceful move'
                + (f" ({snap['moveName']})" if snap['moveName']
                   else '')
                + ' — reads still answer; retry after the move'),
        )


class QuiesceEndpoint:
    """POST /api/quiesce (engage) + GET /api/quiesce/status +
    POST /api/quiesce/release."""

    def __init__(self, polServer, state):
        self._polServer = polServer
        self._state = state
        add = polServer.falconServer.add_route
        add('/api/quiesce', self)
        add('/api/quiesce/status', self, suffix='status')
        add('/api/quiesce/release', self, suffix='release')

    def _counts(self):
        tables = getattr(self._polServer.manager, 'objectTables',
                         {}) or {}
        return {
            'activeLeases': len(tables.get('MutationLease', {}) or {}),
            'journalEntries': len(tables.get('WriteJournalEntry', {})
                                  or {}),
        }

    def _run_flush(self):
        """The flush body — gate is ALREADY up when this runs. Writes
        live per-class progress into the receipt (mlb-5b: the flush
        is observable piece by piece, module-ordered, one transaction
        per object type), then the final report. A failed flush
        leaves the gate UP with the error as the receipt."""
        state = self._state
        t0 = time.time()

        def progress(step):
            state.receipt.update({
                'phase': 'flushing',
                'currentModule': step['module'],
                'currentClass': step['className'],
                'classesDone': step['classesDone'],
                'classesTotal': step['classesTotal'],
                'rowsDone': step['rowsDone'],
                'elapsedSeconds': round(time.time() - t0, 1),
            })

        flush = {'persisted': False, 'flushSeconds': None,
                 'error': ''}
        try:
            manager = self._polServer.manager
            if getattr(manager, 'db', None) is not None:
                manager.persistTree(progress=progress)
                flush['persisted'] = True
            else:
                flush['error'] = 'no DB on this instance — nothing ' \
                                 'to flush (stateless)'
        except Exception as exc:
            flush['error'] = f'{type(exc).__name__}: {exc}'
        flush['flushSeconds'] = round(time.time() - t0, 3)
        ok = bool(flush['persisted']) or 'stateless' in flush['error']
        state.receipt.update({
            **flush, **self._counts(), 'phase': 'done' if ok
            else 'flush-failed',
            'inFlight': 0 if ok else None})

    def on_post(self, request, response):
        """Engage. Body: {reason?, moveName?, wait?}. The gate goes
        up IMMEDIATELY; the flush runs in a background thread and
        streams per-class progress into /api/quiesce/status (a flush
        can take minutes — one long POST outlives proxy timeouts,
        measured). wait=true runs the flush inline (small instances,
        selftests)."""
        try:
            import json
            body = json.load(request.bounded_stream) or {}
        except Exception:
            body = {}
        if self._state.engaged:
            response.status = '409 Conflict'
            response.media = {
                'ok': False,
                'refusal': 'already quiesced',
                **self._state.snapshot(),
                'suggestion': 'release first, or check moveName — '
                              'two moves must not interleave'}
            return
        self._state.engage(body.get('reason', '') or 'graceful move',
                           body.get('moveName', '') or '')
        self._state.receipt.update({'phase': 'flushing'})
        if body.get('wait'):
            self._run_flush()
            snap = self._state.snapshot()
            ok = bool(snap['receipt'].get('persisted')) \
                or 'stateless' in (snap['receipt'].get('error') or '')
            if not ok:
                response.status = '500 Internal Server Error'
            response.media = {'ok': ok, **snap}
            return
        threading.Thread(target=self._run_flush, daemon=True,
                         name='quiesce-flush').start()
        response.media = {
            'ok': True, 'flushing': True,
            **self._state.snapshot(),
            'note': 'gate is UP; poll /api/quiesce/status until '
                    'receipt.persisted (per-class progress streams '
                    'there)'}

    def on_get_status(self, request, response):
        response.media = {'ok': True, **self._state.snapshot()}

    def on_post_release(self, request, response):
        was = self._state.release()
        response.media = {
            'ok': True, 'released': was,
            'note': ('gate down — mutations flow again' if was
                     else 'was not quiesced (idempotent no-op)')}
