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

fs-2d (his ask, verbatim: "we should already have a way of describing and defining the tasks in C using no-code, so
we will want our tasks to be linked to their no-code solutions that compose them as well"): every `schedule` and
`assignments` row GET /api/firmware/solutions/{name} returns now carries `composed_by` — {graph, node, canvas_route,
solution, capabilities} (`_composed_by`, below) — the REVERSE link from a task to where it is composed: the CGraph +
CGraphNode it is (task == the node's own `instance`), the /display/c-canvas route that opens straight at that node,
any HardwareSolution whose own graph this is, and which Capability names it. The forward half (a c-canvas node
knowing its own firmware wiring) is GET /api/cmod/graphs/{graph}'s per-node `firmware` field (cmod_api.CModAPI).
What "defining tasks in C using no-code" IS today, named plainly (no cmod-2 built this session): a task's C BODY is
hand-written (cmod.custom.ingest parses it into CFunctionAtom rows — ports, resources, cost); the GLUE around it
(frame/parse/tick/dispatch) is generated; the no-code canvas edits the GRAPH of atoms (which exists, wired to what,
in which stage/lane) — never the atom's own C body. A state kind that held a C body and generated the atom FROM it
(the no-code-authored equivalent of today's hand-written-then-parsed atom) does not exist — that gap is cmod-2.
"""
import inspect
import json
import os

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
            add('/api/firmware/solutions/{name}/export', self, suffix='export')      # ucd-0f: POST → the CMake export dir + tar.gz
            add('/api/firmware/exports', self, suffix='exports')                       # ucd-0f: every FirmwareExport row
            add('/api/firmware/exports/{name}/download', self, suffix='download')     # ucd-0f: the tar.gz
            # ucd-0b: the claims chain — PinClaim/PeripheralClaim (cmod) + RegisterSetting/RegisterFieldSetting/
            # SignalRoute (board), materialized into the manager's tables on every GET of the solution; one pin's
            # own chain for the frontend's Target details ("why")
            add('/api/firmware/solutions/{name}/pins/{canonical}/chain', self, suffix='pin_chain')

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
        caps = self._capabilities(s)
        schedule_rows = [self._d(r) for r in sched]
        for row in schedule_rows:
            row['composed_by'] = self._composed_by(s, row['task'], caps)
        assignments = [dict(a, composed_by=self._composed_by(s, a['task'], caps)) for a in assignments]
        # ucd-0b: the claims chain, materialized into the manager's tables on every GET (upsert by name, same idiom
        # as assignments/schedule above — the object pages read these rows straight off the register)
        chain = self._claims_chain(s)
        # fs-2a (his naming, verbatim): 'Unregistered Tasks' / per-pin 'Registered Tasks'
        response.media = {'ok': True, 'solution': self._d(s), 'schedule': schedule_rows,
                          'assignments': assignments, 'unregistered_tasks': FW.unregistered_tasks(assignments),
                          'registered_tasks': FW.registered_tasks_by_pin(assignments),
                          'validation': {'ok': ok, 'why': why}, 'builds': [self._d(r) for r in builds],
                          'capabilities': caps,
                          'claims': chain['claims'], 'peripheral_claims': chain['peripheral_claims'],
                          'register_settings': chain['register_settings'], 'field_settings': chain['field_settings'],
                          'routes': chain['routes']}

    def _claims_chain(self, s):
        """ucd-0b: {claims, peripheral_claims, register_settings, field_settings, routes} for one FirmwareSolution
        row — derived (`cmod.custom.claims`) and MATERIALIZED into the manager's own tables (PinClaim/
        PeripheralClaim here, RegisterSetting/RegisterFieldSetting/SignalRoute in the board module — one flat
        object register, same posture as every cross-module reference in this file), upserted by name so the
        generic object pages (`/object/<Class>/<name>`) show them."""
        from cmod.custom import claims as C
        name, graph = getattr(s, 'name', ''), getattr(s, 'graph', '')
        claims = C.pin_claims(name, graph, manager=self.manager)
        periph = C.peripheral_claims(name, graph, manager=self.manager)
        gen = C.register_settings(name, graph, manager=self.manager)
        if self.manager is not None:
            from cmod.cmod_basis import PinClaim, PeripheralClaim
            from board.board_basis import RegisterSetting, RegisterFieldSetting, SignalRoute
            self._upsert('PinClaim', PinClaim, claims)
            self._upsert('PeripheralClaim', PeripheralClaim, periph)
            self._upsert('RegisterSetting', RegisterSetting, gen['RegisterSetting'])
            self._upsert('RegisterFieldSetting', RegisterFieldSetting, gen['RegisterFieldSetting'])
            self._upsert('SignalRoute', SignalRoute, gen['SignalRoute'])
        return {'claims': claims, 'peripheral_claims': periph, 'register_settings': gen['RegisterSetting'],
               'field_settings': gen['RegisterFieldSetting'], 'routes': gen['SignalRoute']}

    def _upsert(self, cls_name, cls, rows):
        """Upsert `rows` (dicts) into `self.manager.objectTables[cls_name]` by `name` — update an existing row's
        fields in place (never a duplicate), construct+register a new one (treeObjectInit auto-registers it onto
        the manager). Same idiom as `_record_export` above."""
        table = (self.manager.objectTables or {}).setdefault(cls_name, {})
        by_name = {getattr(r, 'name', ''): r for r in table.values()}
        for row in rows:
            existing = by_name.get(row['name'])
            if existing is not None:
                for k, v in row.items():
                    setattr(existing, k, v)
            else:
                cls(manager=self.manager, **row)

    def _composed_by(self, s, task, caps=None):
        """fs-2d (his ask, verbatim: "our tasks to be linked to their no-code solutions that compose them") — the
        REVERSE link from a task row to where it is COMPOSED: the CGraph + the CGraphNode (same `task`/`instance`
        name — RegisterAssignment.task and ScheduleSlot.task are already the CGraphNode's own `instance`, cmod.
        custom.firmware.assignments_for/schedule_for), the canvas route that opens straight at that node, any
        SolutionDefinition/HardwareSolution whose own graph IS this CGraph (the same `cgraph` field GET /api/cmod/
        graphs/{graph}'s `used_by` already reads, cmod_api.CModAPI.on_get_graph_one), and which of this solution's
        own Capabilities (self._capabilities) name this task. Never a new graph, never a new canvas — a read over
        rows already produced elsewhere, same posture as every other *_api.py in this arc."""
        graph = getattr(s, 'graph', '')
        hw = sorted({getattr(r, 'name', '') for r in self._rows('HardwareSolution') if getattr(r, 'cgraph', '') == graph})
        caps = caps if caps is not None else self._capabilities(s)
        cap_names = sorted({c['name'] for c in caps if task in c.get('task_names', [])})
        return {'graph': graph, 'node': task, 'canvas_route': '/display/c-canvas?graph=%s&node=%s' % (graph, task),
                'solution': hw[0] if hw else '', 'capabilities': cap_names}

    def _capabilities(self, s):
        """hw priorities P1: the Capabilities grouping the firmware panel's Tasks section by (D-hw-2/P1 §4
        'Capability' — the UI word everywhere) — every CapabilityDefinition over this solution's own graph (the
        live rows when a manager is present, else the seed functions directly — same pure/live duality as
        FW.validate), status re-derived from its acceptance Scenario's latest run, never hand-set."""
        import json as _json
        from cmod.custom import capabilities as CAP
        live = [r for r in self._rows('CapabilityDefinition') if getattr(r, 'graph', '') == s.graph]
        caps = [self._d(r) for r in live] if live else [c for c in CAP.SEED_CAPABILITIES if c['graph'] == s.graph]
        out = []
        for d in caps:
            status, last_proof, _ = CAP.derive_status(d, manager=self.manager)
            tasks = _json.loads(d.get('tasks_by_runtime_json') or '{}')
            task_names = sorted({t.rpartition(':')[2] for refs in tasks.values() for t in refs})
            out.append({'name': d.get('name'), 'goal': d.get('goal', ''), 'status': status, 'last_proof': last_proof,
                       'task_names': task_names})
        return sorted(out, key=lambda c: c['name'])

    def on_get_pin_chain(self, request, response, name, canonical):
        """ucd-0b: GET /api/firmware/solutions/{name}/pins/{canonical}/chain — one pin's PinClaim + the
        RegisterFieldSettings/RegisterSetting values it produced + the board's own hardware-chain hops (BoardPin ->
        SocPin -> PinFunction -> PeripheralSignal -> Peripheral -> Register -> RegisterField), reusing
        `board.custom.hardware_chain.chain_for` over the SAME live tables — never a second chain walk. This is the
        frontend's Target-details "why" in one door."""
        import falcon
        s = self._solution(name, response)
        if s is None:
            return
        from cmod.custom import claims as C
        from board.custom import board_object as BO
        from board.custom import hardware_chain as HC
        chain = self._claims_chain(s)
        claim = next((c for c in chain['claims'] if c['name'] == '%s:%s' % (name, canonical)), None)
        # an unclaimed pin is NOT an error: the page still shows the board's own chain for it, with claim = null
        # ("no task claims this pin in <solution>"); only a pin the board does not have refuses (chain_for's KeyError)
        field_settings = [f for f in chain['field_settings'] if claim and f['pin_claim'] == claim['name']]
        register_settings = [r for r in chain['register_settings']
                             if r['name'] in {f['register_setting'] for f in field_settings}]
        routes = [r for r in chain['routes'] if claim and r['pin_claim'] == claim['name']]
        tables = C._chain_tables(self.manager)
        try:
            hops = HC.chain_for(getattr(s, 'board_resolved', '') or getattr(s, 'board_definition', ''), canonical, tables)
        except KeyError as e:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': '%s (GET /api/board/<board>/pins lists them)' % e.args[0], 'solution': name, 'canonical': canonical}
            return
        except BO.BoardObjectRefused as e:
            hops = []
            response.media = {'ok': True, 'solution': name, 'canonical': canonical, 'claim': claim,
                              'field_settings': field_settings, 'register_settings': register_settings,
                              'routes': routes, 'hops': hops, 'hops_why': str(e)}
            return
        response.media = {'ok': True, 'solution': name, 'canonical': canonical, 'claim': claim,
                          'field_settings': field_settings, 'register_settings': register_settings,
                          'routes': routes, 'hops': hops}

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

    def on_post_export(self, request, response, name):
        """ucd-0f (UNO_CORE_DEMO_PLAN.md §5b): POST /api/firmware/solutions/<name>/export {target: both|board|twin,
        verify: bool} → writes the export directory (the rendered plain-C project + CMakeLists.txt + the avr-gcc
        toolchain + the one-command build + README + polari-export.json) and its tar.gz under module_home('exp'),
        records a FirmwareExport row, and — with verify — runs the exported CMake build on the engines rung and
        compares its hex sha with the committed Makefile build's (parity). Refuses, named, when the solution does
        not validate or its graph has no rendered project."""
        import falcon
        from cmod.custom import export_cmake as EX
        s = self._solution(name, response)
        if s is None:
            return
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:  # noqa: BLE001
            body = {}
        try:
            row = EX.export(s, manager=self.manager, target=body.get('target', 'both'), verify_build=bool(body.get('verify', True)))
        except EX.ExportRefused as e:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': str(e), 'solution': name}
            return
        self._record_export(row)
        response.media = {'ok': row['status'] != 'refused', 'solution': name, 'export': row}

    def _record_export(self, row):
        from cmod.cmod_basis import FirmwareExport
        table = (self.manager.objectTables or {}).get('FirmwareExport', {}) if self.manager is not None else {}
        existing = next((r for r in table.values() if getattr(r, 'name', '') == row['name']), None)
        if existing is not None:
            for k, v in row.items():
                setattr(existing, k, v)
            return existing
        obj = FirmwareExport(manager=self.manager, **row)
        try:
            self.manager.save(obj)
        except Exception:  # noqa: BLE001 — the row is in the table even when the DB write is deferred
            pass
        return obj

    def on_get_exports(self, request, response):
        table = (self.manager.objectTables or {}).get('FirmwareExport', {}) if self.manager is not None else {}
        rows = [{k: getattr(r, k, '') for k in ('name', 'solution', 'graph', 'board', 'form', 'target', 'tar_sha256', 'makefile_sha256',
                                               'cmake_sha256', 'parity', 'download_url', 'created_at', 'status', 'why')} for r in table.values()]
        rows.sort(key=lambda r: r['created_at'], reverse=True)
        response.media = {'ok': True, 'rows': rows}

    def on_get_download(self, request, response, name):
        import falcon
        from cmod.custom import export_cmake as EX
        table = (self.manager.objectTables or {}).get('FirmwareExport', {}) if self.manager is not None else {}
        r = next((x for x in table.values() if getattr(x, 'name', '') == name), None)
        if r is None or not (os.path.isdir(getattr(r, 'path', '')) or os.path.isfile(getattr(r, 'tar_path', ''))):
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no export %r on this server (GET /api/firmware/exports lists them; exports are transient)' % name}
            return
        response.content_type = 'application/gzip'
        response.downloadable_as = '%s.tar.gz' % name
        response.data = EX.tarball({'name': name, 'path': r.path, 'tar_path': r.tar_path})

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
        config = body.get('config')   # ucd-0b: {mode?, pull?, edge?, initial?} — the pin page's design choice, persisted
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
            if config is not None:
                # ucd-0b: merge onto whatever is already persisted — a person setting only `pull` on the pin page
                # does not erase an `edge` chosen earlier
                try:
                    merged = json.loads(getattr(existing, 'config_json', '') or '{}')
                except (TypeError, ValueError):
                    merged = {}
                merged.update({k: v for k, v in config.items() if k in ('mode', 'pull', 'edge', 'initial')})
                existing.config_json = json.dumps(merged)
            self.manager.saveObjToDB(existing) if hasattr(self.manager, 'saveObjToDB') else None
            resp = {'ok': True, 'assignment': self._d(existing), 'how': 'updated in place (canvas-set, fs-1\'s drag)'}
            if drop_status == 'undetermined':
                resp['warning'] = drop_why
            response.media = resp
            return
        response.media = {'ok': False, 'error': 'no existing RegisterAssignment row %r to assign onto (fs-0 does not create '
                                                'new targets — only (fs-1\'s drag over) a derived one, task %r port %r)'
                                                % (row_name, task, port)}
