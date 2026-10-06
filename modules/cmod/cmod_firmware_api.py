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
                                               (fs-1) will call; fs-0 just upserts the RegisterAssignment row;
                                               fs-2a: REFUSES (4xx, named reason) when board.custom.target_compat.
                                               compatible() says no, the pin is power/ground, or it would conflict
                                               with a non-cooperating task; 'undetermined' is allowed, with a warning
GET  /api/firmware/solutions/{name}/tasks/{task}/valid-targets
                                               fs-2a (his ruling 2026-10-06): for every pin of the solution's board,
                                               valid | invalid | undetermined + a one-line reason, whether it is
                                               already registered to another task and whether that cooperates or
                                               conflicts (board.custom.target_compat + cmod.custom.firmware.
                                               valid_targets_for_task)
GET  /api/firmware/solutions/for-installer    {ok, rows:[...]} — fs-1 item 4's FALLBACK: /display/firmware-installer
                                               gets a described table (wiring the live install door into
                                               firmware-installer-panel was judged out of fs-1b's time box) with a
                                               documented `run_command` column per row (`pol firmware run <name>
                                               --mode digital-twin` — the safe, non-flashing default; hardware mode
                                               is a person's own choice, never defaulted to)
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
            add('/api/firmware/solutions/{name}/tasks/{task}/valid-targets', self, suffix='valid_targets')
            add('/api/firmware/solutions/for-installer', self, suffix='for_installer')

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

    def on_get_for_installer(self, request, response):
        """fs-1 item 4's FALLBACK table (/display/firmware-installer): one row per FirmwareSolution with the
        documented `pol firmware run` command alongside — never composed/run here, just shown (same posture as
        firmware-installer-panel's own DRY-RUN argv: the command is text, confirming/running it is a person's
        own CLI act). `{ok, rows}` so class-rows-table's dataPath contract reads it directly (no JSON wall)."""
        from cmod.custom import firmware as FW
        rows = []
        for r in sorted(self._rows('FirmwareSolution'), key=lambda r: r.name):
            ok, why, _ = FW.validate(r, manager=self.manager)
            rows.append({'name': r.name, 'title': getattr(r, 'title', ''), 'graph': getattr(r, 'graph', ''),
                        'board_resolved': getattr(r, 'board_resolved', ''), 'runtime': getattr(r, 'runtime', ''),
                        'validation': 'ok' if ok else 'refused', 'validation_why': why,
                        'task_count': getattr(r, 'task_count', 0),
                        'run_command': 'pol firmware run %s --mode digital-twin' % r.name})
        response.media = {'ok': True, 'rows': rows}

    def on_get_solution_one(self, request, response, name):
        s = self._solution(name, response)
        if s is None:
            return
        from cmod.custom import firmware as FW
        ok, why, details = FW.validate(s, manager=self.manager)
        sched = sorted((r for r in self._rows('ScheduleSlot') if r.solution == name), key=lambda r: (r.lane, r.order))
        asg = sorted((r for r in self._rows('RegisterAssignment') if r.solution == name), key=lambda r: (r.target_kind, r.task))
        builds = sorted((r for r in self._rows('CGlueBuild') if r.graph == s.graph), key=lambda r: r.name)
        assignments = [self._d(r) for r in asg] or details.get('assignments', [])
        # fs-2a (his naming, verbatim): 'Unregistered Tasks' / per-pin 'Registered Tasks'
        response.media = {'ok': True, 'solution': self._d(s), 'schedule': [self._d(r) for r in sched],
                          'assignments': assignments, 'unregistered_tasks': FW.unregistered_tasks(assignments),
                          'registered_tasks': FW.registered_tasks_by_pin(assignments),
                          'validation': {'ok': ok, 'why': why}, 'builds': [self._d(r) for r in builds]}

    def on_get_valid_targets(self, request, response, name, task):
        """fs-2a: GET /api/firmware/solutions/{name}/tasks/{task}/valid-targets — board.custom.target_compat checked
        against EVERY pin of the solution's board for this one task, plus registration/cooperation state."""
        s = self._solution(name, response)
        if s is None:
            return
        from cmod.custom import firmware as FW
        r = FW.valid_targets_for_task(s.graph, name, task, manager=self.manager)
        response.media = dict(r, ok=True, solution=name, task=task)

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
        # fs-2a (his ruling 2026-10-06): an invalid drop is REFUSED — compat says no, the pin is power/ground, or a
        # non-cooperating conflict. 'undetermined' is allowed, with a warning in the response (never silently guessed).
        from cmod.custom import firmware as FW
        drop_ok, drop_status, drop_why = FW.check_drop(s.graph, name, task, lives_on, manager=self.manager)
        if not drop_ok:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': True, 'error': drop_why, 'task': task, 'lives_on': lives_on}
            return
        row_name = '%s:%s%s' % (name, task, ('.' + port) if port else '')
        existing = next((r for r in self._rows('RegisterAssignment') if r.name == row_name), None)
        status = 'unbound' if lives_on in ('', 'unbound') else 'bound'
        if existing is not None and self.manager is not None:
            existing.lives_on, existing.status, existing.provenance = lives_on, status, 'canvas'
            self.manager.saveObjToDB(existing) if hasattr(self.manager, 'saveObjToDB') else None
            resp = {'ok': True, 'assignment': self._d(existing), 'how': 'updated in place (canvas-set, fs-1\'s drag)'}
            if drop_status == 'undetermined':
                resp['warning'] = drop_why
            response.media = resp
            return
        response.media = {'ok': False, 'error': 'no existing RegisterAssignment row %r to assign onto (fs-0 does not create '
                                                'new targets — only (fs-1\'s drag over) a derived one, task %r port %r)'
                                                % (row_name, task, port)}
