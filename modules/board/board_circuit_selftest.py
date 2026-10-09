"""board_circuit_selftest — ucd-0c (UNO_CORE_DEMO_PLAN.md §1, §5f item 3, §5g's adopted list): THE DEMO CIRCUIT AS
ROWS + THE ELECTRICAL FINDINGS. The bench: pushbutton on D2 (internal pull-up), LED on D6 through a 220 ohm
resistor to GND, jumper D6->D3 (the sense pin). Checks: the circuit seeds (nets, parts, the new `switch` kind
renders in the netlist seed without an exception), the four BoardPinNet rows resolve both ways, the Phase-1
findings for uno-button-clock on arduino-uno-r3 (LED current, single driver, shared ground, level compatibility,
the button's pull — warn today, ok once a claim defines it), a synthetic two-driver circuit refuses, and a rule
with a missing cite reads undetermined, never a guess. Run by board_selftest.main().
"""
BOARD = 'arduino-uno-r3'
CIRCUIT = 'uno-button-clock'


def run_circuit(check):
    _circuit_seeds(check)
    _board_pin_net_rows(check)
    _findings_ok_path(check)
    _pull_rule_warn_then_ok(check)
    _two_drivers_refuse(check)
    _missing_cite_undetermined(check)


# ---------------------------------------------------------------- part 1: the circuit rows themselves
def _circuit_seeds(check):
    from electrodevice.objects.circuit._shared import COMPONENT_KINDS, SEED_CIRCUITS, SEED_CIRCUIT_NETS, SEED_CIRCUIT_COMPONENTS
    from electrodevice import circuit_netlist_seed as CN
    import types

    check("'switch' is a COMPONENT_KINDS member (the momentary pushbutton)", 'switch' in COMPONENT_KINDS)
    circuit = next((c for c in SEED_CIRCUITS if c['name'] == CIRCUIT), None)
    check('uno-button-clock is a seeded CircuitDefinition', circuit is not None, circuit)
    nets = {n['net'] for n in SEED_CIRCUIT_NETS if n['circuit_name'] == CIRCUIT}
    check('its four nets are LED_CONTROL, LED_ANODE, GND, BUTTON_INPUT (no VCC5 — the pull-up is internal)',
          nets == {'LED_CONTROL', 'LED_ANODE', 'GND', 'BUTTON_INPUT'}, nets)
    comps = {c['name']: c for c in SEED_CIRCUIT_COMPONENTS if c['circuit_name'] == CIRCUIT}
    check('three parts: a resistor (R1), an LED, a switch (SW1) — one of each new/typed kind',
          {c['kind'] for c in comps.values()} == {'resistor', 'led', 'switch'}, sorted(comps))
    sw = next(c for c in comps.values() if c['kind'] == 'switch')
    check("the switch's params carry a typed 'state' (open|closed)",
          __import__('json').loads(sw['params_json']).get('state') in ('open', 'closed'), sw['params_json'])

    # the switch kind renders in the netlist seed WITHOUT AN EXCEPTION (the acceptance bar — not a full ngspice run)
    mgr = types.SimpleNamespace(objectTables={
        'CircuitDefinition': {c['name']: types.SimpleNamespace(**c) for c in SEED_CIRCUITS},
        'CircuitNetDefinition': {n['name']: types.SimpleNamespace(**n) for n in SEED_CIRCUIT_NETS},
        'CircuitComponentDefinition': {c['name']: types.SimpleNamespace(**c) for c in SEED_CIRCUIT_COMPONENTS},
    }, db=None)
    try:
        rendered = CN.render_circuit(mgr, CIRCUIT)
        ok, why = True, ''
    except Exception as e:  # noqa: BLE001 — the test itself asserts "no exception"; a raise IS the failure to report
        ok, why = False, str(e)
    check('the switch kind renders in the netlist seed without an exception', ok, why)
    if ok:
        check('the rendered netlist carries a resistor element for the switch (near-open by default: state=open)',
              'Rubc_sw1' in rendered['netlist'] and str(CN.SWITCH_OPEN_OHMS) in rendered['netlist'], rendered['netlist'])
        check('no undeclared-net suggestions (every pin sits on a declared net)', rendered['suggestions'] == [])


