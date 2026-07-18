"""
@cross-cutting
@module polariapps.apps_analysis

Pure Polari-App logic (tt-12): plan computation against a topology,
the exportable app package (same portable-document idiom as
topology packages — credential-free, kind-tagged, schema-versioned,
deployable later by pointing the pol CLI at the JSON file), and the
rows-only apply. NO framework imports; manager duck-typed.

Plan rows are SUGGESTIONS: each unplaced module names the exact
`pol allocate` command; apply writes ModuleAssignment rows and
nothing else — deploying containers stays `pol topology apply`,
always human-invoked.

@consumers
  - polariapps.apps_api / polariapps.selftest_apps
  - polari-cli scripts/apps.sh (export/deploy round trip)
"""

import json

APP_PACKAGE_KIND = 'polari-app-package'
APP_SCHEMA_VERSION = '1'


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _loads(row, attr, default):
    try:
        text = getattr(row, attr, '') or ''
        return json.loads(text) if text else default
    except Exception:
        return default


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _module_available(manager, module):
    """Honest availability: an installed PolariModule row or ANY
    ModuleAssignment — absence means the module isn't in this
    image/topology at all."""
    row = _named(manager, 'PolariModule', module)
    if row is not None and getattr(row, 'status', '') == 'installed':
        return True
    return any(getattr(a, 'module_name', '').split('.')[0] == module
               for a in _rows(manager, 'ModuleAssignment'))


def app_plan(manager, app_name, topology_name):
    """Where each of the app's modules stands on one topology:
    already-placed (enabled assignment exists), needs-assignment
    (available but unplaced — suggested instance + the exact
    command), or missing (not in this image; build/install first)."""
    app = _named(manager, 'PolariAppDefinition', app_name)
    if app is None:
        return {'ok': False,
                'error': f'no PolariAppDefinition named "{app_name}"'}
    instances = sorted(
        getattr(i, 'name', '') for i in _rows(
            manager, 'InstanceDefinition')
        if getattr(i, 'topology_name', '') == topology_name)
    if not instances:
        return {'ok': False,
                'error': f'no instances in topology '
                         f'"{topology_name}"'}
    # Deterministic suggestion: the alphabetically-first instance
    # whose kind carries a backend (falls back to first instance).
    backendish = [i for i in instances
                  for row in _rows(manager, 'InstanceDefinition')
                  if getattr(row, 'name', '') == i
                  and 'backend' in getattr(row, 'kind', '')]
    suggested_instance = (backendish[0] if backendish
                          else instances[0])
    placements = []
    for module in _loads(app, 'modules_json', []):
        placed_on = sorted({
            getattr(a, 'instance_name', '')
            for a in _rows(manager, 'ModuleAssignment')
            if getattr(a, 'topology_name', '') == topology_name
            and getattr(a, 'state', '') == 'enabled'
            and getattr(a, 'module_name', '').split('.')[0]
            == module})
        if placed_on:
            placements.append({
                'module': module, 'status': 'already-placed',
                'instances': placed_on, 'suggestedInstance': '',
                'suggestedCommand': ''})
        elif _module_available(manager, module):
            placements.append({
                'module': module, 'status': 'needs-assignment',
                'instances': [],
                'suggestedInstance': suggested_instance,
                'suggestedCommand':
                    f'pol allocate {module} {suggested_instance}'})
        else:
            placements.append({
                'module': module, 'status': 'missing',
                'instances': [], 'suggestedInstance': '',
                'suggestedCommand':
                    f'module "{module}" is not in this image — '
                    'build/install it first'})
    placed = sum(1 for p in placements
                 if p['status'] == 'already-placed')
    return {
        'ok': True, 'app': app_name, 'topology': topology_name,
        'title': getattr(app, 'title', ''),
        'useCase': getattr(app, 'use_case', ''),
        'pages': _loads(app, 'pages_json', []),
        'placements': placements,
        'readiness': placed / len(placements) if placements else 0.0,
        'note': 'applying writes ModuleAssignment rows only; '
                'deploying containers stays '
                '`pol topology apply` (human-invoked)',
    }


def export_app(manager, app_name, topology_name=''):
    """The portable, credential-free app package — a JSON file the
    pol CLI can deploy later (`pol apps deploy <file.json>`)."""
    app = _named(manager, 'PolariAppDefinition', app_name)
    if app is None:
        return {'ok': False,
                'error': f'no PolariAppDefinition named "{app_name}"'}
    doc = {
        'kind': APP_PACKAGE_KIND,
        'schema_version': APP_SCHEMA_VERSION,
        'app': {
            'name': getattr(app, 'name', ''),
            'title': getattr(app, 'title', ''),
            'use_case': getattr(app, 'use_case', ''),
            'description': getattr(app, 'description', ''),
            'modules_json': getattr(app, 'modules_json', '[]'),
            'pages_json': getattr(app, 'pages_json', '[]'),
            'notes': getattr(app, 'notes', ''),
        },
    }
    if topology_name:
        plan = app_plan(manager, app_name, topology_name)
        if plan.get('ok'):
            doc['plan'] = {'topology': topology_name,
                           'placements': plan['placements']}
    return {'ok': True, 'document': doc}


def validate_app_document(doc):
    """Refuse non-app documents honestly (the CLI feeds files in)."""
    if not isinstance(doc, dict) or doc.get(
            'kind') != APP_PACKAGE_KIND:
        return f'not a {APP_PACKAGE_KIND} document'
    if str(doc.get('schema_version', '')) != APP_SCHEMA_VERSION:
        return (f'schema_version {doc.get("schema_version")!r} != '
                f'supported {APP_SCHEMA_VERSION!r}')
    if not (doc.get('app') or {}).get('name'):
        return 'app document without an app.name'
    return ''


def apply_app(manager, app_name, topology_name, assignment_factory,
              save=lambda row: None):
    """Write the plan's needs-assignment rows (rows ONLY — the
    deploy suggestion comes back as text). Idempotent: modules
    already placed are skipped."""
    plan = app_plan(manager, app_name, topology_name)
    if not plan.get('ok'):
        return plan
    created, skipped = [], []
    for placement in plan['placements']:
        if placement['status'] == 'already-placed':
            skipped.append({'module': placement['module'],
                            'reason': 'already placed on '
                            + ', '.join(placement['instances'])})
            continue
        if placement['status'] == 'missing':
            skipped.append({'module': placement['module'],
                            'reason': 'not in this image'})
            continue
        instance = placement['suggestedInstance']
        row = assignment_factory(
            name=f'{placement["module"]}@{instance}',
            module_name=placement['module'],
            instance_name=instance, state='enabled',
            topology_name=topology_name,
            notes=f'placed by app "{app_name}" '
                  '(pol apps deploy / /api/apps/apply)')
        save(row)
        created.append({'module': placement['module'],
                        'instance': instance})
    return {
        'ok': True, 'app': app_name, 'topology': topology_name,
        'created': created, 'skipped': skipped,
        'suggestedCommand': 'pol topology apply --plan',
        'note': 'rows written; deploying containers stays the '
                'human-run pol command',
    }
