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
    active_topology_name, drift_report, graph_payload, resolve_edges,
    validate_topology,
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
            add('/api/topology/drift', self, suffix='drift')
            add('/api/topology/observe', self, suffix='observe')
            add('/api/topology/export', self, suffix='export')
            add('/api/topology/import', self, suffix='import_doc')
            add('/api/topology/machine', self, suffix='machine')
            add('/api/topology/instance', self, suffix='instance')

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
        response.media = {'ok': True, 'machines': [
            {'name': getattr(m, 'name', ''),
             'sshAlias': getattr(m, 'ssh_alias', ''),
             'arch': getattr(m, 'arch', ''),
             'memGb': getattr(m, 'mem_gb', 0.0),
             'roles': json.loads(getattr(m, 'roles_json', '[]')
                                 or '[]'),
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
        if self._find('InstanceDefinition', to_instance) is None:
            return self._refuse(
                response,
                f'no InstanceDefinition named "{to_instance}"',
                '404 Not Found')
        moved = []
        if from_instance:
            for asg in self._table('ModuleAssignment').values():
                if (getattr(asg, 'topology_name', '') == name
                        and getattr(asg, 'module_name', '') == module
                        and getattr(asg, 'instance_name',
                                    '') == from_instance
                        and getattr(asg, 'state', '') != 'disabled'):
                    asg.state = 'disabled'
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
