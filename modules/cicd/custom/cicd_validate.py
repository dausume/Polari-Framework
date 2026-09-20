"""
@module cicd.custom.cicd_validate

THE ONE RULE SET for a pipeline device's settings — `polari-jenkins/device.sh device_validate` +
`device_validate_stages`, ported to python so that the page, the door and the shell say the SAME thing about
the same configuration.

Why port rather than call: the core answering `GET /api/cicd` is not on the pipeline device (it may be a
swarm on another box entirely), so it cannot source a shell file that lives beside a `device.env` it has
never seen. The two copies are kept honest by feeding them the SAME cases: `polari-jenkins/selftest.sh`
section 6 and `cicd_selftest.py`'s parity block use one list of inputs and compare the verdicts.

Every row is `(key, value, status, message)` with status in OK | WARN | FAIL — the same four fields
`device.sh _row` prints with `|` separators, so `doctor.sh`'s reader needs no second shape.

⚠ ci-8 adds ONE rule the shell does not have: `isle_ssh_alias` must be an ssh ALIAS, and anything that
parses as an IPv4/IPv6 address or a dotted hostname is REFUSED (FAIL), not stored. `device.env` is
gitignored so the shell could afford a warning; a Polari row is persisted, restored, rendered on a page and
served by an API, so an address must never get in at all (his privacy rule).
"""
import json
import os
import re

OK, WARN, FAIL = 'OK', 'WARN', 'FAIL'

#: CI_MODE (his addendum 2026-09-19) — the whole suite, or ONE app somebody maintains
MODES = ('suite', 'app')
#: CI_CORE_SOURCE — PULL an official release's core artifacts, or rebuild core from a suite checkout
CORE_SOURCE_BUILD = 'build'
CORE_SOURCE_RELEASE_PREFIX = 'release:'
#: the upstream owner an app-mode device may never publish under (a fork is never republished upstream)
UPSTREAM_OWNER = 'dausume'

#: device.sh: CI_ISLE_TARGET
TARGETS = ('local', 'ssh')
#: device.sh: CI_ISLE_NESTED
NESTED = ('auto', 'required', 'off')
#: secrets.sh SECRETS_ACTIVE_ROUTES / SECRETS_PARKED_ROUTES
ACTIVE_ROUTES = ('github-release', 'ghcr', 'homebrew', 'apt-repo')
PARKED_ROUTES = ('dockerhub', 'npm', 'pypi', 'launchpad', 'snap')
#: the positive-whole-number keys, in device.sh's order
NUMERIC = (('vm_ram_gb', 'CI_ISLE_VM_RAM_GB'), ('vm_vcpus', 'CI_ISLE_VM_VCPUS'),
           ('vm_disk_gb', 'CI_ISLE_VM_DISK_GB'), ('min_free_gb', 'CI_MIN_FREE_GB'),
           ('min_ram_headroom_gb', 'CI_MIN_RAM_HEADROOM_GB'), ('executors', 'CI_EXECUTORS'))
#: device.sh warns below this: an isle install wants the room
MIN_VM_DISK_GB = 30

_IPV4 = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')
_DOTTED = re.compile(r'^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)+$')


def _row(key, value, status, message=''):
    return {'key': key, 'value': '' if value is None else str(value), 'status': status, 'message': message}


def _is_positive_int(v):
    try:
        return int(str(v).strip()) > 0 and str(v).strip().lstrip('-').isdigit()
    except Exception:
        return False


def alias_findings(alias):
    """ci-8's own rule: an ssh ALIAS, never an address. '' is fine (a local target has none)."""
    a = (alias or '').strip()
    if not a:
        return []
    if _IPV4.match(a) or ':' in a:
        return ['%r is an ADDRESS, not an ssh alias — a Polari row is persisted and rendered, so an address '
                'may never be stored here; add a Host entry to ~/.ssh/config and name that' % a]
    if _DOTTED.match(a):
        return ['%r looks like a hostname, not an ssh alias — name a Host entry from ~/.ssh/config instead '
                '(nothing in a tracked row or page may carry a real host)' % a]
    return []


def known_apps(modules_dir=None):
    """Every module with a `polari-app.json` — the catalogue a stage's app names are checked against."""
    d = modules_dir or os.environ.get('CICD_MODULES_DIR') or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    try:
        return sorted(n for n in os.listdir(d)
                      if os.path.isfile(os.path.join(d, n, 'polari-app.json')))
    except Exception:
        return []


