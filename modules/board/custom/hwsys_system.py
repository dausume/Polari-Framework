"""
@module board.custom.hwsys_system

hsp-1 (L6): THE HARDWARE SYSTEM ROW(S). Today one: `uno-light-system` at stage S1-breadboard — the UNO with its two chips, the bench circuit `uno-button-clock` (button SW1, LED1,
R1, the D6 -> D3 jumper), the host's serial/bridge runtime, the firmware, Polari and the person pressing the button. Participants use the SHAPE of a cmod Purpose's participants
(cmod.custom.purpose_seeds._PARTICIPANTS: role / kind / ref / variant); `kind` is extended with hardware · software · person and `ref` is Class:name. Every ref is DERIVED from a row
(the circuit's component kinds, the bridge seed, the BoardPinNet wiring); nothing about a part is typed here a second time. Verification and the undetermined text are the
honest state: the bench board's package and USB-interface variants are PENDING (his ruling 2026-10-15), no Person class exists, nothing here has run on a bench.
"""
import json

from board.custom import board_pin_nets as BPN

SYSTEM = 'uno-light-system'
STAGES = ('S1-breadboard', 'S2-protoboard', 'S3-pcb', 'S4-vendor-soc', 'S5-blcnc-soc')
KINDS = ('hardware', 'software', 'person')
LIGHT = 'uno-light'   # hwnocode light_solutions.LIGHT_SOLUTION (the Cross-Domain Solution), cmod FirmwareSolution, grpcbridge LIGHT_BRIDGE: one name by design


def _circuit_part(tables, circuit, kind):
    return next((c['name'] for c in tables.get('CircuitComponentDefinition', []) if c.get('circuit_name') == circuit and c.get('kind') == kind), '')


def participants(tables, board='arduino-uno-r3', circuit=BPN.CIRCUIT):
    p = lambda role, kind, ref, **kw: dict({'role': role, 'kind': kind, 'ref': ref}, **kw)   # noqa: E731
    parts = [p('board', 'hardware', 'BoardDefinition:%s' % board, variant='pending'),
             p('chip U1 (mcu)', 'hardware', 'BoardComponent:%s:U1' % board, variant='pending'),
             p('chip U2 (usb-bridge)', 'hardware', 'BoardComponent:%s:U2' % board, variant='pending'),
             p('bench circuit', 'hardware', 'CircuitDefinition:%s' % circuit)]
    for role, kind in (('button SW1', 'switch'), ('LED1', 'led'), ('resistor R1', 'resistor')):
        nm = _circuit_part(tables, circuit, kind)
        parts.append(p(role, 'hardware', 'CircuitComponentDefinition:%s' % (nm or '?')))
    parts.append(p('jumper D6-D3', 'hardware', 'BoardPinNet:%s' % BPN._name('D3', 'LED_CONTROL')))
    parts += [p('firmware', 'software', 'FirmwareSolution:%s' % LIGHT),
              p('host serial / bridge', 'software', 'HardwareBridgeDefinition:%s-bridge' % LIGHT),
              p('host bridge runtime', 'software', 'Runtime:java-bridge'),
              p('Polari backend', 'software', 'Runtime:python-backend'),
              p('Polari page', 'software', 'Runtime:typescript-browser'),
              p('person', 'person', 'Person:bench-operator')]
    return parts


def rows(tables):
    parts = participants(tables)
    board = next(p['ref'] for p in parts if p['ref'].startswith('BoardDefinition:'))
    comps = [p['ref'] for p in parts if p['ref'].startswith(('BoardComponent:', 'CircuitComponentDefinition:', 'BoardPinNet:'))]
    return [{
        'name': SYSTEM, 'title': 'UNO light demo — breadboard system (S1)', 'stage': 'S1-breadboard', 'participants_json': json.dumps(parts),
        'boards_json': json.dumps([board]), 'components_json': json.dumps(comps),
        'circuits_json': json.dumps([p['ref'] for p in parts if p['ref'].startswith('CircuitDefinition:')]),
        'links_refs_json': '[]',   # filled by board.custom.hardware_system.build from the links actually derived
        'task_plan': '', 'solution': LIGHT, 'verification': 'partial',
        'undetermined': 'which package (28-SPDIP or 32-TQFP) and which USB interface (16U2 verified, CH340 unverified) the bench board carries is PENDING identification; '
                        'there is no Person class yet (the person is a role); nothing here has run on a physical bench; the Task Plan arrives with fgm-3',
        'notes': 'stage S1 Breadboard (SYSTEM_HIERARCHY_TERMINOLOGY.md §11): the bought development board plus a kit button, LED and resistor and one jumper wire'}]
