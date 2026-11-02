"""cmod_retest_selftest - bss-4 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md; cfg-4 merged): after a configuration or isotope change, the affected nodes are re-tested
FIRST, from the root, each along its fastest path; the executions' isotopes follow the Firmware Solution's configurations (a person's explicit one kept); the
confirmations of other builds are voided by the runs themselves; a run's kept rows are readable; the doors; the manifest. On the real twin.

    PYTHONPATH=.:modules python3 -m cmod.cmod_retest_selftest      # from polari-framework/
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
    from cmod.custom import catom_config as CF
    from cmod.custom import config_rows as R
    from cmod.custom import retest as RT
    ready, why = light_twin.engine_ready()
    check('the avr engines are reachable: %s' % why, ready, why)
    if not ready:
        print('\n%d/%d passed' % (passed, total))
        return 1
    m = _manager()
    _seed(m)
    v = T.view(m, BS)
    boot = next(n for n in v['nodes'] if n['kind'] == 'boot')
    press = '%s:press-PD2' % BS
    T.define(m, BS, 'light-on', 'light on', boot['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 1}],
             executions=[{'atom': 'apps/light.led_follow_state', 'isotope': 'drive-led:gpio-out'}])
    T.define(m, BS, 'toggled-once', 'toggled once', boot['name'], 'trigger', press, requirements=[{'object_map': MAP, 'field': 'toggles', 'kind': 'exact', 'value': 1}],
             executions=[{'atom': 'apps/light.led_toggle', 'isotope': 'read-button:ext-interrupt'}])
    check('AFFECTED: the catom read-button touches toggled-once (led_toggle is one of its atoms) and not light-on (led_follow_state is drive-led\'s)',
          RT.affected(m, BS, 'read-button') == ['%s:toggled-once' % BS] and RT.affected(m, BS, 'drive-led') == ['%s:light-on' % BS], (RT.affected(m, BS, 'read-button'), RT.affected(m, BS, 'drive-led')))
    CF.set_isotope(m, 'uno-light', 'read-button', 'gpio-poll')
    synced = RT.sync_isotopes(m, BS)
    x = R.rows(m, 'StructNodeExecution', node='%s:toggled-once' % BS)[0]
    check('SYNC: the Firmware Solution\'s configuration of read-button (gpio-poll) lands on the execution as read-button:gpio-poll, said where it came from',
          synced == [{'execution': x['name'], 'from': 'read-button:ext-interrupt', 'to': 'read-button:gpio-poll'}] and x['isotope'] == 'read-button:gpio-poll'
          and x['notes'].startswith('isotope: from CatomConfiguration'), (synced, x))
    R.upsert(m, 'StructNodeConfirmation', '%s:light-on#conf1' % BS, node='%s:light-on' % BS, by='twin', state='confirmed', hex_sha256='c' * 64)
    out = RT.retest(m, BS, 'read-button')
    check('RETEST after a change to read-button: toggled-once runs FIRST, then light-on; both reached; the older build\'s confirmation of light-on voided by its run',
          [r['node'].split(':')[-1] for r in out['runs']] == ['toggled-once', 'light-on'] and out['runs'][0]['affected'] and not out['runs'][1]['affected']
          and all(r['outcome'] == 'reached' for r in out['runs']) and out['confirmations_voided'] == 1 and '2 nodes re-tested (1 affected' in out['words'], out)
    run = out['runs'][1]['run']
    sig = RT.run_signals(m, run)
    edges = RT.run_edges(m, run)
    check('A RUN\'s kept rows are readable: its signals (led_on 0 -> 1, the wired pin) and its edges in order', any(s['signal'] == 'led_on' and s['last'] == '1' for s in sig)
          and [e['order'] for e in edges] == [1, 2, 3], ([(s['signal'], s['last']) for s in sig], [e['order'] for e in edges]))
    from cmod.cmod_retest_api import RetestAPI
    api = RetestAPI(polServer=None, manager=m)

    def call(method, *args, body=None):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        req = types.SimpleNamespace(bounded_stream=types.SimpleNamespace(read=lambda: json.dumps(body or {}).encode()))
        getattr(api, method)(req, resp, *args)
        return resp
    g = call('on_get_signals', BS, run)
    nf = call('on_get_edges', BS, 'nope')
    bad = call('on_post_retest', 'nope', body={})
    check('DOORS: GET a run\'s signals; unknown run -> 404; retest on an unknown Bench Solution -> 404', len(g.media['rows']) >= 1 and nf.status.startswith('404') and bad.status.startswith('404'),
          (nf.status, bad.status))
    from moduleService.manifests import conform
    rr = conform('cmod')
    rb = conform('board')
    check('MANIFEST: pol modules conform cmod and board are clean', rr['ok'] and rb['ok'], (rr.get('findings'), rb.get('findings')))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
