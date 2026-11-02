"""cmod_node_run_selftest - bss-2 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 6b): ONE NODE TEST ON THE REAL TWIN. The UNO light's "light on" node
(led_on = 1, reached from boot by a press on PD2) is run from reset along its fastest path: the flash edge is the hex, the init edge meets boot's written
requirement, the press stimulus lands at a known cycle and led_on is watched by address; the requirement is met at an exact cycle; the executions are
observed with the twin's own function counters; the collateral is read or honestly unmeasured; the assessment rows are kept and the events are not; a
node the firmware never reaches is not-reached in words; a wrong requirement is diverged; a blocked node does not run; the doors; the manifest.

Needs the avr engines (a local polari-avr-twin or the prf-board-engines image): the first check says so when they are missing.

    PYTHONPATH=.:modules python3 -m cmod.cmod_node_run_selftest      # from polari-framework/
"""
import json
import sys
import types

passed = total = 0
BS = 'uno-light-on-desk'
MAP = 'LightState_t->LightState'


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _manager():
    return types.SimpleNamespace(objectTables={}, idList=[], db=None, noteTreeMutation=lambda *a, **k: None)


def _seed(m):
    from cmod.custom import config_rows as R
    from cmod.custom.catom_assertions import SEED_ASSERTIONS, SEED_STRUCT_OBJECT_MAPS
    R.upsert(m, 'BenchConditions', 'room', ambient_min_c=18.0, ambient_max_c=30.0)
    R.upsert(m, 'BenchSolution', BS, bench='home-bench', firmware_solution='uno-light', conditions='room')
    for a in SEED_ASSERTIONS:
        if a['variant'] == 'uno-light':
            R.upsert(m, 'CatomAssertion', a['name'], **{k: v for k, v in a.items() if k != 'name'})
    som = SEED_STRUCT_OBJECT_MAPS[0]
    R.upsert(m, 'StructObjectMap', som['name'], **{k: v for k, v in som.items() if k != 'name'})


