"""cmod_light_topology_selftest - bss-8 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 7): THE WHOLE LIGHT TOPOLOGY, EVERY ROUTE, ON THE TWIN. The
topology spec of the UNO light bench (custom/topologies/uno-light-bench.json: on / off by the button and by the command, from either; the report; the
reset) is applied to three Bench Solutions whose firmware reads the button by three routes (D2 external interrupt, D4 pin-change interrupt, a voltage on
A0): the roles resolve to each Solution's own events, the executions' isotopes to each variant's route knobs, and EVERY node is reached by EVERY path on
the real twin, so the coverage's untested list is empty - the only green. The new stimuli (reset, the period, an ADC level), the enum labels, the command
frame that carries only the command's field, the chain nodes counted as crossed, the doors, the manifest.

bss-11 FAULT EDGES: the fault stimuli offered beside every press (a bouncing press, a long press released with bounce, a held button, a release, idle time) and
the HOLD nodes on them (requirements met AND kept to the end of the window). THE FINDING: on all three button routes a long press released with bounce
toggles the light TWICE - the 30 ms lockout counts from the last accepted press, so the release's falling edges land outside it - said as a divergence with
the cycle, and proposed as a node (led_on 0, toggles 2) for a person to name; the bouncing press, the held button, the release and idle time all hold.

Needs the avr engines (the prf-board-engines:trixie image WITH --adc-at and 256 --pin-at entries, rebuilt 2026-11-03).

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
          '0.1 s from telemetry_hz; reset everywhere; bss-11: the fault stimuli bounce- / long-press- / held- beside every press (the same pin, the same pressed level) '
          'and idle (time, no stimulus) everywhere',
          'press-PD2' in ev[BS] and 'press-PD4' in ev['uno-light-pcint-on-desk'] and ev['uno-light-analog-on-desk']['press-ADC0']['value'] == '0'
          and ev['uno-light-analog-on-desk']['release-ADC0']['value'] == '4800' and all(d['command-uno-1-bridge']['value'] == 'led_on' for d in ev.values())
          and all(d['period-telemetry_send']['value'] == '0.1' for d in ev.values()) and all('reset' in d and 'idle' in d for d in ev.values())
          and {'bounce-PD2', 'long-press-PD2', 'held-PD2'} <= set(ev[BS]) and ev[BS]['long-press-PD2']['value'] == 'low'
          and ev['uno-light-analog-on-desk']['bounce-ADC0']['value'] == '0' and 'held-PD4' in ev['uno-light-pcint-on-desk'],
          {bs: sorted(d) for bs, d in ev.items()})
    st = {k: NR._stimulus(ev[BS]['%s-PD2' % k], 1600000, manager=m) for k in ('press', 'bounce', 'long-press', 'held')}
    pts = [(int(a.split(',')[0].split('=')[1]), int(a.split('level=')[1])) for a in st['bounce'][1::2]]
    sta = NR._stimulus(ev['uno-light-analog-on-desk']['bounce-ADC0'], 1600000, manager=m)
    check('THE FAULT STIMULI (bss-11): a press = 2 pin-at entries; a bounce = 14 (an edge train of 6 extra edges down, quadratically spaced, settling low 2.5 ms in; '
          'the hold; the same train up from 5 ms, settling high at 7.5 ms); a long press = 14 with the release train from 500 ms; held = 1 entry, never released; '
          'on the analog route the same as an adc-at level train 0 / 4800 mV',
          len(st['press']) == 4 and len(st['bounce']) == 28 and pts[0] == (1600000, 0) and pts[6] == (1640000, 0) and pts[7] == (1680000, 1) and pts[13] == (1720000, 1)
          and pts[1][1] == 1 and pts[2][0] - pts[1][0] < pts[6][0] - pts[5][0] and len(st['long-press']) == 28 and st['long-press'][-1].startswith('cycle=%d,' % (1600000 + 8000000 + 40000))
          and st['held'] == ['--pin-at', 'cycle=1600000,pin=PD2,level=0'] and len(sta) == 28 and sta[0] == '--adc-at' and sta[1].endswith('mv=0') and sta[3].endswith('mv=4800'),
          (st, sta[:4]))
    sp = SP.specs()
    check('THE SPEC is shipped data, one per Bench System: uno-light-bench, 11 nodes (6 reach + 5 hold, bss-11), roles press / command / reset / period + the fault roles '
          'bounce / long-press / held / release / idle',
          [s['name'] for s in sp] == ['uno-light-bench'] and sp[0]['nodes'] == 11
          and sp[0]['roles'] == ['bounce', 'command', 'held', 'idle', 'long-press', 'period', 'press', 'release', 'reset'], sp)
    out = SP.apply(m, BS)
    nodes = {n['name'].split(':')[-1]: n for n in out['nodes']}
    check('APPLIED to uno-light-on-desk: the roles resolved to its events (press = press-PD2, long-press = long-press-PD2, idle = idle), 11 nodes, 13 paths; the '
          'isotopes from the route knobs (read-button:ext-interrupt, drive-led:gpio-out, receive-command:uart-rx-interrupt, report-state:uart-tx); the enum label kept '
          'as the person\'s word; the hold nodes carry expect = hold',
          out['roles']['press'].endswith(':press-PD2') and out['roles']['long-press'].endswith(':long-press-PD2') and out['roles']['idle'].endswith(':idle')
          and len(out['nodes']) == 11 and sum(len(n['paths']) for n in out['nodes']) == 13
          and nodes['on-by-long-press']['expect'] == 'hold' and nodes['released']['expect'] == 'hold' and nodes['on-by-button']['expect'] == 'reach'
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
    check('PROOF: EVERY NODE BY EVERY PATH run on the twin from the root - 12 of 13 reached (%.0f s): every reach node, and the hold nodes "one bouncing press", '
          '"held", "released", "idle" KEPT their requirements to the end of their windows; ONE diverged' % secs, ra['reached'] == 12 and ra['of'] == 13
          and all(set(v) == {'reached'} for k, v in by.items() if k != 'on-by-long-press') and by['on-by-long-press'] == ['diverged'], ra['runs'])
    lp = next(r for r in ra['runs'] if r['node'].endswith(':on-by-long-press'))
    lpe = RT.run_edges(m, lp['run'])[-1]
    prop = [n for n in R.rows(m, 'StructNode', bench_solution=BS, basis='proposed')]
    preq = {q['field']: q['value'] for q in R.rows(m, 'StructNodeRequirement', node=prop[0]['name'])} if prop else {}
    check('THE FINDING (bss-11): a LONG PRESS RELEASED WITH BOUNCE toggles the light TWICE on the D2 external-interrupt route - met at the press, then led_on back to 0 '
          'and toggles 2 about 500 ms later (the release\'s falling edges land outside the 30 ms lockout, which counts from the last accepted press); said as a '
          'divergence with the cycles, the fault the edge exists to find; the reached values proposed as a node (led_on 0, toggles 2, source button) for a person to name',
          lp['outcome'] == 'diverged' and 'then led_on became 0 at cycle' in lpe['words'] and 'toggles became 2 at cycle' in lpe['words'] and '(500.' in lpe['words']
          and 'a hold node keeps its requirements' in lpe['words'] and len(prop) == 1 and preq == {'led_on': '0', 'source': '2', 'toggles': '2'}, (lpe['words'][:300], preq))
    check('THE UNTESTED LIST names exactly the finding\'s consequences: the long-press node\'s collateral unmeasured (it diverged) and the proposed node not yet accepted; '
          'nothing else - every other node confirmed by every path, every event used (the release and idle now USED by hold edges, so no longer inert), every assertion '
          'exercised, the chain nodes crossed',
          ra['untested'] == ['%s:on-by-long-press: collaterals measured 0 / 2' % BS, '%s:proposed-1: proposed from a divergence, not yet accepted or discarded' % BS], ra['untested'])
    strip = COV.strip(m, BS)
    check('THE STRIP: 10 state nodes + flashed + boot confirmed by the twin, 1 diverged, 1 proposed, none never-tested; 14 of 16 paths (13 state paths + the two chain '
          'nodes\' own + the proposed node\'s; the diverged one and the proposal untested); nothing inert any more (the release and idle are used); 7 of 7 assertions '
          'exercised; fields led_on, toggles, source, status, seq, boot_session covered (every field a node requires and a run changed)',
          strip['nodes_by_state']['confirmed-twin'] == 12 and strip['nodes_by_state']['never-tested'] == 0 and strip['nodes_by_state']['diverged'] == 1
          and strip['nodes_by_state']['proposed'] == 1 and strip['paths_tested'] == 14 and strip['paths'] == 16 and strip['inert_events'] == []
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
    faults = {}
    for bs2 in ('uno-light-pcint-on-desk', 'uno-light-analog-on-desk'):
        for slug in ('on-by-bouncy-press', 'on-by-long-press'):
            rr = NR.run(m, bs2, '%s:%s' % (bs2, slug))
            faults[(bs2, slug)] = (rr['run']['outcome'], RT.run_edges(m, rr['run']['name'])[-1]['words'])
    check('THE FINDING ON EVERY ROUTE (bss-11): the pin-change route (D4) and the analog route (A0, a level train) each toggle ONCE on a bouncing press (held to the end '
          'of the window) and TWICE on a long press released with bounce (diverged, toggles 2 about 500 ms in) - the same lockout-from-the-last-press in all three '
          'read-button isotopes; the fix is a debounce option (the catom-config arc), not a topology change',
          all(v[0] == 'reached' and 'held to the end' in v[1] for k, v in faults.items() if k[1] == 'on-by-bouncy-press')
          and all(v[0] == 'diverged' and 'toggles became 2 at cycle' in v[1] and '(500.' in v[1] for k, v in faults.items() if k[1] == 'on-by-long-press'),
          {k: (v[0], v[1][:120]) for k, v in faults.items()})
    # ---- bss-9: the owed list - per-edge counts, the driven pin, net-current, the failure capture, the other LED / sense routes, the samples view
    e1 = next(e for e in NR.runs(m, nodes['on-by-button']['name']) if e['outcome'] == 'reached')
    ed1 = RT.run_edges(m, e1['name'])[-1]
    check('PER-EDGE EXECUTION COUNTS (bss-9): led_toggle ran between the press and the requirement being met - counted by the twin\'s windowed --fn-cycles '
          '(@lo:hi), no longer over the whole run; a polled atom counts passes, said', 'led_toggle: observed (ran n=' in ed1['executions'] and 'between the stimulus and' in ed1['executions']
          and 'WHOLE run' not in ed1['executions'] and 'counts passes' in ed1['executions'], ed1['executions'][:300])
    check('NET-CURRENT (bss-9): the declared collateral on "light on" ran the LED branch in ngspice (batch) at the pin\'s level with TMAX = the node\'s step: ~14.7 mA '
          'through R 220 + the generic LED model, inside the bound 5..20 mA; every knob named (VCC, the LED model)',
          'net-current PD6: 14.' in ed1['collaterals'] and 'bound 0.005..0.020 A: met' in ed1['collaterals'] and 'knobs: VCC 5 V' in ed1['collaterals'], ed1['collaterals'][:400])
    held_run = next(r for r in ra['runs'] if r['node'].endswith(':on-while-held'))
    edh = RT.run_edges(m, held_run['run'])[-1]
    edr = RT.run_edges(m, next(r for r in ra['runs'] if r['node'].endswith(':rebooted'))['run'])[-1]
    check('THE ELECTRICAL CHECK AT EVERY NODE (bss-12): the bench circuit (uno-button-clock, matched to the config by its pins) in the state the node leaves it, its .op '
          'by ngspice judged against the chip\'s cited limits - "light on": state led-on, D6 14.715 mA under the 20 mA recommended, ok; "held": state led-on-button-held, '
          'the pull-up\'s 0.250 mA through D2 at the 20 k end, ok; "rebooted": idle-led-off, 0 mA; the worst-case bound said; a derived `electrical circuit` collateral on every node',
          'electrical circuit: ok - circuit uno-button-clock in state led-on (' in ed1['collaterals'] and 'D6 carries 14.715 mA in state led-on' in ed1['collaterals']
          and 'the worst-case bound' in ed1['collaterals'] and 'state led-on-button-held' in edh['collaterals'] and 'D2 carries 0.250 mA' in edh['collaterals']
          and 'electrical circuit: ok - circuit uno-button-clock in state idle-led-off' in edr['collaterals'] and 'D6 carries 0.000 mA' in edr['collaterals']
          and any(c['kind'] == 'electrical' for c in nodes['reported']['collateral_rows']),
          ([w for w in ed1['collaterals'].split(' ; ') if w.startswith('electrical')], [w for w in edh['collaterals'].split(' ; ') if w.startswith('electrical')][:1]))
    ed2 = RT.run_edges(m, r2['run']['name'])[-1]
    s2 = {s['signal']: s for s in RT.run_signals(m, r2['run']['name']) if s['kind'] == 'pin'}
    check('THE ELECTRICAL CHECK SAYS WHAT IT RAN (bss-12): on the pin-change build the only seeded bench circuit has its switch on D2, which that build leaves high-Z, so '
          'the verdict is WARN with the floating input named - the circuit for the D4 button is not seeded, said by the words, not hidden',
          'electrical circuit: warn - circuit uno-button-clock' in ed2['collaterals'] and 'D2 read a floating line' in ed2['collaterals'] and 'D2 high-z' in ed2['collaterals'],
          [w for w in ed2['collaterals'].split(' ; ') if w.startswith('electrical')])
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
    rp = NR.run(m, BS, nodes['on-by-button']['name'], pin=True)
    pins_ = RT.run_captures(m, rp['run']['name'])
    check('A PINNED CAPTURE (bss-10, D-bss-6): pin = true on a REACHED run keeps the target edge\'s WHOLE window (3 lines, acquisition pin-...), the run\'s words say pinned; '
          'the captures door lists the rows with kept = pinned and the line each is', rp['run']['outcome'] == 'reached' and rp['capture'].startswith('pin-')
          and 'pinned capture' in rp['run']['words'] and len(pins_) == 3 and all(c['kept'] == 'pinned' for c in pins_) and sorted(c['line'] for c in pins_) == ['PD2', 'PD3', 'PD6']
          and all(c['acquisition'] == rp['capture'] for c in pins_), (rp['capture'], rp['run']['words'][-160:], pins_[:1]))
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
    cp = call(rapi, 'on_get_captures', BS, r7['run']['name'])
    cbad = call(rapi, 'on_get_captures', BS, 'nope#run9')
    check('DOORS: GET topology-specs lists the spec; POST apply-spec re-applies idempotently (11 nodes, the same 13 paths); POST run-all on an unknown Bench Solution -> 404; '
          'GET runs/{run}/captures lists the diverged run\'s 3 failure lines (kept = on failure) and 404s an unknown run',
          s.media['rows'][0]['name'] == 'uno-light-bench' and a.media['ok'] and len(a.media['nodes']) == 11 and sum(len(n['paths']) for n in a.media['nodes']) == 13
          and bad.status.startswith('404') and len(cp.media['rows']) == 3 and all(r['kept'] == 'on failure' for r in cp.media['rows']) and cbad.status.startswith('404'),
          (s.media, a.media.get('words'), bad.status, cp.media, cbad.status))
    from cmod.hardware_events_page import HARDWARE_EVENTS_PAGES
    d = json.loads(HARDWARE_EVENTS_PAGES[0]['definition'])
    tabs = {t['key']: t for t in d['tabs']}
    ids = {i['id']: i for r in tabs['runs']['rows'] for i in r['items']}
    check('THE PAGE (bss-10): the Hardware Events page\'s Runs tab selects a run, lists the traces it kept (the captures door) and draws the chosen acquisition with the '
          'instruments arc\'s own graph (instruments-capture, the osc chart door); run and acquisition are page scopes',
          {'he-runs', 'he-run-captures', 'he-run-chart'} <= set(ids) and ids['he-run-chart']['componentProps']['inputs']['graphName'] == 'instruments-capture'
          and '/runs/{scope:run}/captures' in json.dumps(ids['he-run-captures']['componentProps']) and {'run', 'acquisition'} <= set(d['scope_from_query']),
          (sorted(ids), d.get('scope_from_query')))
    from moduleService.manifests import conform
    rr = conform('cmod')
    check('MANIFEST: pol modules conform cmod is clean with the new file and selftest listed', rr['ok'], rr.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
