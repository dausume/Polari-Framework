"""
@module cicd.custom.cicd_rows

Reading the cicd tables back — the shapes the doors and the pages answer with.

`everything(manager, device)` is the ONE read the pipeline makes at the top of a run: settings + stages +
routes in a single answer, which `cicd-sync.sh pull` turns straight into `device.env`. One request, because
a pipeline that has to make four is a pipeline that half-configures itself when the third one times out.
"""
import json


def _table(manager, class_name):
    return list(((getattr(manager, 'objectTables', None) or {}).get(class_name, {}) or {}).values())


def _list(v):
    try:
        out = json.loads(v or '[]')
        return out if isinstance(out, list) else []
    except Exception:
        return []


def _dict(v):
    try:
        out = json.loads(v or '{}')
        return out if isinstance(out, dict) else {}
    except Exception:
        return {}


def devices(manager):
    return sorted(_table(manager, 'PipelineDevice'), key=lambda r: str(getattr(r, 'name', '')))


def device_named(manager, name):
    for r in devices(manager):
        if str(getattr(r, 'name', '')) == str(name):
            return r
    return None


def default_device(manager, asked=''):
    """The device a door is about: the one asked for, else the only one, else none.

    Deliberately NOT "the first alphabetically": a core with two pipeline devices must be asked which, or it
    would answer one device's settings to the other's pipeline — and that pipeline would write them into its
    own `device.env`.
    """
    if asked:
        return device_named(manager, asked)
    rows = devices(manager)
    return rows[0] if len(rows) == 1 else None


def stages_of(manager, device):
    rows = [r for r in _table(manager, 'PipelineStage') if str(getattr(r, 'device', '')) == device]
    return sorted(rows, key=lambda r: int(getattr(r, 'index', 0) or 0))


def routes_of(manager, device):
    rows = [r for r in _table(manager, 'PipelineRoute') if str(getattr(r, 'device', '')) == device]
    return sorted(rows, key=lambda r: str(getattr(r, 'name', '')))


def secrets_of(manager, device):
    rows = [r for r in _table(manager, 'PipelineSecretPresence') if str(getattr(r, 'device', '')) == device]
    return sorted(rows, key=lambda r: str(getattr(r, 'name', '')))


def runs(manager, device='', limit=200):
    rows = _table(manager, 'PipelineRun')
    if device:
        rows = [r for r in rows if str(getattr(r, 'device', '')) == device]
    rows.sort(key=lambda r: (str(getattr(r, 'started', '')), int(getattr(r, 'number', 0) or 0)), reverse=True)
    return rows[:limit]


def results(manager, device='', version='', limit=500):
    rows = _table(manager, 'IsleTestResult')
    if device:
        rows = [r for r in rows if str(getattr(r, 'device', '')) == device]
    if version:
        rows = [r for r in rows if str(getattr(r, 'version', '')) == version]
    rows.sort(key=lambda r: (str(getattr(r, 'version', '')), int(getattr(r, 'stage_index', 0) or 0)))
    return rows


def releases(manager, device='', limit=200):
    rows = _table(manager, 'ReleaseRecord')
    if device:
        rows = [r for r in rows if str(getattr(r, 'device', '')) == device]
    rows.sort(key=lambda r: str(getattr(r, 'version', '')), reverse=True)
    return rows[:limit]


#: what each mode IS, stated plainly wherever the settings are shown (his addendum 2026-09-19)
MODE_SUITE = ('SUITE mode: this pipeline builds, tests and releases the whole Polari suite. The core is '
              'built here, and every stage tests against the core this run produced.')
MODE_APP = ('APP mode: this pipeline maintains ONE Polari app — %s. The core is NOT rebuilt: its debs and '
            'images are pulled from %s and the app is tested against that core, so the release names the '
            'core it passed against. Only that app\'s deb is released, and only to this developer\'s own '
            'routes — never under an upstream Polari name.')

