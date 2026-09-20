"""cicd_selftest — the rows, the ONE rule set (parity with polari-jenkins/device.sh), the two modes, the
mirror's refusals, the token shown once, the release-rule fields, and the §54 route guard.

    cd polari-rf-node/polari-framework && PYTHONPATH=.:modules python3 modules/cicd/cicd_selftest.py
"""
import inspect
import json
import sys
import types

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, ('→ %s' % (extra,)) if not cond else ''))


class _M:
    """A manager that is only what these doors actually touch: the tables, and a no-op persist."""

    def __init__(self, *classes):
        self.objectTables = {c: {} for c in classes}
        self.idList = []          # treeObject.makeUniqueIdentifier reads it
        self.db = None

    def persistTree(self):
        return None

    def noteTreeMutation(self, *a, **k):
        return None


def _named(m, class_name, name):
    """Rows are keyed by their generated tree id, not by `name` — look one up the way a door does."""
    for r in (m.objectTables.get(class_name) or {}).values():
        if str(getattr(r, 'name', '')) == name:
            return r
    return None


class _Req:
    def __init__(self, ui=None, media=None, headers=None, **params):
        self.params = params
        self.media = media or {}
        self._headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.context = types.SimpleNamespace(user_info=ui)
        self.remote_addr = '127.0.0.1'

    def get_header(self, name):
        return self._headers.get(str(name).lower())


class _Res:
    def __init__(self):
        self.status = '200 OK'
        self.media = None


# ---------------------------------------------------------------- the rows
def _row_checks():
    from cicd.custom.cicd_ingest import value_like_fields
    from cicd.cicd_basis import (CICD_CLASSES, CICD_MIRROR_CLASSES, CICD_SETTINGS_CLASSES, IsleTestResult,
                                 PipelineDevice, PipelineRoute, PipelineRun, PipelineSecretPresence,
                                 PipelineStage, ReleaseRecord)
    check('the module registers exactly NINE row classes — the count is asserted so a class added without a '
          'manifest entry, a feature-import entry and a defClassList entry cannot ride in unnoticed',
          len(CICD_CLASSES) == 9, [c.__name__ for c in CICD_CLASSES])
    check('the classes split into the SETTINGS a person owns and the rows the pipeline mirrors in',
          [c.__name__ for c in CICD_SETTINGS_CLASSES] == ['PipelineDevice', 'PipelineStage', 'PipelineRoute']
          and [c.__name__ for c in CICD_MIRROR_CLASSES] == ['PipelineSecretPresence', 'PipelineRun',
                                                            'IsleTestResult', 'ReleaseRecord',
                                                            'PipelineSetupStep', 'TestVerdict'])
    check('every class is one file under objects/cicd/ and re-exported by cicd_basis (the module convention)',
          all(c.__module__ == 'cicd.objects.cicd.%s' % c.__name__ for c in CICD_CLASSES),
          [c.__module__ for c in CICD_CLASSES])
    check('PipelineDevice carries the device.env knobs AND the two modes',
          {'isle_target', 'isle_ssh_alias', 'vm_ram_gb', 'vm_disk_gb', 'nested', 'min_free_gb',
           'min_ram_headroom_gb', 'executors', 'routes_json', 'setup_steps_done', 'setup_ready',
           'last_seen', 'posted_by', 'mode', 'app_name', 'app_repo', 'core_source'}
          <= set(inspect.signature(PipelineDevice.__init__).parameters))
    check('a PipelineDevice keeps the HASH of the posting token and no column that could hold the token',
          'ingest_token_hash' in inspect.signature(PipelineDevice.__init__).parameters
          and 'ingest_token' not in inspect.signature(PipelineDevice.__init__).parameters)
    check('PipelineRoute separates the knob Polari owns (enabled) from the reading the device reports (armed), '
          'and names WHOSE route it is (target) so an app developer publishes to their own namespace',
          {'enabled', 'armed', 'parked', 'why', 'target'}
          <= set(inspect.signature(PipelineRoute.__init__).parameters))
    check('ReleaseRecord carries BOTH halves of the release rule — what shipped and what did not, with the '
          'reason — plus the CORE release an app was tested against',
          {'released_json', 'not_released_json', 'results_present', 'tag_pushed', 'published_routes_json',
           'tested_against', 'mode', 'app_name'} <= set(inspect.signature(ReleaseRecord.__init__).parameters))
    check('IsleTestResult is per run × stage, with core_ok beside the per-app results',
          {'run', 'stage_index', 'apps_json', 'core_ok', 'results_json'}
          <= set(inspect.signature(IsleTestResult.__init__).parameters))
    # ci-10: the teardown, and it is TWO readings — the product's hand-back (a test result that
    # gates the release) and our own leak diff (a resource guard that gates the next stage).
    check('IsleTestResult carries the TEARDOWN as two separate readings — the product\'s uninstall '
          'verdict, and the pipeline\'s own leak diff with the RAM/disk that did or did not come back',
          {'uninstall_verdict', 'uninstall_json', 'leak_verdict', 'leaks_json',
           'ram_delta_mb', 'disk_delta_mb'} <= set(inspect.signature(IsleTestResult.__init__).parameters))
    check('  …and both vocabularies are declared, not left to a string anybody can invent',
          IsleTestResult.UNINSTALL_VERDICTS == ('clean', 'dirty', 'failed', 'skipped')
          and 'leaked-after-rewipe' in IsleTestResult.LEAK_VERDICTS)
    check('  …the leak fields are NOT value-shaped, so the mirror door cannot refuse its own results',
          not value_like_fields({'leaks_json': [], 'leak_verdict': '', 'ram_delta_mb': 0,
                                 'disk_delta_mb': 0, 'uninstall_verdict': '', 'uninstall_json': {}}))
    check('PipelineRun knows the SIX jobs (ci-12 added `test` and `release-manual`) and the five statuses',
          PipelineRun.JOBS == ('dev-build', 'test', 'release', 'release-manual', 'publish', 'isle-test')
          and 'running' in PipelineRun.STATUSES and 'success' in PipelineRun.STATUSES, PipelineRun.JOBS)

    # ---- THE PRESENCE CLASS MAY NOT HAVE A VALUE-SHAPED FIELD. Asserted, not assumed.
    from cicd.custom.cicd_ingest import VALUE_LIKE, VALUE_LIKE_EXEMPT
    leaky = [p for p in inspect.signature(PipelineSecretPresence.__init__).parameters
             if p.lower() not in VALUE_LIKE_EXEMPT and VALUE_LIKE.search(p)]
    check('PipelineSecretPresence has NO field named like a value (value/token/key/secret/password/'
          'credential) — presence is a boolean and a name, and that is all the class can physically hold',
          leaky == [], leaky)
    check('  …and `secret_name` is the one deliberate exemption: a NAME is what these rows are for',
          'secret_name' in inspect.signature(PipelineSecretPresence.__init__).parameters
          and 'secret_name' in VALUE_LIKE_EXEMPT)
    allleaky = {c.__name__: [p for p in inspect.signature(c.__init__).parameters
                             if p.lower() not in VALUE_LIKE_EXEMPT and VALUE_LIKE.search(p)
                             and p != 'ingest_token_hash']
                for c in CICD_CLASSES}
    check('no class in the module has a value-shaped field (the token hash is the one allowed, and it is a hash)',
          all(not v for v in allleaky.values()), {k: v for k, v in allleaky.items() if v})
    check('PipelineStage is an ORDERED row per stage, keyed to its device',
          {'device', 'index', 'apps_json', 'note'} <= set(inspect.signature(PipelineStage.__init__).parameters))