def validate_settings(settings, modules_dir=None):
    """`settings` = the device's knobs as a dict (the PipelineDevice columns, or a POST body).

    Returns the list of rows. The caller decides what a FAIL means: the door REFUSES a POST carrying one,
    the page shows them all, and `cicd-sync.sh pull` writes `device.env` only from a settings set with none.
    """
    s = dict(settings or {})
    rows = []
    rows.extend(validate_mode(s, modules_dir=modules_dir))

    target = str(s.get('isle_target') or 'local')
    if target in TARGETS:
        rows.append(_row('CI_ISLE_TARGET', target, OK,
                         'the throwaway isle is created on this machine' if target == 'local'
                         else 'the throwaway isle is created on another device'))
    else:
        rows.append(_row('CI_ISLE_TARGET', target, FAIL,
                         'unknown target → set it to local or ssh'))

    alias = str(s.get('isle_ssh_alias') or '').strip()
    bad_alias = alias_findings(alias)
    if bad_alias:
        rows.append(_row('CI_ISLE_SSH_HOST', alias, FAIL, bad_alias[0]))
    elif target == 'ssh':
        if not alias:
            rows.append(_row('CI_ISLE_SSH_HOST', '', FAIL,
                             'target is ssh but no alias is set → pol jenkins target ssh <alias>'))
        else:
            rows.append(_row('CI_ISLE_SSH_HOST', alias, OK,
                             'an ssh alias — whether ~/.ssh/config knows it is the DEVICE\'s reading '
                             '(pol jenkins doctor); a core cannot see another machine\'s ssh config'))
    elif alias:
        rows.append(_row('CI_ISLE_SSH_HOST', alias, WARN,
                         'set but the target is local → it is ignored; pol jenkins target ssh %s to use it' % alias))
    else:
        rows.append(_row('CI_ISLE_SSH_HOST', '', OK, 'not used (target is local)'))

    for field, key in NUMERIC:
        v = s.get(field)
        if _is_positive_int(v):
            rows.append(_row(key, v, OK))
        else:
            rows.append(_row(key, v, FAIL, 'not a positive whole number'))
    disk = s.get('vm_disk_gb')
    if _is_positive_int(disk) and int(disk) < MIN_VM_DISK_GB:
        rows.append(_row('CI_ISLE_VM_DISK_GB', disk, WARN,
                         'an isle install wants ≥ %d GB → raise it' % MIN_VM_DISK_GB))

    nested = str(s.get('nested') or 'auto')
    rows.append(_row('CI_ISLE_NESTED', nested, OK) if nested in NESTED
                else _row('CI_ISLE_NESTED', nested, FAIL, 'unknown value → auto|required|off'))

    routes = s.get('routes')
    if isinstance(routes, str):
        routes = [r for r in re.split(r'[,\s]+', routes) if r]
    routes = [str(r) for r in (routes or [])]
    bad = []
    for r in routes:
        if r in ACTIVE_ROUTES:
            continue
        bad.append('%s(PARKED)' % r if r in PARKED_ROUTES else '%s(unknown)' % r)
    if bad:
        rows.append(_row('CI_ROUTES', ','.join(routes), FAIL,
                         'not publishable: %s → ACTIVE routes are %s'
                         % (' '.join(bad), ','.join(ACTIVE_ROUTES))))
    else:
        rows.append(_row('CI_ROUTES', ','.join(routes), OK, 'routes that may publish for real'))

    if _is_positive_int(s.get('executors')) and int(s['executors']) != 1:
        rows.append(_row('CI_EXECUTORS', s.get('executors'), WARN,
                         'more than one executor on a home box overlaps builds → set CI_EXECUTORS=1'))

    rows.extend(validate_cache(s))
    rows.extend(validate_route_target(s))
    rows.extend(validate_stages(s.get('stages'), modules_dir=modules_dir,
                                mode=str(s.get('mode') or 'suite'), app_name=str(s.get('app_name') or '')))
    return rows


#: the owner nothing in `app` mode may publish under — a fork is never
#: republished under an upstream name (ci-8's rule, ci-9's key).
UPSTREAM_OWNER = 'dausume'