#: the release rule, in his words — carried by every answer that decides what may ship
RELEASE_RULE = ('THE RELEASE RULE: the pipeline only generates artifacts for things it TESTED in a '
                'throwaway isle. Core debs and images publish only when the isle test recorded core_ok; an '
                'app deb ships only when its stage result is pass; with no isle-test results for a version '
                'NOTHING is published and the tag is not pushed. DRY_RUN=false does not override it.')


def _route_validation(route_rows, settings):
    from cicd.custom.cicd_validate import validate_routes
    return validate_routes(route_rows, mode=str(settings.get('mode') or 'suite'),
                           app_name=str(settings.get('app_name') or ''))


def everything(manager, device_row):
    """The ONE read `cicd-sync.sh pull` makes — settings + stages + routes, ready to become device.env."""
    from cicd.custom.cicd_validate import settings_from_device, validate_settings, device_env
    from cicd.custom.cicd_stages import rows_to_stages, render
    if device_row is None:
        return {'ok': False, 'device': None,
                'refusal': 'no PipelineDevice row — POST /api/cicd/ingest {"kind":"device",…} adopts this '
                           'device, or name one with ?device=<name> when the core knows several',
                'devices': [str(getattr(r, 'name', '')) for r in devices(manager)],
                'release_rule': RELEASE_RULE}
    name = str(getattr(device_row, 'name', ''))
    settings = settings_from_device(device_row)
    stages = rows_to_stages(stages_of(manager, name))
    stage_rows = [{'index': int(getattr(r, 'index', 0) or 0), 'apps': _list(getattr(r, 'apps_json', '[]')),
                   'note': str(getattr(r, 'note', ''))} for r in stages_of(manager, name)]
    route_rows = [{'route': str(getattr(r, 'name', '')).split(':', 1)[-1], 'enabled': bool(getattr(r, 'enabled', False)),
                   'armed': bool(getattr(r, 'armed', False)), 'parked': bool(getattr(r, 'parked', False)),
                   'why': str(getattr(r, 'why', '')), 'needs': _list(getattr(r, 'secrets_json', '[]')),
                   'target': str(getattr(r, 'target', ''))}
                  for r in routes_of(manager, name)]
    settings = dict(settings, routes=[r['route'] for r in route_rows if r['enabled']] or settings['routes'])
    mode = str(settings.get('mode') or 'suite')
    return {
        'ok': True, 'device': name, 'role': str(getattr(device_row, 'role', 'pipeline')),
        'mode': mode, 'app': str(settings.get('app_name') or ''),
        'mode_reading': (MODE_SUITE if mode == 'suite'
                         else MODE_APP % (settings.get('app_name') or '(unnamed)',
                                          settings.get('core_source') or 'release:latest')),
        'settings': settings, 'stages': stage_rows, 'routes': route_rows,
        'stages_knob': render(stages),
        'device_env': device_env(settings, stages),
        'validation': validate_settings(dict(settings, stages=stages)) + _route_validation(route_rows, settings),
        'readiness': {'steps_done': int(getattr(device_row, 'setup_steps_done', 0) or 0),
                      'steps_total': int(getattr(device_row, 'setup_steps_total', 8) or 8),
                      'ready': bool(getattr(device_row, 'setup_ready', False)),
                      'verdict': str(getattr(device_row, 'setup_verdict', '')),
                      'doctor_warnings': int(getattr(device_row, 'doctor_warnings', 0) or 0),
                      'preflight': str(getattr(device_row, 'preflight_verdict', '')),
                      'last_seen': str(getattr(device_row, 'last_seen', ''))},
        'release_rule': RELEASE_RULE,
        'how': ('Polari is the SOURCE OF TRUTH for these settings; device.env is the fallback. '
                'cicd-sync.sh pull writes device.env from `device_env` above; when this core does not '
                'answer, the device keeps the file it has and says so. Edits happen on the rows\' own '
                'pages (/display/cicd-overview, /display/cicd-stages) — admins only.'),
    }