# -------------------------------------------- the ONE rule set (device.sh parity)
def _validation_checks():
    """The SAME cases polari-jenkins/selftest.sh section 4 and 6 feed the shell, fed to the python port.

    The two are separate implementations on purpose (a core is not on the pipeline device and cannot source
    a shell file that lives beside a device.env it has never seen), so the only thing keeping them honest is
    that both are fed this list.
    """
    from cicd.custom import cicd_validate as V

    def verdicts(**settings):
        base = dict(mode='suite', isle_target='local', isle_ssh_alias='', vm_ram_gb=4, vm_vcpus=2,
                    vm_disk_gb=30, nested='auto', min_free_gb=20, min_ram_headroom_gb=1, executors=1,
                    routes=['github-release'], core_source='release:latest', stages=[[]])
        base.update(settings)
        return {r['key']: (r['status'], r['message']) for r in V.validate_settings(base)}

    ok = verdicts()
    check('a well-formed device validates clean — no FAIL anywhere',
          not [k for k, (s, _) in ok.items() if s == 'FAIL'],
          {k: v for k, v in ok.items() if v[0] == 'FAIL'})
    v = verdicts(isle_target='sideways')
    check('device.sh case: an unknown target → FAIL naming local/ssh',
          v['CI_ISLE_TARGET'][0] == 'FAIL' and 'unknown target' in v['CI_ISLE_TARGET'][1], v.get('CI_ISLE_TARGET'))
    v = verdicts(isle_target='ssh', isle_ssh_alias='')
    check('device.sh case: an ssh target with no alias → FAIL',
          v['CI_ISLE_SSH_HOST'][0] == 'FAIL' and 'no alias is set' in v['CI_ISLE_SSH_HOST'][1])
    v = verdicts(isle_target='local', isle_ssh_alias='isle-core')
    check('device.sh case: an alias set while the target is local → WARN, it is ignored',
          v['CI_ISLE_SSH_HOST'][0] == 'WARN' and 'it is ignored' in v['CI_ISLE_SSH_HOST'][1])
    v = verdicts(vm_ram_gb='lots')
    check('device.sh case: a non-numeric size → FAIL "not a positive whole number"',
          v['CI_ISLE_VM_RAM_GB'][0] == 'FAIL' and 'not a positive whole number' in v['CI_ISLE_VM_RAM_GB'][1])
    v = verdicts(vm_disk_gb=10)
    check('device.sh case: a too-small VM disk → WARN "an isle install wants"',
          v['CI_ISLE_VM_DISK_GB'][0] == 'WARN' and 'an isle install wants' in v['CI_ISLE_VM_DISK_GB'][1])
    v = verdicts(nested='sometimes')
    check('device.sh case: an unknown CI_ISLE_NESTED → FAIL naming auto|required|off',
          v['CI_ISLE_NESTED'][0] == 'FAIL' and 'auto|required|off' in v['CI_ISLE_NESTED'][1])
    v = verdicts(routes=['github-release', 'npm', 'wat'])
    check('device.sh case: a PARKED route → FAIL, marked npm(PARKED)',
          v['CI_ROUTES'][0] == 'FAIL' and 'npm(PARKED)' in v['CI_ROUTES'][1], v.get('CI_ROUTES'))
    check('device.sh case: an unknown route → wat(unknown), in the same row',
          'wat(unknown)' in v['CI_ROUTES'][1])
    v = verdicts(executors=4)
    check('device.sh case: more than one executor → WARN "overlaps builds"',
          v['CI_EXECUTORS'][0] == 'WARN' and 'overlaps builds' in v['CI_EXECUTORS'][1])

    # ---- ci-8's OWN rule: an alias is an alias, never an address
    for bad in ('203.0.113.9', '198.51.100.7', '2001:db8::1'):   # the reserved documentation ranges
        f = V.alias_findings(bad)
        check('an ssh alias that is an ADDRESS (%s) is REFUSED, not stored — a Polari row is persisted and '
              'rendered, so the shell\'s warning is not enough here' % bad,
              bool(f) and 'ADDRESS' in f[0], f)
    f = V.alias_findings('box.example.invalid')
    check('a dotted HOSTNAME is refused for the same reason, naming ~/.ssh/config as the way to do it right',
          bool(f) and 'ssh/config' in f[0], f)
    check('a real alias passes, and an empty one (a local target) is fine',
          V.alias_findings('isle-core') == [] and V.alias_findings('') == [])

    # ---- the stages (device.sh section 6)
    from cicd.custom.cicd_stages import parse, render
    check('the literal core parses to ONE stage with no apps', parse('core') == [[]], parse('core'))
    check("';' separates stages, ',' separates apps inside one",
          parse('core; household; gears,cntfet') == [[], ['household'], ['gears', 'cntfet']])
    check('whitespace anywhere is ignored', parse('  core ;  gears , cntfet  ') == [[], ['gears', 'cntfet']])
    check('core named inside a stage is implicit and drops out', parse('core; core,household')[1] == ['household'])
    check('an empty stage stays a LINE, not a dropped entry (the validation has to be able to warn about it)',
          len(parse('core; household; ; gears')) == 4)
    check('render is parse\'s inverse for the knob device.env holds',
          render(parse('core; household; gears,cntfet')) == 'core; household; gears,cntfet')
    check('  …and an empty build is just core', render([]) == 'core' and render([[]]) == 'core')

    def st(stages, **kw):
        return {r['key']: (r['status'], r['message']) for r in V.validate_stages(stages, **kw)}
    v = st('core; nosuchappanywhere')
    check('device.sh case: an unknown app name → WARN naming it and listing the known apps',
          v['CI_ISLE_STAGES'][0] == 'WARN' and 'nosuchappanywhere' in v['CI_ISLE_STAGES'][1]
          and 'known apps:' in v['CI_ISLE_STAGES'][1])
    v = st('core; security; security')
    check('device.sh case: an app in two stages → WARN "tested twice"',
          'isle stages (twice)' in v and 'tested twice' in v['isle stages (twice)'][1], sorted(v))
    v = st('core; ; security')
    check('device.sh case: an empty stage after the first → WARN',
          'isle stages (empty)' in v and 'empty stage' in v['isle stages (empty)'][1], sorted(v))
    v = st([])
    check('device.sh case: no stage at all → FAIL "no testing stage"',
          v['CI_ISLE_STAGES'][0] == 'FAIL' and 'no testing stage' in v['CI_ISLE_STAGES'][1])
    v = st('core')
    check('core alone is OK, and says what it tests', v['CI_ISLE_STAGES'][0] == 'OK'
          and 'core only' in v['CI_ISLE_STAGES'][1], v.get('CI_ISLE_STAGES'))

    check('refusals() is what a POST is refused for — the FAIL rows and nothing else',
          [r['key'] for r in V.refusals(V.validate_settings(dict(isle_target='sideways', vm_ram_gb=4,
                                                                 vm_vcpus=2, vm_disk_gb=30, nested='auto',
                                                                 min_free_gb=20, min_ram_headroom_gb=1,
                                                                 executors=1, routes=[], stages=[[]])))]
          == ['CI_ISLE_TARGET'])


