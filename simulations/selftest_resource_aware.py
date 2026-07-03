"""
Self-test for the resource-aware simulation layer: step-cost tracking
with stat freezing, budget projection + the plain-language warning, and
data-saving suggestions.

Run from polari-framework/:
    python3 -m simulations.selftest_resource_aware
"""

import json
import os
import tempfile
from types import SimpleNamespace

from simulations.step_cost_tracker import (
    NUMERIC_FREEZE_SAMPLES,
    TEXT_FREEZE_SAMPLES,
    config_hash,
    get_profile,
    reset_profile,
    track_step,
)
from simulations.resource_monitor import project_run, system_resources
from simulations.resource_suggestions import suggestions_for
from simulations.simulation_runner import _effective_field_save_rules

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


class _FakeDB:
    def __init__(self):
        self.saves = 0

    def saveInstanceInDB(self, inst):
        self.saves += 1


def _manager():
    m = SimpleNamespace()
    m.objectTables = {'StepCostProfile': {}}
    m.objectTypingDict = {}
    m.db = _FakeDB()
    return m


def _register_profile_factory(manager):
    """StepCostProfile construction needs the real treeObject machinery;
    for the pure-python selftest we intercept creation by pre-seeding an
    empty profile SimpleNamespace the tracker will find and update."""
    def make(sim_ref):
        p = SimpleNamespace(
            name=f'{sim_ref}-cost-profile', simulation_ref=sim_ref,
            config_hash='', step_count=0,
            avg_step_seconds=0.0, max_step_seconds=0.0,
            avg_step_bytes=0.0, max_step_bytes=0.0,
            field_stats_json='{}', updated_step=0,
        )
        manager.objectTables['StepCostProfile'][p.name] = p
        return p
    return make


def _sim_def(name='demo-sim', params='{"g": 9.81}'):
    return SimpleNamespace(
        name=name, parameters_json=params,
        field_save_overrides_json='{}',
        participating_sim_state_classes_json='["S"]',
        time_step_seconds=0.01, duration_seconds=1.0,
        recording_interval_steps=1,
    )


def _run(sim='demo-sim'):
    return SimpleNamespace(
        name='r1', simulation_ref=sim, parameter_overrides_json='{}',
        field_save_overrides_json='{}', time_step_seconds=0.0,
    )


def _tracking():
    print('Resource-aware — step-cost tracking + stat freezing\n')
    m = _manager()
    make = _register_profile_factory(m)
    sim, run = _sim_def(), _run()
    profile = make(sim.name)
    profile.config_hash = config_hash(sim, run)

    # Numeric fields freeze after 3 identical-width samples.
    for step in range(1, 4):
        track_step(m, run, sim, {'S': {'px': 0.5, 'name': 'x'}}, step, 0.01)
    stats = json.loads(profile.field_stats_json)
    check('numeric field frozen after 3 consistent samples',
          stats['S.px']['frozen'] is True
          and stats['S.px']['n'] == NUMERIC_FREEZE_SAMPLES,
          f"n={stats['S.px']['n']}")
    check('identity fields are never measured', 'S.name' not in stats)

    # Stable text freezes at n>=20 with cv<0.05; volatile text never does.
    m2 = _manager()
    make2 = _register_profile_factory(m2)
    p2 = make2(sim.name)
    p2.config_hash = config_hash(sim, run)
    stable = json.dumps([[1.0] * 6] * 64)          # constant-size grid
    for step in range(1, TEXT_FREEZE_SAMPLES + 1):
        rows = {'G': {'cells_json': stable,
                      'blob': 'x' * (10 if step % 2 else 4000)}}
        track_step(m2, run, sim, rows, step, 0.02)
    st2 = json.loads(p2.field_stats_json)
    check('constant-size grid payload FROZEN at 20 samples (measurement '
          'consolidates itself away)',
          st2['G.cells_json']['frozen'] is True)
    check('volatile payload never freezes (keeps being measured)',
          st2['G.blob']['frozen'] is False and st2['G.blob']['cv'] > 0.05,
          f"cv={st2['G.blob']['cv']}")
    check('EMA/max step bytes populated sanely',
          p2.avg_step_bytes > 0 and p2.max_step_bytes >= p2.avg_step_bytes)

    # Frozen fields are skipped but still counted via their constant.
    before_n = st2['G.cells_json']['n']
    track_step(m2, run, sim, {'G': {'cells_json': stable, 'blob': 'y' * 100}},
               99, 0.02)
    st3 = json.loads(p2.field_stats_json)
    check('frozen field is no longer sampled (n unchanged)',
          st3['G.cells_json']['n'] == before_n)

    # Config-hash change resets the stats (usage pattern changed).
    sim_changed = _sim_def(params='{"g": 1.62}')
    track_step(m2, run, sim_changed, {'G': {'cells_json': stable}}, 100, 0.02)
    st4 = json.loads(p2.field_stats_json)
    check('config change auto-resets the profile (re-learn)',
          p2.step_count == 1 and st4['G.cells_json']['n'] == 1)

    # The purposeful re-measure switch.
    check('reset_profile clears stats', reset_profile(m2, sim.name) is True
          and p2.field_stats_json == '{}')

    # Failure isolation: a hostile manager cannot break the step.
    hostile = SimpleNamespace(objectTables=None, db=None)
    try:
        track_step(hostile, run, sim, {'S': {'px': 1}}, 1, 0.01)
        isolated = True
    except Exception:
        isolated = False
    check('tracking is failure-isolated (observer never kills the observed)',
          isolated)


