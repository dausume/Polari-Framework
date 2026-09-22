"""
@module cicd.custom.cicd_ingest

THE MIRROR — what `POST /api/cicd/ingest` accepts, and everything it refuses.

SEVEN KINDS, and nothing else: `device` (the device reporting its own readings), `secrets` (presence, never
a value), `run` (a Jenkins build at start and at end), `isle-test` (one stage of one run), `release` (what a
version was allowed to ship, and what it was not), `setup` (ci-11a — the walkthrough `pol jenkins setup
--json` produced on that device) and `test-verdict` (ci-12 — the ONE answer a test run reached for one
superproject sha). An unknown kind is a 400 naming the seven — never a shrug, and never a row written from
a body nobody designed.

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
#: `setup` (ci-11a) is the walkthrough itself — the document `pol jenkins setup --json` produced on the
#: device, so a browser with no desktop shell can still see where that device got to. The core cannot run
#: `pol`; only the device can, and this is the one way that state arrives.
#: ci-12: `test-verdict` is the product of the TEST pipeline — one row per superproject sha, and the thing
#: `pol jenkins promote main` and every publish route refuse on.
#: dep-1: `deploy` is what deploy/apply.sh wrote on the device (applied.json | failed.json) — one deploy of one
#: release to one target, mirrored so the pages can say what runs where.
KINDS = ('device', 'secrets', 'run', 'isle-test', 'release', 'setup', 'test-verdict', 'deploy')

#: a field name that could carry a secret. Matched on the key itself and on any `_`-suffixed form.
VALUE_LIKE = re.compile(r'(?:^|_)(value|token|key|secret|password|passphrase|credential|privkey)s?$', re.I)
#: names that LOOK value-like but are provably not — a secret's NAME is the whole point of these rows
VALUE_LIKE_EXEMPT = frozenset({'secret_name'})

#: a run's console URL must be the controller's own loopback UI
_LOOPBACK = re.compile(r'^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?(/|$)', re.I)

#: the ONE machine protocol this door mirrors (polari-jenkins/setup/protocol.py emits it)
SETUP_PROTOCOL = 'polari-pipeline-setup/1'
#: what a `secret` question may say about itself, and nothing else
SECRET_ANSWERS = ('', 'present')


def setup_value_leak(steps):
    """A setup post that smuggles a secret VALUE, named — or None.

    The generic value-shaped-key guard cannot see inside `questions_json`, because it is a string. This is
    the guard for what the string contains: a question of kind `secret` may answer `present` or nothing.
    Anything else is refused and nothing is stored, the same posture as every other refusal here — a
    dropped field is a leak that happened to miss, a refusal is a leak that could not start.
    """
    for s in steps:
        try:
            questions = json.loads(str(s.get('questions_json') or '[]'))
        except ValueError:
            return 'step %r posted questions_json that is not JSON' % s.get('name')
        if not isinstance(questions, list):
            return 'step %r posted a questions_json that is not a list' % s.get('name')
        for q in questions:
            if not isinstance(q, dict) or str(q.get('kind') or '') != 'secret':
                continue
            answered = str(q.get('answered') or '')
            if answered not in SECRET_ANSWERS:
                return ('step %r question %r is a SECRET and carries an answer that is not %s'
                        % (s.get('name'), q.get('key'), ' or '.join(repr(a) for a in SECRET_ANSWERS)))
            if str(q.get('default') or ''):
                return ('step %r question %r is a SECRET and carries a default — a secret has no default'
                        % (s.get('name'), q.get('key')))
    return None


def setup_step_rows(body, posted_by=''):
    """A `setup` post → PipelineSetupStep rows, one per step of the walkthrough.

    Verbatim: Polari STORES what the device computed and never re-derives it. The device is the only
    machine that can run `pol jenkins setup`, so a second opinion here would be a guess.
    """
    device = str(body.get('device')).strip()
    at = str(body.get('at') or '')
    out = []
    for s in body.get('steps') or []:
        step = str(s.get('name') or '')
        out.append({
            'name': '%s:%s' % (device, step), 'device': device, 'step': step,
            'index': _int(s.get('index')), 'total': _int(s.get('total'), 8),
            'title': str(s.get('title') or ''), 'state': str(s.get('state') or 'todo'),
            'explain': str(s.get('explain') or ''),
            'checks_json': str(s.get('checks_json') or '[]'),
            'questions_json': str(s.get('questions_json') or '[]'),
            'actions_json': str(s.get('actions_json') or '[]'),
            'where_json': str(s.get('where_json') or '[]'),
            'at': at, 'posted_by': posted_by,
        })
    return out


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
    if kind == 'test-verdict':
        from cicd.cicd_basis import TestVerdict
        verdict = str(body.get('verdict') or '')
        if verdict not in TestVerdict.VERDICTS:
            return False, ('unknown verdict %r — a test run reaches exactly one of: %s'
                           % (verdict, ', '.join(TestVerdict.VERDICTS)))
        if not str(body.get('sha') or '').strip():
            return False, ('a test verdict is ABOUT a superproject sha: {"sha": "<40 hex>"}. Without one it '
                           'names nothing, and `promote main` could never find it')
        if verdict != 'passed' and not str(body.get('why') or '').strip():
            return False, ('refused: a verdict that is not `passed` must say WHY in words — a bare "failed" '
                           'is a result nobody can act on')
    if kind == 'release' and str(body.get('mode') or 'suite') == 'app' and not str(body.get('tested_against') or ''):
        return False, ('refused: an app-mode release must name the CORE release it was tested against '
                       '("tested_against": "release:<tag>") — a deb that passed against an unnamed core is '
                       'an unfalsifiable claim')
    if kind == 'deploy':
        if not str(body.get('target') or '').strip() or not str(body.get('release') or '').strip():
            return False, 'refused: a deploy names its TARGET and its RELEASE ({"target": …, "release": "polari-v…"})'
        if str(body.get('result') or '') not in ('applied', 'failed'):
            return False, ('refused: a deploy record is one of applied | failed (a SKIP is not a record — nothing '
                           'touched the target; it lives in the device\'s pool as skipped.json)')
        if str(body.get('result')) == 'failed' and not str(body.get('rollback') or ''):
            return False, ('refused: a FAILED deploy says in words where it left the target ("rollback": '
                           '"rolled back to …" | "nothing moved …" | "ROLLBACK FAILED …")')
    if kind == 'setup':
        if str(body.get('setup_protocol') or '') != SETUP_PROTOCOL:
            return False, ('refused: this door mirrors %r; the body declares %r. A front end that read a '
                           'different protocol would render a step it does not understand.'
                           % (SETUP_PROTOCOL, body.get('setup_protocol')))
        steps = body.get('steps')
        if not isinstance(steps, list) or not steps:
            return False, 'a setup post carries the walkthrough\'s steps: {"steps": [{"name": …}, …]}'
        from cicd.cicd_basis import PipelineSetupStep
        for s in steps:
            if not isinstance(s, dict) or not str(s.get('name') or '').strip():
                return False, 'every step of a setup post names itself: {"name": "role", "index": 1, …}'
            state = str(s.get('state') or '')
            if state not in PipelineSetupStep.STATES:
                return False, ('unknown step state %r — a step is one of: %s'
                               % (state, ', '.join(PipelineSetupStep.STATES)))
            bad = [k for k in s if k in ('checks', 'questions', 'actions', 'where')]
            if bad:
                return False, ('refused: a step posts its sub-structures as JSON STRINGS (%s), not as nested '
                               'objects — the value-shaped-key guard cannot see inside a nested question, '
                               'whose key is literally `key`. Offending: %s'
                               % ('checks_json, questions_json, actions_json, where_json', ', '.join(sorted(bad))))
        leak = setup_value_leak(steps)
        if leak:
            return False, ('refused: %s. A secret question carries `present` or nothing — never a value.' % leak)
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
    """A stage of an isle test → the IsleTestResult row.

    ci-10: the teardown arrives as TWO readings and is stored as two. `uninstall_verdict` is what the
    PRODUCT'S own `isle uninstall --everything` said about handing the machine back — a test result, and
    `core_ok` is ANDed with it here as well as in the pipeline, so a mirrored row can never claim a passing
    core for an isle that could not leave. `leak_verdict` and the deltas are what OUR wipe left behind — a
    resource guard that is recorded, never a release gate.
    """
    device = str(body.get('device')).strip()
    run = str(body.get('run') or '')
    idx = _int(body.get('stage_index'), 1)
    uninstall = str(body.get('uninstall_verdict') or 'skipped')
    return {'name': '%s:stage%d' % (run or device, idx), 'device': device, 'run': run,
            'version': str(body.get('version') or ''), 'stage_index': idx,
            'apps_json': _j([str(a) for a in (body.get('apps') or [])]),
            'core_ok': (bool(body.get('core_ok')) and uninstall == 'clean'
                        and bool((body.get('install') or {}).get('ok'))
                        and bool((body.get('verify') or {}).get('ok'))),
            'results_json': _j(body.get('results') or {}, '{}'),
            'started': str(body.get('started') or ''), 'finished': str(body.get('finished') or ''),
            'error': str(body.get('error') or ''),
            'uninstall_verdict': uninstall,
            'uninstall_json': _j({'verdict': uninstall,
                                  'findings': [str(f) for f in (body.get('uninstall_findings') or [])]}, '{}'),
            'leak_verdict': str(body.get('leak_verdict') or 'clean'),
            'leaks_json': _j([str(x) for x in (body.get('leaks') or [])]),
            'ram_delta_mb': _int(body.get('ram_delta_mb')),
            'disk_delta_mb': _int(body.get('disk_delta_mb')),
            # ---- ci-3: the cycle. core_ok is ANDed with install AND verify here too, for the
            # same reason it is ANDed with the uninstall verdict: a mirrored row must not be
            # able to claim a passing core that the pipeline never claimed.
            'install_ok': bool((body.get('install') or {}).get('ok')),
            'install_json': _j(body.get('install') or {}, '{}'),
            'seconds_to_online': _int((body.get('install') or {}).get('time_to_online')),
            'verify_ok': bool((body.get('verify') or {}).get('ok')),
            'verify_json': _j(body.get('verify') or {}, '{}'),
            'selftests_json': _j(body.get('selftests') or {}, '{}'),
            'selftest_suites': _int((body.get('selftest_counts') or {}).get('suites')),
            'selftest_failed': _int((body.get('selftest_counts') or {}).get('fail')),
            'images_json': _j(body.get('images') or {}, '{}'),
            'posted_by': posted_by}


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


def deploy_row(body, posted_by=''):
    """dep-1 — ONE DEPLOY OF ONE RELEASE TO ONE TARGET → the DeployRecord row.

    Stored as told: the apply/verify/rollback happened on the device and the target; this mirror judges
    nothing. `rollback` is kept in words because it is what a person reads first after a failure.
    """
    device = str(body.get('device')).strip()
    target = str(body.get('target') or '').strip()
    release = str(body.get('release') or '')
    return {'name': '%s:%s:%s' % (device, target, release), 'device': device, 'target': target,
            'release': release, 'from_release': str(body.get('from_release') or ''),
            'result': str(body.get('result') or ''), 'failed_at': str(body.get('failed_at') or ''),
            'rollback': str(body.get('rollback') or ''), 'stash': str(body.get('stash') or ''),
            'apply_seconds': int(body.get('apply_seconds') or 0), 'at': str(body.get('at') or ''),
            'posted_by': posted_by}


def test_verdict_row(body, posted_by=''):
    """ci-12 — ONE SHA, ONE ANSWER → the TestVerdict row.

    The three summaries arrive already shaped by `polari-jenkins/verdict.py` (the one place the arithmetic
    lives) and are stored as JSON STRINGS: they are opaque to the row, and the page renders them as
    configured columns rather than as a raw-JSON panel. Nothing here recomputes the verdict — a mirror that
    second-guessed the pipeline would be a second implementation of the rule, and the two would drift.

    `core_ok` is lifted out of the isle summary into a column of its own because it is the half the release
    rule turns on. ci-3 also carries `report_path`, so a row on the page can link straight to the page a
    person actually reads.
    """
    device = str(body.get('device')).strip()
    sha = str(body.get('sha') or '')
    selftests = body.get('selftests') or {}
    isle = body.get('isle') or {}
    return {'name': '%s:%s' % (device, sha), 'device': device, 'sha': sha,
            'git_branch': str(body.get('branch') or 'test'),
            'verdict': str(body.get('verdict') or 'partial'),
            'why': str(body.get('why') or ''),
            'built': bool(body.get('built')),
            'scans_json': _j(body.get('scans') or {}, '{}'),
            'selftests_json': _j(selftests, '{}'),
            'isle_json': _j(isle, '{}'),
            'selftest_suites': _int(selftests.get('suites')),
            'selftest_passed': _int(selftests.get('passed')),
            'selftest_failed': _int(selftests.get('failed')),
            'core_ok': bool(isle.get('core_ok')),
            'run': str(body.get('run') or ''),
            'decided_by': str(body.get('decided_by') or 'pipeline'),
            'report_path': str(body.get('report_path') or ''),
            'at': str(body.get('at') or ''), 'posted_by': posted_by}
