"""circuit_states_selftest — cst-0/1 (PROTOTYPING_VIEWS_PLAN.md §2, §8): THE CIRCUIT STATES OF uno-light (S1), derived never typed.

The bench circuit is matched to the config by the pins it uses (uno-button-clock: D2, D3, D6); the HAL init modes are read from the source (D2 input +
pull-up, D6 output low, D3 input); the pin writer comes from the parsed atoms (led_on -> apply_command / led_toggle -> led_follow_state -> D6); the six
states and eighteen transitions (external 6, firmware 6, lifecycle 6) come out with their names; the press-driven flip is timed by the press record,
SET_LED is read from the source; with ngspice, the .op per running state gives the LED branch ~14.7 mA (= D6's current, within the 20 mA recommended),
the pull-up 0.25 mA at 20 kΩ / 0.10 mA at 50 kΩ only while the button is held, every running state `ok`; the reset states are not simulated and carry the
structural floating-input findings. Rows persist on a manager; the ladder's rung-7 reader and the Battery term's active_current read them back; the doors.

    PYTHONPATH=.:modules python3 -m electrodevice.circuit_states_selftest      # from polari-framework/
"""
import json
import sys
import types

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


class _M:
    def __init__(self, *classes):
        self.objectTables = {c: {} for c in classes}
        self.idList = []
        self.db = None

    def persistTree(self):
        return None

    def noteTreeMutation(self, *a, **k):
        return None


def _tables():
    from board.custom import electrical_check as EC
    from board.custom import electrical_atmega328p as E
    t = EC.tables_for(None)
    t['ElectricalCharacteristic'] = E.characteristics()
    t['PinGroupBudget'] = E.budgets()
    return t


