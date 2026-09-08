"""
@cross-cutting
@module polariapps.custom.apps_nav

nav-2 (NAVIGATION_REVAMP_PLAN): the app-navigation read model. Takes
the nav_json rows nav-1 seeded and answers, for THIS instance, what
every menu item's availability actually is — a TRI-STATE:

  enabled  — the item's module is downloaded + enabled here
  absent   — the module is known and NOT available; the item still
             renders, carrying a bring-online affordance
             (/modules/bringup + the requires chain when readable)
  unknown  — the gating machinery itself is unavailable, so the
             honest answer is "cannot say" (never guessed to
             enabled, never hidden)

Items are NEVER dropped: the abstract map (structure, tech trees,
what an app WOULD offer) survives absent modules — that is the
nav-6 requirement, computed here so every consumer gets it.

Groups carry `topMenu` through from nav_json: the side menu is
always the complete map; topMenu groups are ADDITIONALLY promoted
to the shell's top bar (apps leverage both menus, replace neither).

Apps with no nav_json (the tt-12 use-case apps) get a SYNTHESIZED
'Pages' group from pages_json, flagged synthesized=True — honest
about being derived, so the shell can render every app.

NO framework imports at module level; the gating + requires lookups
are duck-typed and guarded (apps_analysis's rule) — a broken import
degrades to 'unknown', loudly in the payload, never a crash.

@consumers
  - polariapps.apps_api (/api/apps/nav, /api/apps/nav/{app})
  - polariapps.apps_selftest
"""

import json

TRI_STATES = ('enabled', 'absent', 'unknown')
#: dyn-6: the QUAD-state — 'elsewhere' is what the tri-state could
#: not say, and the reason nav could not survive a module move.
QUAD_STATES = ('enabled', 'elsewhere', 'absent', 'unknown')
BRINGUP_ROUTE = '/modules/bringup'
_UNSET = object()


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table)


def _loads(row, attr, default):
    try:
        text = getattr(row, attr, '') or ''
        return json.loads(text) if text else default
    except Exception:
        return default


def default_feature_check():
    """The real gating hook, resolved lazily and guarded: None when
    the import is unavailable (=> tri-state 'unknown')."""
    try:
        from moduleService.module_loading import feature_available
        return feature_available
    except Exception:
        return None


def default_placement_map(manager):
    """dyn-6/8: {module: {instance, baseUrl, wsUrl}} for modules
    another instance serves, from the same ModuleAssignment +
    PeerNode data the refs directory uses. {} when unreadable — the
    nav then degrades to the old tri-state, never to a guess."""
    try:
        from polariApiServer.module_gating import module_enabled
        from polariRefs.ref_format import local_identity
        rows = (getattr(manager, 'objectTables', None) or {})
        peers = {}
        for node in (rows.get('PeerNode', {}) or {}).values():
            base = (getattr(node, 'base_url', '') or '').rstrip('/')
            if base:
                peers[getattr(node, 'name', '')] = base
        here = local_identity().get('instanceName', '')
        found = {}
        for row in (rows.get('ModuleAssignment', {}) or {}).values():
            if getattr(row, 'state', '') != 'enabled':
                continue
            instance = getattr(row, 'instance_name', '')
            module = (getattr(row, 'module_name', '')
                      or '').split('.')[0]
            if not module or instance == here or module_enabled(
                    module):
                continue
            base = next((url for name, url in peers.items()
                         if name == instance or name.endswith(
                             instance) or instance.endswith(name)),
                        '')
            if base:
                found[module] = {
                    'instance': instance, 'baseUrl': base,
                    'wsUrl': base.replace('https://', 'wss://')
                    .replace('http://', 'ws://') + '/'}
        return found
    except Exception:
        return {}


def default_requires_map():
    """{module: [requires...]} from the registry, {} when
    unreadable — the affordance then just omits the chain."""
    try:
        from moduleService.module_boot_records import (
            load_module_requires,
        )
        return {m: sorted(reqs)
                for m, reqs in load_module_requires().items()}
    except Exception:
        return {}


def _availability(module, feature_check, placement=None):
    """dyn-6: QUAD-state. 'enabled' | 'elsewhere' (another instance
    serves it — carry the target, never an 'install it here' chip) |
    'absent' (admittable here) | 'unknown' (the gate itself failed).
    'elsewhere' is the state the tri-state could not express, which
    is why nav could not survive a module move."""
    if not module:
        return 'enabled'  # core surfaces gate nothing
    if feature_check is None:
        return 'unknown'
    try:
        if feature_check(module):
            return 'enabled'
    except Exception:
        return 'unknown'
    if placement and module in placement:
        return 'elsewhere'
    return 'absent'