# ------------------------------------------------------------- the two modes
def _mode_checks():
    from cicd.custom import cicd_validate as V

    def verdicts(**settings):
        base = dict(isle_target='local', vm_ram_gb=4, vm_vcpus=2, vm_disk_gb=30, nested='auto',
                    min_free_gb=20, min_ram_headroom_gb=1, executors=1, routes=['github-release'],
                    stages=[[]])
        base.update(settings)
        return {r['key']: (r['status'], r['message']) for r in V.validate_settings(base)}

    v = verdicts(mode='suite')
    check('SUITE mode asks for nothing more — the whole suite is built, tested and released',
          v['CI_MODE'][0] == 'OK' and 'whole Polari suite' in v['CI_MODE'][1], v.get('CI_MODE'))
    v = verdicts(mode='app', app_name='', app_repo='')
    check('APP mode without an app name → FAIL: a device that says it builds one app must name it, or it '
          'would test the suite and release nothing, silently',
          v['CI_APP_NAME'][0] == 'FAIL' and 'names none' in v['CI_APP_NAME'][1], v.get('CI_APP_NAME'))
    check('  …and without the app\'s own repo → FAIL naming polari-module-<name> and the pol project loop',
          v['CI_APP_REPO'][0] == 'FAIL' and 'polari-module-' in v['CI_APP_REPO'][1], v.get('CI_APP_REPO'))
    v = verdicts(mode='app', app_name='security', app_repo='https://example.invalid/polari-module-security.git',
                 route_target='some-developer', stages=[[], ['security']])
    check('a complete APP-mode device validates clean',
          not [k for k, (s, _) in v.items() if s == 'FAIL'], {k: x for k, x in v.items() if x[0] == 'FAIL'})

    # ---- ci-9: CI_ROUTE_TARGET — where an app-mode device's OWN releases go
    v = verdicts(mode='app', app_name='security', app_repo='x', stages=[[], ['security']])
    check('ci-9: APP mode with no CI_ROUTE_TARGET → FAIL: "publish it somewhere" is not a release, and the '
          'one place it may NOT go is upstream',
          v['CI_ROUTE_TARGET'][0] == 'FAIL' and 'names none' in v['CI_ROUTE_TARGET'][1], v.get('CI_ROUTE_TARGET'))
    v = verdicts(mode='app', app_name='security', app_repo='x', route_target='dausume',
                 stages=[[], ['security']])
    check('  …CI_ROUTE_TARGET = the UPSTREAM owner → FAIL, in the device settings as well as in the routes',
          v['CI_ROUTE_TARGET'][0] == 'FAIL' and 'UPSTREAM owner' in v['CI_ROUTE_TARGET'][1], v.get('CI_ROUTE_TARGET'))
    v = verdicts(mode='suite', route_target='some-developer')
    check('  …set while the mode is suite → WARN, it is ignored (the suite publishes to the suite\'s routes)',
          v['CI_ROUTE_TARGET'][0] == 'WARN' and 'it is ignored' in v['CI_ROUTE_TARGET'][1], v.get('CI_ROUTE_TARGET'))

    # ---- ci-9: the offline-first cache is ADVISORY — a bad knob slows a build, never stops it
    v = verdicts(cache='on')
    check('ci-9: CI_CACHE=on says plainly what it does — read first, fetch only what is missing',
          v['CI_CACHE'][0] == 'OK' and 'fetch only what is missing' in v['CI_CACHE'][1], v.get('CI_CACHE'))
    v = verdicts(cache='off')
    check('  …CI_CACHE=off is a WARN, not a FAIL: turning the cache off is legal, just slow',
          v['CI_CACHE'][0] == 'WARN' and 're-downloads' in v['CI_CACHE'][1], v.get('CI_CACHE'))
    v = verdicts(cache='maybe')
    check('  …a value outside on|off IS a FAIL — a device that cannot read its own knob is unpredictable, '
          'which is worse than slow',
          v['CI_CACHE'][0] == 'FAIL' and 'on|off' in v['CI_CACHE'][1], v.get('CI_CACHE'))
    v = verdicts(cache_max_gb='lots')
    check('  …a non-numeric CI_CACHE_MAX_GB → FAIL', v['CI_CACHE_MAX_GB'][0] == 'FAIL')
    v = verdicts(cache_proxies='on')
    check('  …CI_CACHE_PROXIES=on names the four proxies and the command that shows them',
          v['CI_CACHE_PROXIES'][0] == 'OK' and 'cache proxies status' in v['CI_CACHE_PROXIES'][1],
          v.get('CI_CACHE_PROXIES'))
    v = verdicts(cache_proxies='off')
    check('  …and OFF is the default and is stated as the whole of tier one',
          v['CI_CACHE_PROXIES'][0] == 'OK' and 'no services to keep alive' in v['CI_CACHE_PROXIES'][1])
    v = verdicts()
    check('  …an empty CI_CACHE_DIR is OK and explains WHY the default is relative to the pool '
          '(an ssh isle target caches on its own disk)',
          v['CI_CACHE_DIR'][0] == 'OK' and 'own disk' in v['CI_CACHE_DIR'][1], v.get('CI_CACHE_DIR'))
    v = verdicts(mode='wat')
    check('a mode outside suite|app is a WARN and reads as suite — an unknown mode from a newer core must '
          'not stop an older device running the pipeline it already has',
          v['CI_MODE'][0] == 'WARN' and 'reading it as suite' in v['CI_MODE'][1], v.get('CI_MODE'))
    v = verdicts(mode='suite', app_name='security')
    check('an app name set while the mode is suite → WARN, it is ignored',
          v['CI_APP_NAME'][0] == 'WARN' and 'it is ignored' in v['CI_APP_NAME'][1])

    v = verdicts(mode='app', app_name='security', app_repo='x', core_source='release:latest',
                 stages=[[], ['security']])
    check('core_source release:latest is OK and says the core is PULLED, never rebuilt',
          v['CI_CORE_SOURCE'][0] == 'OK' and 'PULLED' in v['CI_CORE_SOURCE'][1], v.get('CI_CORE_SOURCE'))
    _app = dict(mode='app', app_name='security', app_repo='x', stages=[[], ['security']])
    v = verdicts(core_source='release:polari-v2026.09.19', **_app)
    check('  …and an exact release tag names that release',
          v['CI_CORE_SOURCE'][0] == 'OK' and 'polari-v2026.09.19' in v['CI_CORE_SOURCE'][1])
    v = verdicts(core_source='release:', **_app)
    check('  …release: with no tag → FAIL (the shape is checked here; nothing is fetched)',
          v['CI_CORE_SOURCE'][0] == 'FAIL' and 'no tag' in v['CI_CORE_SOURCE'][1])
    v = verdicts(core_source='build', **_app)
    check('  …build is the escape hatch for a developer who also patches core',
          v['CI_CORE_SOURCE'][0] == 'OK' and 'REBUILT' in v['CI_CORE_SOURCE'][1])
    v = verdicts(core_source='somewhere-else', **_app)
    check('  …anything else → FAIL naming the two shapes',
          v['CI_CORE_SOURCE'][0] == 'FAIL' and 'release:<tag>' in v['CI_CORE_SOURCE'][1])

    # ci-12 addendum 7 — and every one of those verdicts is an APP-MODE verdict.
    # In SUITE mode the core is what the run builds, so this key decides nothing
    # and the row must not promise otherwise. ci-9's default (release:latest) is
    # in every device.env whichever mode it is in, and a suite device that
    # believed it sent its isle stage off to pull a core release that does not
    # exist (polari-isle-test #5, polari-release #84–#86).
    v = verdicts(mode='suite', core_source='release:latest')
    check('SUITE mode: release:latest is INFO — the core is built here and the knob is ignored',
          v['CI_CORE_SOURCE'][0] == 'OK' and 'is an app-mode knob and is ignored' in v['CI_CORE_SOURCE'][1],
          v.get('CI_CORE_SOURCE'))
    check('  …and it does NOT say the core is PULLED, which is what the Jenkinsfiles believed',
          'PULLED' not in v['CI_CORE_SOURCE'][1], v.get('CI_CORE_SOURCE'))
    v = verdicts(mode='suite', core_source='release:')
    check('  …a malformed release: cannot FAIL a suite device on a knob it never reads',
          v['CI_CORE_SOURCE'][0] == 'OK', v.get('CI_CORE_SOURCE'))

    # the app-mode stage warnings
    def st(stages, **kw):
        return {r['key']: (r['status'], r['message']) for r in V.validate_stages(stages, **kw)}
    v = st([[], ['security'], ['iso']], mode='app', app_name='security')
    check('APP mode: a stage naming ANOTHER app → WARN, not a refusal — testing it here is reasonable, '
          'releasing it here is not, and the warning says exactly that',
          'isle stages (other apps)' in v
          and 'maintains security' in v['isle stages (other apps)'][1]
          and 'never released here' in v['isle stages (other apps)'][1], sorted(v))
    v = st([[]], mode='app', app_name='security')
    check('APP mode: no stage tests the app it maintains → WARN naming the default (core; <app>)',
          'isle stages (the app)' in v and 'core; security' in v['isle stages (the app)'][1], sorted(v))
    v = st([[], ['security']], mode='app', app_name='security')
    check('  …and the default stage list itself warns about nothing',
          not [k for k in v if k.startswith('isle stages')], sorted(v))
    check('default_stages: suite → core only; app → core, then the one app',
          V.default_stages('suite') == [[]] and V.default_stages('app', 'security') == [[], ['security']])

    # routes: a fork is never republished upstream
    r = V.validate_routes([{'route': 'github-release', 'target': 'dausume/polari-suite'}],
                          mode='app', app_name='security')
    check('APP mode: a route pointed at the UPSTREAM owner is a FAIL — a fork republished under an upstream '
          'name is a false claim about provenance, and the fix is one field away',
          r and r[0]['status'] == 'FAIL' and 'upstream owner' in r[0]['message'], r)
    r = V.validate_routes([{'route': 'github-release', 'target': 'somebody-else/polari-module-security'}],
                          mode='app', app_name='security')
    check('  …their own namespace is fine', r and r[0]['status'] == 'OK', r)
    r = V.validate_routes([{'route': 'github-release', 'target': 'dausume/polari-suite'}], mode='suite')
    check('  …and in SUITE mode the upstream owner is exactly right', r and r[0]['status'] == 'OK', r)

    # device.env carries the mode keys (ci-8) and the cache + route-target keys (ci-9),
    # in device.sh's own order
    env = V.device_env(dict(mode='app', app_name='security', app_repo='https://example.invalid/r.git',
                            core_source='release:latest', isle_target='local', vm_ram_gb=4, vm_vcpus=2,
                            vm_disk_gb=30, nested='auto', min_free_gb=20, min_ram_headroom_gb=1,
                            executors=1, routes=['ghcr'], cache='on', cache_max_gb=40,
                            cache_proxies='off', route_target='some-developer'), [[], ['security']])
    keys = [line.split('=', 1)[0] for line in env.strip().splitlines()]
    check('the rendered device.env exports the mode keys FIRST and every device.sh key exactly once',
          keys[:4] == ['CI_MODE', 'CI_APP_NAME', 'CI_APP_REPO', 'CI_CORE_SOURCE']
          and len(keys) == len(set(keys)) == 24, keys)
    check('  …and the stages knob is rendered from the rows, not copied from a string',
          'CI_ISLE_STAGES=core; security\n' in env, env)
    # ci-9: a pull must not ERASE a key the core knows nothing about — the five new
    # keys are rendered, so an older device.env gains them instead of losing them.
    check('ci-9: the rendered device.env carries the cache knobs and the route target',
          all(('\n%s=' % k) in ('\n' + env) for k in
              ('CI_CACHE', 'CI_CACHE_DIR', 'CI_CACHE_MAX_GB', 'CI_CACHE_PROXIES', 'CI_ROUTE_TARGET')), keys)
    check('  …with the cache ON by default, because a pull from a core that never heard of ci-9 must not '
          'silently turn a device\'s cache off',
          'CI_CACHE=on\n' in V.device_env(dict(mode='suite'), [[]]),
          V.device_env(dict(mode='suite'), [[]]))


