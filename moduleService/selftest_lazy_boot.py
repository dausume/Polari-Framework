"""
Self-test for mlb-1/2/3: the two-phase lazy boot.

Covers, without booting a full server (stub manager/polServer):
- knob semantics (POLARI_LAZY_BOOT off by default);
- dependency ordering over the json register ({A requires B} admits
  B first; cycles refuse loudly; outside deps are satisfied);
- the FEATURE_REQUIRES vs polari-modules.json drift pin;
- boot-timing history math (median, instance preference, honest
  no-history None) — Dustin's time-to-online-after-deps tracking;
- the registry lifecycle + honest-503 middleware + /api/health and
  /api/modules/status behavior through a real falcon App;
- the admission worker end-to-end on stubs: order, status rows,
  failure propagation (failed dependency blocks dependents, LOUDLY).

Run from polari-framework/:
    python3 -m moduleService.selftest_lazy_boot
"""

import os
import sys
import types

import falcon
import falcon.testing as ft

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def test_knob():
    print('[knob: off by default]')
    from polariApiServer.lazy_boot import lazy_boot_enabled
    old = os.environ.pop('POLARI_LAZY_BOOT', None)
    try:
        check('unset -> monolithic (off)', lazy_boot_enabled() is False)
        os.environ['POLARI_LAZY_BOOT'] = 'on'
        check('on -> lazy', lazy_boot_enabled() is True)
        os.environ['POLARI_LAZY_BOOT'] = 'garbage'
        check('unknown -> off (safe default)',
              lazy_boot_enabled() is False)
    finally:
        if old is None:
            os.environ.pop('POLARI_LAZY_BOOT', None)
        else:
            os.environ['POLARI_LAZY_BOOT'] = old


def test_dependency_order():
    print('[dependency order: json register is the source]')
    from moduleService.module_boot_records import (
        dependency_order, load_module_requires, requires_drift,
    )
    requires = load_module_requires()
    check('register knows aquaponics requires plant_morphology + '
          'scoring',
          {'plant_morphology', 'scoring'}
          <= requires.get('aquaponics', set()))
    check('register carries the pspp->materialsScience edge '
          '(json-only, not in FEATURE_REQUIRES)',
          'materialsScience' in requires.get('pspp', set()))
    got = dependency_order(['aquaponics', 'scoring',
                            'plant_morphology'])
    check('deps admit before dependents', got['ok'] and
          got['order'].index('aquaponics')
          > max(got['order'].index('scoring'),
                got['order'].index('plant_morphology')))
    solo = dependency_order(['aquaponics'])
    check('deps OUTSIDE the admitted set are treated satisfied',
          solo['ok'] and solo['order'] == ['aquaponics'])
    cyc = dependency_order(['x1', 'x2'],
                           requires={'x1': {'x2'}, 'x2': {'x1'}})
    check('a cycle refuses loudly with the members',
          cyc['ok'] is False and 'x1' in cyc['refusal']
          and 'x2' in cyc['refusal'])
    check('FEATURE_REQUIRES has NO edges the json register lacks '
          '(drift pin — json is authoritative)',
          requires_drift() == {})


def test_timing_history():
    print('[timing history: median ETA, honest no-history]')
    from moduleService.module_boot_records import expected_duration_s
    rows = [
        {'module_name': 'pspp', 'instance_name': 'a',
         'status': 'online', 'duration_after_deps_s': 10.0},
        {'module_name': 'pspp', 'instance_name': 'a',
         'status': 'online', 'duration_after_deps_s': 30.0},
        {'module_name': 'pspp', 'instance_name': 'a',
         'status': 'online', 'duration_after_deps_s': 20.0},
        {'module_name': 'pspp', 'instance_name': 'b',
         'status': 'online', 'duration_after_deps_s': 500.0},
        {'module_name': 'pspp', 'instance_name': 'a',
         'status': 'failed', 'duration_after_deps_s': 999.0},
    ]
    check('median of this instance\'s ONLINE runs',
          expected_duration_s(rows, 'pspp', 'a') == 20.0)
    check('other-instance history is the fallback, not the mix',
          expected_duration_s(rows, 'pspp', 'c') is not None)
    check('failed runs never enter the ETA',
          expected_duration_s(rows, 'pspp', 'a') != 999.0)
    check('no history -> None (no invented ETA)',
          expected_duration_s(rows, 'techtree', 'a') is None)
    even = rows[:2]
    check('even count -> midpoint median',
          expected_duration_s(even, 'pspp', 'a') == 20.0)


class _FakeCrude:
    """Looks like polariCRUDE to the middleware (has apiObject)."""
    def __init__(self, class_name):
        self.apiObject = class_name

    def on_get(self, request, response):
        response.media = {'ok': True}


def _registry_and_app(lazy=True):
    from polariApiServer.lazy_boot import (
        HealthEndpoint, ModuleBootRegistry, ModuleLoadingMiddleware,
        ModulesStatusEndpoint,
    )
    old = os.environ.get('POLARI_LAZY_BOOT')
    os.environ['POLARI_LAZY_BOOT'] = 'on' if lazy else 'off'
    try:
        registry = ModuleBootRegistry()
    finally:
        if old is None:
            os.environ.pop('POLARI_LAZY_BOOT', None)
        else:
            os.environ['POLARI_LAZY_BOOT'] = old
    stub = types.SimpleNamespace(bootRegistry=registry)
    app = falcon.App(middleware=[ModuleLoadingMiddleware(stub)])
    stub.falconServer = app
    HealthEndpoint(stub)
    ModulesStatusEndpoint(stub)
    return registry, app