def validate_cache(settings):
    """CI_CACHE / CI_CACHE_DIR / CI_CACHE_MAX_GB / CI_CACHE_PROXIES (ci-9).

    His ask 2026-09-19: *"the jenkins pipeline should try and use offline artifacts for building where
    possible, that way we are taking less time when repeatedly using the same data."*

    Every row here is advisory on purpose. The cache is an OPTIMISATION: a misconfigured one must make a
    build slower, never refuse it. Only a value outside the vocabulary is a FAIL, and only because a
    device that cannot read its own knob would behave unpredictably rather than slowly.

    The exact counterpart of `device.sh device_validate_cache` — the same keys, the same verdicts, the
    same sentences. (A PORT, not a call: the core is not on the pipeline device.)
    """
    s = dict(settings or {})
    rows = []
    cache = str(s.get('cache', 'on') or 'on')
    if cache == 'on':
        rows.append(_row('CI_CACHE', 'on', OK,
                         'builds read the cache first and fetch only what is missing'))
    elif cache == 'off':
        rows.append(_row('CI_CACHE', 'off', WARN,
                         'every build re-downloads its wheels, npm packages, debs and base images '
                         '→ set CI_CACHE=on (the default)'))
    else:
        rows.append(_row('CI_CACHE', cache, FAIL, 'unknown value → on|off'))

    max_gb = s.get('cache_max_gb', 40)
    if _is_positive_int(max_gb):
        rows.append(_row('CI_CACHE_MAX_GB', max_gb, OK,
                         'the budget the doctor warns past (it never deletes: pol jenkins cache prune does)'))
    else:
        rows.append(_row('CI_CACHE_MAX_GB', max_gb, FAIL, 'not a positive whole number'))

    proxies = str(s.get('cache_proxies', 'off') or 'off')
    if proxies == 'off':
        rows.append(_row('CI_CACHE_PROXIES', 'off', OK,
                         'tier one only — one directory, no services to keep alive'))
    elif proxies == 'on':
        rows.append(_row('CI_CACHE_PROXIES', 'on', OK,
                         'tier two: registry/devpi/verdaccio/apt-cacher-ng on 127.0.0.1 '
                         '(pol jenkins cache proxies status)'))
    else:
        rows.append(_row('CI_CACHE_PROXIES', proxies, FAIL, 'unknown value → off|on'))

    cdir = str(s.get('cache_dir', '') or '')
    rows.append(_row('CI_CACHE_DIR', cdir, OK,
                     'the default: <pool>/cache (relative to the pool, so an ssh target caches on its own disk)'
                     if not cdir else 'an explicit cache root'))
    return rows


def validate_route_target(settings):
    """CI_ROUTE_TARGET — WHERE this device's own releases go (ci-9).

    In `suite` mode it is unused: the suite publishes to the suite's routes. In `app` mode it is required
    and it is checked, because the whole point of app mode is that somebody else's fork of the pipeline
    publishes THEIR app under THEIR name. A target equal to the upstream owner is a FAIL, not a warning:
    republishing a fork under an upstream name is the one thing this mode must make impossible.
    """
    s = dict(settings or {})
    mode = str(s.get('mode') or 'suite')
    target = str(s.get('route_target', '') or '')
    if mode != 'app':
        if target:
            return [_row('CI_ROUTE_TARGET', target, WARN,
                         'set but the mode is suite → it is ignored; set CI_MODE=app to publish to your own routes')]
        return [_row('CI_ROUTE_TARGET', '', OK,
                     'not used (suite mode publishes to the suite\'s own routes)')]
    if not target:
        return [_row('CI_ROUTE_TARGET', '', FAIL,
                     'app mode releases to YOUR routes but names none '
                     '→ set CI_ROUTE_TARGET to your own owner/namespace')]
    if target == UPSTREAM_OWNER or target.startswith(UPSTREAM_OWNER + '/'):
        return [_row('CI_ROUTE_TARGET', target, FAIL,
                     'that is the UPSTREAM owner — a fork is never republished under an upstream name '
                     '→ set CI_ROUTE_TARGET to your own owner/namespace')]
    return [_row('CI_ROUTE_TARGET', target, OK,
                 'this device\'s releases go to %s, never upstream' % target)]


