"""
@cross-cutting
@module topology.topology_api

TopologyAPI (top-1): the /api/topology/* surface. Reads serve the
Topology tab and the CLI (top-2 pull/report/diff); writes are
row-level (assign/observe/import) — the API NEVER shells out or
deploys anything. Applying a topology is the CLI's job
(`pol topology apply`), always human-invoked
(knobs-and-suggestions).

@consumers
  - polariServer (instantiated next to ScoringAPI)
  - polari-platform-angular /topology page (top-5/6)
  - polari-cli scripts/topology.sh (top-2/3)
"""

import json
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit

from topology.topology_analysis import (
    active_topology_name, drift_report, graph_payload,
    placement_check, plan_move, resolve_edges, validate_topology,
)
from topology.topology_basis import (
    InstanceDefinition, OrchestrationTarget, PolariNodeMachine,
)
from topology.topology_io import export_topology, merge_topology_doc
from topology.topology_links import ServiceConnection
from topology.topology_module_graph import (
    designate_transients, module_graph,
)
from topology.topology_modules import (
    ModuleAssignment, ModuleDependencyEdge,
)
from topology.topology_state import (
    TopologyDefinition, TopologyObservation,
)

#: Constructors merge_topology_doc plans against (import applies).
CLASS_MAP = {
    'PolariNodeMachine': PolariNodeMachine,
    'OrchestrationTarget': OrchestrationTarget,
    'TopologyDefinition': TopologyDefinition,
    'InstanceDefinition': InstanceDefinition,
    'ModuleAssignment': ModuleAssignment,
    'ModuleDependencyEdge': ModuleDependencyEdge,
    'ServiceConnection': ServiceConnection,
    'TopologyObservation': TopologyObservation,
}