def test_registry_and_middleware():
    print('[registry + middleware: honest 503, health flips]')
    registry, app = _registry_and_app(lazy=True)

    class PsppRow:
        __module__ = 'pspp.some_file'
    registry.class_owner['DigitizedDataset'] = 'pspp'
    registry.plan(['pspp'], {})
    app.add_route('/api/DigitizedDataset',
                  _FakeCrude('DigitizedDataset'))
    client = ft.TestClient(app)

    got = client.simulate_get('/api/health')
    check('health 503 before core data', got.status_code == 503)
    check('health names the phase',
          got.json.get('phase') == 'core-boot')
    got = client.simulate_get('/api/DigitizedDataset')
    check('pending module CRUDE -> 503 (never 404/empty)',
          got.status_code == 503)
    check('503 body names the module',
          'pspp' in got.json.get('description', ''))

    registry.core_ready()
    got = client.simulate_get('/api/health')
    check('health 200 at core-ready', got.status_code == 200)
    got = client.simulate_get('/api/DigitizedDataset')
    check('feature module still 503 until ITS admission',
          got.status_code == 503)

    registry.mark('pspp', 'online')
    registry.finish()
    got = client.simulate_get('/api/DigitizedDataset')
    check('online module serves', got.status_code == 200)
    got = client.simulate_get('/api/modules/status')
    check('status doc reports 100% with times',
          got.json['percentOnline'] == 100.0
          and got.json['secondsToCore'] is not None)

    mono_registry, mono_app = _registry_and_app(lazy=False)
    mono_app.add_route('/api/DigitizedDataset',
                       _FakeCrude('DigitizedDataset'))
    got = ft.TestClient(mono_app).simulate_get('/api/DigitizedDataset')
    check('monolithic boot: middleware is a no-op',
          got.status_code == 200)
    got = ft.TestClient(mono_app).simulate_get('/api/health')
    check('monolithic health is 200 (core-ready by construction)',
          got.status_code == 200)


def _fake_class(name, module):
    return type(name, (), {'__module__': f'{module}.rows'})


def test_admission_worker():
    print('[admission worker on stubs: order + failure propagation]')
    from polariApiServer.lazy_boot import (
        AdmissionWorker, ModuleBootRegistry,
    )
    old = os.environ.get('POLARI_LAZY_BOOT')
    os.environ['POLARI_LAZY_BOOT'] = 'on'
    try:
        registry = ModuleBootRegistry()
    finally:
        if old is None:
            os.environ.pop('POLARI_LAZY_BOOT', None)
        else:
            os.environ['POLARI_LAZY_BOOT'] = old

    calls = []
    def_classes = [
        _fake_class('CoreThing', 'topology'),
        _fake_class('ScoreTerm', 'scoring'),
        _fake_class('PlantDefinition', 'plant_morphology'),
        _fake_class('PotDefinition', 'aquaponics'),
    ]
    registry.register_classes(def_classes)

    def ensure(only_classes=None):
        calls.append(('ensure', frozenset(only_classes or ())))
        if only_classes and 'ScoreTerm' in only_classes:
            raise RuntimeError('scoring seed exploded')

    polServer = types.SimpleNamespace(
        defClassList=def_classes,
        bootRegistry=registry,
        ensureDefinitionTables=ensure,
        initializeDynamicModules=lambda: calls.append(('dynamic',)),
    )
    manager = types.SimpleNamespace(
        polServer=polServer,
        objectTables={},
        db=None,
        jumpstartDatabase=lambda **kw: calls.append(
            ('jumpstart', frozenset(kw.get('skip_restore_tables')
                                    or ()))),
        restoreTables=lambda only_tables=None: calls.append(
            ('restore', frozenset(only_tables or ()))),
        persistTree=lambda: calls.append(('persist',)),
    )
    worker = AdmissionWorker(manager)
    worker.run()  # run() must swallow nothing silently — statuses tell

    snap = registry.snapshot()
    mods = snap['modules']
    check('feature modules planned (core class excluded)',
          set(m for m in mods
              if mods[m]['status'] != 'disabled')
          == {'scoring', 'plant_morphology', 'aquaponics'})
    check('warm-restore of feature tables deferred at jumpstart',
          ('jumpstart', frozenset({'ScoreTerm', 'PlantDefinition',
                                   'PotDefinition'})) in calls)
    core_ensure = [c for c in calls if c[0] == 'ensure'
                   and 'CoreThing' in c[1]]
    check('core classes ensured in Phase A', len(core_ensure) == 1)
    check('scoring FAILED loudly (its seed raised)',
          mods['scoring']['status'] == 'failed'
          and 'exploded' in mods['scoring']['error'])
    check('plant_morphology came online',
          mods['plant_morphology']['status'] == 'online')
    check('aquaponics BLOCKED by the failed dependency, not skipped '
          'silently',
          mods['aquaponics']['status'] == 'blocked'
          and 'scoring' in mods['aquaponics']['error'])
    ensure_order = [c for c in calls if c[0] == 'ensure']
    check('dependency order: plant_morphology/scoring attempted '
          'before aquaponics would have been',
          all('PotDefinition' not in c[1] for c in ensure_order))
    check('dynamic modules + persistTree ran in close-out',
          ('dynamic',) in calls and ('persist',) in calls)
    check('disabled modules are visible in the snapshot',
          any(r['status'] == 'disabled' for r in mods.values()))
    check('online timing recorded (finished_at set)',
          mods['plant_morphology']['finished_at'] is not None)


def main():
    test_knob()
    test_dependency_order()
    test_timing_history()
    test_registry_and_middleware()
    test_admission_worker()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
