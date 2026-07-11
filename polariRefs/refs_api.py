"""
@cross-cutting
@module polariRefs.refs_api

HTTP surface for the ONE reference ladder (xsim-3):

  POST /api/refs/resolve   {ref: {kind:'objectRef', ...}, path?: bool}
      → {'ok', 'value'|'fields', 'provenance'} or the honest refusal.
        Read-only by construction — the resolver hands back values and
        GenericRemoteObject field dicts, never live write handles.

@consumers
  - live verification + the later frontend ref-inspector
@see /CROSS_INSTANCE_SIM_PLAN.md
"""

import falcon

from objectTreeDecorators import treeObject, treeObjectInit
from polariRefs.resolver import resolve_ref, walk_path


def _serializable(obj):
    from polariRefs.remote_hydration import GenericRemoteObject
    from polariRefs.resolver import RowView
    if isinstance(obj, GenericRemoteObject):
        return {'fields': obj.polariRefFields}
    if isinstance(obj, RowView):
        return {'fields': {k: v for k, v in obj.__dict__.items()
                           if not k.startswith('_')
                           and not k.startswith('polariRef')}}
    # a live local tree object: its persistable fields (JSON-safe
    # coerced) — this IS what a rung-4 peer hydrates from, so the
    # body must be complete, not just identifying (read-only either
    # way; writes go through apply-write).
    fields = {}
    for key, value in vars(obj).items():
        if key in ('manager', 'branch', 'inTree') or callable(value):
            continue
        if isinstance(value, (str, int, float, bool, type(None))):
            fields[key] = value
        elif isinstance(value, (list, dict)):
            try:
                import json as _json
                _json.dumps(value)
                fields[key] = value
            except (TypeError, ValueError):
                fields[key] = str(value)
        else:
            fields[key] = str(value)
    fields.setdefault('className', type(obj).__name__)
    return {'fields': fields}