def _projection():
    print('\nResource-aware — budget projection + the critical warning\n')
    m = _manager()
    make = _register_profile_factory(m)
    sim, run = _sim_def(), _run()
    p = make(sim.name)
    p.config_hash = config_hash(sim, run)
    p.step_count = 50
    p.avg_step_bytes = 2.1 * 1024 * 1024      # ~2.1 MB/step
    p.avg_step_seconds = 0.05
    p.field_stats_json = json.dumps({
        'G.cells_json': {'n': 20, 'meanBytes': 2.0 * 1024 * 1024,
                         'maxBytes': 2100000, 'cv': 0.01, 'frozen': True},
        'S.px': {'n': 3, 'meanBytes': 8, 'maxBytes': 8, 'cv': 0.0,
                 'frozen': True},
    })

    res = {'memory': {'limitBytes': None, 'usedBytes': None,
                      'availableBytes': 12 * 1024 ** 3},
           'disk': {'freeBytes': 60 * 1024 ** 3}, 'source': 'test'}
    ok = project_run(m, run, sim, 100, resources=res)
    check('small batch projects ok', ok['level'] == 'ok'
          and ok['source'] == 'measured')
    warn = project_run(m, run, sim, 4000, resources=res)
    check('mid batch projects warning (>50% of budget)',
          warn['level'] == 'warning', f"level={warn['level']}")
    crit = project_run(m, run, sim, 5500, resources=res)
    check('big batch projects critical (>85% of budget)',
          crit['level'] == 'critical')
    check('message is plain language with real numbers',
          'steps at the ~2.1 MB/step' in crit['message']
          and 'nearly drain' in crit['message'],
          crit['message'][:100])
    check('top consumers ranked for the UI',
          crit['topConsumers'][0]['field'] == 'G.cells_json'
          and crit['topConsumers'][0]['frozen'] is True)

    # No measurements yet → static-estimate source (predictor fallback).
    m_empty = _manager()
    m_empty.objectTypingDict = {}
    proj = project_run(m_empty, run, sim, 10, resources=res)
    check('falls back to the static predictor before measurements exist',
          proj['source'] == 'static-estimate')


def _resources_parsing():
    print('\nResource-aware — cgroup/meminfo parsing\n')
    with tempfile.TemporaryDirectory() as d:
        def w(name, content):
            path = os.path.join(d, name)
            with open(path, 'w') as f:
                f.write(content)
            return path
        paths = {
            'v2_max': w('max', '8589934592\n'),
            'v2_cur': w('cur', '2147483648\n'),
            'v1_max': os.path.join(d, 'missing1'),
            'v1_cur': os.path.join(d, 'missing2'),
            'meminfo': os.path.join(d, 'missing3'),
        }
        r = system_resources(db_dir=d, paths=paths)
        check('cgroup v2 limit/used/available parsed',
              r['memory']['limitBytes'] == 8589934592
              and r['memory']['availableBytes'] == 8589934592 - 2147483648
              and r['source'] == 'cgroup-v2')
        paths['v2_max'] = w('max2', 'max\n')  # unlimited → host fallback
        paths['meminfo'] = w('meminfo',
                             'MemTotal: 16000000 kB\nMemAvailable: 12000000 kB\n')
        r2 = system_resources(db_dir=d, paths=paths)
        check("'max' (no limit) falls through to /proc/meminfo",
              r2['source'] == 'proc-meminfo'
              and r2['memory']['availableBytes'] == 12000000 * 1024)
        check('disk free reported', isinstance(r2['disk']['freeBytes'], int))


def _suggestions():
    print('\nResource-aware — data-saving suggestions\n')
    m = _manager()
    make = _register_profile_factory(m)
    sim = _sim_def(name='wind-sim')
    p = make(sim.name)
    p.step_count = 30
    p.avg_step_bytes = 5000.0
    p.field_stats_json = json.dumps({
        'G.cells_json': {'n': 20, 'meanBytes': 4600.0, 'maxBytes': 4700,
                         'cv': 0.01, 'frozen': True},
        'S.px': {'n': 3, 'meanBytes': 8, 'maxBytes': 8, 'cv': 0.0,
                 'frozen': True},
    })
    sugg = suggestions_for(m, 'wind-sim')
    check('suggestions produced and ranked by savings',
          len(sugg) >= 3
          and sugg[0]['savingsBytesPerStep'] >= sugg[-1]['savingsBytesPerStep'])
    check('tiny fields not suggested about (noise floor)',
          all(s['target'] != 'S.px' for s in sugg))
    top = next(s for s in sugg if s['kind'] == 'fieldPolicy')
    check('fieldPolicy suggestion worded as the user\'s call',
          'Your call' in top['message'])

    # A fragment is ready-to-apply through the per-run override channel.
    frag = next(s for s in sugg if s['kind'] == 'fieldInterval')['proposal']
    fake_mgr = SimpleNamespace(objectTypingDict={})
    fake_run = SimpleNamespace(field_save_overrides_json=json.dumps(frag))
    rules = _effective_field_save_rules(
        fake_mgr, _sim_def(), fake_run, 'G')
    check('fragment applies through the existing per-run channel',
          rules.get('cells_json', {}).get('interval') == 10,
          f"rules={rules.get('cells_json')}")

    check('no suggestions before any measurement',
          suggestions_for(_manager(), 'never-ran') == [])


if __name__ == '__main__':
    _tracking()
    _projection()
    _resources_parsing()
    _suggestions()
    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