def main():
    from board.custom import light_twin
    from cmod.custom import bench_topology as T
    from cmod.custom import config_rows as R
    from cmod.custom import node_run as NR
    ready, why = light_twin.engine_ready()
    check('the avr engines are reachable (a local polari-avr-twin or the prf-board-engines image): %s' % why, ready, why)
    if not ready:
        print('\n%d/%d passed' % (passed, total))
        return 1
    m = _manager()
    _seed(m)
    v = T.view(m, BS)
    boot = next(n for n in v['nodes'] if n['kind'] == 'boot')
    press = '%s:press-PD2' % BS
    T.define(m, BS, 'light-on', 'light on', boot['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 1}],
             executions=[{'atom': 'apps/light.led_toggle', 'isotope': 'read-button:ext-interrupt'}, {'atom': 'apps/light.led_follow_state', 'isotope': 'drive-led:gpio-out'}])
    out = NR.run(m, BS, '%s:light-on' % BS)
    run, edges = out['run'], out['edges']
    by = {e['order']: e for e in edges}
    check('PROOF: "light on" is REACHED on the twin from reset along the fastest path: flash met (the hex), init met (boot_session written before the press), '
          'the press met led_on = 1 at an exact cycle after its stimulus', run['outcome'] == 'reached' and [by[i]['outcome'] for i in (1, 2, 3)] == ['met', 'met', 'met']
          and by[2]['met_cycle'] > 0 and by[3]['met_cycle'] > by[3]['stimulus_cycle'] > 0, (run['outcome'], run['words'], [(e['outcome'], e['met_cycle'], e['words'][:80]) for e in edges]))
    check('THE DURATION is the stimulus -> met time of the last edge (under 100 ms for a debounced press), and what set it is said',
          0 < run['duration_s'] < 0.1 and run['duration_set_by'], (run['duration_s'], run['duration_set_by']))
    check('THE STEP is the node\'s: one cycle (both executions are cycle rules: the interrupt and the GPIO write), and which asked is said',
          abs(run['step_s'] - 62.5e-9) < 1e-15 and '(cycle' in run['step_set_by'], run['step_set_by'])
    check('EXECUTIONS OBSERVED with the twin\'s own function counters: led_toggle and led_follow_state each observed (n > 0) or honestly "no symbol (inlined)"',
          'led_toggle: ' in by[3]['executions'] and 'led_follow_state: ' in by[3]['executions'] and 'not observed' not in by[3]['executions'], by[3]['executions'])
    check('THE COLLATERAL PD6 is read from the wire when the config carries the sense jumper, else said unmeasured - never guessed',
          by[3]['collaterals'].startswith('pin-level PD6: high at cycle') or by[3]['collaterals'].startswith('pin-level PD6: unmeasured'), by[3]['collaterals'])
    sig = {s['signal']: s for s in out['signals']}
    check('THE ASSESSMENT IS KEPT, NOT THE TRACE: led_on first 0 last 1 with its change cycles; the twin\'s events (%d) were the working buffer and are gone; no '
          'WaveformCapture row' % out['working_events'],
          sig['led_on']['first'] == '0' and sig['led_on']['last'] == '1' and sig['led_on']['changes'] >= 1 and sig['led_on']['first_change_cycle'] > 0
          and out['working_events'] > 0 and not m.objectTables.get('WaveformCapture'), sig.get('led_on'))
    T.define(m, BS, 'seven', 'a value the code never sets', boot['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 7}],
             executions=['apps/light.led_toggle'])
    o2 = NR.run(m, BS, '%s:seven' % BS)
    check('A required field that lands OUTSIDE its requirement is DIVERGED (D-bss-10), in words: led_on became 1, required exact 7', o2['run']['outcome'] == 'diverged'
          and 'led_on became 1, required exact 7' in o2['run']['words'], o2['run']['words'])
    T.define(m, BS, 'renamed', 'a field a press never touches', boot['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'name', 'kind': 'exact', 'value': 1}],
             executions=['apps/light.led_toggle'])
    o2b = NR.run(m, BS, '%s:renamed' % BS)
    check('A field the edge never changes is NOT-REACHED, in words naming the field and what it stayed', o2b['run']['outcome'] == 'not-reached'
          and o2b['run']['words'].startswith('name stayed'), o2b['run']['words'])
    T.define(m, BS, 'stays-off', 'light stays off on a press (wrong)', boot['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 0}],
             executions=['apps/light.led_toggle'])
    o3 = NR.run(m, BS, '%s:stays-off' % BS)
    check('A requirement the code contradicts is... met at the stimulus (led_on is still 0 when the press lands) - the user\'s rule: requirements are judged when met, '
          'so a "stays" claim needs a written / timing check (bss-3); said here as met at the stimulus cycle',
          o3['run']['outcome'] == 'reached' and o3['edges'][-1]['met_cycle'] == o3['edges'][-1]['stimulus_cycle'], (o3['run']['outcome'], o3['edges'][-1]['words']))
    R.upsert(m, 'StructFieldSamples', '%s:toggles' % MAP, object_map=MAP, field='toggles', kind='samples', values='1,2,3')
    T.define(m, BS, 'five', '', boot['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'toggles', 'kind': 'exact', 'value': 5}], executions=['apps/light.led_toggle'])
    o4 = NR.run(m, BS, '%s:five' % BS)
    check('A BLOCKED node (toggles = 5 is not a declared sample) does not run: outcome blocked with the words, no edges', o4['run']['outcome'] == 'blocked'
          and 'not a declared sample' in o4['run']['words'] and o4['edges'] == [], o4['run'])
    check('RUNS are kept per node, named in order', [r['name'] for r in NR.runs(m, '%s:light-on' % BS)] == ['%s:light-on#run1' % BS])
    from cmod.cmod_node_run_api import NodeRunAPI
    api = NodeRunAPI(polServer=None, manager=m)

    def call(method, *args, body=None):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        req = types.SimpleNamespace(bounded_stream=types.SimpleNamespace(read=lambda: json.dumps(body or {}).encode()))
        getattr(api, method)(req, resp, *args)
        return resp
    g = call('on_get_runs', BS, 'light-on')
    bad = call('on_post_run', BS, 'nope')
    check('DOORS: GET runs lists the kept run; POST run on an unknown node -> 404 in words', len(g.media['rows']) == 1 and bad.status.startswith('404') and 'no node' in bad.media['error'],
          (bad.status, bad.media))
    from moduleService.manifests import conform
    rr = conform('cmod')
    check('MANIFEST: pol modules conform cmod is clean with the new rows and files listed', rr['ok'], rr.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