# ---------------------------------------------------------------- part 2: BoardPinNet both ways
def _board_pin_net_rows(check):
    from board.custom.board_pin_nets import SEED_BOARD_PIN_NETS
    from board.custom import board_object as BO
    r = BO.rows_for(BOARD)
    board_pins = {p['name'] for p in r['pins']}
    check('four BoardPinNet rows: D6 driver, D3 input, D2 input, GND ground', len(SEED_BOARD_PIN_NETS) == 4, SEED_BOARD_PIN_NETS)
    by_role = {row['role']: row for row in SEED_BOARD_PIN_NETS if row['role'] in ('driver', 'ground')}
    check('D6 is the one driver (LED_CONTROL)', by_role['driver']['board_pin'] == '%s:D6' % BOARD, by_role.get('driver'))
    inputs = sorted(row['board_pin'] for row in SEED_BOARD_PIN_NETS if row['role'] == 'input')
    check('D2 and D3 are both role input (D3 senses what D6 drives; D2 reads the button)',
          inputs == ['%s:D2' % BOARD, '%s:D3' % BOARD], inputs)
    check("GND's row carries board_pin='' (a power/reference connector label, never a BoardPin row) with notes naming it",
          by_role['ground']['board_pin'] == '' and 'connector' in by_role['ground']['notes'].lower(), by_role.get('ground'))

    # forward: every non-GND row's board_pin resolves to a real BoardPin
    bad_fwd = [row['name'] for row in SEED_BOARD_PIN_NETS if row['board_pin'] and row['board_pin'] not in board_pins]
    check('forward: every BoardPinNet.board_pin (where set) resolves to a real BoardPin row', not bad_fwd, bad_fwd)

    # forward: every row's circuit_net resolves to a real CircuitNetDefinition row
    from electrodevice.objects.circuit._shared import SEED_CIRCUIT_NETS
    net_names = {n['name'] for n in SEED_CIRCUIT_NETS}
    bad_net = [row['name'] for row in SEED_BOARD_PIN_NETS if row['circuit_net'] not in net_names]
    check('forward: every BoardPinNet.circuit_net resolves to a real CircuitNetDefinition row', not bad_net, bad_net)

    # reverse: the net's own board_pins_refs_json names the pins back (additive field, ucd-0c item 3)
    import json
    by_net_name = {n['name']: n for n in SEED_CIRCUIT_NETS}
    bad_rev = []
    for row in SEED_BOARD_PIN_NETS:
        if not row['board_pin']:
            continue
        net = by_net_name.get(row['circuit_net'], {})
        refs = json.loads(net.get('board_pins_refs_json') or '[]')
        if ('BoardPin:%s' % row['board_pin']) not in refs:
            bad_rev.append(row['name'])
    check("reverse: every pin-bearing row's own net names it back in board_pins_refs_json", not bad_rev, bad_rev)


# ---------------------------------------------------------------- part 3: the findings, the happy path
def _findings_ok_path(check):
    from board.custom import electrical_check as EC
    tables = EC.tables_for(manager=None)
    findings = EC.check(CIRCUIT, BOARD, tables)
    by_rule = {f['rule']: f for f in findings}

    check('led_current: ok, with a computed mA figure and its cites',
          by_rule['led_current']['status'] == 'ok' and 'mA' in by_rule['led_current']['detail']
          and by_rule['led_current']['cite'], by_rule.get('led_current'))
    import re
    m = re.search(r'([-+]?[0-9.]+) mA', by_rule['led_current']['detail'])
    check('led_current: the computed figure is 13.636 mA ((5.0 - 2.0) / 220 * 1000), under the pin\'s 20 mA limit',
          m is not None and abs(float(m.group(1)) - 13.636) < 0.01, by_rule['led_current']['detail'])
    check('single_driver: ok (D6 is the only driver of LED_CONTROL — D3 is role input, never a second driver)',
          by_rule['single_driver']['status'] == 'ok', by_rule.get('single_driver'))
    check('shared_ground: ok (every part reaches GND, which ties to the board\'s own GND)',
          by_rule['shared_ground']['status'] == 'ok', by_rule.get('shared_ground'))
    check('level_compatible: ok (D6 drives, D3 reads — one board, one cited logic level)',
          by_rule['level_compatible']['status'] == 'ok', by_rule.get('level_compatible'))
    check('every finding carries the five keys {rule, status, subject, detail, cite}',
          all(set(f) == {'rule', 'status', 'subject', 'detail', 'cite'} for f in findings), findings)


