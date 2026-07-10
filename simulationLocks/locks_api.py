"""
@cross-cutting
@module simulationLocks.locks_api

HTTP surface for the single-writer machinery (xsim-2):

  GET  /api/simulation-locks/lease            lease status (+ breakable)
  POST /api/simulation-locks/lease/break      {by, reason, force} —
                                              evented break knob
  GET  /api/simulation-locks/locks?run=       lock rows (working sets,
                                              quarantined orphans)
  POST /api/simulation-locks/locks/{name}/break  {by, reason} — admin
                                              single-lock break, evented
  GET  /api/simulation-queue                  queue (persisted rows)
  POST /api/simulation-queue/{name}/cancel    cancel queued OR running
  POST /api/simulation-queue/{name}/promote   priority knob
  POST /api/simulation-queue/pump             start+run the head (the
                                              event-driven runner)

@consumers
  - frontend queue page (xsim frontend tail: lock chips + queue tab)
@see /CROSS_INSTANCE_SIM_PLAN.md
"""

import falcon

from objectTreeDecorators import treeObject, treeObjectInit
from simulationLocks.lease import break_lease, lease_status
from simulationLocks.object_locks import break_lock
from simulationLocks.runner import pump_queue
from simulationLocks.sim_queue import (
    cancel_entry, promote_entry, queue_list,
)


class SimulationLocksAPI(treeObject):
    """Lease + object locks + queue endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/simulation-locks'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/simulation-locks/lease', self, suffix='lease')
            add('/api/simulation-locks/lease/break', self,
                suffix='lease_break')
            add('/api/simulation-locks/locks', self, suffix='locks')
            add('/api/simulation-locks/locks/{lock_name}/break', self,
                suffix='lock_break')
            add('/api/simulation-queue', self, suffix='queue')
            add('/api/simulation-queue/pump', self, suffix='pump')
            add('/api/simulation-queue/{entry_name}/cancel', self,
                suffix='cancel')
            add('/api/simulation-queue/{entry_name}/promote', self,
                suffix='promote')

    def _media(self, request):
        try:
            return request.get_media() or {}
        except Exception:
            return {}

    def on_get_lease(self, request, response):
        response.media = {'ok': True, **lease_status(self.manager)}

    def on_post_lease_break(self, request, response):
        body = self._media(request)
        result = break_lease(self.manager,
                             str(body.get('by', 'api') or 'api'),
                             str(body.get('reason', '') or ''),
                             force=bool(body.get('force', False)))
        response.status = falcon.HTTP_200 if result['ok'] \
            else falcon.HTTP_409
        response.media = result

    def on_get_locks(self, request, response):
        run_filter = request.get_param('run') or ''
        table = (getattr(self.manager, 'objectTables', None) or {}).get(
            'ObjectLockEntry', {}) or {}
        rows = table.values() if isinstance(table, dict) else table
        response.media = {'ok': True, 'locks': [
            {'name': lock.name, 'runId': lock.run_id,
             'className': lock.class_name,
             'selectorKind': lock.selector_kind,
             'selectorValue': lock.selector_value, 'tag': lock.tag,
             'status': lock.status, 'tokenEpoch': lock.token_epoch,
             'createdAt': lock.created_at, 'notes': lock.notes}
            for lock in rows
            if not run_filter or lock.run_id == run_filter]}

    def on_post_lock_break(self, request, response, lock_name):
        body = self._media(request)
        result = break_lock(self.manager, lock_name,
                            str(body.get('by', 'api') or 'api'),
                            str(body.get('reason', '') or ''))
        response.status = falcon.HTTP_200 if result['ok'] \
            else falcon.HTTP_404
        response.media = result

    def on_get_queue(self, request, response):
        response.media = {'ok': True,
                          'lease': lease_status(self.manager),
                          'entries': queue_list(self.manager)}

    def on_post_pump(self, request, response):
        response.media = pump_queue(self.manager)

    def on_post_cancel(self, request, response, entry_name):
        body = self._media(request)
        result = cancel_entry(self.manager, entry_name,
                              by=str(body.get('by', 'api') or 'api'))
        response.status = falcon.HTTP_200 if result['ok'] \
            else falcon.HTTP_404
        response.media = result

    def on_post_promote(self, request, response, entry_name):
        result = promote_entry(self.manager, entry_name)
        response.status = falcon.HTTP_200 if result['ok'] \
            else falcon.HTTP_404
        response.media = result
