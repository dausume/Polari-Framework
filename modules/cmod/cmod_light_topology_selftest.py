"""cmod_light_topology_selftest - bss-8 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 7): THE WHOLE LIGHT TOPOLOGY, EVERY ROUTE, ON THE TWIN. The
topology spec of the UNO light bench (custom/topologies/uno-light-bench.json: on / off by the button and by the command, from either; the report; the
reset) is applied to three Bench Solutions whose firmware reads the button by three routes (D2 external interrupt, D4 pin-change interrupt, a voltage on
A0): the roles resolve to each Solution's own events, the executions' isotopes to each variant's route knobs, and EVERY node is reached by EVERY path on
the real twin, so the coverage's untested list is empty - the only green. The new stimuli (reset, the period, an ADC level), the enum labels, the command
frame that carries only the command's field, the chain nodes counted as crossed, the doors, the manifest.

Needs the avr engines (the prf-board-engines:trixie image WITH --adc-at, rebuilt 2026-11-02).

    PYTHONPATH=.:modules python3 -m cmod.cmod_light_topology_selftest      # from polari-framework/
"""
import json
import sys
import time
import types

passed = total = 0
MAP = 'LightState_t->LightState'
BENCHES = (('uno-light-on-desk', 'uno-light'), ('uno-light-pcint-on-desk', 'uno-light-pcint'), ('uno-light-analog-on-desk', 'uno-light-analog'))


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _manager():
    return types.SimpleNamespace(objectTables={}, idList=[], db=None, noteTreeMutation=lambda *a, **k: None)


def _seed(m):
    """The bench rows as board_seed ships them (bss-8) - NO CatomAssertion rows, so every variant's assertions come from catom_assertions.for_variant."""
    from board.board_seed import SEED_BENCH_CONDITIONS, SEED_BENCH_SOLUTIONS, SEED_BENCH_SYSTEMS
    from cmod.custom import config_rows as R
    from cmod.custom.catom_assertions import SEED_STRUCT_OBJECT_MAPS
    for r in SEED_BENCH_CONDITIONS:
        R.upsert(m, 'BenchConditions', r['name'], **{k: v for k, v in r.items() if k != 'name'})
    for r in SEED_BENCH_SYSTEMS:
        R.upsert(m, 'BenchSystem', r['name'], **{k: v for k, v in r.items() if k != 'name'})
    for r in SEED_BENCH_SOLUTIONS:
        R.upsert(m, 'BenchSolution', r['name'], **{k: v for k, v in r.items() if k != 'name'})
    som = SEED_STRUCT_OBJECT_MAPS[0]
    R.upsert(m, 'StructObjectMap', som['name'], **{k: v for k, v in som.items() if k != 'name'})


