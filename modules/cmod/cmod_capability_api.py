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
                                          exist) or when --hardware finds no board (the readiness reason, named);
                                          refuses 409, writing NO ScenarioRun, when the engines rung this server
                                          resolves to cannot run a twin build at all (a remote single-engine worker —
                                          cmod.custom.cmod_engines.resolve('make') refused) — an honest server never
                                          writes a hollow 'undetermined' run just because its own rung can't build
POST /api/capabilities/{name}/runs       body = a finished ScenarioRun record (the shape `firmwarefaults.custom.
                                          acceptance.run()` already produces — repro facts included: hex sha, engine
                                          versions, frames_seen, field-arrival ms, mode, host) proved SOMEWHERE ELSE
                                          (a host whose rung can run the twin build) and pushed here so the run a page
                                          reads actually exists on the server those pages read (the proof-push rule:
                                          a proof counts only when its run row exists on the server). Stores the row,
                                          re-derives the capability's status and returns it. Never runs anything.
POST /api/capabilities/{name}/attest     ucd-attest (his ruling 2026-10-09, "yes on attestation and overrides"): body
                                          {"mode": "hardware"|"digital-twin", "board_instance"?, "observed", "outcome":
                                          "passed"|"failed"} — a PERSON'S OWN confirmation of the Purpose's acceptance
                                          Scenario, written as a ScenarioRun of kind='attested' (no engine runs —
                                          nothing changes before this confirm). Refuses 422 when the capability has no
                                          acceptance_scenario, and 400 when `observed` or a valid `outcome` is missing
                                          (a person's words are required, never defaulted). Stamped with the acting
                                          person's Keycloak subject id, read the SAME way every other door does
                                          (`request.context.user_info['sub']`) — '' when the request carried none,
                                          and the response says so rather than silently writing a blank attester.
                                          Re-derives + persists the capability's status (same tail as /prove and
                                          /runs) and returns {ok, run, status, last_proof, status_why, proof_kind}.
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
            add('/api/capabilities/{name}/runs', self, suffix='runs')
            add('/api/capabilities/{name}/attest', self, suffix='attest')

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

    def _sub(self, request):
        """The caller's opaque Keycloak subject id — the SAME read every other door uses (security_api.py's own
        `_sub`): `request.context.user_info['sub']`, '' when the request carried no identity. Polari rows key a
        person by `sub` alone (D18-1) — never a name."""
        ui = getattr(getattr(request, 'context', None), 'user_info', None)
        return str(ui.get('sub') or '') if isinstance(ui, dict) else ''

    def _summary(self, row):
        from cmod.custom import capabilities as CAP
        cap = self._d(row)
        status, last_proof, why, proof_kind = CAP.derive_status(cap, manager=self.manager)
        if (status, last_proof) != (row.status, row.last_proof) and self.manager is not None:
            row.status, row.last_proof = status, last_proof
            db = getattr(self.manager, 'db', None)
            if db is not None and hasattr(db, 'saveInstanceInDB'):
                db.saveInstanceInDB(row)
        cap['status'], cap['last_proof'] = status, last_proof
        cap['status_why'] = why
        cap['proof_kind'] = proof_kind
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
        if mode == 'digital-twin':
            # honest server door (proof-push rule): a twin build runs through `make` (glue_build.build/prove, on
            # the SAME rung avr-gcc resolves to) — if THIS server's rung is a remote single-engine worker (or
            # nothing at all), it cannot run that build, so it must refuse BEFORE writing a hollow 'undetermined'
            # ScenarioRun, never after.
            from cmod.custom import cmod_engines as CE
            rung = CE.resolve('make')
            if rung['how'] == 'refused':
                response.status = falcon.HTTP_409
                response.media = {'ok': False, 'refused': True, 'error': rung['why'],
                                  'retry': ('this server cannot run the twin build itself — run it on a host that '
                                            'can (a local avr-gcc or the local prf-board-engines:trixie image) and '
                                            'push the result: POLARI_API=<this server> pol capability prove %s '
                                            '--twin' % name)}
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
        status, last_proof, swhy, proof_kind = CAP.derive_status(cap, manager=self.manager)
        if self.manager is not None:
            row.status, row.last_proof = status, last_proof
            db = getattr(self.manager, 'db', None)
            if db is not None and hasattr(db, 'saveInstanceInDB'):
                db.saveInstanceInDB(row)
        response.media = {'ok': True, 'capability': name, 'mode': mode, 'run': out, 'status': status,
                          'last_proof': last_proof, 'status_why': swhy, 'proof_kind': proof_kind}

    def on_post_runs(self, request, response, name):
        """Store a ScenarioRun proved ELSEWHERE (the proof-push rule) and re-derive the capability's status from it.
        Never runs anything — a pure upsert + re-derive, same posture as on_post_prove's own persist tail."""
        import falcon
        row = self._capability(name, response)
        if row is None:
            return
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:  # noqa: BLE001
            body = {}
        if self.manager is None:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'no live manager on this server to store a run on'}
            return
        from cmod.custom import capabilities as CAP
        cap = self._d(row)
        scen = cap.get('acceptance_scenario', '')
        if body.get('scenario') and body['scenario'] != scen:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': ('run names scenario %r but capability %r\'s acceptance_scenario '
                                                      'is %r' % (body['scenario'], name, scen))}
            return
        if not body.get('name'):
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'run has no name'}
            return
        run_row = dict(body)
        run_row['scenario'] = scen
        run_row.setdefault('side', 'acceptance')
        from firmwarefaults.custom.sink import ManagerSink
        sink = ManagerSink(self.manager)
        sink.upsert('ScenarioRun', run_row)
        status, last_proof, swhy, proof_kind = CAP.derive_status(cap, manager=self.manager)
        row.status, row.last_proof = status, last_proof
        db = getattr(self.manager, 'db', None)
        if db is not None and hasattr(db, 'saveInstanceInDB'):
            db.saveInstanceInDB(row)
        response.media = {'ok': True, 'capability': name, 'run': run_row, 'status': status,
                          'last_proof': last_proof, 'status_why': swhy, 'proof_kind': proof_kind}

    def on_post_attest(self, request, response, name):
        """ucd-attest: a PERSON'S OWN confirmation, written as a ScenarioRun of kind='attested' — no engine runs,
        nothing changes before this confirm. See the module docstring for the door's shape."""
        import datetime
        import falcon
        row = self._capability(name, response)
        if row is None:
            return
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:  # noqa: BLE001
            body = {}
        from cmod.custom import capabilities as CAP
        cap = self._d(row)
        scen = cap.get('acceptance_scenario', '')
        if not scen:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'Purpose %r has no acceptance_scenario — nothing to attest' % name}
            return
        observed = (body.get('observed') or '').strip()
        outcome = body.get('outcome', '')
        if not observed:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': "'observed' is required: a person's own words on what was seen (never defaulted)"}
            return
        if outcome not in ('passed', 'failed'):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': "'outcome' must be 'passed' or 'failed'"}
            return
        mode = body.get('mode', 'digital-twin')
        if mode not in ('hardware', 'digital-twin'):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': "'mode' must be 'hardware' or 'digital-twin'"}
            return
        sub = self._sub(request)
        ran_at = datetime.datetime.now().isoformat(timespec='seconds')
        who_words = sub if sub else 'an unauthenticated request (no signed-in person on this request)'
        verdict_words = 'attested by %s: %s' % (who_words, observed)
        run_row = {'name': '%s@attested@%s' % (scen, ran_at), 'scenario': scen, 'side': 'acceptance',
                  'outcome': outcome, 'verdict_words': verdict_words, 'kind': 'attested', 'attested_by': sub,
                  'observed': observed, 'board_instance': body.get('board_instance', '') or '',
                  'repro_json': json.dumps({'mode': mode, 'scenario': scen, 'capability': name, 'attested': True}),
                  'ran_at': ran_at, 'notes': "a person's confirmation (ucd-attest) — no engine ran"}
        if self.manager is None:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'no live manager on this server to store an attestation on'}
            return
        from firmwarefaults.custom.sink import ManagerSink
        sink = ManagerSink(self.manager)
        sink.upsert('ScenarioRun', run_row)
        status, last_proof, swhy, proof_kind = CAP.derive_status(cap, manager=self.manager)
        row.status, row.last_proof = status, last_proof
        db = getattr(self.manager, 'db', None)
        if db is not None and hasattr(db, 'saveInstanceInDB'):
            db.saveInstanceInDB(row)
        response.media = {'ok': True, 'capability': name, 'run': run_row, 'status': status,
                          'last_proof': last_proof, 'status_why': swhy, 'proof_kind': proof_kind}
