"""
@cross-cutting
@module polariapps.custom.apps_roles

ROLES -> APPS, and one person's refinement of it (his ask 2026-09-18):

    "We want to be able to have a primary role and additional roles. We will want to be able to tie Apps to
     roles so that the user can see and navigate to the apps they need more easily. And then the user should
     be able to refine that further and add apps they want to use or remove ones they do not care about."

The read model behind `/api/apps/roles` and `/api/apps/mine`. Three layers, in this order:

  1. INSTITUTIONAL — `RoleAppBinding` rows: role (a Keycloak GROUP name) -> ordered app names. Derived from
     what the modules declare (`app.roles` in a module's `polari-app.json`; the older `personas` list as a
     fallback where the persona name IS the role name), or set by an administrator, or accepted from a
     role-play review. A derivation NEVER overwrites an administrator's row.
  2. HELD — which of those roles this caller actually has: the token's `groups` claim, nothing stored. A row
     can therefore never claim a role the person does not hold.
  3. PERSONAL — `UserAppPreference`: the primary role, plus added and hidden apps. Keyed by the Keycloak
     `sub` alone (his rule D18-1); there is no username anywhere in this file's writes.

Hiding an app HIDES it. It grants nothing and revokes nothing — permission stays with
`accessControl.app_permissions_gate` and the `AppPermissionProfile` rows.

The role-play review is a SUGGESTION and only ever that: `suggested_for_role()` reads what a role was recorded
using and offers it; binding it is an administrator's explicit POST (knobs-and-suggestions).

NO framework imports at module level; the manifest and review lookups are guarded and duck-typed (apps_nav's
rule) — a missing security module or an unreadable manifest degrades to "nothing suggested", loudly in the
payload, never a crash.

@consumers
  - polariapps.apps_api (/api/apps/roles, /api/apps/roles/{role}, /api/apps/roles/{role}/suggested,
    /api/apps/mine)
  - polariapps.apps_selftest
"""

import json
import types
from datetime import datetime, timezone

#: How a binding came to exist, and how a manifest-sourced one was derived.
from polariapps.objects.apps_roles._shared import (  # noqa: F401
    BINDING_SOURCES, DERIVATIONS, VIA,
)

BINDING_TABLE = 'RoleAppBinding'
PREFERENCE_TABLE = 'UserAppPreference'

#: Same escape hatch security_observe uses: a test double cannot construct tree objects, and a foreign object
#: in the manager's own table breaks the CRUDE view of the class. Keyed by id(objectTables).
_FALLBACK = {}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _tables(manager):
    return getattr(manager, 'objectTables', None) or {}


def _rows(manager, table):
    tables = _tables(manager)
    rows = list((tables.get(table) or {}).values())
    seen = {getattr(r, 'name', '') for r in rows}
    return rows + [r for n, r in _FALLBACK.get(id(tables), {}).get(table, {}).items()
                   if n not in seen]


def _find(manager, table, name):
    for row in _rows(manager, table):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _new_row(manager, table, cls, fields):
    """Construct the tree object the way every module API does. A manager that cannot (a test double) keeps a
    plain row in _FALLBACK — never in the manager's own table (the 2026-09-16 PolyTyping gotcha)."""
    try:
        if getattr(manager, 'idList', None) is not None:
            return cls(manager=manager, **fields)
    except Exception:  # noqa: BLE001
        pass
    row = types.SimpleNamespace(**fields)
    _FALLBACK.setdefault(id(_tables(manager)), {}).setdefault(table, {})[fields['name']] = row
    return row


def _loads(row, attr, default):
    try:
        text = getattr(row, attr, '') or ''
        value = json.loads(text) if text else default
        return value if isinstance(value, type(default)) else default
    except Exception:  # noqa: BLE001
        return default


