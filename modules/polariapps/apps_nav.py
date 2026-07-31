"""
@cross-cutting
@module polariapps.apps_nav

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
  - polariapps.selftest_apps
"""

import json

TRI_STATES = ('enabled', 'absent', 'unknown')
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


def _availability(module, feature_check):
    if not module:
        return 'enabled'  # core surfaces gate nothing
    if feature_check is None:
        return 'unknown'
    try:
        return 'enabled' if feature_check(module) else 'absent'
    except Exception:
        return 'unknown'


def _nav_item(item, feature_check, requires_map):
    module = item.get('requires_module', '')
    out = {'label': item.get('label', ''),
           'kind': item.get('kind', 'page'),
           'availability': _availability(module, feature_check)}
    for src, dst in (('route', 'route'), ('ref', 'ref'),
                     ('requires_module', 'requiresModule')):
        if item.get(src):
            out[dst] = item[src]
    if out['availability'] == 'absent':
        out['bringup'] = {'route': BRINGUP_ROUTE}
        chain = (requires_map or {}).get(module)
        if chain:
            out['bringup']['requires'] = list(chain)
    return out


def _page_label(route):
    tail = route.strip('/').split('/')[-1] or route
    return tail.replace('-', ' ').replace('_', ' ').title()


def _app_nav(row, feature_check, requires_map):
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
            'items': [_nav_item(i, feature_check, requires_map)
                      for i in grp.get('items', [])]})
    return {
        'name': getattr(row, 'name', ''),
        'title': getattr(row, 'title', ''),
        'useCase': getattr(row, 'use_case', ''),
        'discipline': getattr(row, 'discipline', '') or '',
        'personas': _loads(row, 'personas_json', []),
        'pages': _loads(row, 'pages_json', []),
        'modules': _loads(row, 'modules_json', []),
        'navSynthesized': synthesized,
        'nav': groups,
    }


def apps_nav(manager, feature_check=_UNSET, requires_map=None):
    """Every app's nav tree with derived availability, plus the
    persona -> app-names index the nav-5 chips filter on."""
    if feature_check is _UNSET:
        feature_check = default_feature_check()
    if requires_map is None:
        requires_map = default_requires_map()
    apps = [_app_nav(row, feature_check, requires_map)
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
                   requires_map=None):
    """One app's nav tree — 404-shaped refusal for unknown names."""
    if feature_check is _UNSET:
        feature_check = default_feature_check()
    if requires_map is None:
        requires_map = default_requires_map()
    for row in _rows(manager, 'PolariAppDefinition'):
        if getattr(row, 'name', '') == name:
            report = _app_nav(row, feature_check, requires_map)
            report['ok'] = True
            report['gatingReadable'] = feature_check is not None
            return report
    return {'ok': False, 'error': f"no app named '{name}'"}