def run_circuit_states(check):
    from electrodevice.custom import cst_modes as M, cst_sources as SRC, cst_netlist as N, cst_verdict as V
    print('  -- circuit states (cst-0/1)')
    t = _tables()
    init = SRC.hal_init_modes('uno-light')
    check('cst-0 SOURCE: the HAL init modes of uno-light are read from the rendered sources — D2 input + pull-up (hal_button_init), D6 output low (hal_led_init via LED_DDR/LED_BIT -> LED_PIN 6), D3 input, no pull (hal_sense_init in the route file)',
          init.get('D2', {}).get('mode') == 'input' and init['D2']['pull'] == 'up' and 'hal_button_init' in init['D2']['source']
          and init.get('D6', {}).get('mode') == 'output' and init['D6']['initial'] == 'low' and 'LED_DDR' in init['D6']['source']
          and init.get('D3', {}).get('mode') == 'input' and init['D3']['pull'] == 'none' and 'hal_sense_poll.c' in init['D3']['source'], init)
    w = SRC.pin_writer('uno-light')
    check('cst-0 SOURCE: the pin writer from the parsed atoms — LightState.led_on, written by apply_command + led_toggle, read by led_follow_state which drives D6',
          w and w['pin'] == 'D6' and w['field'] == 'led_on' and w['writers'] == ['apply_command', 'led_toggle'] and w['reader'] == 'led_follow_state', w)
    pr = SRC.press_record('uno-light')
    check('cst-0 SOURCE: the committed press record of uno-light (press -> D6 rise) carries best/worst ms and its sha', pr and pr['worst_ms'] > pr['best_ms'] > 0 and len(pr['sha256']) == 64, pr)
    circuit, why = SRC.circuit_for('uno-light', t)
    check('cst-0 the bench circuit is matched BY THE PINS the config uses: uno-button-clock carries D2, D3 and D6', circuit == 'uno-button-clock' and 'D2, D3, D6' in why, why)
    try:
        SRC.circuit_for('uno-echo', t)
        check('a config no circuit covers refuses', False)
    except SRC.SourceRefused as e:
        check('cst-0 a config whose pins no bench circuit names (uno-echo: D0/D1 only) is REFUSED in words', 'no bench circuit names a pin' in str(e), str(e))
    cat = M.catalogue('uno-light', t)
    check('cst-0 CATALOGUE: SW1 open|closed (external), LED1 off|forward (follows D6), R1 passive; D6 can be driven-low|driven-high (+ high-z), D2 input-pullup, D3 input-hiz',
          cat['components']['ubc-sw1']['modes'] == ['open', 'closed'] and cat['components']['ubc-led1']['modes'] == ['off', 'forward'] and 'D6' in cat['components']['ubc-led1']['who']
          and cat['pins']['D6']['can'] == ['driven-low', 'driven-high', 'high-z'] and cat['pins']['D2']['at_init'] == 'input-pullup' and cat['pins']['D3']['at_init'] == 'input-hiz',
          {p: (d['can'], d['at_init']) for p, d in cat['pins'].items()})
    sts = M.states('uno-light', t, cat)
    names = [s['name'] for s in sts]
    check('cst-0 STATES (6, named from their modes): idle-led-off, led-on, button-held-led-off, led-on-button-held, reset-high-z, reset-button-held — the product pruned to what the firmware and a finger can reach',
          sorted(names) == sorted(['idle-led-off', 'led-on', 'button-held-led-off', 'led-on-button-held', 'reset-high-z', 'reset-button-held']), names)
    by = {s['name']: s for s in sts}
    check('cst-0 a state is one assignment of every mode: led-on-button-held = SW1 closed, LED1 forward, D6 driven-high, D2 input-pullup, D3 input-hiz; reset-high-z = every pin high-z, LED off',
          by['led-on-button-held']['modes'] == {'ubc-sw1': 'closed', 'ubc-led1': 'forward', 'D6': 'driven-high', 'D2': 'input-pullup', 'D3': 'input-hiz'}
          and by['reset-high-z']['modes'] == {'ubc-sw1': 'open', 'ubc-led1': 'off', 'D6': 'high-z', 'D2': 'high-z', 'D3': 'high-z'}, (by['led-on-button-held']['modes'], by['reset-high-z']['modes']))
    trs = M.transitions('uno-light', t, cat, sts)
    kinds = {k: sum(1 for x in trs if x['kind'] == k) for k in ('external', 'firmware', 'lifecycle')}
    check('cst-0 TRANSITIONS (18): external 6 (press / release in every lifecycle), firmware 6 (the press acted on x2, SET_LED x4), lifecycle 6 (init x2, power/reset x4)',
          len(trs) == 18 and kinds == {'external': 6, 'firmware': 6, 'lifecycle': 6}, kinds)
    press = next((x for x in trs if x['from_state'] == 'button-held-led-off' and x['to_state'] == 'led-on-button-held' and x['kind'] == 'firmware'), None)
    cmd = next((x for x in trs if x['from_state'] == 'idle-led-off' and x['to_state'] == 'led-on' and x['kind'] == 'firmware'), None)
    check('cst-0 the press-driven flip names its atoms (led_toggle -> led_follow_state) and is TIMED by the press record (worst %s ms); SET_LED names apply_command -> led_follow_state and says it was read from the source' % (press or {}).get('timing_ms'),
          press and press['atoms'] == 'led_toggle, led_follow_state' and press['timing_ms'] == pr['worst_ms'] and 'measured on the twin' in press['timing']
          and cmd and cmd['atoms'] == 'apply_command, led_follow_state' and cmd['timing_ms'] == -1.0 and 'read from the source' in cmd['timing'], (press, cmd))
    init_t = next((x for x in trs if x['from_state'] == 'reset-high-z' and x['to_state'] == 'idle-led-off'), None)
    check('cst-0 lifecycle: reset-high-z -> idle-led-off is the init (hal_button_init, hal_led_init, hal_sense_init); every running state -> reset on power/reset (DS §14.2.1 cited)',
          init_t and set(init_t['atoms'].split(', ')) == {'hal_button_init', 'hal_led_init', 'hal_sense_init'}
          and all(any(x['from_state'] == s['name'] and x['kind'] == 'lifecycle' and x['to_state'].startswith('reset') and '14.2.1' in x['evidence'] for x in trs) for s in sts if s['lifecycle'] == 'running'), init_t)
    check('cst-0 every state says what reaches it (reachable_by) and where its modes were read (evidence names hal.c and the parsed atoms)',
          all(s['reachable_by'] for s in sts) and all('hal' in s['evidence'] for s in sts), [(s['name'], s['reachable_by'][:40]) for s in sts])
    # ---- cst-1: the decks + the structural rule (no engine needed)
    cat['_components'] = [c for c in t['CircuitComponentDefinition'] if c.get('circuit_name') == cat['circuit']]
    text, probes = N.deck(by['led-on-button-held'], cat, 20000)
    check('cst-1 DECK (led-on-button-held, RPU 20k): R1 220, the LED with its ammeter and the renderer\'s model, SW1 as the near-short, D6 an ideal 5 V source through an ammeter, D2\'s pull-up 20000 to 5 V through an ammeter, D3 no element; GND is ngspice\'s ground (no shorted source)',
          'Rubc_r1 LED_CONTROL LED_ANODE 220' in text and '.model polari_led' in text and 'Rubc_sw1 BUTTON_INPUT GND 0.1' in text and 'VD6 n_D6 0 DC 5.0' in text and 'Vam_D6 n_D6 LED_CONTROL DC 0' in text
          and 'Rpu_D2 n_D2_vcc n_D2 20000' in text and '* D3 input-hiz: no element' in text and 'Vgnd' not in text and 'i(vam_d6)' in probes and 'i(vpu_d2)' in probes, text)
    fl = {f['net']: f['inputs'] for f in N.floating_nets(by['reset-high-z'], cat)}
    fl2 = {f['net']: f['inputs'] for f in N.floating_nets(by['reset-button-held'], cat)}
    check('cst-1 STRUCTURAL: at reset every pin is high-Z — LED_CONTROL floats under D6 and D3, BUTTON_INPUT floats under D2 (the pull-up is off); with the button held BUTTON_INPUT is at GND and only LED_CONTROL floats; running states float nothing',
          fl == {'LED_CONTROL': ['D6', 'D3'], 'BUTTON_INPUT': ['D2']} and fl2 == {'LED_CONTROL': ['D6', 'D3']} and not N.floating_nets(by['led-on'], cat) and not N.floating_nets(by['idle-led-off'], cat), (fl, fl2))
    lim = V.limits(t)
    check('cst-1 LIMITS come from the cited rows, never typed here: I_PIN abs-max 40 mA, recommended 20 mA, VCC/GND 200 mA (DS40002061B)',
          lim['pin_abs_max_ma'] == 40.0 and lim['pin_recommended_ma'] == 20.0 and lim['supply_abs_max_ma'] == 200.0 and 'ds40002061b' in lim['cite']['pin_abs_max'].lower(), lim)
    fake = {'ok': True, 'measurements': {'i(vam_d6)': -0.045, 'i(vd6)': -0.045, 'v(led_control)': 5.0}}
    j = V.judge(by['led-on'], fake, cat, lim)
    check('cst-1 JUDGE: a pin past 40 mA REFUSES, past 20 mA WARNS, else ok (a synthetic 45 mA run refuses D6 and cites the abs-max row)',
          j['verdict'] == 'refuse' and any(f['rule'] == 'pin-current-abs-max' and 'ds40002061b' in f['cite'].lower() for f in j['findings'])
          and V.judge(by['led-on'], {'ok': True, 'measurements': {'i(vam_d6)': 0.025, 'i(vd6)': 0.025}}, cat, lim)['verdict'] == 'warn', j)
    # ---- cst-1 with the engine
    from electrodevice.custom.spice_run import capability
    if not capability()['available']:
        check('SKIP cst-1 .op runs: no ngspice on this node (%s)' % (capability().get('suggestion') or {}).get('how', ''), True)
        doc = V.document('uno-light', t, spice=False)
    else:
        doc = V.document('uno-light', t, spice=True)
        b = {s['name']: s for s in doc['states']}
        led = b['led-on']['currents']
        check('cst-1 .op led-on: the LED branch carries ~14.7 mA (= D6\'s current: (5 V - the LED\'s 1.76 V forward) / 220 ohm), within the 20 mA recommended -> ok; the pull-up draws nothing with the button up',
              b['led-on']['spice_verdict'] == 'ok' and 14.0 < led['i(vam_ubc_led1)'] < 15.5 and abs(led['i(vam_d6)'] - led['i(vam_ubc_led1)']) < 0.01 and led['i(vam_d2)'] == 0.0
              and 1.6 < led['v(led_anode)'] < 1.9 and abs(led['i(gnd-return)'] - led['i(vam_d6)']) < 0.01, led)
        held = b['button-held-led-off']
        per = {p['pullup_ohms']: p['currents']['i(vam_d2)'] for r in doc['runs'] if r['state'] == 'button-held-led-off' for p in r['runs']}
        check('cst-1 .op button-held-led-off: the pull-up current through D2 is 0.25 mA at 20 kΩ and 0.10 mA at 50 kΩ (both ends kept), D6 and the LED carry nothing, the state is ok',
              held['spice_verdict'] == 'ok' and abs(per.get(20000, 0) - 0.25) < 0.005 and abs(per.get(50000, 0) - 0.10) < 0.005 and held['currents']['i(vam_d6)'] == 0.0, (per, held['currents']))
        check('cst-1 .op: all four running states ok against the limits, the two reset states not-simulated with their structural findings (3 floating-input warnings in all); 4 runs stored per state x 2 pull-ups',
              all(b[n]['spice_verdict'] == 'ok' for n in ('idle-led-off', 'led-on', 'button-held-led-off', 'led-on-button-held'))
              and all(b[n]['spice_verdict'] == 'not-simulated' for n in ('reset-high-z', 'reset-button-held'))
              and sum(1 for f in V.finding_rows(doc) if f['status'] == 'warn') == 3 and doc['counts']['simulated'] == 4 and all(len(r['runs']) == 2 for r in doc['runs']), doc['counts'])
        rows = V.spice_rows(doc)
        check('cst-1 the spice table: one row per state x pull-up end (8) with the currents as columns', len(rows) == 8 and all('i(vam_d6)' in r for r in rows), len(rows))
        # rows on a manager + the two readers
        m = _M('CircuitState', 'CircuitStateTransition', 'CircuitRunResult')
        V.persist(m, doc)
        check('cst-1 ROWS: 6 CircuitState + 18 CircuitStateTransition + 4 CircuitRunResult (<config>:<state>:op) rows on a manager',
              len(m.objectTables['CircuitState']) == 6 and len(m.objectTables['CircuitStateTransition']) == 18 and len(m.objectTables['CircuitRunResult']) == 4
              and any(getattr(r, 'name', '') == 'uno-light:led-on:op' for r in m.objectTables['CircuitRunResult'].values()), {k: len(v) for k, v in m.objectTables.items()})
        r7 = V.rung7_findings('uno-light', 'D6', manager=m, tables=t)
        check('cst-1 RUNG 7 reader: the stored .op currents of the states that drive D6 come back as electrical findings (8: 4 states x 2 pull-ups, all ok, the led-on ones at ~14.7 mA)',
              len(r7) == 8 and all(f['status'] == 'ok' for f in r7) and any('14.7' in f['detail'] and 'led-on' in f['detail'] for f in r7), r7[:2])
        ma, basis = V.active_current_ma('uno-light', m)
        check('cst-1 active_current: the Battery term\'s basis = the led-on state\'s ground return (~14.7 mA), named as a SPICE .op; the MCU core current is said to be missing',
              ma and 14.0 < ma < 15.5 and 'led-on' in basis and 'core current is not in it' in basis, (ma, basis))
        from cmod.custom import fsc_values as FV
        qv = FV.active_current('uno-light', m)
        check('cst-1 cmod.custom.fsc_values.active_current wraps it as q(measured, mA, basis); None without a stored run', qv and qv['kind'] == 'measured' and qv['value'] == ma and FV.active_current('uno-light', _M('CircuitRunResult')) is None, qv)
        from board.custom import ladder as L
        found = L._rung7({'_manager': m, 'BoardPinNet': t['BoardPinNet']}, 'arduino-uno-r3', {'canonical': 'D6'}, 'D6', {'circuit': 'uno-button-clock', 'config': 'uno-light'}, {})
        check('cst-1 the ladder\'s rung 7 with a config in the context carries the SPICE currents beside the rule verdict (D6: the LED current named; the Vf-undetermined rule still decides)',
              found and 'SPICE' in found.get('detail', '') and '14.7' in found.get('detail', ''), found)
    # ---- the doors
    from electrodevice.circuit_states_api import CircuitStatesAPI
    api = CircuitStatesAPI(polServer=None, manager=None)
    resp = types.SimpleNamespace(status='200 OK', media=None)
    api.on_get_transitions(None, resp, 'uno-light')
    check('cst-1 door GET /api/circuit-states/uno-light/transitions answers 18 rows + counts', resp.media['ok'] and resp.media['count'] == 18 and resp.media['counts']['states'] == 6)
    resp = types.SimpleNamespace(status='200 OK', media=None)
    api.on_get_doc(None, resp, 'uno-echo')
    check('cst-1 door: a config no circuit covers answers 404 in words', resp.status.startswith('404') and 'no bench circuit' in resp.media['error'], resp.media)
    resp = types.SimpleNamespace(status='200 OK', media=None)
    api.on_get_configs(None, resp)
    check('cst-1 door GET /api/circuit-states/configs lists the UNO configs', any(r['name'] == 'uno-light' for r in resp.media['rows']))
    import electrodevice.custom.spice_run as SR
    keep = SR.ngspice_bin
    SR.ngspice_bin = lambda: None
    try:
        resp = types.SimpleNamespace(status='200 OK', media=None)
        api.on_get_spice(None, resp, 'uno-light')
        check('cst-1 door GET .../spice without an engine answers 424 with the knob (NGSPICE_BIN), and POST .../run the same', resp.status.startswith('424') and 'NGSPICE_BIN' in resp.media['error'] + json.dumps(resp.media.get('capability')), resp.media)
    finally:
        SR.ngspice_bin = keep


def main():
    run_circuit_states(check)
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