def _persist(manager):
    """ONE trailing persist per burst (ledger §51) — a preference set through the API must survive the next
    redeploy. Never raises: a manager with no DB is a perfectly good test double."""
    try:
        from polariApiServer.persist_debounce import schedule_persist
        schedule_persist(manager)
    except Exception:  # noqa: BLE001
        pass


def _save(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001
        pass
    _persist(manager)


# ---------------------------------------------------------------- apps

def app_index(manager):
    """{name: {name, title, route}} for every PolariAppDefinition. The route is the app's own home
    (`/app/<name>`) — it exists for every app, so a bound app can always be navigated to."""
    out = {}
    for row in _rows(manager, 'PolariAppDefinition'):
        name = getattr(row, 'name', '')
        if not name:
            continue
        out[name] = {'name': name, 'title': getattr(row, 'title', '') or name,
                     'route': f'/app/{name}'}
    return out


def _app_modules(row):
    return [str(m).split('.')[0] for m in _loads(row, 'modules_json', [])]


# ------------------------------------------------ derivations (manifests, personas)

def manifest_role_modules():
    """{module alias: [role names]} from every module manifest's `app.roles`.

    Aliases are the manifest id, its package and its directory name, because an app's `modules_json` names
    modules by whichever of those the seed used. Returns {} when the manifest machinery is unreadable —
    the derivation then contributes nothing and says so."""
    out = {}
    try:
        from moduleService import manifests
        packages = manifests.all_packages()
    except Exception:  # noqa: BLE001
        return out
    for pkg in packages:
        try:
            manifest = manifests.load(pkg)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(manifest, dict):
            continue
        roles = ((manifest.get('app') or {}).get('roles') or [])
        roles = [str(r).strip() for r in roles if str(r).strip()]
        if not roles:
            continue
        for alias in {manifest.get('id') or '', manifest.get('package') or '', pkg}:
            if alias:
                out.setdefault(alias, [])
                for role in roles:
                    if role not in out[alias]:
                        out[alias].append(role)
    return out


def derive_bindings(manager, role_modules=None):
    """{role: {'apps': [...], 'derived_from': 'app.roles'|'personas'}} — what the DATA says, before any
    administrator touched anything.

    `app.roles` wins: a module that declares roles binds every app that carries the module. The older
    `personas` list is the FALLBACK, and only where the persona name IS a role name that nothing declared —
    an app tagged 'researcher' has always meant "a researcher wants this"."""
    if role_modules is None:
        role_modules = manifest_role_modules()
    declared, personas = {}, {}
    for row in _rows(manager, 'PolariAppDefinition'):
        name = getattr(row, 'name', '')
        if not name:
            continue
        for module in _app_modules(row):
            for role in role_modules.get(module, ()):
                declared.setdefault(role, [])
                if name not in declared[role]:
                    declared[role].append(name)
        for persona in _loads(row, 'personas_json', []):
            persona = str(persona).strip()
            if not persona:
                continue
            personas.setdefault(persona, [])
            if name not in personas[persona]:
                personas[persona].append(name)
    out = {role: {'apps': sorted(apps), 'derived_from': 'app.roles'}
           for role, apps in declared.items()}
    for persona, apps in personas.items():
        if persona not in out:
            out[persona] = {'apps': sorted(apps), 'derived_from': 'personas'}
    return out


def ensure_bindings(manager, role_modules=None, save=True):
    """Converge the derived bindings into RoleAppBinding rows, idempotently.

    An `admin` (or `prototype-review`) row is LEFT ALONE — a person's decision outranks a derivation, the same
    rule the app-definition upsert follows with `is_prior`. A `manifest` row is rewritten when the derivation
    changed, so editing a manifest reaches the live instance without anybody acting.

    Returns {'created': [...], 'updated': [...], 'kept': [...]} — evidence, printed by the selftest."""
    from polariapps.objects.apps_roles.RoleAppBinding import RoleAppBinding
    derived = derive_bindings(manager, role_modules)
    report = {'created': [], 'updated': [], 'kept': []}
    for role, info in sorted(derived.items()):
        row = _find(manager, BINDING_TABLE, role)
        if row is None:
            _new_row(manager, BINDING_TABLE, RoleAppBinding, {
                'name': role, 'role': role,
                'apps_json': json.dumps(info['apps']),
                'source': 'manifest', 'derived_from': info['derived_from'],
                'updated_at': _now(), 'updated_by': '',
                'notes': 'derived — an administrator POST to /api/apps/roles/%s replaces it' % role,
                'is_prior': True})
            report['created'].append(role)
            continue
        if getattr(row, 'source', 'manifest') != 'manifest':
            report['kept'].append(role)
            continue
        if _loads(row, 'apps_json', []) != info['apps'] or \
                getattr(row, 'derived_from', '') != info['derived_from']:
            row.apps_json = json.dumps(info['apps'])
            row.derived_from = info['derived_from']
            row.updated_at = _now()
            report['updated'].append(role)
            if save:
                _save(manager, row)
        else:
            report['kept'].append(role)
    return report


# ---------------------------------------------------------------- reads

def binding_apps(manager, role):
    row = _find(manager, BINDING_TABLE, role)
    return _loads(row, 'apps_json', []) if row is not None else []


def bindings(manager, role_modules=None, converge=True):
    """Every binding, with the apps resolved to {name, title, route}. `converge` runs the derivation first so
    a read is always current with the manifests (it is idempotent and cheap)."""
    if converge:
        ensure_bindings(manager, role_modules)
    index = app_index(manager)
    out = []
    for row in _rows(manager, BINDING_TABLE):
        names = _loads(row, 'apps_json', [])
        out.append({
            'role': getattr(row, 'role', '') or getattr(row, 'name', ''),
            'source': getattr(row, 'source', 'manifest'),
            'derivedFrom': getattr(row, 'derived_from', ''),
            'updatedAt': getattr(row, 'updated_at', ''),
            'apps': [index[n] for n in names if n in index],
            'unknownApps': [n for n in names if n not in index],
        })
    out.sort(key=lambda b: b['role'])
    return {'ok': True, 'bindings': out,
            'sources': list(BINDING_SOURCES),
            'note': 'a `manifest` binding is re-derived on every read from the modules\' own '
                    '`app.roles` (personas as the fallback); an `admin` binding is never overwritten'}


def set_binding(manager, role, apps, source='admin', by='', notes=''):
    """Bind a role to an ORDERED list of apps. Refuses unknown app names with the list, so an administrator
    can act on the refusal. `by` is a Keycloak `sub` (D18-1) or ''."""
    from polariapps.objects.apps_roles.RoleAppBinding import RoleAppBinding
    role = (role or '').strip()
    if not role:
        return {'ok': False, 'error': 'a role name is required'}
    if source not in BINDING_SOURCES:
        return {'ok': False, 'error': f'source must be one of {list(BINDING_SOURCES)}'}
    if not isinstance(apps, list):
        return {'ok': False, 'error': 'payload needs {apps: [app names]}'}
    index = app_index(manager)
    wanted, unknown = [], []
    for name in apps:
        name = str(name).strip()
        if not name or name in wanted:
            continue
        (wanted if name in index else unknown).append(name)
    if unknown:
        return {'ok': False,
                'error': 'unknown app(s): %s' % ', '.join(sorted(unknown)),
                'knownApps': sorted(index)}
    row = _find(manager, BINDING_TABLE, role)
    fields = {'name': role, 'role': role, 'apps_json': json.dumps(wanted),
              'source': source, 'derived_from': '', 'updated_at': _now(),
              'updated_by': by or '', 'notes': notes, 'is_prior': False}
    created = row is None
    if created:
        row = _new_row(manager, BINDING_TABLE, RoleAppBinding, fields)
    else:
        for key, value in fields.items():
            setattr(row, key, value)
    _save(manager, row)
    return {'ok': True, 'role': role, 'created': created, 'source': source,
            'apps': [index[n] for n in wanted]}


def suggested_for_role(manager, role):
    """What a role-play review says the role actually USED, offered as a SUGGESTION (never bound).

    The review lives in the security module; this reads it through a guarded import so an instance without
    security answers honestly instead of failing. `bound` marks the apps the current binding already has."""
    role = (role or '').strip()
    if not role:
        return {'ok': False, 'error': 'a role name is required'}
    index = app_index(manager)
    already = binding_apps(manager, role)
    suggestions, why = [], ''
    try:
        from security.custom.security_observe import review as _review
        report = _review(manager, role)
    except Exception as exc:  # noqa: BLE001
        report, why = None, f'no role-play review available ({exc.__class__.__name__}) — is the security module loaded?'
    for used in ((report or {}).get('apps') or []):
        name = str(used.get('item') or '')
        if not name or name not in index:
            continue
        entry = dict(index[name])
        entry['count'] = used.get('count', 0)
        entry['lastSeen'] = used.get('last_seen', '')
        entry['bound'] = name in already
        suggestions.append(entry)
    suggestions.sort(key=lambda s: (-int(s.get('count') or 0), s['name']))
    return {'ok': True, 'role': role, 'suggested': suggestions,
            'boundNow': [index[n] for n in already if n in index],
            'why': why,
            'note': 'SUGGESTION ONLY — a review records what a role was seen doing; binding it is an '
                    'explicit POST /api/apps/roles/%s by an administrator' % role}


# --------------------------------------------------------------- my apps

def caller_sub_and_groups(user_info):
    """(sub, held roles) for the caller. The roles a person holds ARE the `groups` claim of their token — the
    same key the permission model grants by — so nothing about role membership is ever stored here."""
    if not isinstance(user_info, dict):
        return '', []
    sub = str(user_info.get('sub') or '')
    try:
        from polariapps.objects.apps_permissions._shared import caller_groups
        groups, _sources = caller_groups(user_info)
    except Exception:  # noqa: BLE001
        groups = set(str(r) for r in (user_info.get('roles') or []))
        raw = user_info.get('raw_claims') or {}
        if isinstance(raw.get('groups'), list):
            groups |= {str(g).lstrip('/') for g in raw['groups']}
    return sub, sorted(groups)


def _preference(manager, sub):
    return _find(manager, PREFERENCE_TABLE, sub)


def my_apps(manager, user_info, role_modules=None, converge=True):
    """Everything the shell needs to render "My apps" for the signed-in caller.

    401-shaped refusal without an identity: this answer is about ONE person, and a person is a Keycloak `sub`.
    A caller who holds no bound role gets an empty list and no error — the catalogue is still there."""
    sub, held = caller_sub_and_groups(user_info)
    if not sub:
        return {'ok': False, 'status': 401,
                'error': 'sign in first — /api/apps/mine answers for the signed-in person, '
                         'who is identified by their Keycloak subject id'}
    if converge:
        ensure_bindings(manager, role_modules)
    index = app_index(manager)
    pref = _preference(manager, sub)
    added = _loads(pref, 'added_apps_json', []) if pref is not None else []
    removed = _loads(pref, 'removed_apps_json', []) if pref is not None else []

    bound = {role: binding_apps(manager, role) for role in held}
    stored_primary = (getattr(pref, 'primary_role', '') if pref is not None else '') or ''
    primary = stored_primary if stored_primary in held else ''
    if not primary:
        primary = next((role for role in held if bound.get(role)), '')
    additional = [role for role in held if role != primary]

    apps, seen = [], set()

    def _offer(name, via, role):
        if name in seen or name in removed or name not in index:
            return
        seen.add(name)
        entry = dict(index[name])
        entry['via'] = via
        entry['role'] = role
        entry['removable'] = True
        apps.append(entry)

    for name in bound.get(primary, []):
        _offer(name, 'primary', primary)
    for role in additional:
        for name in bound.get(role, []):
            _offer(name, 'additional', role)
    for name in added:
        _offer(name, 'added', '')

    bound_names = {n for names in bound.values() for n in names}
    suggestions = [dict(index[n], why='bound to a role you hold')
                   for n in removed if n in index and n in bound_names]
    return {
        'ok': True,
        'sub': sub,
        'held_roles': held,
        'primary_role': primary,
        'additional_roles': additional,
        'apps': apps,
        'removed': [index[n] if n in index else {'name': n, 'title': n, 'route': ''}
                    for n in removed],
        'suggestions': suggestions,
        'unboundRoles': [role for role in held if not bound.get(role)],
        'note': 'hiding an app hides it — it grants and revokes nothing (permission stays with the '
                'AppPermissionProfile gate)',
    }


def update_my_apps(manager, user_info, payload, role_modules=None):
    """`{primary_role?, add?, remove?, restore?}` for the signed-in caller.

    `primary_role` must be a role the person HOLDS — the token is the authority, not the row; asking for one
    they do not hold is refused with the roles they do. `add`/`remove`/`restore` are app names; unknown names
    are refused with the known list rather than silently dropped."""
    from polariapps.objects.apps_roles.UserAppPreference import UserAppPreference
    sub, held = caller_sub_and_groups(user_info)
    if not sub:
        return {'ok': False, 'status': 401,
                'error': 'sign in first — a preference belongs to a Keycloak subject id'}
    if not isinstance(payload, dict):
        return {'ok': False, 'status': 400, 'error': 'payload must be a JSON object'}
    index = app_index(manager)

    def _names(key):
        value = payload.get(key) or []
        if not isinstance(value, list):
            return None, f'{key} must be a list of app names'
        out = []
        for name in value:
            name = str(name).strip()
            if name and name not in out:
                out.append(name)
        unknown = [n for n in out if n not in index]
        if unknown:
            return None, 'unknown app(s) in %s: %s' % (key, ', '.join(sorted(unknown)))
        return out, ''

    to_add, err_add = _names('add')
    to_remove, err_remove = _names('remove')
    to_restore, err_restore = _names('restore')
    problem = err_add or err_remove or err_restore
    if problem:
        return {'ok': False, 'status': 400, 'error': problem, 'knownApps': sorted(index)}

    primary = payload.get('primary_role')
    if primary is not None:
        primary = str(primary).strip()
        if primary and primary not in held:
            return {'ok': False, 'status': 400,
                    'error': f"'{primary}' is not a role you hold — your primary role must be one of your own "
                             'roles (they come from your token, not from this row)',
                    'held_roles': held}

    row = _preference(manager, sub)
    if row is None:
        row = _new_row(manager, PREFERENCE_TABLE, UserAppPreference, {
            'name': sub, 'sub': sub, 'primary_role': '',
            'added_apps_json': '[]', 'removed_apps_json': '[]',
            'updated_at': _now()})
    added = _loads(row, 'added_apps_json', [])
    removed = _loads(row, 'removed_apps_json', [])

    for name in to_add:
        if name not in added:
            added.append(name)
        if name in removed:
            removed.remove(name)
    for name in to_remove:
        if name not in removed:
            removed.append(name)
        if name in added:
            added.remove(name)
    for name in to_restore:
        if name in removed:
            removed.remove(name)

    if primary is not None:
        row.primary_role = primary
    row.added_apps_json = json.dumps(added)
    row.removed_apps_json = json.dumps(removed)
    row.updated_at = _now()
    _save(manager, row)

    result = my_apps(manager, user_info, role_modules, converge=False)
    result['saved'] = {'primary_role': getattr(row, 'primary_role', ''),
                       'added': added, 'removed': removed}
    return result
