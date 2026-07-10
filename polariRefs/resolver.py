"""
@module polariRefs.resolver

The resolution ladder (xsim-1: local rungs live, remote rungs refuse
honestly naming their phase):

    1. local tree     — manager.objectTables (today's path)
    2. local DB       — residency-demoted row via managedDB
                        (read-only RowView; typed hydration arrives
                        with the stable-objects/residency phase)
    3. shared-DB peer — NOT BUILT: xsim-3
    4. remote API     — NOT BUILT: xsim-6

Hydration rules:
- resolved instances go through the identity map keyed
  (authority, className, id) — instance a row 5 and instance b row 5
  never collapse.
- schemaVersion present + local version differs → refusal naming BOTH
  versions (OOPS-style widen path later); local version unknown →
  resolve with a provenance note, never a silent None.
- unreachable/non-local authority → honest refusal naming the instance
  and the phase that builds that rung. NEVER a silent None
  mid-simulation.
"""

import json
from typing import Any, Dict, Optional, Tuple

from polariRefs.identity_map import identity_map_for
from polariRefs.ref_format import (
    authority_key, local_identity, parse_ref, schema_version_of,
)


class RowView:
    """A residency-demoted (rung 2) row: attributes from DB columns,
    READ-ONLY — writes go through the mutation lease (xsim-2) or
    refuse. Not registered in the identity map (untyped; typed
    hydration is the residency phase's job)."""

    def __init__(self, class_name: str, fields: Dict[str, Any],
                 provenance: Dict):
        object.__setattr__(self, '_frozen', False)
        self.polariRefClassName = class_name
        self.polariRefProvenance = provenance
        for field, value in fields.items():
            if isinstance(field, str) and field.isidentifier():
                setattr(self, field, value)
        object.__setattr__(self, '_frozen', True)

    def __setattr__(self, name, value):
        if getattr(self, '_frozen', False):
            raise AttributeError(
                f'RowView({self.polariRefClassName}) is read-only — '
                'writes to demoted/remote objects go through the '
                'mutation lease (xsim-2), never through attribute '
                'assignment')
        object.__setattr__(self, name, value)


def _is_local_instance(name: str) -> bool:
    ident = local_identity()
    return name.strip().lower() in (
        ident['instanceId'].lower(), ident['instanceName'].lower())


def _class_installed(manager, class_name: str) -> bool:
    if class_name in (getattr(manager, 'objectTables', None) or {}):
        return True
    if class_name in (getattr(manager, 'dynamicClasses', None) or {}):
        return True
    for typing_row in getattr(manager, 'objectTyping', None) or []:
        if getattr(typing_row, 'className', '') == class_name:
            return True
    return False


def _route_authority(manager, ref) -> Tuple[str, str, Optional[Dict]]:
    """Decide WHERE the ref's authority lives →
    ('local'|'remote'|'refuse', resolved_instance, refusal|None)."""
    authority = ref['authority']
    if authority is None:
        return 'local', '', None
    if 'instance' in authority:
        target = authority['instance']
        if _is_local_instance(target):
            return 'local', target, None
        return 'remote', target, None
    # authority.module — the topology layer names the owning instance,
    # so refs survive module reallocation.
    module = authority['module']
    provider = None
    try:
        from topology.provider_registry import resolve_provider
        provider = resolve_provider(module)
    except Exception as e:                          # registry import/boot
        provider = {'ok': False, 'error': f'provider registry '
                                          f'unavailable: {e}'}
    if provider.get('ok'):
        instance = provider.get('instance', '')
        if _is_local_instance(instance):
            return 'local', instance, None
        return 'remote', instance, None
    # No topology answer — an installed local module still resolves
    # (single-node reality); an uninstalled one refuses naming the knob.
    if _class_installed(manager, ref['className']):
        return 'local', '', None
    return 'refuse', '', {
        'error': f"authority.module '{module}' resolves to no instance "
                 f"({provider.get('error', 'no provider')}) and class "
                 f"'{ref['className']}' is not installed locally",
        'suggestion': {'knob': 'ModuleAssignment (Topology tab / '
                               'pol allocate)',
                       'action': f'pol allocate {module} <instance>, '
                                 'or install the module here'}}