def validate_mode(settings, modules_dir=None):
    """CI_MODE / CI_APP_NAME / CI_APP_REPO / CI_CORE_SOURCE (his addendum 2026-09-19).

    `suite` is today's shape and asks for nothing. `app` says this device exists to maintain ONE Polari app,
    and then the app and its repo are not optional: a device that says "I build one app" without naming it
    would test the suite and release nothing, silently.

    A mode outside suite|app is a WARN, not a FAIL, and falls back to `suite` — the same reading
    `device.sh` gives it, because an unknown mode from a newer device must not stop an older core from
    answering the settings that device still needs.
    """
    s = dict(settings or {})
    rows = []
    mode = str(s.get('mode') or 'suite')
    app_name = str(s.get('app_name') or '').strip()
    app_repo = str(s.get('app_repo') or '').strip()
    core_source = str(s.get('core_source') or 'release:latest').strip()

    if mode in MODES:
        rows.append(_row('CI_MODE', mode, OK,
                         'the whole Polari suite is built, tested and released'
                         if mode == 'suite' else
                         'this device maintains ONE Polari app: %s' % (app_name or '(unnamed)')))
    else:
        rows.append(_row('CI_MODE', mode, WARN,
                         'unknown mode → suite|app; reading it as suite'))
        mode = 'suite'

    if mode == 'app':
        if not app_name:
            rows.append(_row('CI_APP_NAME', '', FAIL,
                             'app mode maintains ONE app but names none → set CI_APP_NAME to the module '
                             'package (modules/<name>/polari-app.json)'))
        else:
            catalogue = set(known_apps(modules_dir))
            if catalogue and app_name not in catalogue:
                rows.append(_row('CI_APP_NAME', app_name, WARN,
                                 'not a module in this checkout — fine for an app maintained in its own '
                                 'repo, but the stage validation cannot check its name here'))
            else:
                rows.append(_row('CI_APP_NAME', app_name, OK, 'the app this device maintains'))
        if not app_repo:
            rows.append(_row('CI_APP_REPO', '', FAIL,
                             'app mode needs the app\'s own repository → set CI_APP_REPO to the '
                             'polari-module-%s git URL (the `pol project` standalone loop)'
                             % (app_name or '<name>')))
        else:
            rows.append(_row('CI_APP_REPO', app_repo, OK, 'the developer\'s own repository'))
    else:
        if app_name or app_repo:
            rows.append(_row('CI_APP_NAME', app_name, WARN,
                             'set but the mode is suite → it is ignored; set CI_MODE=app to maintain one app'))

    # ci-12 addendum 7 — CI_CORE_SOURCE IS AN APP-MODE KNOB, and only that. In
    # suite mode the core under test is the one the run itself builds; nothing
    # reads this key, so a row promising "the core debs are PULLED from that
    # release" would be describing a device that does no such thing. ci-9's
    # default is release:latest and it is written into EVERY device.env, suite
    # ones included — which is exactly how a suite-mode pipeline device came to
    # send its isle stage off to pull a core release that has never been
    # published. The shell says the same thing in device.sh; these two must not
    # drift.
    if mode != 'app':
        rows.append(_row('CI_CORE_SOURCE', core_source, OK,
                         'INFO: suite mode builds its own core here; CI_CORE_SOURCE is an app-mode knob '
                         'and is ignored'))
    elif core_source == CORE_SOURCE_BUILD:
        rows.append(_row('CI_CORE_SOURCE', core_source, OK,
                         'the core is REBUILT from this suite checkout (for a developer who also patches core)'))
    elif core_source.startswith(CORE_SOURCE_RELEASE_PREFIX):
        tag = core_source[len(CORE_SOURCE_RELEASE_PREFIX):].strip()
        if not tag:
            rows.append(_row('CI_CORE_SOURCE', core_source, FAIL,
                             'release: with no tag → release:latest, or release:<a Polari release tag>'))
        else:
            rows.append(_row('CI_CORE_SOURCE', core_source, OK,
                             'the core debs and images are PULLED from the %s Polari release, never rebuilt '
                             '(resolved at run time by the release:<tag> reader; nothing is fetched here)'
                             % ('newest' if tag == 'latest' else tag)))
    else:
        rows.append(_row('CI_CORE_SOURCE', core_source, FAIL,
                         'unknown core source → release:<tag> | release:latest (pull) or build (rebuild)'))
    return rows


