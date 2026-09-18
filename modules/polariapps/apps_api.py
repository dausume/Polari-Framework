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

from polariapps.custom.apps_analysis import (
    app_plan, apply_app, export_app, validate_app_document,
)
from polariapps.custom.apps_nav import app_nav_report, apps_nav
from polariapps.apps_basis import (
    AppDeploymentPlan, PolariAppDefinition,
)
from topology.topology_analysis import (
    active_topology_name, resolve_edges,
)
from topology.topology_module_graph import designate_transients
from topology.topology_modules import ModuleAssignment

#: Everything an app IS, so a person can author all of it through the
#: API rather than only the half the first pass exposed. nav_json was
#: the notable omission — it is the app's own menu, i.e. the routes and
#: capabilities that make it an app at all, so without it the endpoint
#: could create an app that could not be navigated.
_APP_FIELDS = ('title', 'use_case', 'description', 'modules_json',
               'pages_json', 'nav_json', 'personas_json', 'discipline',
               'engine_page', 'notes')


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
            # sep-7: per-app permission profiles (decision 10/11).
            add('/api/apps/permissions/my', self,
                suffix='permissions_my')
            add('/api/apps/permissions/profiles', self,
                suffix='permissions_profiles')
            # roles -> apps (his ask 2026-09-18): the apps a role
            # needs, and one person's refinement of what their roles
            # gave them. NOTE the falcon gotcha (ledger §54): a
            # suffix with no matching responder makes add_route RAISE
            # at boot — every suffix below has its on_<verb>_<suffix>.
            add('/api/apps/roles', self, suffix='roles')
            add('/api/apps/roles/{role}', self, suffix='role')
            add('/api/apps/roles/{role}/suggested', self,
                suffix='role_suggested')
            add('/api/apps/mine', self, suffix='mine')

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

    def on_get_permissions_my(self, request, response):
        """sep-7: the caller's resolved grants — which profiles
        matched (and via which groups), which apps, which classes
        with which verbs, plus the enforcement MODE so the shell can
        act honestly (auto-route only when the system is on)."""
        from accessControl.app_permissions_gate import gate_mode
        from polariapps.apps_permissions_basis import resolve_grants
        ctx = getattr(request, 'context', None)
        user_info = getattr(ctx, 'user_info', None)
        grants = resolve_grants(self.manager, user_info)
        grants['ok'] = True
        grants['mode'] = gate_mode()
        response.media = grants

    def on_get_permissions_profiles(self, request, response):
        """The profile rows (no secrets live here — grants are
        group NAMES; membership stays in Keycloak)."""
        from polariapps.apps_permissions_basis import (
            classes_for_app)
        rows = []
        for row in self._table('AppPermissionProfile').values():
            app_name = getattr(row, 'app_name', '')
            rows.append({
                'name': getattr(row, 'name', ''),
                'title': getattr(row, 'title', ''),
                'app': app_name,
                'kcGroups': json.loads(
                    getattr(row, 'kc_groups_json', '[]') or '[]'),
                'verbs': json.loads(
                    getattr(row, 'verbs_json', '[]') or '[]'),
                'coveredClasses': sorted(
                    classes_for_app(self.manager, app_name))
                if app_name else json.loads(
                    getattr(row, 'extra_classes_json', '[]')
                    or '[]'),
                'published': getattr(row, 'published', True),
            })
        rows.sort(key=lambda r: r['name'])
        # ADAPTIVE (Dustin 2026-08-15: never invent groups — tie
        # profiles to KNOWN EXISTING groups): the same live sources
        # the auth section already uses (/api/groups + /api/roles,
        # via the Keycloak admin client). Honest when the admin
        # client is unconfigured/unreachable — authoring then binds
        # by name against Keycloak's own admin console instead.
        known = {'groups': [], 'realmRoles': [], 'source': ''}
        try:
            from accessControl.keycloak_client import KeycloakClient
            kc = KeycloakClient.get()
            if kc.configured:  # @property, not a method
                known['groups'] = [
                    {'name': g.get('name', ''),
                     'path': g.get('path', ''),
                     'realmRoles': g.get('realmRoles',
                                         g.get('realm_roles', []))}
                    for g in (kc.list_groups() or [])]
                known['realmRoles'] = [
                    r.get('name', '') for r in
                    (kc.list_realm_roles() or [])]
                known['source'] = 'keycloak-admin-api (live)'
            else:
                known['source'] = ('keycloak admin client not '
                                   'configured (POLARI_KEYCLOAK_'
                                   'ADMIN_URL + secret) — bind '
                                   'group names from the KC admin '
                                   'console')
        except Exception as e:  # noqa: BLE001
            known['source'] = f'keycloak unreachable: {e}'
        response.media = {'ok': True, 'profiles': rows,
                          'knownGroups': known}

    # ---- roles -> apps (his ask 2026-09-18) -------------------------

    def _user_info(self, request):
        ctx = getattr(request, 'context', None)
        info = getattr(ctx, 'user_info', None)
        return info if isinstance(info, dict) else None

    def _status(self, result, ok_status='200 OK'):
        code = int((result or {}).get('status') or 0)
        return {400: '400 Bad Request', 401: '401 Unauthorized',
                403: '403 Forbidden', 404: '404 Not Found',
                }.get(code, '400 Bad Request' if not result.get('ok')
                      else ok_status)

    def on_get_roles(self, request, response):
        """Every role -> apps binding, with each binding's SOURCE.
        Readable by anyone: it says what a role needs, never who
        holds it (membership lives in Keycloak)."""
        from polariapps.custom.apps_roles import bindings
        response.media = bindings(self.manager)

    def on_post_role(self, request, response, role):
        """Bind a role to an ordered list of apps. ADMIN ONLY
        (ADMIN_ROLES) — a binding is institutional, so it is not a
        thing a person changes for themselves; that is what
        /api/apps/mine is for."""
        from polariapps.custom.apps_roles import set_binding
        from polariapps.objects.apps_permissions._shared import (
            ADMIN_ROLES, caller_groups)
        user_info = self._user_info(request)
        if not user_info:
            return self._refuse(
                response, 'sign in first — binding a role to apps is '
                'an administrator act', '401 Unauthorized')
        groups, _sources = caller_groups(user_info)
        if not (set(ADMIN_ROLES) & set(groups)):
            return self._refuse(
                response, 'administrators only (ADMIN_ROLES: '
                + ', '.join(sorted(ADMIN_ROLES)) + ') — your own '
                'view is POST /api/apps/mine', '403 Forbidden')
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        result = set_binding(
            self.manager, role, (payload or {}).get('apps'),
            source=(payload or {}).get('source', 'admin'),
            by=str(user_info.get('sub') or ''),
            notes=(payload or {}).get('notes', ''))
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_role_suggested(self, request, response, role):
        """What a role-play review says this role actually used —
        offered, never bound (knobs-and-suggestions)."""
        from polariapps.custom.apps_roles import suggested_for_role
        result = suggested_for_role(self.manager, role)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_mine(self, request, response):
        """The signed-in person's apps: their primary role's first,
        then their additional roles', then what they added — minus
        what they hid, plus the restore suggestions."""
        from polariapps.custom.apps_roles import my_apps
        result = my_apps(self.manager, self._user_info(request))
        if not result.get('ok'):
            response.status = self._status(result)
        response.media = result

    def on_post_mine(self, request, response):
        """{primary_role?, add?, remove?, restore?} — the person's own
        refinement. The primary role must be one they HOLD."""
        from polariapps.custom.apps_roles import update_my_apps
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        result = update_my_apps(
            self.manager, self._user_info(request), payload)
        if not result.get('ok'):
            response.status = self._status(result)
        response.media = result

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
        #: A person's app is NOT a prior. The model's own contract:
        #: seeds are priors, people's edits are not — a row with
        #: is_prior False is never touched again by the upsert seed
        #: pass. Anything authored through this endpoint is therefore
        #: marked authored, or the next boot would quietly overwrite
        #: it with the seed. Pass is_prior explicitly to override
        #: (a module seeding through the API).
        updates['is_prior'] = bool(payload.get('is_prior', False))
        if created:
            row = PolariAppDefinition(
                name=name, **updates, manager=self.manager)
        else:
            for k, v in updates.items():
                setattr(row, k, v)
        self._save(row)
        response.media = {'ok': True, 'name': name,
                          'created': created,
                          'isPrior': row.is_prior,
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
