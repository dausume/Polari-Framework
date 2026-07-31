"""
@cross-cutting
@module polariapps.apps_api

AppsAPI (tt-12): the /api/apps surface. Reads serve the /apps page
and the pol CLI (`pol apps list|plan|export`); the two writes are
row-level: definition upsert and APPLY — which writes
ModuleAssignment rows per the plan and re-resolves edges, nothing
more. Deploying containers stays the human's pol command
(knobs-and-suggestions). Export emits the credential-free JSON
package `pol apps deploy <file.json>` points at; import (deploy)
accepts the same document, upserting the app then applying.

@consumers
  - polariServer (instantiated next to TopologyAPI)
  - polari-cli scripts/apps.sh · polari-platform-angular /apps
"""

import json
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit

from polariapps.apps_analysis import (
    app_plan, apply_app, export_app, validate_app_document,
)
from polariapps.apps_nav import app_nav_report, apps_nav
from polariapps.apps_basis import (
    AppDeploymentPlan, PolariAppDefinition,
)
from topology.topology_analysis import (
    active_topology_name, resolve_edges,
)
from topology.topology_module_graph import designate_transients
from topology.topology_modules import ModuleAssignment

_APP_FIELDS = ('title', 'use_case', 'description', 'modules_json',
               'pages_json', 'notes')


class AppsAPI(treeObject):
    """Polari-App endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/apps'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/apps', self, suffix='list')
            add('/api/apps/nav', self, suffix='nav')
            add('/api/apps/nav/{app}', self, suffix='nav_app')
            add('/api/apps/plan', self, suffix='plan')
            add('/api/apps/export', self, suffix='export')
            add('/api/apps/definition', self, suffix='definition')
            add('/api/apps/apply', self, suffix='apply')

    # ---- helpers ----------------------------------------------------

    def _payload(self, request):
        try:
            return json.load(request.bounded_stream), None
        except Exception as e:
            return None, f'bad JSON payload: {e}'

    def _topology(self, request, payload=None):
        name = (payload or {}).get('topology', '') or (
            request.params.get('topology', ''))
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
            pass

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    # ---- reads ------------------------------------------------------

    def on_get_list(self, request, response):
        response.media = {'ok': True, 'apps': [
            {'name': getattr(a, 'name', ''),
             'title': getattr(a, 'title', ''),
             'useCase': getattr(a, 'use_case', ''),
             'description': getattr(a, 'description', ''),
             'modules': json.loads(
                 getattr(a, 'modules_json', '[]') or '[]'),
             'pages': json.loads(
                 getattr(a, 'pages_json', '[]') or '[]')}
            for a in self._table('PolariAppDefinition').values()]}

    def on_get_nav(self, request, response):
        """nav-2: every app's nav tree with tri-state availability
        (enabled | absent | unknown) + persona index. Absent modules
        keep their items, carrying bringup affordances — the map
        survives the missing territory."""
        response.media = apps_nav(self.manager)

    def on_get_nav_app(self, request, response, app):
        report = app_nav_report(self.manager, app)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_plan(self, request, response):
        name = request.params.get('name', '')
        if not name:
            return self._refuse(response, 'needs ?name=<app>')
        topology = self._topology(request)
        report = app_plan(self.manager, name, topology)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_export(self, request, response):
        name = request.params.get('name', '')
        if not name:
            return self._refuse(response, 'needs ?name=<app>')
        report = export_app(self.manager, name,
                            self._topology(request))
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    # ---- writes (rows only) -----------------------------------------

    def on_post_definition(self, request, response):
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        name = (payload or {}).get('name', '')
        if not name:
            return self._refuse(response, 'payload needs {name}')
        row = self._find('PolariAppDefinition', name)
        created = row is None
        updates = {k: payload[k] for k in _APP_FIELDS if k in payload}
        if created:
            row = PolariAppDefinition(
                name=name, **updates, manager=self.manager)
        else:
            for k, v in updates.items():
                setattr(row, k, v)
        self._save(row)
        response.media = {'ok': True, 'name': name,
                          'created': created,
                          'updated': sorted(updates)}

    def on_post_apply(self, request, response):
        """Apply an app (by name, or a whole exported document) to a
        topology: upsert the definition when a document arrives,
        write the plan's assignment rows, re-resolve — and record
        the AppDeploymentPlan receipt. Deploy stays human."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        doc = (payload or {}).get('document')
        name = (payload or {}).get('name', '')
        if doc is not None:
            problem = validate_app_document(doc)
            if problem:
                return self._refuse(response, problem)
            app_fields = doc['app']
            name = app_fields['name']
            row = self._find('PolariAppDefinition', name)
            if row is None:
                row = PolariAppDefinition(
                    name=name,
                    **{k: v for k, v in app_fields.items()
                       if k in _APP_FIELDS},
                    manager=self.manager)
            else:
                for k in _APP_FIELDS:
                    if k in app_fields:
                        setattr(row, k, app_fields[k])
            self._save(row)
        if not name:
            return self._refuse(
                response, 'payload needs {name} or {document}')
        if not (payload or {}).get('confirm', False):
            return self._refuse(
                response,
                'apply writes ModuleAssignment rows — pass '
                '{"confirm": true} (plan first: GET /api/apps/plan)')
        topology = self._topology(request, payload)
        result = apply_app(
            self.manager, name, topology,
            assignment_factory=lambda **fields: ModuleAssignment(
                **fields, manager=self.manager),
            save=self._save)
        if not result.get('ok'):
            return self._refuse(response, result.get('error'),
                                '404 Not Found')
        resolve_edges(self.manager, topology)
        designate_transients(self.manager, topology)
        for edge in self._table('ModuleDependencyEdge').values():
            if getattr(edge, 'topology_name', '') == topology:
                self._save(edge)
        now = datetime.now(timezone.utc).isoformat()
        receipt = AppDeploymentPlan(
            name=f'{name}@{topology}@{now}', app_name=name,
            topology_name=topology,
            placements_json=json.dumps(result['created']
                                       + result['skipped']),
            status='applied', created_at=now, applied_at=now,
            manager=self.manager)
        self._save(receipt)
        result['planReceipt'] = getattr(receipt, 'name', '')
        response.media = result