def validate_stages(stages, modules_dir=None, mode='suite', app_name=''):
    """`stages` = a list of app lists (the PipelineStage rows, ordered) or the raw CI_ISLE_STAGES string.

    device.sh's three warnings, verbatim in meaning: an app that is not a module, an app tested twice, an
    empty stage after the first — plus the FAIL for no stage at all.

    APP MODE adds one (his addendum 2026-09-19): a stage naming an app that is NOT the one this device
    maintains is a WARN, not a refusal. Testing another app against your core is a perfectly reasonable
    thing to want; releasing it from here is not, so the warning says exactly that rather than stopping the
    run.
    """
    from cicd.custom.cicd_stages import parse, render
    if isinstance(stages, str):
        stages = parse(stages)
    stages = list(stages or [])
    value = render(stages) if stages else ''
    rows = []
    if not stages:
        return [_row('CI_ISLE_STAGES', value, FAIL,
                     'no testing stage at all → set at least: CI_ISLE_STAGES=core')]
    catalogue = set(known_apps(modules_dir))
    unknown, dupes, empties, seen, tested = [], [], [], set(), []
    for i, apps in enumerate(stages, start=1):
        apps = [str(a) for a in (apps or []) if a]
        if not apps:
            if i != 1:
                empties.append(i)
            continue
        for a in apps:
            if catalogue and a not in catalogue:
                unknown.append(a)
            if a in seen:
                dupes.append(a)
            else:
                seen.add(a)
                tested.append(a)
    if unknown:
        rows.append(_row('CI_ISLE_STAGES', value, WARN,
                         'not a module with a polari-app.json: %s → known apps: %s'
                         % (' '.join(unknown), ' '.join(sorted(catalogue)))))
    else:
        rows.append(_row('CI_ISLE_STAGES', value, OK,
                         '%d stage(s); apps tested: %s' % (len(stages),
                                                           ' '.join(tested) or 'none (core only)')))
    if dupes:
        rows.append(_row('isle stages (twice)', ' '.join(dupes), WARN,
                         'tested twice (each stage installs core + its own apps): %s → name each app in ONE stage'
                         % ' '.join(dupes)))
    if empties:
        rows.append(_row('isle stages (empty)', 'stage %s' % ' '.join(str(e) for e in empties), WARN,
                         'empty stage(s) %s — they would re-test core only → remove them, or name their apps'
                         % ' '.join(str(e) for e in empties)))
    if mode == 'app' and app_name:
        others = [a for a in tested if a != app_name]
        if others:
            rows.append(_row('isle stages (other apps)', ' '.join(others), WARN,
                             'this device maintains %s; other apps are tested but never released here: %s'
                             % (app_name, ' '.join(others))))
        if app_name not in tested:
            rows.append(_row('isle stages (the app)', app_name, WARN,
                             'app mode maintains %s but no stage tests it → nothing can be released '
                             '(the default is: core; %s)' % (app_name, app_name)))
    return rows


def validate_routes(routes, mode='suite', app_name=''):
    """A route's TARGET — whose GitHub/registry a publish lands in (his addendum 2026-09-19).

    An `app`-mode device publishing under the upstream owner is a FAIL, not a warning: a fork republished
    under an upstream name is a false claim about provenance, and the honest fix (point it at your own
    namespace) is one field away. A route with no target is fine — it simply has not been pointed anywhere
    yet, and a route nobody pointed publishes nowhere.
    """
    rows = []
    for r in routes or []:
        name = str((r or {}).get('route') or (r or {}).get('name') or '')
        target = str((r or {}).get('target') or '').strip()
        if not target:
            continue
        if mode == 'app' and target.split('/')[0].lower() == UPSTREAM_OWNER:
            rows.append(_row('route %s' % name, target, FAIL,
                             'an app-mode device may not publish under the upstream owner %r — point this '
                             'route at your own namespace; a fork is never republished under an upstream '
                             'name' % UPSTREAM_OWNER))
        else:
            rows.append(_row('route %s' % name, target, OK, 'publishes to %s' % target))
    return rows


def default_stages(mode='suite', app_name=''):
    """The stages a device starts with. `suite` → core only; `app` → core, then that one app."""
    if mode == 'app' and app_name:
        return [[], [app_name]]
    return [[]]


def refusals(rows):
    """The FAIL rows — what a POST is refused for."""
    return [r for r in rows if r['status'] == FAIL]