def main():
    from board.custom import light_twin
    from cmod.custom import bench_events as E
    from cmod.custom import bench_topology_spec as SP
    from cmod.custom import catom_assertions as CA
    from cmod.custom import config_rows as R
    from cmod.custom import node_run as NR
    from cmod.custom import retest as RT
    from cmod.custom import topology_coverage as COV
    ready, why = light_twin.engine_ready()
    check('the avr engines are reachable: %s' % why, ready, why)
    if not ready:
        print('\n%d/%d passed' % (passed, total))
        return 1
    m = _manager()
    _seed(m)
    BS = BENCHES[0][0]
    pins = {v: [(a['atom'].split('.')[-1], a['pins'], a['event']) for a in CA.for_variant(v) if a['atom'].endswith(('led_toggle', 'led_follow_state'))]
            for v in ('uno-light', 'uno-light-pcint', 'uno-light-analog', 'uno-light-unsensed')}
    check('ASSERTIONS PER VARIANT, re-pinned from each variant\'s own knobs: uno-light PD2 edge-fall; -pcint PD4 edge-fall; -analog ADC0 level; -unsensed PD2; '
          'the LED atom on PD6 everywhere; a variant of another app or an unknown one has none',
          pins['uno-light'] == [('led_toggle', 'PD2', 'edge-fall'), ('led_follow_state', 'PD6', 'poll')] and pins['uno-light-pcint'][0] == ('led_toggle', 'PD4', 'edge-fall')
          and pins['uno-light-analog'][0] == ('led_toggle', 'ADC0', 'level') and pins['uno-light-unsensed'][0][1] == 'PD2'
          and all(p[1][1] == 'PD6' for p in pins.values()) and CA.for_variant('uno-sim-rig') == [] and CA.for_variant('no-such-variant') == [], pins)
    check('THE COMMAND\'S FIELDS come from the receiving atom\'s own body (the presence bits apply_command tests): led_on only - the stamps are the firmware\'s',
          E.command_fields('apps/light.apply_command', CA.SEED_ASSERTIONS[1]['basis']) == ['led_on'])
    ev = {bs: {e['name'].split(':', 1)[1]: e for e in E.offered(m, bs)} for bs, _v in BENCHES}
    check('OFFERED EVENTS per Bench Solution: the press is press-PD2 / press-PD4 / press-ADC0 (0 mV, the release 4800 mV); the command carries led_on; the period is '
          '0.1 s from telemetry_hz; reset everywhere',
          'press-PD2' in ev[BS] and 'press-PD4' in ev['uno-light-pcint-on-desk'] and ev['uno-light-analog-on-desk']['press-ADC0']['value'] == '0'
          and ev['uno-light-analog-on-desk']['release-ADC0']['value'] == '4800' and all(d['command-uno-1-bridge']['value'] == 'led_on' for d in ev.values())
          and all(d['period-telemetry_send']['value'] == '0.1' for d in ev.values()) and all('reset' in d for d in ev.values()),
          {bs: sorted(d) for bs, d in ev.items()})
    sp = SP.specs()
    check('THE SPEC is shipped data, one per Bench System: uno-light-bench, 6 nodes, roles press / command / reset / period',
          [s['name'] for s in sp] == ['uno-light-bench'] and sp[0]['nodes'] == 6 and sp[0]['roles'] == ['command', 'period', 'press', 'reset'], sp)
    out = SP.apply(m, BS)
    nodes = {n['name'].split(':')[-1]: n for n in out['nodes']}
    check('APPLIED to uno-light-on-desk: the roles resolved to its events (press = press-PD2), 6 nodes, 8 paths; the isotopes from the route knobs '
          '(read-button:ext-interrupt, drive-led:gpio-out, receive-command:uart-rx-interrupt, report-state:uart-tx); the enum label kept as the person\'s word',
          out['roles']['press'].endswith(':press-PD2') and len(out['nodes']) == 6 and sum(len(n['paths']) for n in out['nodes']) == 8
          and [x['isotope'] for x in nodes['on-by-button']['executions']] == ['read-button:ext-interrupt', 'drive-led:gpio-out']
          and [x['isotope'] for x in nodes['on-by-command']['executions']] == ['receive-command:uart-rx-interrupt', 'drive-led:gpio-out']
          and nodes['reported']['executions'][0]['isotope'] == 'report-state:uart-tx'
          and next(q['value'] for q in nodes['on-by-button']['requirements'] if q['field'] == 'source') == 'button', out['words'])
    check('TWO PATHS into "off by the button" (on by the button, on by the command) and into "off by the command": every way to switch the light',
          len(nodes['off-by-button']['paths']) == 2 and len(nodes['off-by-command']['paths']) == 2 and nodes['off-by-button']['paths'][0]['length'] == 4)
    q = NR._labelled(m, {'object_map': MAP, 'field': 'source', 'kind': 'exact', 'value': 'button'})
    check('AN ENUM LABEL is judged by its wire byte through the contract\'s own encoder: source = button -> 2 (0 is unknown; command = 1), the label kept',
          q['value'] == '2' and q['label'] == 'button' and NR._labelled(m, {'object_map': MAP, 'field': 'source', 'kind': 'exact', 'value': 'command'})['value'] == '1')
    frame, vals = NR._command_frame(m, ev[BS]['command-uno-1-bridge'], R.rows(m, 'StructNodeRequirement', node=nodes['off-by-command']['name']), 1)
    check('THE COMMAND FRAME into "off by the command" carries led_on = 0 ONLY (not toggles, not source: the firmware stamps those)', vals == {'led_on': False}, vals)
    t0 = time.time()
    ra = RT.run_all(m, BS)
    secs = time.time() - t0
    by = {}
    for r in ra['runs']:
        by.setdefault(r['node'].split(':')[-1], []).append(r['outcome'])
    check('PROOF: EVERY NODE BY EVERY PATH reached on the twin from the root - 8 of 8 (%.0f s)' % secs, ra['reached'] == 8 and ra['of'] == 8
          and all(set(v) == {'reached'} for v in by.values()), ra['runs'])
    check('THE UNTESTED LIST IS EMPTY - the only green: every node confirmed by every path, every collateral measured, every event used or inert, every assertion '
          'of the firmware exercised (the command frame arriving included), the chain nodes crossed', ra['untested'] == [], ra['untested'])
    strip = COV.strip(m, BS)
    check('THE STRIP: 6 state nodes + flashed + boot confirmed by the twin, none never-tested; 10 of 10 paths (the 8 state paths + the two chain nodes\' own, crossed); the '
          'release is listed INERT (the firmware asserts nothing on it), not untested; 7 of 7 assertions exercised; fields led_on, toggles, source, status, seq, boot_session '
          'covered (every field a node requires and a run changed)',
          strip['nodes_by_state']['confirmed-twin'] == 8 and strip['nodes_by_state']['never-tested'] == 0 and strip['paths_tested'] == strip['paths'] == 10
          and [e['event'].split(':', 1)[1] for e in strip['inert_events']] == ['release-PD2']
          and strip['assertions_exercised'] == strip['assertions'] == 7 and {'led_on', 'toggles', 'source', 'status', 'seq', 'boot_session'} <= set(strip['fields_covered']),
          {k: strip[k] for k in ('nodes_by_state', 'paths_tested', 'paths', 'inert_events', 'assertions_exercised', 'assertions', 'fields_covered')})
    runs = {r['node'].split(':')[-1]: r for r in ra['runs'] if r['length'] == min(x['length'] for x in ra['runs'] if x['node'] == r['node'])}
    check('THE RESET EDGE: "rebooted" met within a millisecond of the reset (boot_session written again, led_on and toggles back to 0); the twin counts cycles '
          'across the reset', runs['rebooted']['outcome'] == 'reached' and 0 <= runs['rebooted']['duration_s'] < 1e-3, runs['rebooted'])
    check('THE PERIOD EDGE: "reported" met inside one period (0.1 s) with no stimulus at all - the frame left and seq was written, led_on = 1 the sensed level',
          runs['reported']['outcome'] == 'reached' and 0 <= runs['reported']['duration_s'] < 0.1, runs['reported'])
    sig = {s['signal']: s for s in RT.run_signals(m, runs['off-by-command']['run'])}
    check('THE STRUCTS ON ARRIVAL at "off by the command" (on by the button first): led_on 0 -> 1 -> 0, toggles 0 -> 2, source ends 1 (command)',
          sig['led_on']['first'] == '0' and sig['led_on']['last'] == '0' and sig['led_on']['changes'] == 2 and sig['toggles']['last'] == '2' and sig['source']['last'] == '1',
          {k: (s['first'], s['last'], s['changes']) for k, s in sig.items()})
    # the pin-change route (D4) and the analog route (A0): the same spec, other events and isotopes, the light still switches
    out2 = SP.apply(m, 'uno-light-pcint-on-desk')
    r2 = NR.run(m, 'uno-light-pcint-on-desk', 'uno-light-pcint-on-desk:on-by-button')
    check('THE PIN-CHANGE ROUTE: press = press-PD4, the execution\'s isotope read-button:pin-change-interrupt, "light on, by the button" REACHED on the twin',
          out2['roles']['press'].endswith(':press-PD4') and out2['routes']['read-button'] == 'read-button:pin-change-interrupt' and r2['run']['outcome'] == 'reached'
          and r2['run']['step_set_by'].startswith('read-button:pin-change-interrupt'), (out2['roles'], r2['run']['outcome'], r2['run']['words'][:120]))
    out3 = SP.apply(m, 'uno-light-analog-on-desk')
    r3 = NR.run(m, 'uno-light-analog-on-desk', 'uno-light-analog-on-desk:on-by-button')
    e3 = r3['edges'][-1]
    check('THE ANALOG ROUTE: press = press-ADC0 (A0 stepped 4800 -> 0 mV at the cycle by the twin\'s new --adc-at, back after the hold), the isotope '
          'read-button:analog-threshold, "light on, by the button" REACHED; its collateral PD6 read from the DRIVEN port word (no sense wire on this variant, said)',
          out3['roles']['press'].endswith(':press-ADC0') and out3['routes']['read-button'] == 'read-button:analog-threshold' and r3['run']['outcome'] == 'reached'
          and e3['met_cycle'] > e3['stimulus_cycle'] and e3['collaterals'].startswith('pin-level PD6: high, driven') and 'no jumper' in e3['collaterals'],
          (r3['run']['outcome'], r3['run']['words'][:120], e3['collaterals'][:80]))
    r4 = NR.run(m, 'uno-light-analog-on-desk', 'uno-light-analog-on-desk:off-by-button')
    check('THE ANALOG ROUTE twice: "off by the button" (press, press) REACHED - two ADC pulses spaced by the guard', r4['run']['outcome'] == 'reached', r4['run']['words'][:160])
    # ---- bss-9: the owed list - per-edge counts, the driven pin, net-current, the failure capture, the other LED / sense routes, the samples view
    e1 = next(e for e in NR.runs(m, nodes['on-by-button']['name']) if e['outcome'] == 'reached')
    ed1 = RT.run_edges(m, e1['name'])[-1]
    check('PER-EDGE EXECUTION COUNTS (bss-9): led_toggle ran between the press and the requirement being met - counted by the twin\'s windowed --fn-cycles '
          '(@lo:hi), no longer over the whole run; a polled atom counts passes, said', 'led_toggle: observed (ran n=' in ed1['executions'] and 'between the stimulus and' in ed1['executions']
          and 'WHOLE run' not in ed1['executions'] and 'counts passes' in ed1['executions'], ed1['executions'][:300])
    check('NET-CURRENT (bss-9): the declared collateral on "light on" ran the LED branch in ngspice (batch) at the pin\'s level with TMAX = the node\'s step: ~14.7 mA '
          'through R 220 + the generic LED model, inside the bound 5..20 mA; every knob named (VCC, the LED model)',
          'net-current PD6: 14.' in ed1['collaterals'] and 'bound 0.005..0.020 A: met' in ed1['collaterals'] and 'knobs: VCC 5 V' in ed1['collaterals'], ed1['collaterals'][:400])
    ed2 = RT.run_edges(m, r2['run']['name'])[-1]
    s2 = {s['signal']: s for s in RT.run_signals(m, r2['run']['name']) if s['kind'] == 'pin'}
    check('THE DRIVEN PIN (bss-9): on the pin-change build (no sense jumper) PD6 is read from the PORTD / DDRD words the firmware drives - high, driven, the '
          'wire itself said not read; its pin signal is the bit (0 -> 1, one change); the untested list no longer says the collateral is unmeasured',
          ed2['collaterals'].startswith('pin-level PD6: high, driven (PORTD bit 6') and s2.get('PD6', {}).get('last') == '1' and s2['PD6']['changes'] == 1
          and not any('on-by-button: collaterals measured' in w for w in COV.untested(m, 'uno-light-pcint-on-desk')), (ed2['collaterals'][:200], s2.get('PD6')))
    from cmod.custom import bench_topology as T
    seven = T.define(m, BS, 'seven', 'a value the code never sets', '%s:boot' % BS, 'trigger', ev[BS]['press-PD2']['name'],
                     requirements=[{'object_map': MAP, 'field': 'led_on', 'kind': 'exact', 'value': 7}], executions=['apps/light.led_toggle'])
    r7 = NR.run(m, BS, seven['name'])
    caps = [c for c in R.rows(m, 'WaveformCapture') if c['acquisition'] == r7['capture']]
    sig7 = {s['signal']: s for s in r7['signals'] if s['kind'] == 'pin'}
    check('THE FAILURE CAPTURE (bss-9, D-bss-6): a diverged run keeps ONE acquisition of WaveformCapture rows (the osc arc\'s rows, source twin) - the three lines PD2 '
          '(the press), PD3 and PD6 (the jumper) over the failing edge\'s last 10 %%, 4096 points at a coarsened step, said; the pin signals name their capture row; '
          'a reached run keeps none', r7['run']['outcome'] == 'diverged' and len(caps) == 3 and all(c['source'] == 'twin' and c['points'] == 4096 for c in caps)
          and 'failure capture' in r7['run']['words'] and sig7.get('PD6', {}).get('capture', '').startswith('fail-')
          and not any(c['acquisition'] == e1['name'] for c in R.rows(m, 'WaveformCapture')), (r7['run']['words'][-200:], [(c['name'], c['points']) for c in caps]))
    more = {}
    for bs2 in ('uno-light-pwm-on-desk', 'uno-light-transistor-on-desk', 'uno-light-all-pcint-on-desk'):
        a2 = SP.apply(m, bs2)
        rr = NR.run(m, bs2, '%s:on-by-button' % bs2)
        more[bs2] = (a2['routes'].get('drive-led'), a2['routes'].get('sense-led-line'), rr['run']['outcome'], RT.run_edges(m, rr['run']['name'])[-1]['collaterals'][:120])
    check('THE OTHER ROUTES (bss-9): the PWM LED (drive-led:pwm, the button on A0), the transistor LED (drive-led:transistor-switch) and the all-pin-change build '
          '(sense-led-line:pin-change-interrupt on D8) each reach "light on, by the button" on the twin; the PWM pin read on the wire (its port word says nothing, said)',
          more['uno-light-pwm-on-desk'][0] == 'drive-led:pwm' and more['uno-light-transistor-on-desk'][0] == 'drive-led:transistor-switch'
          and more['uno-light-all-pcint-on-desk'][1] == 'sense-led-line:pin-change-interrupt' and all(v[2] == 'reached' for v in more.values())
          and 'on the wire' in more['uno-light-pwm-on-desk'][3], more)
    from cmod.custom import bench_structs as BSX
    R.upsert(m, 'StructFieldSamples', '%s:toggles' % MAP, object_map=MAP, field='toggles', kind='samples', values='1,2', basis='the light test\'s two presses')
    sm = BSX.samples(m)
    check('THE SAMPLES VIEW (bss-9, owed item 7): one row per declared-samples field with the nodes that use a declared value and the nodes BLOCKED (toggles = 0 on '
          '"rebooted" is not declared) - the Structs page\'s foot table reads it (view=samples)', len(sm) == 1 and sm[0]['declared'] == 2 and 'on-by-button' in sm[0]['used_by_nodes']
          and 'rebooted' in sm[0]['blocking_nodes'] and sm[0]['words'].endswith('blocked'), sm)
    R.drop(m, 'StructFieldSamples', field='toggles')
    try:
        SP.apply(m, BS, spec='no-such-spec')
        refused = ''
    except R.ConfigRefused as x:
        refused = (x.status, x.why)
    check('REFUSALS in words: an unknown spec 404 naming the shipped ones', refused == (404, "no topology spec 'no-such-spec' (the shipped ones: uno-light-bench)"), refused)
    from cmod.cmod_bench_topology_api import BenchTopologyAPI
    from cmod.cmod_retest_api import RetestAPI
    api, rapi = BenchTopologyAPI(polServer=None, manager=m), RetestAPI(polServer=None, manager=m)

    def call(a, method, *args, body=None):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        req = types.SimpleNamespace(get_param=lambda k: None, bounded_stream=types.SimpleNamespace(read=lambda: json.dumps(body or {}).encode()))
        getattr(a, method)(req, resp, *args)
        return resp
    s = call(api, 'on_get_specs')
    a = call(api, 'on_post_apply_spec', 'uno-light-pcint-on-desk', body={})
    bad = call(rapi, 'on_post_run_all', 'nope')
    check('DOORS: GET topology-specs lists the spec; POST apply-spec re-applies idempotently (6 nodes, the same paths); POST run-all on an unknown Bench Solution -> 404',
          s.media['rows'][0]['name'] == 'uno-light-bench' and a.media['ok'] and len(a.media['nodes']) == 6 and sum(len(n['paths']) for n in a.media['nodes']) == 8
          and bad.status.startswith('404'), (s.media, a.media.get('words'), bad.status))
    from moduleService.manifests import conform
    rr = conform('cmod')
    check('MANIFEST: pol modules conform cmod is clean with the new file and selftest listed', rr['ok'], rr.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