def _pull_rule_warn_then_ok(check):
    from board.custom import electrical_check as EC
    tables = EC.tables_for(manager=None)
    findings = EC.check(CIRCUIT, 'uno-sim-rig', tables)
    pull = next(f for f in findings if f['rule'] == 'pull_defined')
    check("pull_defined WARNS today (uno-sim-rig's binding has no D2 claim — no task registers it yet)",
          pull['status'] == 'warn' and 'D2' in pull['detail'] and 'pull' in pull['detail'], pull)

    override = [{'board_pin': '%s:D2' % BOARD, 'pull': 'up', 'name': 'uno-sim-rig:D2'}]
    findings2 = EC.check(CIRCUIT, 'uno-sim-rig', tables, pin_claims=override)
    pull2 = next(f for f in findings2 if f['rule'] == 'pull_defined')
    check("…and an override on D2 pull='up' (simulating the real PinClaim ucd-0e2's firmware will add) turns it ok",
          pull2['status'] == 'ok' and 'up' in pull2['detail'], pull2)


# ---------------------------------------------------------------- part 4: a synthetic two-driver circuit refuses
def _two_drivers_refuse(check):
    from board.custom import electrical_check as EC
    tables = EC.tables_for(manager=None)
    tables = dict(tables)
    tables['CircuitDefinition'] = tables['CircuitDefinition'] + [
        {'name': 'synthetic-two-drivers', 'description': 'test fixture', 'analyses_json': '[]', 'probes_json': '[]'}]
    tables['CircuitNetDefinition'] = tables['CircuitNetDefinition'] + [
        {'name': 'syn-net-x', 'circuit_name': 'synthetic-two-drivers', 'net': 'X', 'is_ground': False, 'description': ''}]
    tables['BoardPinNet'] = tables['BoardPinNet'] + [
        {'name': '%s:D6@synthetic-two-drivers:X' % BOARD, 'board': BOARD, 'board_pin': '%s:D6' % BOARD,
         'circuit': 'synthetic-two-drivers', 'circuit_net': 'syn-net-x', 'role': 'driver', 'provenance': 'seed', 'notes': ''},
        {'name': '%s:D5@synthetic-two-drivers:X' % BOARD, 'board': BOARD, 'board_pin': '%s:D5' % BOARD,
         'circuit': 'synthetic-two-drivers', 'circuit_net': 'syn-net-x', 'role': 'driver', 'provenance': 'seed', 'notes': ''},
    ]
    findings = EC.check('synthetic-two-drivers', BOARD, tables)
    single = next(f for f in findings if f['rule'] == 'single_driver')
    check('D6 AND D5 both role driver on one net -> single_driver REFUSES, naming both pins',
          single['status'] == 'refuse' and 'D6' in single['detail'] and 'D5' in single['detail'], single)


# ---------------------------------------------------------------- part 5: a missing cite -> undetermined, never a guess
def _missing_cite_undetermined(check):
    import copy
    from board.custom import electrical_check as EC
    tables = copy.deepcopy(EC.tables_for(manager=None))
    for c in tables['CircuitComponentDefinition']:
        if c['name'] == 'ubc-led1':
            c['params_json'] = '{}'   # no v_forward at all — nothing to compute from, nothing to guess
    findings = EC.check(CIRCUIT, BOARD, tables)
    led = next(f for f in findings if f['rule'] == 'led_current')
    check('a missing v_forward -> led_current reads undetermined, naming what is missing (never a guessed number)',
          led['status'] == 'undetermined' and 'v_forward' in led['detail'], led)
