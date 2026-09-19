"""
@module cicd.custom.cicd_ingest

THE MIRROR — what `POST /api/cicd/ingest` accepts, and everything it refuses.

FIVE KINDS, and nothing else: `device` (the device reporting its own readings), `secrets` (presence, never
a value), `run` (a Jenkins build at start and at end), `isle-test` (one stage of one run) and `release`
(what a version was allowed to ship, and what it was not). An unknown kind is a 400 naming the five — never
a shrug, and never a row written from a body nobody designed.

THREE REFUSALS THAT MATTER:

* **A value-shaped field.** Any key anywhere in the body whose name is (or ends in) value / token / key /
  secret / password / passphrase / credential is a 400 and NOTHING is stored. Not filtered, not dropped —
  refused, with the offending key NAMED. A dropped field is a leak that happened to miss; a refusal is a
  leak that could not start. (`secret_name` is explicitly fine: a name is what these rows are for.)
* **A non-loopback run URL.** `PipelineRun.url` exists so a person at the device can click through to the
  console. The controller binds `127.0.0.1` only, so any other host in that URL is either a
  misconfiguration the doctor already warns about or a LAN address being written into a persisted, rendered
  row. Refused.
* **An ssh alias that is an address.** `cicd_validate.alias_findings` — the same rule, applied on the way in.

AND ONE RULE ABOUT DIRECTION. A `device` post REPORTS; it does not override. The settings columns
(`isle_target`, the VM knobs, the floors, `routes` membership, the stages) belong to Polari, and a push
leaves them exactly as they are — otherwise the fallback file would quietly become the source of truth
again, which is the thing ci-8 exists to stop. The one exception is ADOPTION: when no row for that device
exists yet, the first push creates it from what the device has, because a brand-new device's `device.env`
is the only configuration that exists anywhere.
"""
import json
import re

#: the only kinds the door accepts
KINDS = ('device', 'secrets', 'run', 'isle-test', 'release')

#: a field name that could carry a secret. Matched on the key itself and on any `_`-suffixed form.
VALUE_LIKE = re.compile(r'(?:^|_)(value|token|key|secret|password|passphrase|credential|privkey)s?$', re.I)
#: names that LOOK value-like but are provably not — a secret's NAME is the whole point of these rows
VALUE_LIKE_EXEMPT = frozenset({'secret_name'})

#: a run's console URL must be the controller's own loopback UI
_LOOPBACK = re.compile(r'^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?(/|$)', re.I)


def value_like_fields(body, path=''):
    """Every value-shaped key in a body, deeply. The refusal names them, so the poster can fix its payload."""
    found = []
    if isinstance(body, dict):
        for k, v in body.items():
            key = str(k)
            here = '%s.%s' % (path, key) if path else key
            if key.lower() not in VALUE_LIKE_EXEMPT and VALUE_LIKE.search(key):
                found.append(here)
            found.extend(value_like_fields(v, here))
    elif isinstance(body, (list, tuple)):
        for i, v in enumerate(body):
            found.extend(value_like_fields(v, '%s[%d]' % (path, i)))
    return found


def check(body):
    """(ok, refusal) for a body, before a single row is touched."""
    if not isinstance(body, dict):
        return False, 'body must be a JSON object: {"kind": "<%s>", "device": "<name>", …}' % '|'.join(KINDS)
    kind = str(body.get('kind') or '')
    if kind not in KINDS:
        return False, ('unknown kind %r — the mirror accepts exactly: %s' % (kind, ', '.join(KINDS)))
    if not str(body.get('device') or '').strip():
        return False, 'every ingest names its device: {"device": "<PipelineDevice.name>"}'
    leaks = value_like_fields(body)
    if leaks:
        return False, ('refused: the body carries value-shaped field(s) %s — this door mirrors PRESENCE and '
                       'RESULTS, never a secret value. Nothing was stored.' % ', '.join(sorted(leaks)))
    if kind == 'run':
        from cicd.cicd_basis import PipelineRun
        job = str(body.get('job') or '')
        status = str(body.get('status') or '')
        if job not in PipelineRun.JOBS:
            return False, 'unknown job %r — the pipeline has: %s' % (job, ', '.join(PipelineRun.JOBS))
        if status not in PipelineRun.STATUSES:
            return False, 'unknown status %r — a run is one of: %s' % (status, ', '.join(PipelineRun.STATUSES))
        url = str(body.get('url') or '')
        if url and not _LOOPBACK.match(url):
            return False, ('refused: url %r is not the controller\'s loopback UI — the Jenkins port is bound '
                           'to 127.0.0.1 only, and a row that is persisted and rendered may not carry a host '
                           '(pol jenkins doctor: "port binding")' % url)
    if kind == 'release' and str(body.get('mode') or 'suite') == 'app' and not str(body.get('tested_against') or ''):
        return False, ('refused: an app-mode release must name the CORE release it was tested against '
                       '("tested_against": "release:<tag>") — a deb that passed against an unnamed core is '
                       'an unfalsifiable claim')
    if kind == 'device':
        from cicd.custom.cicd_validate import alias_findings
        alias = str(((body.get('settings') or {}) if isinstance(body.get('settings'), dict) else {}).get('isle_ssh_alias') or '')
        bad = alias_findings(alias)
        if bad:
            return False, 'refused: %s' % bad[0]
    return True, ''