def _nav_item(item, feature_check, requires_map, placement=None):
    module = item.get('requires_module', '')
    out = {'label': item.get('label', ''),
           'kind': item.get('kind', 'page'),
           'availability': _availability(module, feature_check,
                                         placement)}
    for src, dst in (('route', 'route'), ('ref', 'ref'),
                     ('requires_module', 'requiresModule')):
        if item.get(src):
            out[dst] = item[src]
    if out['availability'] == 'absent':
        out['bringup'] = {'route': BRINGUP_ROUTE}
        chain = (requires_map or {}).get(module)
        if chain:
            out['bringup']['requires'] = list(chain)
        # dyn-6: the app is the demand signal — offer the act, with
        # the evidence, never auto-applied.
        out['bringup']['admit'] = {
            'action': f'POST /modules/{module}/admit',
            'withDeps': f'POST /modules/{module}/admit?withDeps=true',
        }
    elif out['availability'] == 'elsewhere':
        out['servedBy'] = dict(placement.get(module) or {})
    return out


def _page_label(route):
    tail = route.strip('/').split('/')[-1] or route
    return tail.replace('-', ' ').replace('_', ' ').title()


def _app_nav(row, feature_check, requires_map,
             placement=None):
    nav = _loads(row, 'nav_json', [])
    groups = []
    synthesized = False
    if not nav:
        pages = _loads(row, 'pages_json', [])
        if pages:
            synthesized = True
            nav = [{'group': 'Pages', 'items': [
                {'label': _page_label(p), 'kind': 'page', 'route': p}
                for p in pages]}]
    for grp in nav:
        groups.append({
            'group': grp.get('group', ''),
            'topMenu': bool(grp.get('top_menu')),
            'items': [_nav_item(i, feature_check, requires_map,
                                placement)
                      for i in grp.get('items', [])]})
    modules = _loads(row, 'modules_json', [])
    return {
        'name': getattr(row, 'name', ''),
        'title': getattr(row, 'title', ''),
        'useCase': getattr(row, 'use_case', ''),
        'discipline': getattr(row, 'discipline', '') or '',
        # sep-4: the engine DATA PAGE this app carries ('' = not an
        # engine); duals keep their own UI, this rides secondary.
        'enginePage': getattr(row, 'engine_page', '') or '',
        'personas': _loads(row, 'personas_json', []),
        'pages': _loads(row, 'pages_json', []),
        'modules': modules,
        # The app-home module strip: same derivation as the items,
        # computed server-side so the shell never guesses.
        'moduleStates': {m: _availability(m, feature_check,
                                          placement)
                         for m in modules},
        # dyn-6: the app's module CLOSURE plan — what is missing and
        # the one call that brings it up, in order. Evidence-bearing
        # suggestion; nothing here acts.
        'modulePlan': _module_plan(modules, feature_check,
                                   requires_map, placement),
        'navSynthesized': synthesized,
        'nav': groups,
    }


def _module_plan(modules, feature_check, requires_map,
                 placement=None):
    """dyn-6: which of an app's modules are not live here, what
    they pull in, and the exact acts that would bring them up."""
    missing, elsewhere = [], []
    for module in modules:
        state = _availability(module, feature_check, placement)
        if state == 'absent':
            missing.append(module)
        elif state == 'elsewhere':
            elsewhere.append(module)
    closure = []
    for module in missing:
        for dep in (requires_map or {}).get(module, ()):
            if (dep not in modules and dep not in closure
                    and _availability(dep, feature_check, placement)
                    != 'enabled'):
                closure.append(dep)
    return {
        'ready': not missing and not elsewhere,
        'missingHere': missing,
        'servedElsewhere': elsewhere,
        'alsoPulledIn': sorted(closure),
        'admit': [f'POST /modules/{m}/admit?withDeps=true'
                  for m in missing],
        'note': 'suggestion only — admitting is an explicit act',
    }


def apps_nav(manager, feature_check=_UNSET, requires_map=None,
             placement=None):
    """Every app's nav tree with derived availability, plus the
    persona -> app-names index the nav-5 chips filter on."""
    if feature_check is _UNSET:
        feature_check = default_feature_check()
    if requires_map is None:
        requires_map = default_requires_map()
    if placement is None:
        placement = default_placement_map(manager)
    apps = [_app_nav(row, feature_check, requires_map, placement)
            for row in _rows(manager, 'PolariAppDefinition')]
    apps.sort(key=lambda a: (a['discipline'] == '', a['name']))
    personas = {}
    for app in apps:
        for persona in app['personas']:
            personas.setdefault(persona, []).append(app['name'])
    return {'ok': True,
            'gatingReadable': feature_check is not None,
            'apps': apps, 'personas': personas}


def app_nav_report(manager, name, feature_check=_UNSET,
                   requires_map=None, placement=None):
    """One app's nav tree — 404-shaped refusal for unknown names."""
    if feature_check is _UNSET:
        feature_check = default_feature_check()
    if requires_map is None:
        requires_map = default_requires_map()
    if placement is None:
        placement = default_placement_map(manager)
    for row in _rows(manager, 'PolariAppDefinition'):
        if getattr(row, 'name', '') == name:
            report = _app_nav(row, feature_check, requires_map,
                              placement)
            report['ok'] = True
            report['gatingReadable'] = feature_check is not None
            return report
    return {'ok': False, 'error': f"no app named '{name}'"}