def _remote_refusal(ref, instance: str) -> Dict:
    ident = local_identity()
    return {
        'error': f"{ref['className']} "
                 f"'{ref['name'] or ref['id']}' lives on instance "
                 f"'{instance}' — this is '{ident['instanceId']}', the "
                 'shared object DB is not available here, and the '
                 'remote-API rung is not built yet',
        'rung': 'remote-api',
        'phase': 'xsim-6 (remote API); shared-DB rung needs '
                 'POLARI_SHARED_OBJECT_DB',
        'suggestion': {'knob': 'POLARI_SHARED_OBJECT_DB / '
                               'binding.authority',
                       'action': 'share the object DB with the owner, '
                                 'or wait for the remote-API rung'}}


def _find_in_tree(manager, ref):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        ref['className'], {}) or {}
    rows = table if isinstance(table, dict) else \
        {getattr(r, 'id', i): r for i, r in enumerate(table)}
    if ref['id']:
        return rows.get(ref['id'])
    return next((r for r in rows.values()
                 if getattr(r, 'name', '') == ref['name']), None)


def _find_in_db(manager, ref) -> Optional[RowView]:
    db = getattr(manager, 'db', None)
    if db is None or not hasattr(db, 'getAllInTable'):
        return None
    try:
        column_names, data_sets = db.getAllInTable(ref['className'])
    except Exception:
        return None
    if not column_names:
        return None
    for row in data_sets or []:
        fields = dict(zip(column_names, row))
        if ref['id'] and str(fields.get('id', '')) == ref['id']:
            pass
        elif ref['name'] and str(fields.get('name', '')) == ref['name']:
            pass
        else:
            continue
        return RowView(ref['className'], fields, {
            'rung': 'local-db',
            'note': 'residency-demoted row — read-only until typed '
                    'hydration (stable-objects phase)'})
    return None