# -------------------------------------------------------- the mirror's refusals
def _ingest_checks():
    from cicd.cicd_api import CicdAPI
    from cicd.cicd_basis import PipelineDevice
    from cicd.custom.cicd_auth import TOKEN_HEADER, hash_token, mint_token
    from cicd.custom.cicd_ingest import KINDS, check as icheck, value_like_fields

    TABLES = ('PipelineDevice', 'PipelineStage', 'PipelineRoute', 'PipelineSecretPresence',
              'PipelineRun', 'IsleTestResult', 'ReleaseRecord')
    m = _M(*TABLES)
    api = CicdAPI(polServer=None, manager=m)
    tok = mint_token()
    PipelineDevice(manager=m, name='pipe-1', ingest_token_hash=hash_token(tok), mode='suite')
    hdr = {TOKEN_HEADER: tok}

    # ---- no credential
    res = _Res(); api.on_post_ingest(_Req(media={'kind': 'run', 'device': 'pipe-1'}), res)
    check('the mirror with NO credential is 401 — and the refusal names the door that mints one',
          res.status.startswith('401') and 'device/token' in res.media['refusal'], res.media)
    res = _Res(); api.on_post_ingest(_Req(media={'kind': 'run'}, headers={TOKEN_HEADER: 'not-the-token'}), res)
    check('a WRONG credential is 401 too, not a 403 — a token that is not this device\'s is no token at all',
          res.status.startswith('401'))

    # ---- the five kinds, and nothing else
    check('the mirror accepts exactly seven kinds (ci-12 added test-verdict)',
          KINDS == ('device', 'secrets', 'run', 'isle-test', 'release', 'setup', 'test-verdict'), KINDS)
    res = _Res(); api.on_post_ingest(_Req(media={'kind': 'whatever', 'device': 'pipe-1'}, headers=hdr), res)
    check('an unknown kind is a 400 that NAMES the five — never a shrug, never a row from a body nobody designed',
          res.status.startswith('400') and 'unknown kind' in res.media['error']
          and all(k in res.media['error'] for k in KINDS), res.media)

    # ---- a value-shaped field: refused, and NOTHING stored
    before = {t: len(m.objectTables[t]) for t in TABLES}
    body = {'kind': 'secrets', 'device': 'pipe-1',
            'items': [{'area': 'github', 'secret_name': 'github_token', 'present': True,
                       'value': 'ghp_THE_ACTUAL_SECRET'}]}
    res = _Res(); api.on_post_ingest(_Req(media=body, headers=hdr), res)
    after = {t: len(m.objectTables[t]) for t in TABLES}
    check('a body carrying a value-shaped field is a 400 that NAMES the field — filtered would be a leak that '
          'happened to miss; refused is a leak that could not start',
          res.status.startswith('400') and 'value-shaped' in res.media['error']
          and 'items[0].value' in res.media['error'], res.media)
    check('  …and NOTHING was stored: not the row, not the rest of the body, not a redacted version of it',
          before == after and 'ghp_THE_ACTUAL_SECRET' not in repr(m.objectTables), after)
    for bad in ('token', 'api_key', 'password', 'passphrase', 'credential', 'secret', 'privkey'):
        ok, why = icheck({'kind': 'run', 'device': 'p', 'job': 'release', 'status': 'running', bad: 'x'})
        check('a field named %r is refused wherever it appears' % bad, ok is False and bad in why, why)
    check('the scan is DEEP — a value buried three levels down is still found',
          value_like_fields({'a': {'b': [{'token': 1}]}}) == ['a.b[0].token'])
    check('  …and `secret_name` is exempt: presence rows exist to carry names',
          value_like_fields({'secret_name': 'github_token'}) == [])

    # ---- the honest secrets post
    res = _Res()
    api.on_post_ingest(_Req(media={'kind': 'secrets', 'device': 'pipe-1', 'items': [
        {'area': 'github', 'secret_name': 'github_token', 'present': True, 'needed_by': ['github-release']},
        {'area': 'registries', 'secret_name': 'ghcr_token', 'present': False, 'needed_by': ['ghcr']}]},
        headers=hdr), res)
    rows = list(m.objectTables['PipelineSecretPresence'].values())
    check('presence posts store the NAME and the boolean, and the table holds nothing else',
          res.media.get('ok') and len(rows) == 2
          and {(r.area, r.secret_name, r.present) for r in rows}
          == {('github', 'github_token', True), ('registries', 'ghcr_token', False)}, res.media)

    # ---- a run: loopback only, known job, known status
    res = _Res()
    api.on_post_ingest(_Req(media={'kind': 'run', 'device': 'pipe-1', 'job': 'release', 'number': 7,
                                   'status': 'running', 'url': 'http://203.0.113.9:8080/job/x/7/'},
                            headers=hdr), res)
    check('a run URL that is not the controller\'s LOOPBACK console is refused — a persisted, rendered row '
          'may not carry a LAN address',
          res.status.startswith('400') and 'loopback' in res.media['error'], res.media)
    check('  …and no address of any kind reached a row', '203.0.113' not in repr(m.objectTables))
    res = _Res()
    api.on_post_ingest(_Req(media={'kind': 'run', 'device': 'pipe-1', 'job': 'wat', 'number': 1,
                                   'status': 'running'}, headers=hdr), res)
    check('an unknown job is refused naming the four the pipeline has',
          res.status.startswith('400') and 'unknown job' in res.media['error'])
    res = _Res()
    api.on_post_ingest(_Req(media={'kind': 'run', 'device': 'pipe-1', 'job': 'release', 'number': 1,
                                   'status': 'finished'}, headers=hdr), res)
    check('an unknown status is refused too (`finished` is not one of the five)',
          res.status.startswith('400') and 'unknown status' in res.media['error'])
    res = _Res()
    api.on_post_ingest(_Req(media={'kind': 'run', 'device': 'pipe-1', 'job': 'release', 'number': 7,
                                   'status': 'running', 'url': 'http://127.0.0.1:8080/job/x/7/'},
                            headers=hdr), res)
    check('a loopback console URL is stored — that is how a person at the device clicks through',
          res.media.get('ok') and list(m.objectTables['PipelineRun'].values())[0].url.startswith('http://127.0.0.1'))

    # ---- one device's token is never another's
    PipelineDevice(manager=m, name='pipe-2')
    res = _Res()
    api.on_post_ingest(_Req(media={'kind': 'run', 'device': 'pipe-2', 'job': 'release', 'number': 1,
                                   'status': 'running'}, headers=hdr), res)
    check('a credential may post ONLY for its own device — posting for another is 403, naming both',
          res.status.startswith('403') and "'pipe-1'" in res.media['refusal']
          and "'pipe-2'" in res.media['refusal'], res.media)

    # ---- a device post REPORTS, it does not override
    dev = _named(m, 'PipelineDevice', 'pipe-1')
    dev.isle_target = 'ssh'; dev.isle_ssh_alias = 'isle-core'
    res = _Res()
    api.on_post_ingest(_Req(media={'kind': 'device', 'device': 'pipe-1',
                                   'settings': {'isle_target': 'local', 'isle_ssh_alias': ''},
                                   'setup': {'steps_done': 6, 'steps_total': 8, 'ready': False,
                                             'verdict': 'NOT READY', 'doctor_warnings': 3,
                                             'preflight_verdict': 'FAIL'}}, headers=hdr), res)
    check('a device post REPORTS readiness and does NOT override the settings — otherwise device.env would '
          'quietly become the source of truth again, which is the thing ci-8 exists to stop',
          res.media.get('ok') and res.media.get('adopted') is False
          and dev.isle_target == 'ssh' and dev.setup_steps_done == 6 and dev.doctor_warnings == 3
          and dev.preflight_verdict == 'FAIL', (dev.isle_target, dev.setup_steps_done))
    res = _Res()
    api.on_post_ingest(_Req(media={'kind': 'device', 'device': 'pipe-1',
                                   'settings': {'isle_ssh_alias': '198.51.100.7'}}, headers=hdr), res)
    check('  …and a device reporting an ADDRESS as its alias is refused on the way in as well',
          res.status.startswith('400') and 'ADDRESS' in res.media['error'], res.media)

    # ---- ADOPTION: the first post for a device nobody has a row for.
    # The credential itself has to live on a row, so adoption of the SETTINGS is exercised through the
    # builders directly — that is exactly the branch the door takes when `existing` is None.
    from cicd.custom.cicd_ingest import device_rows, stage_rows
    payload, adopted = device_rows({'device': 'newbox', 'settings': {'mode': 'app', 'app_name': 'security',
                                                                     'app_repo': 'https://e.invalid/r.git',
                                                                     'core_source': 'release:latest'}},
                                   existing=None, posted_by='cicd-ingest:newbox')
    check('ADOPTION: a device the core has never seen has its own configuration taken as the first version '
          'of the truth — the only bootstrap path there is',
          adopted is True and payload['mode'] == 'app' and payload['app_name'] == 'security'
          and payload['core_source'] == 'release:latest', payload)
    srows = stage_rows({'device': 'newbox', 'settings': {'mode': 'app', 'app_name': 'security'}})
    check('  …and an adopted APP-mode device with no stages gets the default core; <app>',
          [json.loads(r['apps_json']) for r in srows] == [[], ['security']], srows)

    # ---- the release kind must name the core it was tested against, in app mode
    ok, why = icheck({'kind': 'release', 'device': 'p', 'mode': 'app', 'version': '1'})
    check('an APP-mode release with no `tested_against` is REFUSED — a deb that passed against an unnamed '
          'core is an unfalsifiable claim',
          ok is False and 'tested_against' in why, why)
    ok, why = icheck({'kind': 'release', 'device': 'p', 'mode': 'app', 'version': '1',
                      'tested_against': 'release:polari-v2026.09.19'})
    check('  …and with it, it is accepted', ok is True, why)
    ok, why = icheck({'kind': 'release', 'device': 'p', 'mode': 'suite', 'version': '1'})
    check('  …suite mode needs none: the core it was tested against is the one this run built', ok is True, why)

    from cicd.custom.cicd_ingest import release_row
    row = release_row({'device': 'd', 'version': '2026.09.20', 'mode': 'app', 'app_name': 'security',
                       'tested_against': 'release:polari-v2026.09.19', 'core_ok': True,
                       'results_present': True, 'released': ['polari-app-security_1_all.deb'],
                       'not_released': {'polari-app-iso_1_all.deb': 'untested or failed in the isle test'},
                       'published_routes': ['github-release'], 'dry_routes': {'ghcr': 'secret absent'}})
    check('the release record carries BOTH halves of the rule — what shipped, and what was held back WITH '
          'the reason — plus the core it was tested against',
          json.loads(row['released_json']) == ['polari-app-security_1_all.deb']
          and json.loads(row['not_released_json']) == {'polari-app-iso_1_all.deb':
                                                       'untested or failed in the isle test'}
          and row['tested_against'] == 'release:polari-v2026.09.19'
          and row['results_present'] is True and row['core_ok'] is True, row)