def _j(v, default='[]'):
    try:
        return json.dumps(v)
    except Exception:
        return default


def _int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


def device_rows(body, existing=None, posted_by=''):
    """A `device` post → the columns to write on the PipelineDevice row.

    `existing` = the row already in the table, or None. With a row present this REPORTS only (readiness,
    the doctor/preflight verdicts, last_seen); with no row it ADOPTS the device's own configuration, which
    is the only bootstrap path there is.
    """
    name = str(body.get('device')).strip()
    setup = body.get('setup') or {}
    reported = {
        'name': name,
        'setup_steps_done': _int(setup.get('steps_done')),
        'setup_steps_total': _int(setup.get('steps_total'), 8),
        'setup_ready': bool(setup.get('ready')),
        'setup_verdict': str(setup.get('verdict') or ''),
        'doctor_warnings': _int(setup.get('doctor_warnings')),
        'preflight_verdict': str(setup.get('preflight_verdict') or ''),
        'last_seen': str(body.get('at') or ''),
        'posted_by': posted_by,
    }
    if existing is not None:
        return reported, False
    s = body.get('settings') or {}
    from cicd.custom.cicd_stages import render
    reported.update({
        'role': str(body.get('role') or 'pipeline'),
        # his addendum 2026-09-19: the whole suite, or ONE app somebody maintains
        'mode': str(s.get('mode') or 'suite'),
        'app_name': str(s.get('app_name') or ''),
        'app_repo': str(s.get('app_repo') or ''),
        'core_source': str(s.get('core_source') or 'release:latest'),
        'isle_target': str(s.get('isle_target') or 'local'),
        'isle_ssh_alias': str(s.get('isle_ssh_alias') or ''),
        'isle_ssh_user': str(s.get('isle_ssh_user') or ''),
        'vm_name': str(s.get('vm_name') or 'polari-ci-isle'),
        'vm_ram_gb': _int(s.get('vm_ram_gb'), 4),
        'vm_vcpus': _int(s.get('vm_vcpus'), 2),
        'vm_disk_gb': _int(s.get('vm_disk_gb'), 30),
        'nested': str(s.get('nested') or 'auto'),
        'isle_pool': str(s.get('isle_pool') or ''),
        'image_url': str(s.get('image_url') or ''),
        'min_free_gb': _int(s.get('min_free_gb'), 20),
        'min_ram_headroom_gb': _int(s.get('min_ram_headroom_gb'), 1),
        'executors': _int(s.get('executors'), 1),
        'routes_json': _j([str(r) for r in (s.get('routes') or [])]),
        # ci-9: the offline-first cache, and where this device's own releases go
        'cache': str(s.get('cache') or 'on'),
        'cache_dir': str(s.get('cache_dir') or ''),
        'cache_max_gb': _int(s.get('cache_max_gb'), 40),
        'cache_proxies': str(s.get('cache_proxies') or 'off'),
        'route_target': str(s.get('route_target') or ''),
        'stages_summary': render(body.get('stages') or []),
    })
    return reported, True


def stage_rows(body, posted_by=''):
    """A `device` post's `stages` → PipelineStage rows (adoption only — see device_rows).

    A device that posts no stages gets the default for its MODE (his addendum 2026-09-19): `suite` → core
    only; `app` → core, then the one app it maintains. A new app developer therefore has a working stage
    list from the first sync, which is the whole point of naming the app.
    """
    from cicd.custom.cicd_validate import default_stages
    device = str(body.get('device')).strip()
    s = body.get('settings') or {}
    stages = body.get('stages')
    if not stages:
        stages = default_stages(str(s.get('mode') or 'suite'), str(s.get('app_name') or ''))
    out = []
    for i, apps in enumerate(stages, start=1):
        out.append({'name': '%s:%d' % (device, i), 'device': device, 'index': i,
                    'apps_json': _j([str(a) for a in (apps or []) if a and str(a) != 'core']),
                    'note': '', 'posted_by': posted_by})
    return out