def resolve_ref(manager, raw_ref) -> Dict:
    """The ladder. Returns {'ok', 'object', 'provenance'} or
    {'ok': False, 'refusal': {...}} — refusals always name what was
    tried and which phase builds the missing rung."""
    ok, ref, refusal = parse_ref(raw_ref)
    if not ok:
        return {'ok': False, 'refusal': refusal}
    provenance: Dict[str, Any] = {'className': ref['className'],
                                  'authority': ref['authority']}
    route, resolved_instance, refusal = _route_authority(manager, ref)
    # schemaVersion honesty (edge ledger: mismatch names both
    # versions) — checked against the AUTHORITY's profile: local here
    # for local routes; the owner's inside the shared-DB rung.
    if ref['schemaVersion'] and route == 'local':
        local_version = schema_version_of(manager, ref['className'])
        if local_version and local_version != ref['schemaVersion']:
            return {'ok': False, 'refusal': {
                'error': f"schemaVersion mismatch for "
                         f"{ref['className']}: ref carries "
                         f"'{ref['schemaVersion']}', local profile is "
                         f"'{local_version}'",
                'suggestion': {
                    'knob': 'SchemaStabilityProfile',
                    'action': 'restabilize the class or restamp the '
                              'ref (OOPS widen path arrives later)'}}}
        if not local_version:
            provenance['schemaVersionUnverified'] = (
                f"ref carries '{ref['schemaVersion']}' but "
                f"{ref['className']} has no stabilized local profile")
    if route == 'refuse':
        return {'ok': False, 'refusal': refusal}
    if route == 'remote':
        # rung 3 (xsim-3): shared-DB peer read — same MariaDB,
        # different _instance_id, permitted via PeerAgreement.
        from polariRefs.remote_hydration import hydrate_shared_db
        hydrated = hydrate_shared_db(manager, ref, resolved_instance)
        if hydrated.get('ok'):
            row = hydrated['object']
            registered = identity_map_for(manager).register(
                f'instance:{resolved_instance}', ref['className'],
                str(getattr(row, 'id', '') or ref['id'] or ref['name']),
                row)
            merged = dict(provenance)
            merged.update(hydrated['provenance'])
            merged['identity'] = registered.get('note',
                                                registered.get('error'))
            return {'ok': True, 'object': registered['instance'],
                    'provenance': merged}
        if not hydrated.get('fallthrough'):
            return {'ok': False, 'refusal': hydrated['refusal']}
        # rung 4 (remote API) is xsim-6 — refuse naming the phase.
        return {'ok': False,
                'refusal': _remote_refusal(ref, resolved_instance)}
    if resolved_instance:
        provenance['resolvedInstance'] = resolved_instance
    # rung 1: local tree
    row = _find_in_tree(manager, ref)
    if row is not None:
        provenance['rung'] = 'local-tree'
        registered = identity_map_for(manager).register(
            'local', ref['className'],
            str(getattr(row, 'id', '') or ref['id'] or ref['name']), row)
        provenance['identity'] = registered.get('note',
                                                registered.get('error'))
        return {'ok': True, 'object': registered['instance'],
                'provenance': provenance}
    # rung 2: local DB (residency-demoted)
    view = _find_in_db(manager, ref)
    if view is not None:
        provenance['rung'] = 'local-db'
        provenance.update(view.polariRefProvenance)
        return {'ok': True, 'object': view, 'provenance': provenance}
    return {'ok': False, 'refusal': {
        'error': f"no {ref['className']} "
                 f"'{ref['name'] or ref['id']}' in the local tree or "
                 'local DB',
        'tried': ['local-tree', 'local-db'],
        'suggestion': {'knob': 'binding.name',
                       'action': 'point it at an existing row'}}}


def walk_path(node: Any, path: str) -> Tuple[bool, Any, Optional[Dict]]:
    """Dotted-path walk with component_binding semantics: attributes
    first; a string value along the way is json.loads'd and walked as
    dict keys / integer list indices. Refusals list available keys."""
    for part in path.split('.') if path else []:
        if isinstance(node, str):
            try:
                node = json.loads(node)
            except (TypeError, ValueError):
                return False, None, {
                    'error': f"path '{path}' hit a non-JSON string "
                             f"before '{part}'"}
        if isinstance(node, list):
            try:
                node = node[int(part)]
                continue
            except (ValueError, IndexError):
                return False, None, {
                    'error': f"path '{path}' failed at '{part}' "
                             f"(list of {len(node)})"}
        if isinstance(node, dict):
            if part not in node:
                return False, None, {
                    'error': f"path '{path}' failed at '{part}'",
                    'availableKeys': sorted(node)[:20]}
            node = node[part]
            continue
        if hasattr(node, part):
            node = getattr(node, part)
            continue
        return False, None, {
            'error': f"path '{path}' failed at '{part}' on "
                     f'{type(node).__name__}'}
    return True, node, None


def resolve_ref_value(manager, raw_ref, stage_context=None
                      ) -> Tuple[bool, Any, Optional[Dict]]:
    """resolve_binding-shaped contract: (ok, concrete_value,
    refusal|None) — component_binding delegates authority-carrying
    objectRefs here; `stage_context` is accepted for signature parity
    (authority refs carry no stage keys)."""
    result = resolve_ref(manager, raw_ref)
    if not result['ok']:
        return False, None, result['refusal']
    ok, value, refusal = walk_path(result['object'],
                                   (raw_ref or {}).get('path', ''))
    if not ok:
        refusal = dict(refusal or {})
        refusal['provenance'] = result['provenance']
        return False, None, refusal
    return True, value, None
