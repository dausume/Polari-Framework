"""
@module cmod.cmod_firmware_api

fs-0 (DEMONSTRABLES_PLAN.md §9): FirmwareSolution doors — the model + derivations are pure (`cmod.custom.firmware`);
this API only reads/writes rows and calls them.

GET  /api/firmware/solutions                 every FirmwareSolution row
GET  /api/firmware/solutions/{name}           the row + its DERIVED schedule, register assignments, validation, builds
POST /api/firmware/solutions/{name}/build     cmod-glue render+build (reused, `cmod.custom.firmware.build`) — refuses 422
                                               if validate() fails first
POST /api/firmware/solutions/{name}/run       body {"mode": "digital-twin"|"hardware"} — validate -> build's proof /
                                               the detected board route (`cmod.custom.firmware.run`)
POST /api/firmware/solutions/{name}/assign    body {"task":..,"port":..,"lives_on":".."} — the door a pin-map drag
                                               (fs-1) will call; fs-0 just upserts the RegisterAssignment row
"""
import inspect
import json

from objectTreeDecorators import treeObject, treeObjectInit


class FirmwareAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/firmware/solutions', self, suffix='solutions')
            add('/api/firmware/solutions/{name}', self, suffix='solution_one')
            add('/api/firmware/solutions/{name}/build', self, suffix='build')
            add('/api/firmware/solutions/{name}/run', self, suffix='run')
            add('/api/firmware/solutions/{name}/assign', self, suffix='assign')

    def _rows(self, cls):
        return list(((self.manager.objectTables or {}).get(cls, {}) or {}).values()) if self.manager is not None else []

    @staticmethod
    def _d(row):
        keys = [k for k in inspect.signature(type(row).__init__).parameters if k not in ('self', 'manager')]
        return {k: getattr(row, k, None) for k in keys}

    def _solution(self, name, response):
        import falcon
        hit = [r for r in self._rows('FirmwareSolution') if r.name == name]
        if not hit:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no FirmwareSolution %r (GET /api/firmware/solutions lists them)' % name}
        return hit[0] if hit else None

    def on_get_solutions(self, request, response):
        response.media = {'ok': True, 'solutions': [self._d(r) for r in sorted(self._rows('FirmwareSolution'), key=lambda r: r.name)]}

    def on_get_solution_one(self, request, response, name):
        s = self._solution(name, response)
        if s is None:
            return
        from cmod.custom import firmware as FW
        ok, why, details = FW.validate(s, manager=self.manager)
        sched = sorted((r for r in self._rows('ScheduleSlot') if r.solution == name), key=lambda r: (r.lane, r.order))
        asg = sorted((r for r in self._rows('RegisterAssignment') if r.solution == name), key=lambda r: (r.target_kind, r.task))
        builds = sorted((r for r in self._rows('CGlueBuild') if r.graph == s.graph), key=lambda r: r.name)
        response.media = {'ok': True, 'solution': self._d(s), 'schedule': [self._d(r) for r in sched],
                          'assignments': [self._d(r) for r in asg] or details.get('assignments', []),
                          'validation': {'ok': ok, 'why': why}, 'builds': [self._d(r) for r in builds]}

    def on_post_build(self, request, response, name):
        import falcon
        from cmod.custom.glue import GlueRefused
        s = self._solution(name, response)
        if s is None:
            return
        from cmod.custom import firmware as FW
        try:
            rec = FW.build(s, manager=self.manager)
        except GlueRefused as e:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': str(e)}
            return
        b = rec['build']
        response.media = {'ok': True, 'solution': name, 'built_by': b['built_by'], 'hex_sha256': b['hex_sha256'],
                          'size_text': b['size_text'], 'size_data': b['size_data'], 'size_bss': b['size_bss']}

    def on_post_run(self, request, response, name):
        s = self._solution(name, response)
        if s is None:
            return
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:  # noqa: BLE001
            body = {}
        from cmod.custom import firmware as FW
        r = FW.run(s, body.get('mode', 'digital-twin'), manager=self.manager)
        response.media = dict(r, solution=name)

    def on_post_assign(self, request, response, name):
        import falcon
        s = self._solution(name, response)
        if s is None:
            return
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:  # noqa: BLE001
            body = {}
        task, port, lives_on = body.get('task', ''), body.get('port', ''), body.get('lives_on', '')
        if not task or not lives_on:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': "'task' and 'lives_on' are required (the pin map's drag, fs-1)"}
            return
        row_name = '%s:%s%s' % (name, task, ('.' + port) if port else '')
        existing = next((r for r in self._rows('RegisterAssignment') if r.name == row_name), None)
        status = 'unbound' if lives_on in ('', 'unbound') else 'bound'
        if existing is not None and self.manager is not None:
            existing.lives_on, existing.status, existing.provenance = lives_on, status, 'canvas'
            self.manager.saveObjToDB(existing) if hasattr(self.manager, 'saveObjToDB') else None
            response.media = {'ok': True, 'assignment': self._d(existing), 'how': 'updated in place (canvas-set, fs-1\'s drag)'}
            return
        response.media = {'ok': False, 'error': 'no existing RegisterAssignment row %r to assign onto (fs-0 does not create '
                                                'new targets — only (fs-1\'s drag over) a derived one, task %r port %r)'
                                                % (row_name, task, port)}