# --------------------------------------------------- the admin doors + the token
def _admin_checks():
    from cicd.cicd_api import CicdAPI
    from cicd.cicd_basis import PipelineDevice
    from cicd.cicd_api import CicdAPI
    from cicd.custom.cicd_auth import hash_token

    TABLES = ('PipelineDevice', 'PipelineStage', 'PipelineRoute', 'PipelineSecretPresence',
              'PipelineRun', 'IsleTestResult', 'ReleaseRecord')
    m = _M(*TABLES)
    api = CicdAPI(polServer=None, manager=m)
    PipelineDevice(manager=m, name='pipe-1')
    anon = None
    viewer = {'sub': 'u-1', 'roles': ['polari-viewer'], 'raw_claims': {'groups': []}}
    admin = {'sub': 'a-9', 'roles': ['polari-admin'], 'raw_claims': {'groups': []}}

    res = _Res(); api.on_post_device(_Req(anon, media={'device': 'pipe-1'}), res)
    check('an UNAUTHENTICATED settings change is 401', res.status.startswith('401'), res.media)
    res = _Res(); api.on_post_device(_Req(viewer, media={'device': 'pipe-1'}), res)
    check('a signed-in NON-admin is 403, and the refusal names the rule (ADMIN_ROLES)',
          res.status.startswith('403') and 'administrator' in res.media['refusal'], res.media)

    res = _Res()
    api.on_post_device(_Req(admin, media={'device': 'pipe-1', 'settings': {'isle_target': 'sideways'}}), res)
    check('an admin change that FAILS validation is refused whole — nothing partial is written',
          res.status.startswith('400') and _named(m, 'PipelineDevice', 'pipe-1').isle_target != 'sideways',
          res.media)
    res = _Res()
    api.on_post_device(_Req(admin, media={'device': 'pipe-1',
                                          'settings': {'isle_target': 'ssh', 'isle_ssh_alias': 'isle-core',
                                                       'vm_ram_gb': 8}}), res)
    row = _named(m, 'PipelineDevice', 'pipe-1')
    check('an admin change that validates is stored, and the row records WHOSE sub changed it (D18-1: the '
          'sub alone, never a username)',
          res.media.get('ok') and row.isle_target == 'ssh' and row.vm_ram_gb == 8
          and row.posted_by == 'a-9', res.media)

    # ---- the token, shown once
    res = _Res(); api.on_post_device_token(_Req(viewer, media={'device': 'pipe-1'}), res)
    check('only an administrator may mint the posting credential', res.status.startswith('403'))
    res = _Res(); api.on_post_device_token(_Req(admin, media={'device': 'pipe-1'}), res)
    token = res.media.get('token')
    check('minting returns the token ONCE, says so, and names where the device should keep it',
          bool(token) and res.media.get('shown') == 'once'
          and res.media.get('store_it_as') == 'polari/cicd_ingest_token', res.media)
    check('  …and Polari keeps only the sha256 — the token itself is in no row, anywhere',
          row.ingest_token_hash == hash_token(token) and token not in repr(m.objectTables), row.ingest_token_hash)
    res2 = _Res(); api.on_get_device(_Req(admin, device='pipe-1'), res2)
    check('  …a later read says a token is SET and never echoes it or its hash',
          res2.media.get('token_set') is True and token not in json.dumps(res2.media)
          and row.ingest_token_hash not in json.dumps(res2.media), res2.media.keys())
    res3 = _Res(); api.on_post_device_token(_Req(admin, media={'device': 'pipe-1'}), res3)
    check('  …minting again REVOKES the previous token (a leak is fixed per device, never realm-wide)',
          res3.media['token'] != token and row.ingest_token_hash == hash_token(res3.media['token']))

    # ---- stages: the whole list at once, and a shorter list loses its tail
    res = _Res()
    api.on_post_stages(_Req(admin, media={'device': 'pipe-1', 'stages': [[], ['security'], ['iso']]}), res)
    check('an admin replaces the ordered stage list and gets the rendered knob back',
          res.media.get('ok') and res.media['knob'] == 'core; security; iso'
          and len(m.objectTables['PipelineStage']) == 3, res.media)
    res = _Res()
    api.on_post_stages(_Req(admin, media={'device': 'pipe-1', 'stages': 'core; security'}), res)
    check('  …a shorter list LOSES its tail rows — otherwise stage 3 of the old list would keep running',
          res.media.get('ok') and len(m.objectTables['PipelineStage']) == 2
          and res.media['removed'] == ['pipe-1:3'], res.media)
    check('  …and the answer carries the release rule, because this list IS what can ever ship',
          'only generates artifacts for things it TESTED' in res.media['release_rule'])

    # ---- routes
    res = _Res(); api.on_post_route(_Req(admin, media={'device': 'pipe-1', 'enabled': True}), res, 'npm')
    check('a PARKED route cannot be enabled — it needs an outside account and nothing asks for it (his rule)',
          res.status.startswith('400') and 'PARKED' in res.media['error'], res.media)
    res = _Res(); api.on_post_route(_Req(admin, media={'device': 'pipe-1', 'enabled': True}), res, 'nonsense')
    check('  …and an unknown route is refused naming the four ACTIVE ones',
          res.status.startswith('400') and 'unknown route' in res.media['error'])
    res = _Res(); api.on_post_route(_Req(admin, media={'device': 'pipe-1', 'enabled': True}), res, 'ghcr')
    check('enabling an ACTIVE route stores it and re-derives CI_ROUTES from the rows',
          res.media.get('ok') and res.media['ci_routes'] == ['ghcr']
          and json.loads(_named(m, 'PipelineDevice', 'pipe-1').routes_json) == ['ghcr'], res.media)
    check('  …and the answer says plainly that enabled alone publishes nothing',
          'armed' in res.media['how'] and 'release rule' in res.media['how'])

    # ---- the ONE read the pipeline makes
    res = _Res(); api.on_get(_Req(anon, device='pipe-1'), res)
    body = res.media
    check('GET /api/cicd answers settings + stages + routes + readiness + the rendered device.env in ONE '
          'read — a pipeline that had to make four half-configures itself when the third times out',
          body['ok'] and {'settings', 'stages', 'routes', 'readiness', 'device_env', 'validation',
                          'release_rule', 'mode', 'mode_reading'} <= set(body), sorted(body))
    check('  …and no secret, token or hash is anywhere in it',
          row.ingest_token_hash not in json.dumps(body) and 'token' not in json.dumps(body).lower()
          .replace('"token_set"', ''), [k for k in body])
    res = _Res(); api.on_get(_Req(anon), res)
    check('a core with TWO pipeline devices refuses to guess which — answering one device\'s settings to the '
          'other\'s pipeline would have it write them into its own device.env',
          bool(PipelineDevice(manager=m, name='pipe-2')) and True)
    res = _Res(); api.on_get(_Req(anon), res)
    check('  …the refusal lists the devices it knows and names the ?device= parameter',
          res.media['ok'] is False and set(res.media['devices']) == {'pipe-1', 'pipe-2'}
          and '?device=' in res.media['refusal'], res.media)


# ------------------------------------------------------------ the §54 route guard
def _route_guard_checks():
    """Falcon resolves `on_<method>_<suffix>` and RAISES SuffixedMethodNotFoundError from add_route() ITSELF
    when it finds none — so a suffix that has drifted from its method name does not degrade to a 405, it
    takes the whole backend down at boot. Seen live in the security module (§54); guarded here from day one."""
    from cicd.cicd_api import CicdAPI

    class _Falcon:
        def __init__(self):
            self.routes = []

        def add_route(self, uri, resource, suffix=None):
            self.routes.append((uri, suffix))

    class _Srv:
        def __init__(self):
            self.falconServer = _Falcon()

    srv = _Srv()
    api = CicdAPI(polServer=srv, manager=_M())
    orphans = [uri for uri, suffix in srv.falconServer.routes
               if not any(hasattr(api, 'on_%s%s' % (meth, ('_' + suffix) if suffix else ''))
                          for meth in ('get', 'post', 'put', 'delete'))]
    check('§54 guard: every /api/cicd route registered has a responder named for its suffix — a drifted '
          'suffix RAISES from add_route() and takes the backend down at boot',
          orphans == [], orphans)
    check('  …and all eleven doors are registered (ci-12 added /api/cicd/verdicts)',
          len(srv.falconServer.routes) == 11
          and ('/api/cicd/ingest', 'ingest') in srv.falconServer.routes
          and ('/api/cicd/device/token', 'device_token') in srv.falconServer.routes,
          srv.falconServer.routes)
    from cicd.custom.cicd_ingest import KINDS as _KINDS
    check('  …the ingest kind dispatcher has a handler for each kind (isle-test → _ingest_isle_test)',
          all(hasattr(api, '_ingest_%s' % k.replace('-', '_')) for k in _KINDS), _KINDS)


