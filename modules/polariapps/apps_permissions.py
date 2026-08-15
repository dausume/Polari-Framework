"""
@cross-cutting
@module polariapps.apps_permissions
@tags @xc:accessControl

sep-7 (separation plan decisions 10/11): per-app PERMISSION
PROFILES. ONE Polari login; access composes down the object-coherent
chain: KC group -> AppPermissionProfile -> app -> its modules ->
classes -> CRUDE verbs. Profiles are ROWS (reusable, auditable);
KC groups grant profiles; the union of a caller's profiles is what
they may touch.

Identity is evidence (the group-authority precedent, built ON not
around): every verdict carries WHERE the groups came from and WHICH
profile allowed, never a bare boolean. The `groups` JWT claim is
preferred (Keycloak group-membership mapper); realm/client ROLES
also grant, so existing realms work without new mappers — the
verdict names which source matched.

Enforcement itself lives in accessControl.app_permissions_gate
(core-resident, knob POLARI_APP_PERMISSIONS=off|advisory|enforce,
default off) — this module is the model + resolution only, so the
gate degrades honestly when polariapps is absent.

@consumers
  - accessControl.app_permissions_gate (CRUDE enforcement)
  - polariapps.apps_api (/api/apps/permissions/*)
  - polariapps.selftest_apps
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

#: The CRUDE verb vocabulary. 'events' (STOMP subscriptions) is in
#: the vocabulary but NOT yet enforced anywhere — stated, not
#: implied working.
CRUDE_VERBS = ('read', 'create', 'update', 'delete', 'events')

#: Roles that bypass profiles entirely (the appstore convention).
ADMIN_ROLES = frozenset({'admin', 'polari-admin'})


class AppPermissionProfile(treeObject):
    """One reusable grant bundle: WHICH app (its modules' classes),
    WHICH verbs, granted to WHICH KC groups/roles."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('wax-print-shop-operator').
        name: str = '',
        title: str = '',
        description: str = '',
        # PolariAppDefinition.name whose module closure this profile
        # covers ('' = no app derivation; extra_classes_json only).
        app_name: str = '',
        # JSON list of KC group names (leading '/' tolerated) AND/OR
        # realm/client role names that GRANT this profile.
        kc_groups_json: str = '[]',
        # JSON list of CRUDE_VERBS entries this profile allows.
        verbs_json: str = '["read"]',
        # JSON list of class names covered BEYOND the app derivation
        # (or instead of it when app_name is '').
        extra_classes_json: str = '[]',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.app_name = app_name
        self.kc_groups_json = kc_groups_json
        self.verbs_json = verbs_json
        self.extra_classes_json = extra_classes_json
        self.published = published
        self.is_prior = is_prior
        self.notes = notes


#: sep-7 exemplar seeds — TEMPLATES, deliberately UNPUBLISHED and
#: bound to NO groups (Dustin 2026-08-15: never invent groups — tie
#: profiles to KNOWN EXISTING groups). The realm's real groups come
#: from the auth section's existing surface (GET /api/groups, live
#: from Keycloak; GET /api/roles for realm roles): pick one, set it
#: in kc_groups_json, flip published. resolve_grants skips
#: unpublished rows, so these templates grant nothing as seeded.
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