def route_rows(body, posted_by=''):
    """A `device` post's `routes` → the REPORTED half of PipelineRoute: `armed` and `why`.

    `enabled` is Polari's knob and is never written from here — a device saying "I have the secret" must not
    be able to turn a route on.
    """
    device = str(body.get('device')).strip()
    out = []
    for r in body.get('routes') or []:
        if not isinstance(r, dict):
            continue
        rn = str(r.get('name') or '').strip()
        if not rn:
            continue
        out.append({'name': '%s:%s' % (device, rn), 'device': device,
                    'armed': bool(r.get('armed')), 'parked': bool(r.get('parked')),
                    'why': str(r.get('why') or ''),
                    'secrets_json': _j([str(s) for s in (r.get('needs') or [])]),
                    'target': str(r.get('target') or ''),
                    'posted_by': posted_by})
    return out


def secret_rows(body, posted_by=''):
    """A `secrets` post → PipelineSecretPresence rows. Presence booleans and names; there is no value here."""
    device = str(body.get('device')).strip()
    out = []
    for it in body.get('items') or []:
        if not isinstance(it, dict):
            continue
        area = str(it.get('area') or '').strip()
        sname = str(it.get('secret_name') or '').strip()
        if not area or not sname:
            continue
        out.append({'name': '%s:%s/%s' % (device, area, sname), 'device': device, 'area': area,
                    'secret_name': sname, 'present': bool(it.get('present')),
                    'kind': str(it.get('kind') or 'paste'),
                    'needed_by_json': _j([str(r) for r in (it.get('needed_by') or [])]),
                    'where_to_get': str(it.get('where_to_get') or ''),
                    'how_to_make': str(it.get('how_to_make') or ''),
                    'blocked_why': str(it.get('blocked_why') or ''),
                    'last_checked': str(body.get('at') or ''), 'posted_by': posted_by})
    return out


def run_row(body, posted_by=''):
    device = str(body.get('device')).strip()
    job = str(body.get('job') or '')
    number = _int(body.get('number'))
    return {'name': '%s:%s#%d' % (device, job, number), 'device': device, 'job': job, 'number': number,
            'version': str(body.get('version') or ''), 'status': str(body.get('status') or 'running'),
            'started': str(body.get('started') or ''), 'finished': str(body.get('finished') or ''),
            'duration_seconds': _int(body.get('duration_seconds')),
            'url': str(body.get('url') or ''), 'summary': str(body.get('summary') or ''),
            'commit': str(body.get('commit') or ''), 'posted_by': posted_by}


def isle_test_row(body, posted_by=''):
    device = str(body.get('device')).strip()
    run = str(body.get('run') or '')
    idx = _int(body.get('stage_index'), 1)
    return {'name': '%s:stage%d' % (run or device, idx), 'device': device, 'run': run,
            'version': str(body.get('version') or ''), 'stage_index': idx,
            'apps_json': _j([str(a) for a in (body.get('apps') or [])]),
            'core_ok': bool(body.get('core_ok')),
            'results_json': _j(body.get('results') or {}, '{}'),
            'started': str(body.get('started') or ''), 'finished': str(body.get('finished') or ''),
            'error': str(body.get('error') or ''), 'posted_by': posted_by}


def release_row(body, posted_by=''):
    device = str(body.get('device')).strip()
    version = str(body.get('version') or '')
    return {'name': '%s:%s' % (device, version), 'device': device, 'version': version,
            'tag': str(body.get('tag') or ''), 'tag_pushed': bool(body.get('tag_pushed')),
            'results_present': bool(body.get('results_present')), 'core_ok': bool(body.get('core_ok')),
            # his addendum: an app release must name the CORE it passed against, or "it passed" is unfalsifiable
            'mode': str(body.get('mode') or 'suite'), 'app_name': str(body.get('app_name') or ''),
            'tested_against': str(body.get('tested_against') or ''),
            # ci-9: where it went, and whether the offline cache actually saved anything
            'route_target': str(body.get('route_target') or ''),
            'cache_report_json': _j(body.get('cache_report') or {}, '{}'),
            'published_routes_json': _j([str(r) for r in (body.get('published_routes') or [])]),
            'dry_routes_json': _j(body.get('dry_routes') or {}, '{}'),
            'released_json': _j([str(a) for a in (body.get('released') or [])]),
            'not_released_json': _j(body.get('not_released') or {}, '{}'),
            'run': str(body.get('run') or ''), 'released_at': str(body.get('released_at') or ''),
            'why_not': str(body.get('why_not') or ''), 'posted_by': posted_by}
