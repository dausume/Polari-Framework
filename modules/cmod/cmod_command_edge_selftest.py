"""cmod_command_edge_selftest - bss-7a (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 6b): the SECOND path into "light on" - a Polari command through the
bridge - runs on the real twin: the command edge becomes a `--inject` of a frame built from the node's exact requirements (led_on = 1 -> SET_LED), the
requirement is met at an exact cycle, the same node now has two confirmations by two paths; a command into a node with no wire-field requirement is refused
in words; the manifest.

    PYTHONPATH=.:modules python3 -m cmod.cmod_command_edge_selftest      # from polari-framework/
"""
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
    from cmod.custom import confirmations as C
    from cmod.custom import config_rows as R
    from cmod.custom import node_run as NR
    ready, why = light_twin.engine_ready()
    check('the avr engines are reachable: %s' % why, ready, why)
    if not ready:
        print('\n%d/%d passed' % (passed, total))
        return 1
    m = _manager()
    _seed(m)
    v = T.view(m, BS)
    boot = next(n for n in v['nodes'] if n['kind'] == 'boot')
    press, command = '%s:press-PD2' % BS, '%s:command-uno-1-bridge' % BS
    light = T.define(m, BS, 'light-on', 'light on', boot['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 1}],
                     executions=[{'atom': 'apps/light.apply_command', 'isotope': 'receive-command:uart-rx-interrupt'}])
    light = T.connect(m, BS, boot['name'], light['name'], 'trigger', command)
    cmd_path = next(p for p in light['paths'] if 'via command' in p['edges'])
    out = NR.run(m, BS, light['name'], path=cmd_path['name'])
    e = out['edges'][-1]
    check('THE COMMAND PATH runs on the twin: a SET_LED frame (led_on = 1, from the node\'s own requirement) is injected at the stimulus cycle and led_on meets its '
          'requirement at an exact cycle after it', out['run']['outcome'] == 'reached' and e['met_cycle'] > e['stimulus_cycle'] > 0 and 'via command' in e['edge'],
          (out['run']['outcome'], out['run']['words'], e))
    check('THE DURATION of the command edge is the frame\'s flight plus the firmware (under 100 ms), the step is the UART bit (receive-command:uart-rx-interrupt)',
          0 < out['run']['duration_s'] < 0.1 and 'receive-command:uart-rx-interrupt' in out['run']['step_set_by'], (out['run']['duration_s'], out['run']['step_set_by']))
    sig = {s['signal']: s for s in out['signals']}
    check('led_on went 0 -> 1 once on the command', sig['led_on']['first'] == '0' and sig['led_on']['last'] == '1' and sig['led_on']['changes'] == 1, sig.get('led_on'))
    press_path = next(p for p in light['paths'] if 'via press' in p['edges'])
    out2 = NR.run(m, BS, light['name'], path=press_path['name'])
    live = [c for c in C.of(m, light['name']) if c['state'] == 'confirmed']
    check('THE SAME NODE confirmed by TWO PATHS (the command, the press), both on the same build', out2['run']['outcome'] == 'reached' and len(live) == 2
          and {c['path'] for c in live} == {p['name'] for p in light['paths']} and len({c['hex_sha256'] for c in live}) == 1, [(c['path'], c['by']) for c in live])
    T.define(m, BS, 'toggled', '', boot['name'], 'trigger', command, requirements=[{'object_map': MAP, 'field': 'toggles', 'kind': 'range', 'value': '1..9'}], executions=['apps/light.apply_command'])
    try:
        NR.run(m, BS, '%s:toggled' % BS)
        refused = ''
    except R.ConfigRefused as x:
        refused = x.why
    check('A COMMAND into a node with no EXACT requirement on a wire field is refused in words (the frame has nothing to carry)',
          refused.startswith('the command') and 'exact values on wire fields' in refused, refused)
    from moduleService.manifests import conform
    rr = conform('cmod')
    check('MANIFEST: pol modules conform cmod is clean', rr['ok'], rr.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
