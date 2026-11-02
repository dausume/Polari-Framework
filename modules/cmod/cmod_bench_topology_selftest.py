"""cmod_bench_topology_selftest - bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md): the Hardware Event topology's start on the UNO light bench: the fixed
first chain (plugged in -> flashed -> boot), the offered Hardware Events derived from the firmware's own assertions, the chain an event is predicted to
cause, a defined node (requirements, executions, derived collaterals), its fastest path from the root, a second path, the samples block in words, the
isotope step rules derived from the committed cycle record and cited, the node's step and what set it, no overlap, the refusals, the doors, the manifest.

    PYTHONPATH=.:modules python3 -m cmod.cmod_bench_topology_selftest      # from polari-framework/
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
    from cmod.custom import bench_events as E
    from cmod.custom import bench_topology as T
    from cmod.custom import config_rows as R
    from cmod.custom import isotope_step_rules as S
    m = _manager()
    _seed(m)
    v = T.view(m, BS)
    kinds = {n['name'].split(':')[-1]: n['kind'] for n in v['nodes']}
    boot = next(n for n in v['nodes'] if n['kind'] == 'boot')
    check('THE FIRST CHAIN is fixed and derived: plugged-in (root) -(flash)-> flashed -(init)-> boot; boot requires boot_session WRITTEN (the init lane\'s '
          'assertion boot_session_mint)', kinds == {'plugged-in': 'root', 'flashed': 'flashed', 'boot': 'boot'} and sorted(e['kind'] for e in v['edges']) == ['flash', 'init']
          and [(q['field'], q['kind']) for q in boot['requirements']] == [('boot_session', 'written')], (kinds, boot['requirements']))
    ev = {e['name'].split(':', 1)[1]: e for e in v['events']}
    check('OFFERED EVENTS from the firmware\'s own claims: press / release PD2 (person; the edge-fall assertion), a command on uno-1-bridge (polari; '
          'receives-from-bridge), the telemetry period (time; "per period"), reset (person, always)',
          {'press-PD2', 'release-PD2', 'command-uno-1-bridge', 'period-telemetry_send', 'reset'} <= set(ev) and ev['press-PD2']['value'] == 'low'
          and ev['command-uno-1-bridge']['source'] == 'polari' and ev['period-telemetry_send']['source'] == 'time' and ev['reset']['what'] == 'RESET', sorted(ev))
    chain = E.predicted(m, BS, '%s:press-PD2' % BS)
    check('PREDICTED CHAIN of a press: result led_toggle changes led_on,toggles,source,status -> cascade led_follow_state reads led_on and drives PD6 -> '
          'cascade telemetry_send changes seq -> bridge telemetry_send on uno-1-bridge',
          [(s['stage'], s['atom'].split('.')[-1]) for s in chain] == [('hardware-event-result', 'led_toggle'), ('cascade', 'led_follow_state'), ('cascade', 'telemetry_send'),
                                                                        ('bridge', 'telemetry_send')] and chain[1]['pins'] == 'PD6' and chain[3]['bridge'] == 'uno-1-bridge',
          [(s['stage'], s['atom']) for s in chain])
    check('A release has NO asserted change: the predicted chain is empty (the rule: a run that changes no struct is a finding, bss-2)',
          E.predicted(m, BS, '%s:release-PD2' % BS) == [])
    n = T.define(m, BS, 'light-on', 'light on', boot['name'], 'trigger', '%s:press-PD2' % BS,
                 requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 1}],
                 executions=[{'atom': 'apps/light.led_toggle', 'isotope': 'read-button:gpio-poll'}, {'atom': 'apps/light.led_follow_state', 'isotope': 'drive-led:gpio-out'}])
    check('A DEFINED NODE: requirement led_on = 1, two executions in order, the collateral DERIVED from led_follow_state\'s reads-field: pin-level PD6 on the twin',
          [(q['field'], q['kind'], q['value']) for q in n['requirements']] == [('led_on', 'exact', '1')] and [x['order'] for x in n['executions']] == [1, 2]
          and [(c['kind'], c['signal'], c['source']) for c in n['collateral_rows']] == [('pin-level', 'PD6', 'derived')] and n['collaterals'] == 'derived', n['collateral_rows'])
    fp = n['fastest_path']
    check('THE FASTEST PATH from the root: 3 edges (flash, init, the press), flagged fastest', fp and fp['length'] == 3 and fp['fastest']
          and fp['edges'].split(',')[-1].endswith('boot->light-on via press-PD2'), fp)
    n2 = T.connect(m, BS, boot['name'], n['name'], 'trigger', '%s:command-uno-1-bridge' % BS)
    check('A SECOND PATH into the same node (the command instead of the press): two paths of length 3, exactly one fastest (tie broken by name)',
          len(n2['paths']) == 2 and [p['length'] for p in n2['paths']] == [3, 3] and sum(p['fastest'] for p in n2['paths']) == 1, n2['paths'])
    n3 = T.define(m, BS, 'light-off-again', 'light off again', n['name'], 'trigger', '%s:press-PD2' % BS,
                  requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 0}], executions=['apps/light.led_toggle'])
    check('A node two presses deep has paths of length 4 (through either path into light-on)', [p['length'] for p in n3['paths']] == [4, 4], n3['paths'])
    R.upsert(m, 'StructFieldSamples', '%s:toggles' % MAP, object_map=MAP, field='toggles', kind='samples', values='')
    n4 = T.define(m, BS, 'two-toggles', '', boot['name'], 'trigger', '%s:press-PD2' % BS, requirements=[{'object_map': MAP, 'field': 'toggles', 'kind': 'exact', 'value': 2}],
                  executions=['apps/light.led_toggle'])
    b1 = n4['blocked']
    R.upsert(m, 'StructFieldSamples', '%s:toggles' % MAP, values='1,2,3')
    b2 = T.blocks(m, n4['name'])
    R.upsert(m, 'StructNodeRequirement', '%s:toggles' % n4['name'], value='5')
    b3 = T.blocks(m, n4['name'])
    check('THE SAMPLES BLOCK, in words: an exact value of a samples-kind field is blocked while none are declared, free once declared, blocked again for a '
          'value not declared; a range requirement is never blocked',
          b1 == ['toggles has no declared samples: declare the values it is tested with'] and b2 == [] and b3 == ['toggles = 5 is not a declared sample (declared: 1, 2, 3)']
          and T.blocks(m, (R.upsert(m, 'StructNodeRequirement', '%s:toggles' % n4['name'], kind='range', value='1..9') or {}).get('node')) == [], (b1, b2, b3))
    r = {v: S.rule(v) for v in ('read-button:gpio-poll', 'read-button:ext-interrupt', 'report-state:uart-tx', 'drive-led:pwm', 'read-temperature:analog-sensor')}
    check('STEP RULES from the committed cycle record and the datasheet: gpio-poll = one poll pass (443 cycles = 27.7 us, derived; worst = the worst gap); '
          'ext-interrupt = one cycle (62.5 ns, cited; worst = INT0\'s longest run); uart-tx = one bit at 117 647 Bd (8.5 us, derived); pwm = a knob; '
          'analog-sensor = 13 ADC clocks at the prescaler knob (104 us, cited + knob)',
          r['read-button:gpio-poll']['kind'] == 'loop-period' and abs(r['read-button:gpio-poll']['step_s'] - 443 / 16e6) < 1e-12 and r['read-button:gpio-poll']['basis'] == 'derived'
          and r['read-button:gpio-poll']['worst_s'] > r['read-button:gpio-poll']['step_s'] and 'cycle record' in r['read-button:gpio-poll']['source']
          and abs(r['read-button:ext-interrupt']['step_s'] - 62.5e-9) < 1e-15 and r['read-button:ext-interrupt']['basis'] == 'cited' and r['read-button:ext-interrupt']['worst_s'] > 0
          and abs(r['report-state:uart-tx']['step_s'] - 1 / 117647.0) < 1e-9 and r['drive-led:pwm']['kind'] == 'pwm-period' and r['drive-led:pwm']['step_s'] == -1
          and abs(r['read-temperature:analog-sensor']['step_s'] - 13 * 128 / 16e6) < 1e-12 and 'KNOB' in r['read-temperature:analog-sensor']['source'],
          {k: (x['kind'], x['step_s'], x['basis']) for k, x in r.items()})
    R.upsert(m, 'IsotopeStepRule', 'drive-led:pwm', variant='drive-led:pwm', kind='pwm-period', step_s=1e-3, basis='person', source='typed: a 1 kHz PWM')
    rows = S.derive(m, ['drive-led:pwm', 'drive-led:gpio-out'])
    check('A person\'s step rule is kept by the derivation; the others are written as rows', rows[0]['basis'] == 'person' and rows[0]['step_s'] == 1e-3
          and R.get(m, 'IsotopeStepRule', 'drive-led:gpio-out')['kind'] == 'cycle')
    st = T.step_of(m, n['name'])
    check('THE NODE\'S STEP is the finest among its executions\' rules, and says what set it: drive-led:gpio-out (one cycle) over read-button:gpio-poll (a poll pass)',
          abs(st['step_s'] - 62.5e-9) < 1e-15 and st['step_set_by'].startswith('drive-led:gpio-out (cycle'), st)
    node_row, req_row, edge_row, path_row = R.get(m, 'StructNode', n['name']), n['requirements'][0], v['edges'][0], fp
    check('NO OVERLAP: the node holds no fields or values, the requirement no bench solution, the edge no requirements, the path only edge names',
          not ({'field', 'value', 'requirements'} & set(node_row)) and 'bench_solution' not in req_row and not ({'requirements', 'field'} & set(edge_row))
          and set(path_row) <= {'name', 'node', 'edges', 'length', 'fastest', 'notes'})
    refusals = []
    for args in (('x', '', 'nope-node', 'trigger', '%s:press-PD2' % BS, [{'field': 'a'}]), ('x', '', boot['name'], 'trigger', 'nope-event', [{'field': 'a'}]),
                 ('x', '', boot['name'], 'trigger', '%s:press-PD2' % BS, [])):
        try:
            T.define(m, BS, *args)
            refusals.append('')
        except R.ConfigRefused as e:
            refusals.append((e.status, e.why))
    check('REFUSALS in words: an unknown start node 404, an unknown event 404, a node without requirements 422',
          refusals == [(404, "no node 'nope-node' to start from"), (404, "no Hardware Event 'nope-event'"), (422, 'a node needs at least one requirement on a struct field')], refusals)
    from cmod.cmod_bench_topology_api import BenchTopologyAPI
    api = BenchTopologyAPI(polServer=None, manager=m)

    def call(method, *args, body=None):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        req = types.SimpleNamespace(get_param=lambda k: None, bounded_stream=types.SimpleNamespace(read=lambda: json.dumps(body or {}).encode()))
        getattr(api, method)(req, resp, *args)
        return resp
    w = call('on_get_words')
    g = call('on_get', BS)
    p = call('on_get_predicted', BS, '%s:press-PD2' % BS)
    d = call('on_post_nodes', BS, body={'slug': 'via-door', 'from_node': boot['name'], 'edge_kind': 'trigger', 'event': '%s:reset' % BS,
                                        'requirements': [{'object_map': MAP, 'field': 'boot_session', 'kind': 'written'}], 'executions': ['apps/light.boot_session_mint']})
    s = call('on_post_step_rules', BS, body={'variants': ['read-button:gpio-poll']})
    nf = call('on_get', 'nope')
    check('DOORS: the words; GET the view (6 nodes); GET predicted (4 steps); POST a node through the door -> its view with a path; POST step-rules -> rows; '
          'unknown Bench Solution -> 404',
          w.media['ok'] and 'written' in w.media['requirement_kinds'] and len(g.media['nodes']) == 6 and len(p.media['rows']) == 4 and d.media['ok']
          and d.media['fastest_path']['length'] == 3 and s.media['rows'][0]['kind'] == 'loop-period' and nf.status.startswith('404'), (nf.status, len(g.media['nodes'])))
    from moduleService.manifests import conform
    rr = conform('cmod')
    check('MANIFEST: pol modules conform cmod is clean with the new rows and files listed', rr['ok'], rr.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