class PolariRefsAPI(treeObject):
    """Reference-resolution endpoint."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/refs'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/refs/resolve', self, suffix='resolve')
            polServer.falconServer.add_route(
                '/api/refs/write', self, suffix='write')
            polServer.falconServer.add_route(
                '/api/refs/apply-write', self, suffix='apply_write')
            polServer.falconServer.add_route(
                '/api/refs/journal', self, suffix='journal')
            polServer.falconServer.add_route(
                '/api/refs/directory', self, suffix='directory')

    def on_post_resolve(self, request, response):
        try:
            body = request.get_media() or {}
        except Exception:
            body = {}
        ref = body.get('ref')
        if not isinstance(ref, dict):
            response.status = falcon.HTTP_400
            response.media = {'ok': False,
                              'error': "body needs {'ref': {...}}"}
            return
        result = resolve_ref(self.manager, ref)
        if not result['ok']:
            response.status = falcon.HTTP_404
            response.media = {'ok': False,
                              'refusal': result['refusal']}
            return
        media = {'ok': True, 'provenance': result['provenance']}
        path = str(ref.get('path', '') or '')
        if path:
            ok, value, refusal = walk_path(result['object'], path)
            if not ok:
                response.status = falcon.HTTP_404
                response.media = {'ok': False, 'refusal': refusal,
                                  'provenance': result['provenance']}
                return
            media['value'] = value
        else:
            media.update(_serializable(result['object']))
        response.media = media

    def on_post_write(self, request, response):
        """xsim-4 automated remote write. The run context comes from
        the X-Polari-Run-Id + X-Polari-Lease-Token headers (the
        remote-API presentation shape) or the ambient gated run —
        without a valid fencing token the write is refused AND
        journaled (zombie evidence, never silence)."""
        from polariRefs.remote_writes import write_remote
        try:
            body = request.get_media() or {}
        except Exception:
            body = {}
        ref = body.get('ref')
        fields = body.get('fields')
        if not isinstance(ref, dict) or not isinstance(fields, dict):
            response.status = falcon.HTTP_400
            response.media = {'ok': False,
                              'error': "body needs {'ref': {...}, "
                                       "'fields': {...}}"}
            return
        run_context = None
        header_run = request.get_header('X-Polari-Run-Id')
        header_token = request.get_header('X-Polari-Lease-Token')
        if header_run or header_token:
            try:
                run_context = {'run_id': header_run or '',
                               'lease_token': int(header_token or 0)}
            except (TypeError, ValueError):
                run_context = {'run_id': header_run or '',
                               'lease_token': 0}
        result = write_remote(self.manager, ref, fields,
                              run_context=run_context)
        if not result['ok']:
            refusal = result['refusal']
            response.status = falcon.HTTP_423 \
                if 'fenced out' in refusal.get('error', '') \
                else falcon.HTTP_403
            response.media = {'ok': False, 'refusal': refusal}
            return
        response.media = result

    def on_post_apply_write(self, request, response):
        """xsim-6 OWNER side: another instance's run asks this
        instance to mutate ITS OWN row. The epoch is validated against
        CORE (POLARI_CORE_URL when this instance is not core), local
        object locks are respected, and the application is journaled
        here too — both sides of the hop keep evidence."""
        from polariRefs.remote_api import validate_epoch_for_owner
        from polariRefs.write_journal import journal_write
        from simulationLocks.object_locks import check_write
        try:
            body = request.get_media() or {}
        except Exception:
            body = {}
        ref = body.get('ref') or {}
        fields = body.get('fields')
        class_name = str(ref.get('className', '') or '')
        row_name = str(ref.get('name', '') or '')
        row_id = str(ref.get('id', '') or '')
        if not class_name or not isinstance(fields, dict) \
                or not (row_name or row_id):
            response.status = falcon.HTTP_400
            response.media = {'ok': False,
                              'error': "body needs {'ref': {className,"
                                       " name|id}, 'fields': {...}}"}
            return
        run_id = request.get_header('X-Polari-Run-Id') or ''
        try:
            token = int(request.get_header('X-Polari-Lease-Token')
                        or 0)
        except (TypeError, ValueError):
            token = 0
        fenced = validate_epoch_for_owner(self.manager, token)
        if not fenced['ok']:
            journal_write(self.manager, run_id, 'inbound',
                          class_name, row_id or row_name,
                          list(fields), token, 'refused-stale-token',
                          notes=fenced['error'])
            response.status = falcon.HTTP_423
            response.media = {'ok': False,
                              'refusal': {'error': fenced['error'],
                                          'journaled': True}}
            return
        table = (getattr(self.manager, 'objectTables', None) or {}
                 ).get(class_name, {}) or {}
        target = table.get(row_id) if row_id else next(
            (r for r in table.values()
             if getattr(r, 'name', '') == row_name), None)
        if target is None:
            journal_write(self.manager, run_id, 'inbound', class_name,
                          row_id or row_name, list(fields), token,
                          'refused-write-failed',
                          notes='no such row on this owner')
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'refusal': {
                'error': f"this instance has no {class_name} "
                         f"'{row_name or row_id}'", 'journaled': True}}
            return
        lock = check_write(self.manager, class_name,
                           obj_id=str(getattr(target, 'id', '')),
                           obj_name=getattr(target, 'name', ''),
                           run_id=run_id)
        if not lock.get('allowed', True):
            response.status = falcon.HTTP_423
            response.media = {'ok': False, 'refusal': {
                key: value for key, value in lock.items()
                if key != 'allowed'}}
            return
        applied = []
        for field, value in fields.items():
            if isinstance(field, str) and field.isidentifier() \
                    and not field.startswith('_'):
                setattr(target, field, value)
                applied.append(field)
        try:
            self.manager.db.saveInstanceInDB(target)
        except Exception:
            pass
        entry = journal_write(
            self.manager, run_id, 'inbound', class_name,
            str(getattr(target, 'id', '') or row_name), applied,
            token, 'applied',
            notes=f"remote run '{run_id}' via apply-write")
        response.media = {'ok': True, 'fieldsChanged': sorted(applied),
                          'journal': entry.name}

    def on_get_journal(self, request, response):
        from polariRefs.write_journal import journal_rows
        response.media = {'ok': True, 'entries': journal_rows(
            self.manager, request.get_param('run') or '')}

    def _module_providers(self):
        """module package → {instance, baseUrl} from ModuleAssignment
        (topology data) + PeerNode (the admin-set, browser-reachable
        address book). A module with no remote-addressable assignment
        stays local (baseUrl '')."""
        from polariRefs.remote_hydration import _matches_instance
        rows = (getattr(self.manager, 'objectTables', None) or {})
        assignments = {}
        for a in (rows.get('ModuleAssignment', {}) or {}).values():
            if getattr(a, 'state', '') != 'enabled':
                continue
            package = (getattr(a, 'module_name', '') or '').split('.')[0]
            exact = '.' not in getattr(a, 'module_name', '')
            # exact package assignments outrank dotted sub-assignments
            if package not in assignments or exact:
                assignments[package] = getattr(a, 'instance_name', '')
        peers = list((rows.get('PeerNode', {}) or {}).values())
        providers = {}
        for package, instance_name in assignments.items():
            base_url = ''
            for node in peers:
                if _matches_instance(getattr(node, 'name', ''),
                                     instance_name):
                    base_url = (getattr(node, 'base_url', '')
                                or '').rstrip('/')
                    break
            providers[package] = {'instance': instance_name,
                                  'baseUrl': base_url}
        return providers

    def on_get_directory(self, request, response):
        """modsplit-1: THE coordination contract — core tells the
        frontend which backend serves each class. className →
        {module, instance, baseUrl}; baseUrl '' = fetch from the
        backend that served this directory. Data-driven (topology
        ModuleAssignment + PeerNode), no probing — liveness is the
        caller's honest fallback."""
        from polariApiServer.module_gating import module_of_class
        from polariRefs.ref_format import local_identity
        providers = self._module_providers()
        classes = {}
        for cls in getattr(self.polServer, 'defClassList', []) or []:
            package = module_of_class(cls)
            provider = providers.get(package)
            classes[cls.__name__] = {
                'module': package,
                'instance': provider['instance'] if provider else
                local_identity()['instanceName'],
                'baseUrl': provider['baseUrl'] if provider else ''}
        for class_name in (getattr(self.manager, 'dynamicClasses', {})
                           or {}):
            classes.setdefault(class_name, {
                'module': 'dynamic',
                'instance': local_identity()['instanceName'],
                'baseUrl': ''})
        response.media = {'ok': True,
                          'localInstance': local_identity(),
                          'modules': providers,
                          'classes': classes}