class TopologyAPI(treeObject):
    """Topology orchestration endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/topology'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/topology/summary', self, suffix='summary')
            add('/api/topology/graph', self, suffix='graph')
            add('/api/topology/module-graph', self,
                suffix='module_graph')
            add('/api/topology/machines', self, suffix='machines')
            add('/api/topology/validate', self, suffix='validate')
            add('/api/topology/resolve', self, suffix='resolve')
            add('/api/topology/assign', self, suffix='assign')
            add('/api/topology/move', self, suffix='move')
            add('/api/topology/drift', self, suffix='drift')
            add('/api/topology/observe', self, suffix='observe')
            add('/api/topology/export', self, suffix='export')
            add('/api/topology/import', self, suffix='import_doc')
            add('/api/topology/machine', self, suffix='machine')
            add('/api/topology/instance', self, suffix='instance')
            # gm-2-lite: graceful moves as observable data + the
            # gm-1 probe-cache invalidation.
            add('/api/topology/move-operations', self,
                suffix='move_ops')
            add('/api/topology/move-operations/step', self,
                suffix='move_op_step')
            add('/api/topology/move-operations/finish', self,
                suffix='move_op_finish')
            add('/api/topology/providers/reprobe', self,
                suffix='reprobe')

    # ---- helpers ----------------------------------------------------

    def _payload(self, request):
        try:
            return json.load(request.bounded_stream), None
        except Exception as e:
            return None, f'bad JSON payload: {e}'

    def _topology_name(self, request, payload=None):
        """?name= / payload name, else the active topology."""
        name = ''
        if payload:
            name = payload.get('topology', '') or payload.get(
                'name', '')
        if not name:
            name = request.params.get('name', '')
        return name or active_topology_name(self.manager)

    def _table(self, class_name):
        return (self.manager.objectTables or {}).get(class_name, {})

    def _find(self, class_name, name):
        for row in self._table(class_name).values():
            if getattr(row, 'name', '') == name:
                return row
        return None

    def _save(self, row):
        try:
            self.manager.db.saveInstanceInDB(row)
        except Exception:
            pass  # in-memory row stays authoritative until next save

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    # ---- reads ------------------------------------------------------

    def on_get_summary(self, request, response):
        active = active_topology_name(self.manager)
        counts = {class_name: len(self._table(class_name))
                  for class_name in CLASS_MAP}
        response.media = {
            'ok': True, 'activeTopology': active, 'counts': counts,
            'topologies': [
                {'name': getattr(t, 'name', ''),
                 'status': getattr(t, 'status', ''),
                 'isActive': getattr(t, 'is_active', False),
                 'description': getattr(t, 'description', '')}
                for t in self._table('TopologyDefinition').values()]}

    def on_get_graph(self, request, response):
        name = self._topology_name(request)
        if not name:
            return self._refuse(
                response, 'no active topology and no ?name= given',
                '404 Not Found')
        report = graph_payload(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_module_graph(self, request, response):
        """The bidirectional module graph (tt-1): classifications,
        dependents, transient/primary designation — what the
        circle/nesting renderer draws."""
        name = self._topology_name(request)
        if not name:
            return self._refuse(
                response, 'no active topology and no ?name= given',
                '404 Not Found')
        report = module_graph(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_machines(self, request, response):
        def _roles(m):
            # sim rows carry junk roles_json — never 500 over it.
            try:
                return json.loads(
                    getattr(m, 'roles_json', '[]') or '[]')
            except Exception:
                return []
        response.media = {'ok': True, 'machines': [
            {'name': getattr(m, 'name', ''),
             'sshAlias': getattr(m, 'ssh_alias', ''),
             'arch': getattr(m, 'arch', ''),
             'memGb': getattr(m, 'mem_gb', 0.0),
             'roles': _roles(m),
             'swarmRole': getattr(m, 'swarm_role', 'none'),
             'repoDir': getattr(m, 'repo_dir', ''),
             'source': getattr(m, 'source', ''),
             'notes': getattr(m, 'notes', '')}
            for m in self._table('PolariNodeMachine').values()]}

    def on_get_drift(self, request, response):
        name = self._topology_name(request)
        if not name:
            return self._refuse(
                response, 'no active topology and no ?name= given',
                '404 Not Found')
        report = drift_report(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_export(self, request, response):
        name = self._topology_name(request)
        if not name:
            return self._refuse(
                response, 'no active topology and no ?name= given',
                '404 Not Found')
        report = export_topology(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    # ---- writes (row-level only) ------------------------------------

    def on_post_validate(self, request, response):
        payload, err = self._payload(request)
        if err:
            payload = {}  # empty body = validate the active topology
        name = self._topology_name(request, payload or {})
        if not name:
            return self._refuse(
                response, 'no active topology and no name given',
                '404 Not Found')
        report = validate_topology(self.manager, name)
        if not report.get('ok'):
            return self._refuse(response, report.get('error'),
                                '404 Not Found')
        definition = self._find('TopologyDefinition', name)
        if definition is not None:
            definition.validation_findings_json = json.dumps(
                report['findings'])
            definition.validated_at = datetime.now(
                timezone.utc).isoformat()
            if report['valid'] and getattr(
                    definition, 'status', '') == 'draft':
                definition.status = 'validated'
            self._save(definition)
        response.media = report

    def on_post_resolve(self, request, response):
        payload, err = self._payload(request)
        if err:
            payload = {}
        name = self._topology_name(request, payload or {})
        if not name:
            return self._refuse(
                response, 'no active topology and no name given',
                '404 Not Found')
        report = resolve_edges(self.manager, name)
        # tt-1: the same deterministic pass also (re)stamps the
        # transient/primary designation before edges persist.
        report['designation'] = designate_transients(
            self.manager, name)
        for edge in self._table('ModuleDependencyEdge').values():
            if getattr(edge, 'topology_name', '') == name:
                self._save(edge)
        response.media = report

    def on_post_assign(self, request, response):
        """Move/enable a module on an instance (drag-drop backend +
        the `pol allocate` row-write). Re-resolves edges; deploying
        the change stays the CLI's job."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        module = (payload or {}).get('module', '')
        to_instance = (payload or {}).get('to_instance', '')
        from_instance = (payload or {}).get('from_instance', '')
        if not module or not to_instance:
            return self._refuse(
                response, 'payload needs {module, to_instance}')
        name = self._topology_name(request, payload)
        if not name:
            return self._refuse(
                response, 'no active topology and no topology given',
                '404 Not Found')
        target_row = self._find('InstanceDefinition', to_instance)
        if target_row is None:
            return self._refuse(
                response,
                f'no InstanceDefinition named "{to_instance}"',
                '404 Not Found')
        allowed, why = placement_check(module, target_row)
        if not allowed:
            return self._refuse(response, why)
        moved = []
        if from_instance:
            for asg in self._table('ModuleAssignment').values():
                if (getattr(asg, 'topology_name', '') == name
                        and getattr(asg, 'module_name', '') == module
                        and getattr(asg, 'instance_name',
                                    '') == from_instance
                        and getattr(asg, 'state', '')
                        not in ('disabled', 'transient')):
                    # tt-13: the former location stays visible as a
                    # dashed TRANSIENT ghost (inert; one-click back).
                    asg.state = 'transient'
                    asg.notes = (f'moved to {to_instance} — '
                                 'transient ghost at the former '
                                 'location')
                    self._save(asg)
                    moved.append(getattr(asg, 'name', ''))
        target = None
        for asg in self._table('ModuleAssignment').values():
            if (getattr(asg, 'topology_name', '') == name
                    and getattr(asg, 'module_name', '') == module
                    and getattr(asg, 'instance_name',
                                '') == to_instance):
                target = asg
                break
        if target is None:
            target = ModuleAssignment(
                name=f'{module}@{to_instance}', module_name=module,
                instance_name=to_instance, state='enabled',
                topology_name=name,
                notes='created via /api/topology/assign',
                manager=self.manager)
        else:
            target.state = 'enabled'
        self._save(target)
        resolve = resolve_edges(self.manager, name)
        designate_transients(self.manager, name)
        for edge in self._table('ModuleDependencyEdge').values():
            if getattr(edge, 'topology_name', '') == name:
                self._save(edge)
        response.media = {
            'ok': True, 'topology': name,
            'assignment': getattr(target, 'name', ''),
            'disabled': moved, 'resolve': resolve,
            'suggestedCommand': 'pol topology apply --plan'}

    # ---- gm-2-lite: move operations (moves as data) -----------------

    @staticmethod
    def _stomp_move(row):
        try:
            from polariApiServer.stompWebSocketServer import (
                get_stomp_server,
            )
            from topology.move_operations import move_dict
            server = get_stomp_server()
            if server is not None:
                server.publish('/topic/MoveOperation', {
                    'operation': 'move-status', **move_dict(row)})
        except Exception:
            pass  # push is best-effort; the panel polls too

    def _find_move(self, name):
        for row in self._table('MoveOperation').values():
            if getattr(row, 'name', '') == name:
                return row
        return None

    def on_get_move_ops(self, request, response):
        """The move ledger: recent MoveOperations (newest first) with
        per-step receipts + EXPECTED step durations from prior
        verified moves of the same kind (median; no history = {}).
        ?active=true filters to planned/running."""
        from topology.move_operations import (
            expected_step_durations, move_dict,
        )
        rows = list(self._table('MoveOperation').values())
        if request.params.get('active') == 'true':
            rows = [r for r in rows
                    if getattr(r, 'status', '') in ('planned',
                                                    'running')]
        rows.sort(key=lambda r: getattr(r, 'started_at', 0.0)
                  or 0.0, reverse=True)
        try:
            limit = int(request.params.get('limit', 10))
        except ValueError:
            limit = 10
        history = list(self._table('MoveOperation').values())
        response.media = {
            'ok': True,
            'moves': [
                move_dict(r, expected=expected_step_durations(
                    history, getattr(r, 'kind', ''),
                    getattr(r, 'subject', '')))
                for r in rows[:limit]],
        }

    def on_post_move_ops(self, request, response):
        """Create a MoveOperation with its PLANNED step list (shown
        before anything runs — gm-6 discipline). Body: {kind, subject,
        fromMachine, toMachine, triggeredBy?}. Returns the row +
        expected step durations from history."""
        import json as jsonLib
        import time as timeLib
        from topology.move_operations import (
            MOVE_KINDS, MoveOperation, expected_step_durations,
            move_dict, planned_steps,
        )
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        kind = (payload or {}).get('kind', 'engine-relocation')
        subject = (payload or {}).get('subject', '')
        if kind not in MOVE_KINDS:
            return self._refuse(
                response, f'unknown move kind {kind!r} — one of '
                          f'{MOVE_KINDS}')
        if not subject:
            return self._refuse(response, 'payload needs {subject}')
        steps = planned_steps(kind)
        if not steps:
            return self._refuse(
                response,
                f'move kind {kind!r} has no step plan — every gm '
                'mover is automated: engine-relocation (gm-1), '
                'instance-move (gm-5 sqlite), minio-move/keydb-move '
                '(gm-3), auth-move (gm-4), database-move (gm-5 '
                'MariaDB)')
        row = MoveOperation(
            name=f'{subject}@{int(timeLib.time())}',
            kind=kind, subject=subject,
            from_machine=(payload or {}).get('fromMachine', ''),
            to_machine=(payload or {}).get('toMachine', ''),
            status='running',
            steps_json=jsonLib.dumps(steps),
            started_at=timeLib.time(),
            triggered_by=(payload or {}).get('triggeredBy', ''),
            manager=self.manager)
        self._save(row)
        self._stomp_move(row)
        history = list(self._table('MoveOperation').values())
        response.media = {
            'ok': True,
            'move': move_dict(row, expected=expected_step_durations(
                history, kind, subject)),
        }

    def on_post_move_op_step(self, request, response):
        """One step transition: {name, step, status, receipt?} —
        durations are measured server-side so every mover reports
        identically."""
        from topology.move_operations import (
            apply_step_update, move_dict,
        )
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        row = self._find_move((payload or {}).get('name', ''))
        if row is None:
            return self._refuse(
                response, f"no MoveOperation named "
                          f"{(payload or {}).get('name', '')!r}",
                '404 Not Found')
        verdict = apply_step_update(
            row, (payload or {}).get('step', ''),
            (payload or {}).get('status', ''),
            receipt=(payload or {}).get('receipt'))
        if not verdict.get('ok'):
            return self._refuse(response, verdict['refusal'])
        self._save(row)
        self._stomp_move(row)
        response.media = {'ok': True, 'move': move_dict(row)}

    def on_post_move_op_finish(self, request, response):
        """Close a move: {name, status: verified|failed, error?}."""
        import time as timeLib
        from topology.move_operations import move_dict
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        row = self._find_move((payload or {}).get('name', ''))
        if row is None:
            return self._refuse(
                response, f"no MoveOperation named "
                          f"{(payload or {}).get('name', '')!r}",
                '404 Not Found')
        status = (payload or {}).get('status', '')
        if status not in ('verified', 'failed', 'abandoned'):
            return self._refuse(
                response, 'finish status must be verified | failed '
                          '| abandoned')
        row.status = status
        row.finished_at = timeLib.time()
        row.error = (payload or {}).get('error', '') or ''
        self._save(row)
        self._stomp_move(row)
        response.media = {'ok': True, 'move': move_dict(row)}

    def on_post_reprobe(self, request, response):
        """gm-1 step 4: invalidate the provider probe cache so edges
        re-resolve against the RELOCATED provider immediately instead
        of waiting out the 30s TTL."""
        from topology import provider_registry
        cleared = len(provider_registry._PROBE_CACHE)
        provider_registry._PROBE_CACHE.clear()
        response.media = {
            'ok': True, 'clearedEntries': cleared,
            'note': 'next resolve_provider call probes live'}

    def on_post_move(self, request, response):
        """tt-13 dynamic re-placement: plan_move decides whether
        this is a MODULE reassignment (container target — former
        locations become transient ghosts) or an ENGINE relocation
        (device target — the provider instance re-pins; the stack
        redeploy stays the human-run pol command). Rows persist, so
        the move IS the configuration that comes back up. Pass
        {"plan": true} to preview without touching anything."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        module = (payload or {}).get('module', '')
        if not module:
            return self._refuse(response, 'payload needs {module}')
        name = self._topology_name(request, payload)
        if not name:
            return self._refuse(
                response, 'no active topology and no topology given',
                '404 Not Found')
        plan = plan_move(
            self.manager, name, module,
            to_instance=(payload or {}).get('to_instance', ''),
            to_machine=(payload or {}).get('to_machine', ''))
        if not plan.get('ok'):
            return self._refuse(response, plan.get('error'))
        if (payload or {}).get('plan', False):
            response.media = {**plan, 'planOnly': True}
            return
        if plan['moveKind'] == 'module-reassignment':
            # Reuse the assign path per former location, so the
            # ghosting + resolve/designate logic stays in one place.
            for from_instance in plan['fromInstances']:
                self._reassign(name, module, plan['toInstance'],
                               from_instance)
            if not plan['fromInstances']:
                self._reassign(name, module, plan['toInstance'], '')
            response.media = {
                **plan,
                'suggestedCommand': 'pol topology apply --plan'}
            return
        row = self._find('InstanceDefinition', plan['instance'])
        row.machine_name = plan['toMachine']
        row.placement_constraint = plan['placementConstraint']
        self._save(row)
        response.media = plan

    def _reassign(self, topology, module, to_instance,
                  from_instance):
        """The assign endpoint's row logic, callable internally."""
        if from_instance:
            for asg in self._table('ModuleAssignment').values():
                if (getattr(asg, 'topology_name', '') == topology
                        and getattr(asg, 'module_name', '') == module
                        and getattr(asg, 'instance_name',
                                    '') == from_instance
                        and getattr(asg, 'state', '')
                        not in ('disabled', 'transient')):
                    asg.state = 'transient'
                    asg.notes = (f'moved to {to_instance} — '
                                 'transient ghost at the former '
                                 'location')
                    self._save(asg)
        target = None
        for asg in self._table('ModuleAssignment').values():
            if (getattr(asg, 'topology_name', '') == topology
                    and getattr(asg, 'module_name', '') == module
                    and getattr(asg, 'instance_name',
                                '') == to_instance):
                target = asg
                break
        if target is None:
            target = ModuleAssignment(
                name=f'{module}@{to_instance}', module_name=module,
                instance_name=to_instance, state='enabled',
                topology_name=topology,
                notes='placed via /api/topology/move',
                manager=self.manager)
        else:
            target.state = 'enabled'
        self._save(target)
        resolve_edges(self.manager, topology)
        designate_transients(self.manager, topology)
        for edge in self._table('ModuleDependencyEdge').values():
            if getattr(edge, 'topology_name', '') == topology:
                self._save(edge)

    def on_post_observe(self, request, response):
        """Ingest one node observation (`pol topology report`)."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        node = (payload or {}).get('node', '')
        if not node:
            return self._refuse(response, 'payload needs {node}')
        name = self._topology_name(request, payload)
        observed_at = payload.get('observed_at', '') or datetime.now(
            timezone.utc).isoformat()
        row = TopologyObservation(
            name=f'{node}@{observed_at}', topology_name=name,
            node_name=node, observed_at=observed_at,
            stacks_json=json.dumps(payload.get('stacks', [])),
            services_json=json.dumps(payload.get('services', [])),
            modules_json=json.dumps(payload.get('modules', [])),
            source=payload.get('source', 'pol topology report'),
            manager=self.manager)
        self._save(row)
        response.media = {'ok': True,
                          'observation': getattr(row, 'name', ''),
                          'topology': name}

    _MACHINE_FIELDS = ('ssh_alias', 'arch', 'mem_gb', 'roles_json',
                       'swarm_role', 'repo_dir', 'source', 'notes',
                       # res-1 knob: where the node's /system-info
                       # answers (observed fields are NOT upsertable
                       # here — they come from the observe paths).
                       'system_info_url')
    _INSTANCE_FIELDS = ('kind', 'service_kinds_json', 'replicas',
                        'env_tier', 'machine_name',
                        'placement_constraint', 'db_backend',
                        'image_tag', 'orchestration_target',
                        'topology_name', 'notes')

    def _upsert(self, request, response, class_name, fields,
                required_note):
        """Field-level upsert-by-name (the CLI's row-write seam for
        `pol swarm join` / `pol allocate`)."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        name = (payload or {}).get('name', '')
        if not name:
            return self._refuse(
                response, f'payload needs {{name{required_note}}}')
        row = self._find(class_name, name)
        created = row is None
        updates = {k: payload[k] for k in fields if k in payload}
        if created:
            cls = CLASS_MAP[class_name]
            row = cls(name=name, **updates, manager=self.manager)
        else:
            for k, v in updates.items():
                setattr(row, k, v)
        self._save(row)
        response.media = {'ok': True, 'name': name,
                          'created': created,
                          'updated': sorted(updates)}

    def on_post_machine(self, request, response):
        self._upsert(request, response, 'PolariNodeMachine',
                     self._MACHINE_FIELDS, ', swarm_role, ...')

    def on_post_instance(self, request, response):
        self._upsert(request, response, 'InstanceDefinition',
                     self._INSTANCE_FIELDS, ', machine_name, ...')

    def on_post_import_doc(self, request, response):
        """Apply a portable package (idempotent-by-name upsert)."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        plan = merge_topology_doc(self.manager, payload)
        if not plan.get('ok'):
            return self._refuse(response, plan.get('error'))
        created = []
        for class_name, row in plan['creates']:
            cls = CLASS_MAP[class_name]
            self._save(cls(**row, manager=self.manager))
            created.append({'class': class_name,
                            'name': row.get('name', '')})
        topo = (payload.get('topology') or {}).get('name', '')
        if topo:
            resolve_edges(self.manager, topo)
            designate_transients(self.manager, topo)
            for edge in self._table(
                    'ModuleDependencyEdge').values():
                if getattr(edge, 'topology_name', '') == topo:
                    self._save(edge)
        response.media = {'ok': True, 'created': created,
                          'skipped': plan['skips'],
                          'topology': topo}
