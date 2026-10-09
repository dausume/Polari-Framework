"""
@module board.custom.board_pin_nets

ucd-0c (UNO_CORE_DEMO_PLAN.md §1, §5e Q2, §5g's adopted list): THE DEMO BENCH wired as `BoardPinNet` rows — which
board pin sits on which net of the electrodevice circuit `uno-button-clock`, and whether it drives that net or
only listens to it. Code-owned (seeded, converges) — a person's own wiring is a canvas addition later, same
posture as every other "seed, keep a person's own row" class in this arc.

The bench (UNO_CORE_DEMO_PLAN.md §1, the bare numbers board.custom.board_uno already cites):
  - a pushbutton on **D2** (INT0), internal pull-up — `target_compat` rates `interrupt-in` ok only on INT0/INT1
    (the HAL_INT0 atom already exists); no external pull resistor on this net (the circuit side, electrodevice's
    `uno-button-clock` row SW1), so the pull is DEFINED only once a task's `PinClaim` on D2 carries `pull='up'`
    (ucd-0e2, firmware scope — not yet authored; `electrical_check`'s own pull rule names the gap honestly);
  - an LED on **D6** through the kit's 220 Ω resistor to GND (D6 already carries the LED in `uno-sim-rig`);
  - one jumper wire **D6 → D3** (INT1) — "the sense pin": the MCU independently detects the edges on the LED's
    OWN line through a REAL WIRE, never by reading its own output latch. D6 and D3 sit on the SAME net
    (`LED_CONTROL`): D6 drives it (`role='driver'`), D3 only listens (`role='input'`) — `electrical_check`'s own
    rule (b) refuses two drivers on one net; this wiring is valid because D3 is role input, never a second driver.

GND is a power/reference connector label (`board.custom.power_pins`), never a `BoardPin` row (`board_uno.py` only
makes one per SoC-backed D/A signal pin) — its row's `board_pin` is `''`, and `notes` names the connector pins the
kit book's own "GND and 5V pins" (p.11) are physically on (`board_uno.CONNECTORS`: POWER header 6/7, DIGITAL_H 7).
"""
CIRCUIT = 'uno-button-clock'
BOARD = 'arduino-uno-r3'


def _name(canonical, net):
    return '%s:%s@%s:%s' % (BOARD, canonical, CIRCUIT, net)


SEED_BOARD_PIN_NETS = [
    {
        'name': _name('D6', 'LED_CONTROL'), 'board': BOARD, 'board_pin': '%s:D6' % BOARD,
        'circuit': CIRCUIT, 'circuit_net': 'ubc-net-led-control', 'role': 'driver', 'provenance': 'seed',
        'notes': "drives the LED's own line (UNO_CORE_DEMO_PLAN.md §1: the kit's R1 220 ohm + LED1 branch to GND); "
                "already carries the LED in uno-sim-rig.",
    },
    {
        'name': _name('D3', 'LED_CONTROL'), 'board': BOARD, 'board_pin': '%s:D3' % BOARD,
        'circuit': CIRCUIT, 'circuit_net': 'ubc-net-led-control', 'role': 'input', 'provenance': 'seed',
        'notes': "the jumper D6->D3 (UNO_CORE_DEMO_PLAN.md §1, 'the sense pin'): D3 (INT1) independently reads "
                "the edges on the line D6 drives — a real wire, never the MCU reading its own output latch; role "
                "'input' (never a second driver — electrical_check's own rule on this net).",
    },
    {
        'name': _name('D2', 'BUTTON_INPUT'), 'board': BOARD, 'board_pin': '%s:D2' % BOARD,
        'circuit': CIRCUIT, 'circuit_net': 'ubc-net-button-input', 'role': 'input', 'provenance': 'seed',
        'notes': "internal pull-up: PinClaim pull up (ucd-0e2's firmware task, not yet authored — the circuit "
                "carries no external pull resistor on this net; electrical_check's pull rule warns until the "
                "claim exists).",
    },
    {
        'name': '%s:GND@%s:GND' % (BOARD, CIRCUIT), 'board': BOARD, 'board_pin': '',
        'circuit': CIRCUIT, 'circuit_net': 'ubc-net-gnd', 'role': 'ground', 'provenance': 'seed',
        'notes': "GND is a power/reference connector label (board.custom.power_pins), never a BoardPin row — "
                "board_pin is '' by design; this circuit's ground ties to the board's own GND connector pins "
                "(board_uno.CONNECTORS: POWER header pins 6 and 7, DIGITAL_H pin 7 — the kit book's 'GND and 5V "
                "pins', p.11).",
    },
]