# ----------------------------------------------------------- the pages, the seed
def _page_seed_checks():
    from cicd.cicd_page import SEED_CICD_PAGE_DISPLAYS
    from cicd.cicd_seed import CICD_SEED_PAIRS, SEED_CICD_PERMISSION_PROFILES

    names = [p['name'] for p in SEED_CICD_PAGE_DISPLAYS]
    check('five configured pages: the pipeline, its SETUP WIZARD, its stages, its runs, its releases',
          names == ['cicd', 'cicd-setup', 'cicd-stages', 'cicd-runs', 'cicd-releases'], names)
    comps = set()
    for page in SEED_CICD_PAGE_DISPLAYS:
        for r in json.loads(page['definition'])['rows']:
            for it in r['items']:
                comps.add(it['componentProps']['componentName'])
    check('every item is a generic registered component or the ONE panel ci-11a added — and no api-json-panel '
          '(his rule: nothing raw on a screen)',
          comps == {'class-rows-table', 'api-structured-panel', 'pipeline-setup-panel'}, sorted(comps))
    check('  …and that one panel is used ONLY on the wizard page: everywhere else is still a configured table '
          'or the structured panel',
          {page['name'] for page in SEED_CICD_PAGE_DISPLAYS
           for r in json.loads(page['definition'])['rows'] for it in r['items']
           if it['componentProps']['componentName'] == 'pipeline-setup-panel'} == {'cicd-setup'})
    tables = {it['componentProps']['inputs']['className']
              for page in SEED_CICD_PAGE_DISPLAYS
              for r in json.loads(page['definition'])['rows'] for it in r['items']
              if it['componentProps']['componentName'] == 'class-rows-table'}
    check('the SETTINGS rows all have their own editable table — that IS the editing surface (his per-object '
          'display rule), not a bespoke settings screen',
          {'PipelineDevice', 'PipelineStage', 'PipelineRoute'} <= tables, sorted(tables))
    check('the overview states the MODE plainly, in words, from the API',
          any(it['componentProps']['inputs'].get('pick') == 'mode_reading'
              for r in json.loads(SEED_CICD_PAGE_DISPLAYS[0]['definition'])['rows'] for it in r['items']))

    seeded = {name: rows for name, _cls, rows in CICD_SEED_PAIRS}
    check('NOTHING about a machine or a build is seeded: a device is ADOPTED, and a seeded run would be a '
          'claim about a build nobody ran',
          all(seeded[k] == [] for k in ('PipelineDevice', 'PipelineStage', 'PipelineRoute',
                                        'PipelineSecretPresence', 'PipelineRun', 'IsleTestResult',
                                        'ReleaseRecord')),
          {k: len(v) for k, v in seeded.items()})
    prof = {p['name']: p for p in SEED_CICD_PERMISSION_PROFILES}
    check('the WRITE GATE is seeded: cicd-settings grants the settings classes to administrators, published',
          prof['cicd-settings']['published'] is True
          and json.loads(prof['cicd-settings']['kc_groups_json']) == ['polari-admin']
          and json.loads(prof['cicd-settings']['extra_classes_json'])
          == ['PipelineDevice', 'PipelineStage', 'PipelineRoute'], prof.get('cicd-settings'))
    check('  …and it deliberately grants NO write on the mirrored tables — hand-editing a run that happened '
          'is not a thing to grant',
          not ({'PipelineRun', 'IsleTestResult', 'ReleaseRecord'}
               & set(json.loads(prof['cicd-settings']['extra_classes_json']))))
    check('cicd-observer ships as a TEMPLATE (unpublished, no group bound) — the shipped convention: a '
          'profile grants nothing until somebody binds a real group',
          prof['cicd-observer']['published'] is False
          and json.loads(prof['cicd-observer']['kc_groups_json']) == []
          and json.loads(prof['cicd-observer']['verbs_json']) == ['read'])


# --------------------------------------------------------------- the manifest
def _manifest_checks():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    man = json.load(open(os.path.join(here, 'polari-app.json'), encoding='utf-8'))
    from moduleService.manifests import validate
    problems = validate(man)
    check('the manifest is valid against the standard (moduleService.manifests.validate)', problems == [], problems)
    check('the manifest declares the nine classes plus the API, the endpoints constructor, the seed pairs '
          'and the pages',
          len([c for c in man['classes'] if c != 'CicdAPI']) == 9
          and man['endpoints'] == 'cicd.cicd_endpoints:construct_cicd_endpoints'
          and man['seedPairs'] == 'cicd.cicd_seed:CICD_SEED_PAIRS'
          and man['pages'] == ['cicd.cicd_page:SEED_CICD_PAGE_DISPLAYS'], man['classes'])
    check('it declares NO outbound flows: this module receives a mirror, it does not send rows anywhere',
          man['app'].get('flows') == [], man['app'].get('flows'))
    check('it names its selftest, so `manifests conform` is clean', man['selftests'] == ['cicd_selftest'])

    # ------------------------------------------------------------------ ci-12
    # THE BRANCH MODEL's row: one answer per tested sha, and the linkage a
    # release carries back to it.
    print('-- ci-12: the test verdict — ONE answer per sha, and what a release is allowed by')
    from cicd.cicd_basis import CICD_CLASSES, PipelineDevice, ReleaseRecord
    from cicd.cicd_basis import TestVerdict
    from cicd.cicd_api import CicdAPI
    from cicd.custom.cicd_auth import hash_token
    from cicd.custom.cicd_ingest import VALUE_LIKE, VALUE_LIKE_EXEMPT
    from cicd.custom.cicd_ingest import check as _icheck, test_verdict_row

    check('TestVerdict knows exactly three answers — passed, failed and the honest middle one',
          TestVerdict.VERDICTS == ('passed', 'failed', 'partial'), TestVerdict.VERDICTS)
    check('  …and it carries no value-shaped field, like every other row class here',
          not [p for p in inspect.signature(TestVerdict.__init__).parameters
               if VALUE_LIKE.search(p) and p not in VALUE_LIKE_EXEMPT],
          list(inspect.signature(TestVerdict.__init__).parameters))
    check('  …it is keyed on the SUPERPROJECT sha, not on a version: most tested shas are never released',
          'sha' in inspect.signature(TestVerdict.__init__).parameters
          and 'version' not in inspect.signature(TestVerdict.__init__).parameters)
    check('  …and its git branch column is `git_branch`: `branch` is a treeObject INTERNAL var, and a row '
          'field of that name silently breaks every construction of the class',
          'branch' not in inspect.signature(TestVerdict.__init__).parameters
          and 'git_branch' in inspect.signature(TestVerdict.__init__).parameters,
          list(inspect.signature(TestVerdict.__init__).parameters))
    check('  …the three summaries are JSON STRING columns, so the page renders configured columns and '
          'never a raw-JSON panel (his rule)',
          all(k in inspect.signature(TestVerdict.__init__).parameters
              for k in ('scans_json', 'selftests_json', 'isle_json')))

    ok_, why_ = _icheck({'kind': 'test-verdict', 'device': 'pipe-1', 'sha': 'a' * 40,
                         'verdict': 'passed'})
    check('a passing verdict with a sha is accepted', ok_, why_)
    ok_, why_ = _icheck({'kind': 'test-verdict', 'device': 'pipe-1', 'sha': 'a' * 40, 'verdict': 'green'})
    check('an unknown verdict is refused and NAMES the three', not ok_ and 'passed' in why_ and 'partial' in why_, why_)
    ok_, why_ = _icheck({'kind': 'test-verdict', 'device': 'pipe-1', 'verdict': 'passed'})
    check('a verdict about NO sha is refused — `promote main` could never find it', not ok_ and 'sha' in why_, why_)
    ok_, why_ = _icheck({'kind': 'test-verdict', 'device': 'pipe-1', 'sha': 'b' * 40, 'verdict': 'partial'})
    check('a non-passing verdict with no `why` is refused: a bare "failed" is a result nobody can act on',
          not ok_ and 'why' in why_.lower(), why_)
    ok_, why_ = _icheck({'kind': 'test-verdict', 'device': 'pipe-1', 'sha': 'b' * 40, 'verdict': 'partial',
                         'why': 'the isle stages are still ci-3'})
    check('  …and it is accepted the moment it says why', ok_, why_)
    ok_, why_ = _icheck({'kind': 'test-verdict', 'device': 'pipe-1', 'sha': 'c' * 40, 'verdict': 'passed',
                         'token': 'shhh'})
    check('a verdict carrying a value-shaped field is refused whole, like every other kind', not ok_, why_)

    row = test_verdict_row({'device': 'pipe-1', 'sha': 'd' * 40, 'verdict': 'partial',
                            'why': 'isle skipped', 'built': True,
                            'selftests': {'modules': {'core': 'pass'}, 'suites': 88, 'passed': 88,
                                          'failed': 0},
                            'isle': {'core_ok': False, 'stages': 1},
                            'scans': {'totals': {'high': 3}}}, posted_by='cicd-ingest:pipe-1')
    check('the row is keyed <device>:<sha>', row['name'] == 'pipe-1:' + 'd' * 40, row['name'])
    check('  …the selftest arithmetic is lifted into columns a table can show',
          (row['selftest_suites'], row['selftest_passed'], row['selftest_failed']) == (88, 88, 0))
    check('  …core_ok is lifted out of the isle summary: it is the half the release rule turns on',
          row['core_ok'] is False and 'core_ok' in row['isle_json'])
    check('  …the ADVISORY scan counts are carried and are NOT in the verdict arithmetic',
          '"high": 3' in row['scans_json'] and row['verdict'] == 'partial')
    check('  …the mirror NEVER recomputes the verdict: it stores what the device decided',
          row['verdict'] == 'partial' and row['decided_by'] == 'pipeline')

    check('ReleaseRecord gained the branch-model linkage, and did NOT overload tested_against',
          {'tested_verdict', 'tested_sha', 'tested_against'}
          <= set(inspect.signature(ReleaseRecord.__init__).parameters),
          list(inspect.signature(ReleaseRecord.__init__).parameters))

    from cicd.custom.cicd_auth import TOKEN_HEADER, mint_token
    _m = _M(*[c.__name__ for c in CICD_CLASSES])
    _api = CicdAPI(polServer=None, manager=_m)
    _tok = mint_token()
    PipelineDevice(manager=_m, name='pipe-1', ingest_token_hash=hash_token(_tok))
    _res = _Res()
    _api.on_post_ingest(_Req(media={'kind': 'test-verdict', 'device': 'pipe-1', 'sha': 'e' * 40,
                                    'verdict': 'partial', 'why': 'the isle stages are still ci-3',
                                    'selftests': {'modules': {'core': 'pass'}, 'suites': 3, 'passed': 3,
                                                  'failed': 0},
                                    'isle': {'core_ok': False}, 'scans': {'totals': {'medium': 2}}},
                             headers={TOKEN_HEADER: _tok}), _res)
    check('POST /api/cicd/ingest stores a test verdict and echoes what it says',
          _res.media and _res.media.get('ok') and _res.media.get('says') == 'partial', _res.media)
    _res = _Res(); _api.on_get_verdicts(_Req(), _res)
    check('GET /api/cicd/verdicts answers with the verdicts and the rule, in words',
          _res.media['count'] == 1 and _res.media['verdicts'][0]['verdict'] == 'partial'
          and 'passed' in _res.media['how'], _res.media)
    check('  …and the answer carries the advisory scan counts without them changing a verdict',
          _res.media['verdicts'][0]['scans'].get('totals', {}).get('medium') == 2)

    _pages = {p['pageRoute']: p for p in __import__(
        'cicd.cicd_page', fromlist=['SEED_CICD_PAGE_DISPLAYS']).SEED_CICD_PAGE_DISPLAYS}
    _runs = json.loads(_pages['cicd-runs']['definition'])
    _items = [i for r in _runs['rows'] for i in r['items']]
    _inp = lambda i: (i.get('componentProps') or {}).get('inputs') or {}
    _cmp = lambda i: (i.get('componentProps') or {}).get('componentName')
    check('the cicd-runs page shows the VERDICT column, from a configured table + the structured panel',
          any(_inp(i).get('className') == 'TestVerdict' and 'verdict' in (_inp(i).get('columns') or '')
              for i in _items)
          and any('/api/cicd/verdicts' in str(_inp(i).get('path') or '') for i in _items),
          [(i.get('id'), _cmp(i)) for i in _items])
    check('  …and still uses ONLY the two generic components — no raw-JSON panel anywhere (his rule)',
          all(_cmp(i) in ('class-rows-table', 'api-structured-panel') for i in _items),
          sorted({_cmp(i) for i in _items}))

    # the admission knob, by file: the pipeline-device prod profile ends in ,cicd
    prof = os.path.abspath(os.path.join(here, '..', '..', '..', '..',
                                        'polari-cli', 'prod-profiles', 'pipeline-device.env'))
    if os.path.isfile(prof):
        body = open(prof, encoding='utf-8').read()
        line = [l for l in body.splitlines() if l.startswith('POL_PROD_MODULES=')]
        check('ADMISSION: polari-cli/prod-profiles/pipeline-device.env ends its POL_PROD_MODULES with ,cicd — '
              'that is what "always enabled with the pipeline" means, and it is one file, not a convention',
              line and line[0].rstrip().endswith(',cicd'), line)
    else:
        check('ADMISSION: the pipeline-device prod profile exists', False, prof)
    check('the module is a FEATURE_MODULE (it may be absent from a checkout) and is not core-required',
          man['featureModule'] is True and man['coreRequired'] is False)


