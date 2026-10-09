"""@module electrodevice.objects.circuit._shared — what the circuit row classes share (constants, seeds, helpers); split from circuit_basis.py (sap-2c)."""

COMPONENT_KINDS = ('vsource', 'resistor', 'capacitor', 'inductor',
                   'diode', 'led', 'device',
                   # ucd-0c (UNO_CORE_DEMO_PLAN.md §5f/§5g): a momentary pushbutton — open | closed, no in-between.
                   # electrodevice.circuit_netlist_seed renders it as a near-open / near-short RESISTOR (SWITCH_OPEN_OHMS
                   # / SWITCH_CLOSED_OHMS there) — never a real SPICE switch element (ngspice's native switch needs a
                   # control voltage this demo has no node for; a two-value resistor is the honest, simplest stand-in).
                   'switch')
SEED_CIRCUITS = [
    {
        'name': 'led-branch-row',
        'description': 'One fpga-pin-led branch AS ROWS: pin source '
                       '-> derived CNT sol-gel resistor -> LED -> '
                       'ground. Must reproduce the hand renderer\'s '
                       'proven leg current (2.6123 mA at 3.3 V).',
        'analyses_json': '[{"type": "op"}]',
        'probes_json': '["i(vvpin0)"]',
    },
    {
        'name': 'rc-lowpass-demo',
        'description': 'Capacitor promotion: 10k + 1uF, tau = 10 ms '
                       '— the measured 63% rise time must land on '
                       'RC.',
        'analyses_json': '[{"type": "tran", "args": "0.1m 60m", '
                         '"meas": "tran t63 when v(out)=2.086 '
                         'rise=1"}]',
        'probes_json': '[]',
    },
    # ucd-0c (UNO_CORE_DEMO_PLAN.md §1, the demo bench): a pushbutton on D2 (internal pull-up -- no VCC5 net, no
    # pull resistor on this net), an LED on D6 through a 220 ohm resistor to GND, and a jumper D6->D3 (the "sense
    # pin") so the MCU independently reads the edges on the line it itself drives. The board side (which BoardPin
    # sits on which net, who drives it) is board.custom.board_pin_nets -- this circuit is the physical bench alone.
    # No vsource/device component drives LED_CONTROL here (the board pin D6 is that source, modelled as a
    # BoardPinNet link, never a circuit vsource) -- render_circuit() proves the netlist TEXT renders without
    # exception (ucd-0c's own bar); an actual ngspice RUN would need a source node this slice does not add (not
    # required -- Phase 1 is the electrical CHECK, not a sim).
    {
        'name': 'uno-button-clock',
        'description': "The UNO core demo bench: pushbutton on D2 (internal pull-up), LED on D6 through a 220 ohm "
                       "resistor to GND, jumper D6->D3 so the MCU senses the LED line it drives. Nets are named "
                       "for readability (GND, not the SPICE literal '0') -- not aliased to the simulator's ground "
                       "node; an actual ngspice run of this circuit is not required by ucd-0c, which only proves "
                       "the rows render to a netlist without exception.",
        'analyses_json': '[{"type": "op"}]',
        'probes_json': '[]',
    },
]
SEED_CIRCUIT_NETS = [
    {'name': 'led-net-pin0', 'circuit_name': 'led-branch-row',
     'net': 'pin0', 'description': 'FPGA pin (driven rail)'},
    {'name': 'led-net-mid0', 'circuit_name': 'led-branch-row',
     'net': 'mid0', 'description': 'resistor->LED junction'},
    {'name': 'led-net-gnd', 'circuit_name': 'led-branch-row',
     'net': '0', 'is_ground': True, 'description': 'ground'},
    {'name': 'rc-net-in', 'circuit_name': 'rc-lowpass-demo',
     'net': 'in', 'description': 'source rail'},
    {'name': 'rc-net-out', 'circuit_name': 'rc-lowpass-demo',
     'net': 'out', 'description': 'RC output'},
    {'name': 'rc-net-gnd', 'circuit_name': 'rc-lowpass-demo',
     'net': '0', 'is_ground': True, 'description': 'ground'},
    # uno-button-clock (ucd-0c). board_pins_refs_json (additive, ucd-0c Part 1 item 3): the BoardPin rows the
    # board side (board.custom.board_pin_nets) ties to THIS net, by name, for reverse navigation from the net's
    # own object page -- hand-written here (a fixed, small, cited bench), never derived at import time (electrodevice
    # does not import board; board already references these net rows by name through BoardPinNet.circuit_net).
    {'name': 'ubc-net-led-control', 'circuit_name': 'uno-button-clock', 'net': 'LED_CONTROL',
     'description': "D6 drives this net (the LED's control line, through R1); D3 only senses it (the jumper wire, "
                    "UNO_CORE_DEMO_PLAN.md §1's 'sense pin') -- never a second driver.",
     'board_pins_refs_json': '["BoardPin:arduino-uno-r3:D6", "BoardPin:arduino-uno-r3:D3"]'},
    {'name': 'ubc-net-led-anode', 'circuit_name': 'uno-button-clock', 'net': 'LED_ANODE',
     'description': 'R1 -> LED1 anode junction (no board pin sits directly on this net).',
     'board_pins_refs_json': '[]'},
    {'name': 'ubc-net-gnd', 'circuit_name': 'uno-button-clock', 'net': 'GND', 'is_ground': True,
     'description': "ground -- ties to the board's GND connector pins (POWER header pins 6/7, DIGITAL_H pin 7; "
                    "board.custom.power_pins), never a BoardPin row itself.",
     'board_pins_refs_json': '[]'},
    {'name': 'ubc-net-button-input', 'circuit_name': 'uno-button-clock', 'net': 'BUTTON_INPUT',
     'description': "D2 reads this net; the internal pull-up (PinClaim pull 'up', not yet authored on any task -- "
                    "electrical_check's pull rule names that) holds it high when SW1 is open.",
     'board_pins_refs_json': '["BoardPin:arduino-uno-r3:D2"]'},
]
SEED_CIRCUIT_COMPONENTS = [
    # led-branch-row (the device row is the SEEDED
    # cnt-solgel-led-resistor from electrodevice, derived live).
    {'name': 'vpin0', 'circuit_name': 'led-branch-row',
     'kind': 'vsource', 'params_json': '{"dc": 3.3}',
     'pins_json': '["pin0", "0"]', 'description': 'the FPGA pin'},
    {'name': 'rlimit0', 'circuit_name': 'led-branch-row',
     'kind': 'device', 'params_json': '{}',
     'pins_json': '["pin0", "mid0"]',
     'device_name': 'cnt-solgel-led-resistor',
     'description': 'derived CNT sol-gel current limiter'},
    {'name': 'dled0', 'circuit_name': 'led-branch-row',
     'kind': 'led', 'params_json': '{}',
     'pins_json': '["mid0", "0"]', 'description': 'indicator LED'},
    # rc-lowpass-demo.
    {'name': 'vin', 'circuit_name': 'rc-lowpass-demo',
     'kind': 'vsource', 'params_json': '{"dc": 3.3}',
     'pins_json': '["in", "0"]', 'description': ''},
    {'name': 'r1', 'circuit_name': 'rc-lowpass-demo',
     'kind': 'resistor', 'params_json': '{"ohms": 10000}',
     'pins_json': '["in", "out"]', 'description': ''},
    {'name': 'c1', 'circuit_name': 'rc-lowpass-demo',
     'kind': 'capacitor', 'params_json': '{"farads": 1e-6, "ic": 0}',
     'pins_json': '["out", "0"]', 'description': ''},
    # uno-button-clock (ucd-0c, UNO_CORE_DEMO_PLAN.md §1 + §5g item 1): kit parts cited to board.custom.kit_parts
    # (the Arduino Starter Kit book, cited pages there) + board.custom.uno_facts/board_uno (the board's own cited
    # numbers) -- never a new, uncited figure. Typed limit keys the checker (board.custom.electrical_check) reads:
    # v_forward/max_ma on the LED, max_ma on the switch, ohms on the resistor.
    {'name': 'ubc-r1', 'circuit_name': 'uno-button-clock', 'kind': 'resistor',
     'params_json': '{"ohms": 220}', 'pins_json': '["LED_CONTROL", "LED_ANODE"]',
     'description': "the bench's series resistor (UNO_CORE_DEMO_PLAN.md §1); 220 ohm is the kit's own common "
                    "practice for this LED -- NOT printed on the cited kit page itself (board.custom.kit_parts "
                    "'led' row, driver_needed: \"that exact value is not printed on this page\"); see KitPart "
                    "arduino-starter-kit:resistors (exact ohm values of the kit's own resistors are not listed "
                    "on its cited page either -- read from colour-code bands in hand)."},
    {'name': 'ubc-led1', 'circuit_name': 'uno-button-clock', 'kind': 'led',
     'params_json': '{"v_forward": 2.0}', 'pins_json': '["LED_ANODE", "GND"]',
     'description': "the kit's indicator LED (KitPart arduino-starter-kit:led, Arduino Starter Kit book, Parts in "
                    "your kit p.7); anode on LED_ANODE (through R1), cathode on GND. v_forward: ASSUMED 2.0 V "
                    "typical red LED -- an ASSUMPTION, NOT A FACT (the KitPart's own electrical_notes: 'no "
                    "forward-voltage/current rating printed on the cited page'). max_ma: not cited either, same "
                    "note -- left UNSET here; electrical_check checks the computed current only against the "
                    "DRIVING PIN's own cited limit (board_uno fact pinout.max_current_io, 20 mA), named so in "
                    "its finding, never a guessed device rating."},
    {'name': 'ubc-sw1', 'circuit_name': 'uno-button-clock', 'kind': 'switch',
     'params_json': '{"state": "open"}', 'pins_json': '["BUTTON_INPUT", "GND"]',
     'description': "the kit's momentary pushbutton (KitPart arduino-starter-kit:pushbutton, Arduino Starter Kit "
                    "book, Parts in your kit p.8); wired BUTTON_INPUT to GND, closed only while pressed. D2's own "
                    "internal pull-up (a PinClaim pull 'up', ucd-0e2's firmware scope -- not yet authored on any "
                    "task) holds BUTTON_INPUT high when open; this circuit carries NO external pull resistor on "
                    "this net (electrical_check's pull rule names that honestly until the claim exists)."},
]
