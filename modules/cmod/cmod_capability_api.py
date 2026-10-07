"""
@module cmod.cmod_capability_api

CapabilityDefinition doors (hw priorities P1, AI-Notes/plans/HARDWARE_DEV_PRIORITIES.md §1/§4): the model is pure
(`cmod.custom.capabilities`, `firmwarefaults.custom.acceptance`); this API only reads/writes rows and calls them.

GET  /api/capabilities                   every CapabilityDefinition row, status re-derived from its latest acceptance
                                          ScenarioRun (never hand-set)
GET  /api/capabilities/{name}            the row + tasks grouped by runtime, required targets with their
                                          RegisterAssignment state, the validator's own verdict, last proof
POST /api/capabilities/{name}/prove      body {"mode": "digital-twin"|"hardware"} (default digital-twin) — runs the
                                          capability's acceptance Scenario (firmwarefaults.custom.acceptance.run) and
                                          persists the DERIVED status + last_proof onto the row; refuses 422 when the
                                          validator itself refuses (an unregistered target / a task that does not
                                          exist) or when --hardware finds no board (the readiness reason, named)
"""
import inspect
import json

from objectTreeDecorators import treeObject, treeObjectInit


class CapabilityAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/capabilities', self, suffix='capabilities')
            add('/api/capabilities/{name}', self, suffix='capability_one')
            add('/api/capabilities/{name}/prove', self, suffix='prove')

    def _rows(self, cls):
        return list(((self.manager.objectTables or {}).get(cls, {}) or {}).values()) if self.manager is not None else []

    @staticmethod
    def _d(row):
        keys = [k for k in inspect.signature(type(row).__init__).parameters if k not in ('self', 'manager')]
        return {k: getattr(row, k, None) for k in keys}

    def _capability(self, name, response):
        import falcon
        hit = [r for r in self._rows('CapabilityDefinition') if r.name == name]
        if not hit:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no CapabilityDefinition %r (GET /api/capabilities lists them)' % name}
        return hit[0] if hit else None

    def _summary(self, row):
        from cmod.custom import capabilities as CAP
        cap = self._d(row)
        status, last_proof, why = CAP.derive_status(cap, manager=self.manager)
        if (status, last_proof) != (row.status, row.last_proof) and self.manager is not None:
            row.status, row.last_proof = status, last_proof
            db = getattr(self.manager, 'db', None)
            if db is not None and hasattr(db, 'saveInstanceInDB'):
                db.saveInstanceInDB(row)
        cap['status'], cap['last_proof'] = status, last_proof
        cap['status_why'] = why
        return cap

    def on_get_capabilities(self, request, response):
        response.media = {'ok': True, 'capabilities': [self._summary(r) for r in sorted(self._rows('CapabilityDefinition'), key=lambda r: r.name)]}

    def on_get_capability_one(self, request, response, name):
        row = self._capability(name, response)
        if row is None:
            return
        from cmod.custom import capabilities as CAP
        from cmod.custom import firmware as FW
        cap = self._summary(row)
        ok, why = CAP.validate(cap, manager=self.manager)
        tasks = json.loads(cap.get('tasks_by_runtime_json') or '{}')
        targets = []
        for port_ref in [t.strip() for t in (cap.get('required_targets') or '').split(',') if t.strip()]:
            t_ok, t_why = CAP._target_registered(cap.get('graph', ''), port_ref, manager=self.manager)
            targets.append({'port_ref': port_ref, 'registered': t_ok, 'why': t_why})
        runs = sorted((r for r in self._rows('ScenarioRun') if r.scenario == cap.get('acceptance_scenario')), key=lambda r: r.ran_at)
        response.media = {'ok': True, 'capability': cap, 'tasks_by_runtime': tasks, 'targets': targets,
                          'validation': {'ok': ok, 'why': why}, 'runs': [self._d(r) for r in runs]}

    def on_post_prove(self, request, response, name):
        import falcon
        row = self._capability(name, response)
        if row is None:
            return
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:  # noqa: BLE001
            body = {}
        mode = body.get('mode', 'digital-twin')
        from cmod.custom import capabilities as CAP
        cap = self._d(row)
        ok, why = CAP.validate(cap, manager=self.manager)
        if not ok:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': True, 'error': why}
            return
        from firmwarefaults.custom import acceptance as ACC
        from firmwarefaults.custom.sink import ManagerSink
        sink = ManagerSink(self.manager) if self.manager is not None else None
        out = ACC.run(cap['acceptance_scenario'], mode=mode, manager=self.manager, sink=sink)
        if out['result'].get('route') == 'refused' and not out['result'].get('ok') and mode == 'hardware':
            # hw priorities P2 (not this slice): no board detected — a named refusal, never a fake pass
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': True, 'error': out['verdict_words'] or out['result'].get('why', '')}
            return
        status, last_proof, swhy = CAP.derive_status(cap, manager=self.manager)
        if self.manager is not None:
            row.status, row.last_proof = status, last_proof
            db = getattr(self.manager, 'db', None)
            if db is not None and hasattr(db, 'saveInstanceInDB'):
                db.saveInstanceInDB(row)
        response.media = {'ok': True, 'capability': name, 'mode': mode, 'run': out, 'status': status,
                          'last_proof': last_proof, 'status_why': swhy}