def _teardown_checks():
    """ci-10 — the teardown arrives as two readings, and the coupling is enforced on the way IN too.

    The Jenkinsfile already ANDs core_ok with a clean uninstall. That is one door. This is the second:
    a row posted by anything at all (a re-post, an older pipeline, a hand-rolled curl) may not claim a
    passing core for an isle that could not hand the machine back.
    """
    from cicd.custom.cicd_ingest import isle_test_row

    base = {'kind': 'isle-test', 'device': 'pipe-1', 'run': 'polari-isle-test#7', 'stage_index': 1,
            'version': '2026.09.19', 'apps': ['gears'], 'core_ok': True, 'results': {'gears': 'pass'}}

    r = isle_test_row(dict(base, uninstall_verdict='clean'))
    check('a CLEAN hand-back lets a posted row keep core_ok', r['core_ok'] is True)
    check('  …and the verdict is stored as given', r['uninstall_verdict'] == 'clean')

    r = isle_test_row(dict(base, uninstall_verdict='dirty',
                           uninstall_findings=['volumes remaining: 2']))
    check('a DIRTY hand-back clears core_ok on the way IN, not just in the pipeline', r['core_ok'] is False)
    check('  …and the product\'s own finding is kept verbatim, for the page to show',
          'volumes remaining: 2' in r['uninstall_json'])

    r = isle_test_row(dict(base, uninstall_verdict='skipped'))
    check('a SKIPPED hand-back is not a pass either — it was never exercised', r['core_ok'] is False)

    r = isle_test_row(base)
    check('a post with no uninstall verdict at all defaults to skipped, and so cannot claim a core',
          r['uninstall_verdict'] == 'skipped' and r['core_ok'] is False)

    r = isle_test_row(dict(base, uninstall_verdict='clean', leak_verdict='leaked-after-rewipe',
                           leaks=['file: /var/lib/libvirt/images/polari-ci-isle.qcow2 (absent → 12.0G)'],
                           ram_delta_mb=-1400, disk_delta_mb=-12000))
    check('a LEAK is recorded but does NOT block the release — it is the pipeline\'s mess, not the product\'s',
          r['core_ok'] is True and r['leak_verdict'] == 'leaked-after-rewipe')
    check('  …the leaked things are listed', 'polari-ci-isle.qcow2' in r['leaks_json'])
    check('  …and the RAM that did not come back is a NEGATIVE number, which is the whole reading',
          r['ram_delta_mb'] == -1400 and r['disk_delta_mb'] == -12000)

    r = isle_test_row(dict(base, uninstall_verdict='clean', ram_delta_mb='not-a-number'))
    check('an unreadable delta becomes 0 rather than crashing the mirror', r['ram_delta_mb'] == 0)

    from cicd.cicd_page import SEED_CICD_PAGE_DISPLAYS
    cols = json.dumps(SEED_CICD_PAGE_DISPLAYS)
    check('the cicd-runs page shows both verdicts as CONFIGURED COLUMNS (no raw JSON panel, his rule)',
          'uninstall_verdict' in cols and 'leak_verdict' in cols and 'ram_delta_mb' in cols)