def device_env(settings, stages):
    """The `device.env` body these settings ARE — the file `cicd-sync.sh pull` writes.

    One writer, one shape: the keys are `device.sh DEVICE_KEYS` in that order, minus the two that are
    DEVICE-LOCAL and that a core could not know — `CI_CORE_URL` (a core does not know its own address, and
    erasing it would make the NEXT pull impossible) and `CI_DEVICE_NAME` (the row's own name; a pull that
    rewrote it would rename the device out from under the settings it just fetched). `cicd-sync.sh pull`
    preserves both.
    """
    from cicd.custom.cicd_stages import render
    s = dict(settings or {})
    routes = s.get('routes')
    if not isinstance(routes, str):
        routes = ','.join(str(r) for r in (routes or []))
    pairs = [
        # his addendum 2026-09-19: the whole suite, or ONE app somebody maintains
        ('CI_MODE', s.get('mode') or 'suite'),
        ('CI_APP_NAME', s.get('app_name') or ''),
        ('CI_APP_REPO', s.get('app_repo') or ''),
        ('CI_CORE_SOURCE', s.get('core_source') or 'release:latest'),
        ('CI_ISLE_TARGET', s.get('isle_target') or 'local'),
        ('CI_ISLE_SSH_HOST', s.get('isle_ssh_alias') or ''),
        ('CI_ISLE_SSH_USER', s.get('isle_ssh_user') or ''),
        ('CI_ISLE_VM_NAME', s.get('vm_name') or 'polari-ci-isle'),
        ('CI_ISLE_VM_RAM_GB', s.get('vm_ram_gb')),
        ('CI_ISLE_VM_VCPUS', s.get('vm_vcpus')),
        ('CI_ISLE_VM_DISK_GB', s.get('vm_disk_gb')),
        ('CI_ISLE_NESTED', s.get('nested') or 'auto'),
        ('CI_ISLE_POOL', s.get('isle_pool') or ''),
        ('CI_ISLE_IMAGE_URL', s.get('image_url') or ''),
        ('CI_MIN_FREE_GB', s.get('min_free_gb')),
        ('CI_MIN_RAM_HEADROOM_GB', s.get('min_ram_headroom_gb')),
        ('CI_EXECUTORS', s.get('executors')),
        ('CI_ROUTES', routes),
        ('CI_ISLE_STAGES', render(stages)),
        # ci-9: the offline-first cache, and where an app-mode device's own releases go.
        # They are rendered LAST so an older device.env gains them at the end of the file.
        ('CI_CACHE', s.get('cache') or 'on'),
        ('CI_CACHE_DIR', s.get('cache_dir') or ''),
        ('CI_CACHE_MAX_GB', 40 if s.get('cache_max_gb') is None else s.get('cache_max_gb')),
        ('CI_CACHE_PROXIES', s.get('cache_proxies') or 'off'),
        ('CI_ROUTE_TARGET', s.get('route_target') or ''),
    ]
    return ''.join('%s=%s\n' % (k, '' if v is None else v) for k, v in pairs)


def settings_from_device(row):
    """A PipelineDevice row → the settings dict this module validates and renders."""
    def _list(v):
        try:
            return json.loads(v or '[]')
        except Exception:
            return []
    return {
        'mode': getattr(row, 'mode', 'suite'),
        'app_name': getattr(row, 'app_name', ''),
        'app_repo': getattr(row, 'app_repo', ''),
        'core_source': getattr(row, 'core_source', 'release:latest'),
        'isle_target': getattr(row, 'isle_target', 'local'),
        'isle_ssh_alias': getattr(row, 'isle_ssh_alias', ''),
        'isle_ssh_user': getattr(row, 'isle_ssh_user', ''),
        'vm_name': getattr(row, 'vm_name', 'polari-ci-isle'),
        'vm_ram_gb': getattr(row, 'vm_ram_gb', 4),
        'vm_vcpus': getattr(row, 'vm_vcpus', 2),
        'vm_disk_gb': getattr(row, 'vm_disk_gb', 30),
        'nested': getattr(row, 'nested', 'auto'),
        'isle_pool': getattr(row, 'isle_pool', ''),
        'image_url': getattr(row, 'image_url', ''),
        'min_free_gb': getattr(row, 'min_free_gb', 20),
        'min_ram_headroom_gb': getattr(row, 'min_ram_headroom_gb', 1),
        'executors': getattr(row, 'executors', 1),
        'routes': _list(getattr(row, 'routes_json', '[]')),
        # ci-9
        'cache': getattr(row, 'cache', 'on'),
        'cache_dir': getattr(row, 'cache_dir', ''),
        'cache_max_gb': getattr(row, 'cache_max_gb', 40),
        'cache_proxies': getattr(row, 'cache_proxies', 'off'),
        'route_target': getattr(row, 'route_target', ''),
    }
