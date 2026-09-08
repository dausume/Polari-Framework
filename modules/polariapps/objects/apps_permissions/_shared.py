"""@module polariapps.objects.apps_permissions._shared — what the apps_permissions row classes share (constants, seeds, helpers); split from apps_permissions_basis.py (sap-2c)."""
import json

CRUDE_VERBS = ('read', 'create', 'update', 'delete', 'events')
ADMIN_ROLES = frozenset({'admin', 'polari-admin'})
SEED_PERMISSION_PROFILES = [
    {
        'name': 'wax-print-shop-operator',
        'title': 'Wax Print Shop — operator (template)',
        'description': 'Read + write across the wax-print-shop '
                       'app\'s modules. TEMPLATE: bind an EXISTING '
                       'KC group (see /api/groups) in '
                       'kc_groups_json, then set published=true.',
        'app_name': 'wax-print-shop',
        'kc_groups_json': '[]',
        'verbs_json': '["read", "create", "update"]',
        'extra_classes_json': '[]',
        'published': False,
        'is_prior': True,
        'notes': 'seed: sep-7 template — grants nothing until a '
                 'real group is bound and it is published',
    },
    {
        'name': 'app-climate-viewer',
        'title': 'Climate — viewer (template)',
        'description': 'Read-only over the climate app\'s modules. '
                       'TEMPLATE: bind an EXISTING KC group (see '
                       '/api/groups) in kc_groups_json, then set '
                       'published=true.',
        'app_name': 'app-climate',
        'kc_groups_json': '[]',
        'verbs_json': '["read"]',
        'extra_classes_json': '[]',
        'published': False,
        'is_prior': True,
        'notes': 'seed: sep-7 template — grants nothing until a '
                 'real group is bound and it is published',
    },
]
def _loads(raw, default):
    try:
        parsed = json.loads(raw or '')
        return parsed if isinstance(parsed, type(default)) else default
    except ValueError:
        return default
def classes_for_module(module_name):
    """The class names a module registers, from the core-resident
    feature-import table (dyn-1) — the module -> classes half of the
    profile chain. CamelCase names only (SEED_* lists are data)."""
    try:
        from polariApiServer.feature_imports import (
            FEATURE_IMPORT_BLOCKS)
    except ImportError:
        return set()
    classes = set()
    for feature, blocks in FEATURE_IMPORT_BLOCKS:
        if feature != module_name:
            continue
        for _path, names in blocks:
            for n in names:
                if not n.startswith('SEED_') and n[:1].isupper():
                    classes.add(n)
    return classes
def classes_for_app(manager, app_name):
    """app -> modules -> classes (the derivation the plan names).
    Unknown app or unmapped modules simply contribute nothing —
    the verdict's evidence says what derived."""
    tables = getattr(manager, 'objectTables', None) or {}
    app = None
    for row in tables.get('PolariAppDefinition', {}).values():
        if getattr(row, 'name', '') == app_name:
            app = row
            break
    if app is None:
        return set()
    classes = set()
    for module in _loads(getattr(app, 'modules_json', '[]'), []):
        classes |= classes_for_module(str(module))
    return classes
def caller_groups(user_info):
    """(groups, sources) — the caller's grant keys. Prefers the KC
    `groups` claim (leading '/' stripped); realm/client roles also
    count so ungroomed realms still work. Sources name what was
    actually present, for the evidence trail."""
    if not user_info:
        return set(), []
    groups = set()
    sources = []
    raw = (user_info.get('raw_claims') or {})
    claim = raw.get('groups')
    if isinstance(claim, list) and claim:
        groups |= {str(g).lstrip('/') for g in claim}
        sources.append('jwt-groups-claim')
    roles = user_info.get('roles') or []
    if roles:
        groups |= {str(r) for r in roles}
        sources.append('jwt-roles')
    return groups, sources
def resolve_grants(manager, user_info):
    """The caller's UNION of granted profiles, resolved to
    apps + per-class verbs. Always evidence-bearing."""
    tables = getattr(manager, 'objectTables', None) or {}
    groups, sources = caller_groups(user_info)
    is_admin = bool(ADMIN_ROLES & groups)
    matched = []
    apps = set()
    class_verbs = {}
    for row in tables.get('AppPermissionProfile', {}).values():
        if not getattr(row, 'published', True):
            continue
        grant_keys = {str(g).lstrip('/') for g in
                      _loads(getattr(row, 'kc_groups_json', '[]'),
                             [])}
        via = sorted(groups & grant_keys)
        if not via:
            continue
        verbs = [v for v in
                 _loads(getattr(row, 'verbs_json', '[]'), [])
                 if v in CRUDE_VERBS]
        app_name = getattr(row, 'app_name', '')
        covered = set()
        if app_name:
            covered |= classes_for_app(manager, app_name)
            apps.add(app_name)
        covered |= {str(c) for c in
                    _loads(getattr(row, 'extra_classes_json',
                                   '[]'), [])}
        for cls in covered:
            class_verbs.setdefault(cls, set()).update(verbs)
        matched.append({'profile': getattr(row, 'name', ''),
                        'app': app_name, 'verbs': verbs,
                        'via': via})
    return {
        'authenticated': user_info is not None,
        'admin': is_admin,
        'groupSources': sources,
        'groups': sorted(groups),
        'profiles': matched,
        'apps': sorted(apps),
        'classes': {cls: sorted(verbs)
                    for cls, verbs in sorted(class_verbs.items())},
    }
def permission_verdict(manager, user_info, class_name, verb):
    """The admission verdict for one CRUDE act — evidence-carrying,
    never a bare boolean (the group-authority discipline)."""
    grants = resolve_grants(manager, user_info)
    if grants['admin']:
        return {'allowed': True, 'why': 'admin role bypass',
                'via': sorted(ADMIN_ROLES & set(grants['groups'])),
                'class': class_name, 'verb': verb}
    allowed_verbs = grants['classes'].get(class_name, [])
    if verb in allowed_verbs:
        via = [p['profile'] for p in grants['profiles']
               if verb in p['verbs']]
        return {'allowed': True,
                'why': 'granted by profile(s)', 'via': via,
                'class': class_name, 'verb': verb}
    return {
        'allowed': False,
        'why': ('no authenticated identity — no profile can match'
                if not grants['authenticated'] else
                f'no granted profile covers {class_name}:{verb}'),
        'via': [],
        'class': class_name, 'verb': verb,
        'suggestion': {
            'knob': 'AppPermissionProfile rows + KC group '
                    'membership (see /api/apps/permissions/my)',
            'action': 'grant a profile whose app covers this class '
                      'and whose verbs include the act, to a KC '
                      'group the caller belongs to',
        },
    }