# --------------------------------------- ci-11a: the setup protocol, mirrored, and the page that shows it
def _setup_protocol_checks():
    """THE WIZARD's half in Polari: the `setup` ingest kind, the door that reads it back, and the page.

    The protocol itself is produced by `polari-jenkins/setup.sh --json` and tested by
    `polari-jenkins/selftest.sh`. What is asserted HERE is the contract between the two: what the door
    accepts, what it refuses, and that a secret VALUE cannot survive the trip.
    """
    from cicd.cicd_api import CicdAPI
    from cicd.cicd_basis import PipelineDevice, PipelineSetupStep
    from cicd.cicd_api import CicdAPI
    from cicd.custom.cicd_auth import hash_token
    from cicd.custom.cicd_ingest import KINDS, SETUP_PROTOCOL, check as ingest_check, setup_value_leak

    TABLES = ('PipelineDevice', 'PipelineStage', 'PipelineRoute', 'PipelineSecretPresence',
              'PipelineRun', 'IsleTestResult', 'ReleaseRecord', 'PipelineSetupStep')
    m = _M(*TABLES)
    api = CicdAPI(polServer=None, manager=m)
    PipelineDevice(manager=m, name='pipe-1', ingest_token_hash=hash_token('tok-11a'))
    hdr = {'X-Polari-CICD-Token': 'tok-11a'}

    def step(name='role', index=1, state='todo', **kw):
        out = {'name': name, 'index': index, 'total': 8, 'title': 'a step', 'state': state,
               'explain': 'what this step is, in plain words',
               'checks_json': json.dumps([{'name': 'submodules', 'value': 'all five populated',
                                           'verdict': 'OK', 'fix': ''}]),
               'questions_json': json.dumps([]), 'actions_json': json.dumps([]), 'where_json': json.dumps([])}
        out.update(kw)
        return out

    def body(steps=None, **kw):
        out = {'kind': 'setup', 'device': 'pipe-1', 'at': '2026-09-19T10:00:00',
               'setup_protocol': SETUP_PROTOCOL, 'steps': steps if steps is not None else [step()],
               'todo_json': json.dumps([{'step': 'network', 'text': 'put this device on a wire',
                                         'command': 'nmcli con show'}]),
               'complete': 1, 'steps_total': 8, 'ready': False, 'blocking': 'put this device on a wire'}
        out.update(kw)
        return out

    check('the walkthrough is a MIRRORED kind, not a settings one: nothing a person edits here reaches '
          'the device — `pol jenkins setup` runs on the device and a Polari core cannot run `pol`',
          'setup' in KINDS and PipelineSetupStep in __import__(
              'cicd.cicd_basis', fromlist=['x']).CICD_MIRROR_CLASSES)
    check('the door names the ONE protocol it mirrors', SETUP_PROTOCOL == 'polari-pipeline-setup/1')
    ok, why = ingest_check(body(setup_protocol='polari-pipeline-setup/2'))
    check('a body declaring a DIFFERENT protocol is refused — a front end that read another version would '
          'render a step it does not understand', not ok and 'polari-pipeline-setup/1' in why, why)
    ok, why = ingest_check(body(steps=[step(state='nearly')]))
    check('an unknown step state is refused, naming the four', not ok and 'blocked' in why and 'skipped' in why, why)
    ok, why = ingest_check(body(steps=[dict(step(), checks=[{'name': 'submodules'}])]))
    check('a step posting NESTED sub-structures is refused, naming the four *_json columns it should have '
          'used instead', not ok and 'JSON STRINGS' in why and 'checks' in why, why)
    ok, why = ingest_check(body(steps=[{'name': 'role', 'state': 'todo',
                                        'questions': [{'key': 'CI_MODE'}]}]))
    check('  …and a nested QUESTION is caught even earlier, by the generic value-shaped-key guard — because '
          'a question\'s key is literally `key`. That is exactly why these columns are strings.',
          not ok and 'steps[0].questions[0].key' in why, why)

    # ---- the one refusal this kind exists to make
    leaky = step(questions_json=json.dumps([{'key': 'github/github_token', 'kind': 'secret',
                                             'answered': 'ghp_realtokenvalue'}]))
    ok, why = ingest_check(body(steps=[leaky]))
    check('a SECRET question carrying anything but `present` is REFUSED and nothing is stored — a dropped '
          'field is a leak that happened to miss, a refusal is a leak that could not start',
          not ok and 'present' in why, why)
    check('  …and the refusal NAMES the question, so the poster can fix its payload',
          'github/github_token' in (why or ''), why)
    check('  …the refusal text never repeats the value it refused', 'ghp_realtokenvalue' not in (why or ''))
    ok, _ = ingest_check(body(steps=[step(questions_json=json.dumps(
        [{'key': 'github/github_token', 'kind': 'secret', 'answered': 'present'}]))]))
    check('  …`present` is accepted: presence is exactly what a page may know about a secret', ok)
    check('  …a secret question carrying a DEFAULT is refused too (a secret has no default)',
          setup_value_leak([step(questions_json=json.dumps(
              [{'key': 'x/y', 'kind': 'secret', 'default': 'seed', 'answered': ''}]))]) is not None)
    check('  …a non-secret question is left alone: an answered CI_MODE is a knob, not a value',
          setup_value_leak([step(questions_json=json.dumps(
              [{'key': 'CI_MODE', 'kind': 'choice', 'answered': 'suite'}]))]) is None)

    # ---- the round trip
    res = _Res()
    api.on_post_ingest(_Req(media=body(steps=[step('role', 1, 'done'),
                                              step('network', 3, 'blocked')]), headers=hdr), res)
    check('a well-formed walkthrough is stored, one row per step',
          res.media.get('ok') and res.media.get('steps') == 2, res.media)
    check('  …the answer points at the door that reads it back',
          res.media.get('read_it_back') == '/api/cicd/setup?device=pipe-1', res.media)
    dev = _named(m, 'PipelineDevice', 'pipe-1')
    check('  …and the DOCUMENT-level state lands on the device row: what is blocking, and the to-do list',
          getattr(dev, 'setup_blocking') == 'put this device on a wire'
          and json.loads(getattr(dev, 'setup_todo_json'))[0]['step'] == 'network', dev)

    res = _Res(); api.on_get_setup(_Req(device='pipe-1'), res)
    doc = res.media
    check('GET /api/cicd/setup answers the protocol document, reassembled from the rows',
          doc['protocol'] == SETUP_PROTOCOL and [s['name'] for s in doc['steps']] == ['role', 'network'], doc)
    check('  …with the four sub-structures re-nested as lists, not as the strings they travelled as',
          isinstance(doc['steps'][0]['checks'], list)
          and doc['steps'][0]['checks'][0]['verdict'] == 'OK', doc['steps'][0])
    check('  …and it says LIVE: FALSE — it is the last push, never a live reading, and the page says so '
          'instead of implying it just ran', doc['live'] is False and 'MIRROR' in doc['how'])
    check('  …the summary carries what the device computed, not a recount here',
          doc['summary'] == {'complete': 1, 'total': 8, 'ready': False,
                             'blocking': 'put this device on a wire'}, doc['summary'])
    check('  …the steps come back in the device\'s order, by index',
          [s['index'] for s in doc['steps']] == [1, 3], doc['steps'])

    m2 = _M(*TABLES)
    api2 = CicdAPI(polServer=None, manager=m2)
    PipelineDevice(manager=m2, name='fresh')
    res = _Res(); api2.on_get_setup(_Req(device='fresh'), res)
    check('a device that has never pushed gets an empty document and the exact command that fixes it — '
          'not an error, and not a pretence that the core could run it',
          res.media['ok'] and res.media['steps'] == [] and 'pol jenkins sync push' in res.media['how'],
          res.media)

    # ---- the page
    from cicd.cicd_page import SEED_CICD_PAGE_DISPLAYS
    page = [p for p in SEED_CICD_PAGE_DISPLAYS if p['name'] == 'cicd-setup'][0]
    items = [it for r in json.loads(page['definition'])['rows'] for it in r['items']]
    panel = [it for it in items if it['componentProps']['componentName'] == 'pipeline-setup-panel']
    check('the wizard page exists at /display/cicd-setup and is sourced from the mirrored steps',
          page['pageRoute'] == 'cicd-setup' and page['source_class'] == 'PipelineSetupStep')
    check('  …it carries EXACTLY ONE of the new panel — the whole walkthrough, not one panel per step',
          len(panel) == 1, [it['id'] for it in panel])
    check('  …the panel is pointed at the mirror door, so a browser with no shell still renders something',
          panel[0]['componentProps']['inputs']['path'] == '/api/cicd/setup')
    check('  …and every OTHER item on the page is a configured table or the structured panel (his rule)',
          {it['componentProps']['componentName'] for it in items if it not in panel}
          == {'class-rows-table', 'api-structured-panel'})
    check('  …the page shows secret PRESENCE and where to get each one — the one thing a person actually '
          'needs from a screen — and no column that could hold a value',
          any(it['componentProps']['inputs'].get('className') == 'PipelineSecretPresence'
              and 'where_to_get' in it['componentProps']['inputs']['columns'] for it in items))
    check('PipelineSetupStep has no value-shaped field, like every other row class here',
          not [p for p in inspect.signature(PipelineSetupStep.__init__).parameters
               if __import__('cicd.custom.cicd_ingest', fromlist=['x']).VALUE_LIKE.search(p)],
          list(inspect.signature(PipelineSetupStep.__init__).parameters))
    check('  …and it declares its state vocabulary rather than leaving it to a string anybody invents',
          PipelineSetupStep.STATES == ('done', 'todo', 'blocked', 'skipped'))


def main():
    print('cicd_selftest — the rows, the ONE rule set, the two modes, the mirror\'s refusals, the token')
    print('-- the rows')
    _row_checks()
    print('-- the ONE rule set: parity with polari-jenkins/device.sh')
    _validation_checks()
    print('-- the two modes: the whole suite, or ONE app somebody maintains')
    _mode_checks()
    print('-- the mirror: five kinds, one credential, and what it refuses')
    _ingest_checks()
    print('-- ci-10: the teardown — the product\'s hand-back gates the release, our leak does not')
    _teardown_checks()
    print('-- the admin doors, and the token shown once')
    _admin_checks()
    print('-- the §54 route guard')
    _route_guard_checks()
    print('-- ci-11a: the setup walkthrough, mirrored in, and the page that shows it')
    _setup_protocol_checks()
    print('-- the pages and the seed')
    _page_seed_checks()
    print('-- the manifest and the admission knob')
    _manifest_checks()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
