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

GET  /api/firmware/solutions/{name}/hardware  ucd-scope (his ruling 2026-10-09: a page is scoped to the binding in
                                               use, never "everything possible"): {ok, binding, board, soc, rows:
                                               {pins, soc_pins, pin_functions, signals, peripherals, registers,
                                               fields, settings, field_settings, routes}} — every list holds ONLY
                                               what THIS binding claims/activates/sets (`cmod.custom.scope.
                                               scope_for`, pure over `cmod.custom.claims`/`binding` — never a second
                                               derivation). `?list=<key>` (one of `cmod.custom.scope.LIST_KEYS`)
                                               narrows the answer to `{ok, rows: [...]}` for one list (class-rows-
                                               table's dataPath contract) — /display/hardware-chain's scoped tables
                                               read this per list.

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
            # ucd-0b2b: the HardwareBinding doors (§5h, his ruling 2026-10-08) — every row, and creating one
            add('/api/firmware/bindings', self, suffix='bindings_all')
            add('/api/firmware/solutions/{name}/bindings', self, suffix='solution_bindings')
            add('/api/firmware/solutions/{name}/export', self, suffix='export')      # ucd-0f: POST → the CMake export dir + tar.gz
            add('/api/firmware/exports', self, suffix='exports')                       # ucd-0f: every FirmwareExport row
            add('/api/firmware/exports/{name}/download', self, suffix='download')     # ucd-0f: the tar.gz
            # ucd-0b: the claims chain — PinClaim/PeripheralClaim (cmod) + RegisterSetting/RegisterFieldSetting/
            # SignalRoute (board), materialized into the manager's tables on every GET of the solution; one pin's
            # own chain for the frontend's Target details ("why")
            add('/api/firmware/solutions/{name}/pins/{canonical}/chain', self, suffix='pin_chain')
            add('/api/firmware/solutions/{name}/hardware', self, suffix='hardware')   # ucd-scope: THE SCOPED chain
            # ucd-attest: a person's own correction of one derived field (TargetDefinition.requirement_kind/.role,
            # PinClaim.pull/edge/mode/initial, HardwareBinding.status) — kept beside the derivation, never over it
            add('/api/firmware/overrides', self, suffix='overrides')
            add('/api/firmware/overrides/{name}', self, suffix='override_one')

    def _rows(self, cls):
        return list(((self.manager.objectTables or {}).get(cls, {}) or {}).values()) if self.manager is not None else []

    @staticmethod
    def _d(row):
        keys = [k for k in inspect.signature(type(row).__init__).parameters if k not in ('self', 'manager')]
        return {k: getattr(row, k, None) for k in keys}

    def _solution(self, name, response):
        """Looks up the FirmwareSolution by name — ucd-0b2b: `name` may be '<solution>' or
        '<solution>@<board-or-binding-suffix>' (every door that takes a {name} path segment accepts either; the
        '@...' part, when present, is resolved to a specific HardwareBinding by the callers that need one)."""
        import falcon
        sol_name = name.partition('@')[0] if name else name
        hit = [r for r in self._rows('FirmwareSolution') if r.name == sol_name]
        if not hit:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no FirmwareSolution %r (GET /api/firmware/solutions lists them)' % sol_name}
        return hit[0] if hit else None

    def on_get_solutions(self, request, response):
        response.media = {'ok': True, 'solutions': [self._d(r) for r in sorted(self._rows('FirmwareSolution'), key=lambda r: r.name)]}

    def on_get_bindings_all(self, request, response):
        """ucd-0b2b: GET /api/firmware/bindings — every HardwareBinding row (every solution's), each with its proof summary
        (his ruling 2026-10-09) refreshed from the Purposes' latest runs on this server."""
        from cmod.custom import capabilities as CAP
        rows = []
        for r in sorted(self._rows('HardwareBinding'), key=lambda r: r.name):
            sol = next((x for x in self._rows('FirmwareSolution') if x.name == getattr(r, 'solution', '')), None)
            if sol is not None:
                summ = CAP.purpose_summary(sol.graph, manager=self.manager, board=getattr(r, 'board', ''))
                for k in ('proof_status', 'proof_why', 'purposes_total', 'purposes_proven_twin', 'purposes_proven_hardware', 'advice'):
                    try:
                        setattr(r, k, summ[k])
                    except Exception:  # noqa: BLE001
                        pass
            rows.append(self._d(r))
        from cmod.custom.overrides import apply_overrides
        rows = apply_overrides(rows, 'HardwareBinding', manager=self.manager)
        response.media = {'ok': True, 'bindings': rows}

    def on_post_solution_bindings(self, request, response, name):
        """ucd-0b2b: POST /api/firmware/solutions/{name}/bindings {"board": "..."} — a person's own addition
        (provenance='canvas'), KEPT across a reseed. Derives the binding + its initial RegisterAssignment rows
        (only when the board's own hardware chain is materialized, §5h B3/B5 — else there is nothing to assign yet,
        named 'Phase 2', never a crash) and upserts both."""
        import falcon
        s = self._solution(name, response)
        if s is None:
            return
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:  # noqa: BLE001
            body = {}
        board = body.get('board', '')
        if not board:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': "'board' is required (a BoardDefinition name)"}
            return
        from cmod.custom import binding as BND
        try:
            b = BND.create(s.name, board, manager=self.manager)
        except ValueError as e:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': str(e)}
            return
        from cmod.cmod_basis import HardwareBinding
        self._upsert('HardwareBinding', HardwareBinding, [b])
        if BND.chain_materialized(b['board']):
            from cmod.cmod_basis import RegisterAssignment
            rows = BND.assignment_rows(b['name'], s.graph, manager=self.manager)
            self._upsert('RegisterAssignment', RegisterAssignment, rows)
        response.media = {'ok': True, 'binding': b}

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
        # ucd-0b2: the DERIVED rows (validate() → assignments_for) carry every widened field (requirement_kind, role, required,
        # resource_kind, peripheral, signal, signal_route, configuration); a live row loaded from a store that predates a field
        # answers None for it (the seed-field-addition gotcha) — so serve the derived row and let the live row's own non-None
        # values (config_json, status a person's assign set) overlay it, never the other way round
        derived = {a['name']: dict(a) for a in details.get('assignments', []) if a.get('name')}
        live = {r.name: {k: v for k, v in self._d(r).items() if v is not None} for r in asg}
        assignments = [dict(derived.get(n, {}), **live.get(n, {})) for n in sorted(set(derived) | set(live),
                       key=lambda n: ((derived.get(n) or live.get(n) or {}).get('target_kind', ''), (derived.get(n) or live.get(n) or {}).get('task', '')))]
        # ucd-0b2a: the REQUIREMENT facts (kind per row, role, required, resource_kind) live on the TargetDefinition rows; the page's
        # "Resources this task uses" reads them beside the assignment, so join them in — never recomputed here.
        # ucd-0c (Part 0, the naming fix): a bare (task, port) key is AMBIGUOUS for a task with several whole-node
        # targets (usart_init's D0/uart-rx and D1/uart-tx rows both have port='') — a dict keyed that way silently
        # collapses them, so both assignment rows would read the SAME (wrong, for one of them) requirement_kind.
        # `lives_on` is copied onto a RegisterAssignment row verbatim from the TargetDefinition row that produced it
        # (`cmod.custom.firmware.assignments_for`), so joining by (task, port, lives_on) is exact and unambiguous —
        # the served payload shows TWO usart_init rows (uart-rx on D0, uart-tx on D1), never one.
        try:
            from cmod.custom import targets as TG
            from cmod.custom.overrides import apply_overrides
            # ucd-attest: a person's requirement_kind/role override is laid over the TargetDefinition rows BEFORE
            # they are joined onto the assignment rows below, so an overridden row's `derived_requirement_kind`/
            # `derived_role`/`overrides_refs_json` ride along the SAME join the plain facts already use.
            t_rows = apply_overrides(TG.derive(s.graph), 'TargetDefinition', manager=self.manager)
            req = {(t.get('node'), t.get('port') or '', t.get('lives_on', 'unbound')): t for t in t_rows}
            for a in assignments:
                t = req.get((a.get('task'), a.get('port') or '', a.get('lives_on', 'unbound')))
                if t:
                    for k in ('requirement_kind', 'role', 'required', 'resource_kind'):
                        if a.get(k) in (None, ''):
                            a[k] = t.get(k)
                    for k in ('derived_requirement_kind', 'derived_role', 'overrides_refs_json'):
                        if k in t:
                            a[k] = t[k]
                    # ucd-attest: the TargetDefinition row's OWN name — the Override dialog's `target_name` (never
                    # the RegisterAssignment's own name, a different row entirely)
                    a['target_definition_name'] = t.get('name', '')
        except Exception as e:  # noqa: BLE001 — a derivation refusal must not take the page down; the rows just lack the facts
            why = '%s (requirement facts unavailable: %s)' % (why, e)
        caps = self._capabilities(s)
        # his ruling 2026-10-09: the solution's own state = the summary of its Purposes — derived here, written onto the row
        from cmod.custom import capabilities as CAP
        proof = CAP.purpose_summary(s.graph, manager=self.manager, board=getattr(s, 'board_resolved', '') or getattr(s, 'board_definition', ''))
        for k in ('proof_status', 'proof_why', 'purposes_total', 'purposes_proven_twin', 'purposes_proven_hardware'):
            try:
                setattr(s, k, proof[k])
            except Exception:  # noqa: BLE001
                pass
        schedule_rows = [self._d(r) for r in sched]
        for row in schedule_rows:
            row['composed_by'] = self._composed_by(s, row['task'], caps)
        assignments = [dict(a, composed_by=self._composed_by(s, a['task'], caps)) for a in assignments]
        # ucd-0b: the claims chain, materialized into the manager's tables on every GET (upsert by name, same idiom
        # as assignments/schedule above — the object pages read these rows straight off the register)
        chain = self._claims_chain(s)
        # ucd-0b2b: `binding` is the DEFAULT HardwareBinding row; `bindings` lists every one of this solution's
        from cmod.custom import binding as BND
        from cmod.custom.overrides import apply_overrides
        bindings = apply_overrides(BND.bindings_for_solution(s.name, manager=self.manager), 'HardwareBinding', manager=self.manager)
        default_binding = next((b for b in bindings if b.get('is_default')), None) or (bindings[0] if bindings else None)
        # fs-2a (his naming, verbatim): 'Unregistered Tasks' / per-pin 'Registered Tasks'
        response.media = {'ok': True, 'solution': self._d(s), 'schedule': schedule_rows,
                          'proof': proof,   # the firmware's state as a summary of its Purposes (+ advice)
                          'assignments': assignments, 'unregistered_tasks': FW.unregistered_tasks(assignments),
                          'registered_tasks': FW.registered_tasks_by_pin(assignments),
                          'validation': {'ok': ok, 'why': why}, 'builds': [self._d(r) for r in builds],
                          'binding': default_binding, 'bindings': bindings,
                          # D-ucd-12 (his ruling): person-facing word is Purpose, a task may name several. `purposes`
                          # is the SAME rows as `capabilities` — kept one release for the installer panel/tests that
                          # still read the old key. DEPRECATED: drop `capabilities` once those callers move over.
                          'capabilities': caps, 'purposes': caps,
                          'claims': chain['claims'], 'peripheral_claims': chain['peripheral_claims'],
                          'register_settings': chain['register_settings'], 'field_settings': chain['field_settings'],
                          'routes': chain['routes']}

    def _claims_chain(self, s, binding=None):
        """ucd-0b: {claims, peripheral_claims, register_settings, field_settings, routes} for one FirmwareSolution
        row — derived (`cmod.custom.claims`) and MATERIALIZED into the manager's own tables (PinClaim/
        PeripheralClaim here, RegisterSetting/RegisterFieldSetting/SignalRoute in the board module — one flat
        object register, same posture as every cross-module reference in this file), upserted by name so the
        generic object pages (`/object/<Class>/<name>`) show them. ucd-0b2b: `binding` (a HardwareBinding dict/row)
        scopes this to ONE binding; omitted, it is the solution's own DEFAULT binding (unchanged pre-0b2b posture)."""
        from cmod.custom import claims as C
        target = binding if binding is not None else s
        graph = getattr(s, 'graph', '')
        claims = C.pin_claims(target, graph, manager=self.manager)
        periph = C.peripheral_claims(target, graph, manager=self.manager)
        gen = C.register_settings(target, graph, manager=self.manager)
        if self.manager is not None:
            from cmod.cmod_basis import PinClaim, PeripheralClaim
            from board.board_basis import RegisterSetting, RegisterFieldSetting, SignalRoute
            self._upsert('PinClaim', PinClaim, claims)
            self._upsert('PeripheralClaim', PeripheralClaim, periph)
            self._upsert('RegisterSetting', RegisterSetting, gen['RegisterSetting'])
            self._upsert('RegisterFieldSetting', RegisterFieldSetting, gen['RegisterFieldSetting'])
            self._upsert('SignalRoute', SignalRoute, gen['SignalRoute'])
        # ucd-attest: overrides are applied to the SERVED copy only — the upserts above persist the bare
        # derivation (what claims.py itself computed), never the person's override, so a re-derive is never
        # corrupted by its own prior override.
        from cmod.custom.overrides import apply_overrides
        claims = apply_overrides(claims, 'PinClaim', manager=self.manager)
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
        # D-ucd-12: `purposes` is the same list as `capabilities` (a task may be named by several Purposes) — the
        # old key stays this release for callers that have not moved over yet. DEPRECATED: drop `capabilities`.
        return {'graph': graph, 'node': task, 'canvas_route': '/display/c-canvas?graph=%s&node=%s' % (graph, task),
                'solution': hw[0] if hw else '', 'capabilities': cap_names, 'purposes': cap_names}

    def _capabilities(self, s):
        """hw priorities P1: the Purposes (D-ucd-12: the person-facing word; was 'Capability' per D-hw-2/P1 §4)
        grouping the firmware panel's Tasks section by — every CapabilityDefinition over this solution's own graph
        (the live rows when a manager is present, else the seed functions directly — same pure/live duality as
        FW.validate), status re-derived from its acceptance Scenario's latest run, never hand-set. A task may be
        named by several CapabilityDefinition rows — each one's own `task_names` is computed independently, so the
        task lands in every Purpose that names it, never just one."""
        import json as _json
        from cmod.custom import capabilities as CAP
        live = [r for r in self._rows('CapabilityDefinition') if getattr(r, 'graph', '') == s.graph]
        caps = [self._d(r) for r in live] if live else [c for c in CAP.SEED_CAPABILITIES if c['graph'] == s.graph]
        out = []
        for d in caps:
            status, last_proof, _, _ = CAP.derive_status(d, manager=self.manager)
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
        frontend's Target-details "why" in one door. ucd-0b2b: `name` may be '<solution>@<board>' — answers for the
        NAMED binding (default when `name` has no '@', same as before)."""
        import falcon
        s = self._solution(name, response)
        if s is None:
            return
        from cmod.custom import claims as C
        from cmod.custom import binding as BND
        from board.custom import board_object as BO
        from board.custom import hardware_chain as HC
        b = BND.resolve(name, manager=self.manager)
        chain = self._claims_chain(s, binding=b)
        naming = s.name if (b is None or b.get('is_default', True)) else b['name']
        claim = next((c for c in chain['claims'] if c['name'] == '%s:%s' % (naming, canonical)), None)
        # an unclaimed pin is NOT an error: the page still shows the board's own chain for it, with claim = null
        # ("no task claims this pin in <solution>"); only a pin the board does not have refuses (chain_for's KeyError)
        field_settings = [f for f in chain['field_settings'] if claim and f['pin_claim'] == claim['name']]
        register_settings = [r for r in chain['register_settings']
                             if r['name'] in {f['register_setting'] for f in field_settings}]
        routes = [r for r in chain['routes'] if claim and r['pin_claim'] == claim['name']]
        tables = C._chain_tables(self.manager)
        board = (b or {}).get('board') or getattr(s, 'board_resolved', '') or getattr(s, 'board_definition', '')
        try:
            hops = HC.chain_for(board, canonical, tables)
        except KeyError as e:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': '%s (GET /api/board/<board>/pins lists them)' % e.args[0], 'solution': name, 'canonical': canonical}
            return
        except BO.BoardObjectRefused as e:
            hops = []
            response.media = {'ok': True, 'solution': name, 'binding': (b['name'] if b else name), 'canonical': canonical,
                              'claim': claim, 'field_settings': field_settings, 'register_settings': register_settings,
                              'routes': routes, 'hops': hops, 'hops_why': str(e)}
            return
        response.media = {'ok': True, 'solution': name, 'binding': (b['name'] if b else name), 'canonical': canonical,
                          'claim': claim, 'field_settings': field_settings, 'register_settings': register_settings,
                          'routes': routes, 'hops': hops}

    def on_get_hardware(self, request, response, name):
        """ucd-scope (UNO_CORE_DEMO_PLAN.md §5f, his ruling 2026-10-09): GET /api/firmware/solutions/{name}/hardware
        — THE SCOPED HARDWARE CHAIN of one binding (`name` = '<solution>' or '<solution>@<board>'), reusing
        `cmod.custom.claims`/`cmod.custom.binding` (never a second derivation): {ok, binding, board, soc, rows:
        {pins, soc_pins, pin_functions, signals, peripherals, registers, fields, settings, field_settings, routes}}.
        `?list=<key>` (`cmod.custom.scope.LIST_KEYS`) narrows to `{ok, rows: [...]}` for one list — the contract
        class-rows-table's `dataPath` reads, so /display/hardware-chain's scoped tables point straight at this door
        with a `list` query param each, never a second door per list."""
        import falcon
        from cmod.custom import binding as BND
        from cmod.custom import scope as SCOPE
        s = self._solution(name, response)
        if s is None:
            return
        b = BND.resolve(name, manager=self.manager)
        result = SCOPE.scope_for(b if b is not None else name, s.graph, manager=self.manager)
        list_key = request.params.get('list', '')
        if list_key:
            if list_key not in SCOPE.LIST_KEYS:
                response.status = falcon.HTTP_404
                response.media = {'ok': False, 'error': 'no such list %r (one of %s)' % (list_key, ', '.join(SCOPE.LIST_KEYS))}
                return
            response.media = {'ok': True, 'rows': result['rows'][list_key]}
            return
        response.media = dict(ok=True, **result)

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
        """ucd-0b2b: `name` may be '<solution>@<board>' — binds onto that SPECIFIC HardwareBinding's own
        RegisterAssignment rows (the default binding when `name` has no '@', unchanged pre-0b2b behaviour and row
        naming)."""
        import falcon
        s = self._solution(name, response)
        if s is None:
            return
        from cmod.custom import binding as BND
        b = BND.resolve(name, manager=self.manager)
        if b is None:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no HardwareBinding resolvable for %r' % name}
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
        # ucd-0b2b: occupancy is scoped to THIS binding (`binding_name=b['name']`) — two bindings of the same
        # solution never see each other's claims as a false conflict.
        from cmod.custom import firmware as FW
        drop_ok, drop_status, drop_why = FW.check_drop(s.graph, s.name, task, lives_on, manager=self.manager, binding_name=b['name'])
        if not drop_ok:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': True, 'error': drop_why, 'task': task, 'lives_on': lives_on}
            return
        naming = s.name if b.get('is_default', True) else b['name']
        row_name = '%s:%s%s' % (naming, task, ('.' + port) if port else '')
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
            resp = {'ok': True, 'assignment': self._d(existing), 'binding': b['name'],
                    'how': 'updated in place (canvas-set, fs-1\'s drag)'}
            if drop_status == 'undetermined':
                resp['warning'] = drop_why
            response.media = resp
            return
        response.media = {'ok': False, 'binding': b['name'],
                          'error': 'no existing RegisterAssignment row %r to assign onto (fs-0 does not create '
                                   'new targets — only (fs-1\'s drag over) a derived one, task %r port %r)'
                                   % (row_name, task, port)}

    # ------------------------------------------------------------------------------------------------- ucd-attest

    def _sub(self, request):
        """The caller's opaque Keycloak subject id — the SAME read every other door uses (security_api.py's own
        `_sub`, cmod_capability_api's own copy): `request.context.user_info['sub']`, '' when the request carried no
        identity. Polari rows key a person by `sub` alone (D18-1) — never a name."""
        ui = getattr(getattr(request, 'context', None), 'user_info', None)
        return str(ui.get('sub') or '') if isinstance(ui, dict) else ''

    def on_post_overrides(self, request, response):
        """POST /api/firmware/overrides {target_class, target_name, field, value, why} — a person's own correction
        of one derived field (TargetDefinition.requirement_kind/.role, PinClaim.pull/edge/mode/initial,
        HardwareBinding.status this slice). Writes the ONE DerivedOverride row for (target_class, target_name,
        field) — a repeat call replaces its own prior row, never stacking. `why` is required; refused (422) by name
        without it. Nothing is written before this call (the frontend's confirm dialog), and nothing else changes —
        the next read of the target's own row applies it (`cmod.custom.overrides.apply_overrides`)."""
        import falcon
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:  # noqa: BLE001
            body = {}
        target_class = body.get('target_class', '')
        target_name = body.get('target_name', '')
        field = body.get('field', '')
        value = body.get('value')
        why = body.get('why', '')
        if not (target_class and target_name and field) or value is None:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': "'target_class', 'target_name', 'field' and 'value' are all required"}
            return
        if self.manager is None:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'no live manager on this server to store an override on'}
            return
        from cmod.custom import overrides as OV
        out, why_refused = OV.create(target_class, target_name, field, value, why, self._sub(request), self.manager)
        if out is None:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': why_refused}
            return
        response.media = {'ok': True, 'override': self._d(out)}

    def on_delete_override_one(self, request, response, name):
        """DELETE /api/firmware/overrides/{name} — retires the override (status='retired'; the row itself, and its
        who/when/why, survives as the record of the manual change)."""
        import falcon
        if self.manager is None:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'no live manager on this server to retire an override on'}
            return
        from cmod.custom import overrides as OV
        ok, why = OV.retire(name, self.manager)
        if not ok:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': why}
            return
        response.media = {'ok': True, 'retired': name}
