"""
@module board.custom.board_uno

THE UNO R3 AS A BOARD OBJECT (brd-bo, PCB_FROM_SCRATCH_PLAN §2b): its headers with their pin order, its nets, its 20 board pins
(D0–D13, A0–A5) ↔ ATmega328P port pins, the 16U2 USB bridge as the hardware's USB identity, and its runtime profiles.

Source: Arduino's own pinout, "Arduino UNO R3 (A000066) Full Pinout" — READ 2026-10-03 (PDF, 5 pages, "Last update: 6 Oct,
2022", CC BY-SA 4.0; we cite its facts, we do not copy the drawing), file sha256 088b4d7d…0007:
  p.1  D0–D13 ↔ PD0–PD7 / PB0–PB5, A0–A5 ↔ PC0–PC5 (also D14–D19), D18/SDA = PC4, D19/SCL = PC5, LED_BUILTIN = PB5,
       the power header top-down NC, IOREF, RESET, +3V3, +5V, GND, GND, VIN; 20 mA max per I/O pin, 50 mA on +3V3, VIN 6–20 V
  p.3  the alternate functions per pin (~PWM: D3 OC2B, D5 OC0B, D6 OC0A, D9 OC1A, D10 OC1B, D11 OC2A; D0 RXD, D1 TXD; ADC[n]);
       the ATmega16U2 on the USB side (its own ICSP1 header is not modelled here)
  p.4  the ICSP header of the 328P: 1 CIPO (PB4), 2 +5V, 3 SCK (PB5), 4 COPI (PB3), 5 RESET, 6 GND
Where the pinout and the ATmega328P datasheet both speak (the port pin of each D/A pin, the timer of each PWM pin) they agree;
the selftest checks it against the SocPin rows.

The ROLES our firmware gives pins (the sim rig, brd-1) are the assignment: D13 = LED_BUILTIN (LED_PIN), D6 = PWM_LED (PWM_PIN,
Timer0 OC0A), A0 = TEMP_SENSE (ADC_CHANNEL, the kit's TMP36), D0/D1 = USART0 RXD/TXD (the frames, through the 16U2). Every
other header pin's net is its own label (the Arduino-shield convention).
"""
import json

from board.custom.soc_atmega328p import SOC, PINS as SOC_PINS, FUNCTION_PERIPHERAL

BOARD = 'arduino-uno-r3'
DOC = 'Arduino UNO R3 (A000066) Full Pinout'
REV = 'Last update: 6 Oct, 2022 — fetched 2026-10-03, file sha256 088b4d7d776abf443cb050c31875221aa5fc7f0533470b33e035c249cf240007'
URL = 'https://docs.arduino.cc/resources/pinouts/A000066-full-pinout.pdf'

#: canonical → (SoC pin, number the C side uses)
D_PINS = {'D%d' % i: ('PD%d' % i if i < 8 else 'PB%d' % (i - 8), i) for i in range(14)}
A_PINS = {'A%d' % i: ('PC%d' % i, i) for i in range(6)}
#: the roles the firmware gives (canonical → net, function, signal, firmware_symbol)
ROLES = {'D13': ('LED_BUILTIN', 'led', '', 'LED_PIN'), 'D6': ('PWM_LED', 'pwm', 'OC0A', 'PWM_PIN'),
         'A0': ('TEMP_SENSE', 'adc', 'ADC0', 'ADC_CHANNEL'), 'D0': ('USART0_RX', 'uart', 'RXD', ''), 'D1': ('USART0_TX', 'uart', 'TXD', '')}
#: connector → (ref, kind, footprint, labels in pin order, how the order was assigned)
CONNECTORS = {
    'POWER': ('J1', 'header', 'Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical',
              ['NC', 'IOREF', 'RESET', '+3V3', '+5V', 'GND', 'GND', 'VIN'], 'pin 1 = NC, then as drawn top-down (p.1)'),
    'ANALOG': ('J2', 'header', 'Connector_PinSocket_2.54mm:PinSocket_1x06_P2.54mm_Vertical', ['A0', 'A1', 'A2', 'A3', 'A4', 'A5'], 'pin 1 = A0 (p.1)'),
    'DIGITAL_L': ('J3', 'header', 'Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical', ['D%d' % i for i in range(8)], 'pin 1 = D0 (p.1)'),
    'DIGITAL_H': ('J4', 'header', 'Connector_PinSocket_2.54mm:PinSocket_1x10_P2.54mm_Vertical',
                  ['D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'GND', 'AREF', 'SDA', 'SCL'], 'pin 1 = D8 (p.1 draws it from SCL down to D8)'),
    'ICSP': ('J5', 'icsp', 'Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical', ['CIPO', '+5V', 'SCK', 'COPI', 'RESET', 'GND'],
             'ICSP numbering as printed (p.4)'),
}
ORDER_NOTE = 'header pin numbers are OURS (the pinout prints none except on ICSP); unverified against a KiCad Arduino shield footprint'
#: a connector label that is not a board pin → its net
POWER_NETS = {'NC': '', 'IOREF': 'IOREF', 'RESET': 'RESET', '+3V3': '+3V3', '+5V': '+5V', 'GND': 'GND', 'VIN': 'VIN', 'AREF': 'AREF'}
#: labels that ARE another pin's net (the pinout: D18/SDA = PC4 = A4, D19/SCL = PC5 = A5; ICSP CIPO/SCK/COPI = PB4/PB5/PB3)
SAME_AS = {'SDA': 'A4', 'SCL': 'A5', 'CIPO': 'D12', 'SCK': 'D13', 'COPI': 'D11'}
NOTES = {'D13': 'the on-board LED "L" (LED_BUILTIN = PB5); also ICSP SCK', 'A0': 'also D14 (digital); the kit\'s TMP36 (project 03)',
         'A4': 'also D18 / SDA (DIGITAL_H:9)', 'A5': 'also D19 / SCL (DIGITAL_H:10)',
         'D0': 'to the 16U2 (the USB side) — the SimRigState frames', 'D1': 'to the 16U2 (the USB side) — the SimRigState frames',
         'D3': 'OC2B = Timer2, the 1 ms tick of our bare-C runtime — not a PWM pin here',
         'D11': 'OC2A = Timer2 (the tick); also ICSP COPI', 'D12': 'also ICSP CIPO'}


def _fact(key, value, unit, where, notes=''):
    return {'name': '%s:%s' % (BOARD, key), 'board': BOARD, 'fact_key': key, 'value': str(value), 'unit': unit, 'document': DOC,
            'revision': REV, 'page_table': where, 'url': URL, 'notes': notes}


def facts():
    out = [_fact('pinout.%s' % c, '%s (%s)' % (s, '/'.join(SOC_PINS[s][1])), '', 'p.1 (pin ↔ port); p.3 (alternate functions)')
           for c, (s, n) in sorted({**D_PINS, **A_PINS}.items())]
    out += [_fact('pinout.led_builtin', 'PB5 (D13)', '', 'p.1 LED_BUILTIN'),
            _fact('pinout.max_current_io', 20, 'mA', 'p.1 legend: "MAXIMUM current per I/O pin is 20mA"'),
            _fact('pinout.max_current_3v3', 50, 'mA', 'p.1 legend: "MAXIMUM current per +3.3V pin is 50mA"'),
            _fact('pinout.vin_range', '6-20', 'V', 'p.1 legend: "VIN 6-20V input to the board"'),
            _fact('pinout.power_header', 'NC, IOREF, RESET, +3V3, +5V, GND, GND, VIN', '', 'p.1 (top-down)'),
            _fact('pinout.icsp', '1 CIPO PB4, 2 +5V, 3 SCK PB5, 4 COPI PB3, 5 RESET, 6 GND', '', 'p.4 (ICSP, the ATmega328P side)'),
            _fact('pinout.usb_bridge', 'ATMEGA16U2', '', 'p.3 (the USB side: VBUS, D-, D+ on the 16U2)')]
    return out


def _connector_of():
    out = {}
    for conn, (_, _, _, labels, _) in CONNECTORS.items():
        for i, lab in enumerate(labels, 1):
            out.setdefault(lab, '%s:%d' % (conn, i))
    return out


def board_pins():
    conn_of = _connector_of()
    rows = []
    for c, (s, n) in list(D_PINS.items()) + list(A_PINS.items()):
        net, function, signal, sym = ROLES.get(c, (c, 'gpio', '', ''))
        rows.append({'name': '%s:%s' % (BOARD, c), 'board': BOARD, 'canonical': c, 'number': n, 'soc_pin': s, 'net': net,
                     'connector_pin': conn_of[c], 'function': function, 'peripheral': FUNCTION_PERIPHERAL[signal][0] if signal else '',
                     'signal': signal, 'firmware_symbol': sym, 'alias': '',
                     'electrical_json': json.dumps({'max_ma': 20, 'fact': '%s:pinout.max_current_io' % BOARD}, sort_keys=True),
                     'facts_json': json.dumps(['%s:pinout.%s' % (BOARD, c), '%s:pin.%s' % (SOC, s)]),
                     'origin': 'cited:%s p.1/p.3' % DOC, 'undetermined': '', 'notes': NOTES.get(c, '')})
    return rows


def nets():
    out = [{'name': '%s:%s' % (BOARD, p['net']), 'board': BOARD, 'net': p['net'], 'net_class': 'signal', 'volts': 0.0, 'circuit_net': '',
            'fact': '%s:pinout.%s' % (BOARD, p['canonical']), 'notes': ''} for p in board_pins()]
    volts = {'+5V': 5.0, '+3V3': 3.3}
    for n in ('IOREF', 'RESET', '+3V3', '+5V', 'GND', 'VIN', 'AREF'):
        out.append({'name': '%s:%s' % (BOARD, n), 'board': BOARD, 'net': n,
                    'net_class': 'ground' if n == 'GND' else 'power' if n in ('+5V', '+3V3', 'VIN', 'IOREF') else 'signal',
                    'volts': volts.get(n, 0.0), 'circuit_net': '', 'fact': '%s:pinout.power_header' % BOARD,
                    'notes': {'VIN': '6-20 V input (pinout p.1)', 'IOREF': 'the I/O reference voltage pin — its value is not in the cited sources',
                              'AREF': 'the ADC reference input'}.get(n, '')})
    return out


def connectors():
    out, pins = [], []
    bp = {p['canonical']: p for p in board_pins()}
    for conn, (ref, kind, fp, labels, order) in CONNECTORS.items():
        fkey = {'ICSP': 'pinout.icsp', 'POWER': 'pinout.power_header'}.get(conn, 'pinout.%s' % labels[0])
        out.append({'name': '%s:%s' % (BOARD, conn), 'board': BOARD, 'connector': conn, 'ref': ref, 'kind': kind, 'pin_count': len(labels),
                    'footprint': fp, 'order_note': order if conn == 'ICSP' else '%s; %s' % (order, ORDER_NOTE), 'fact': '%s:%s' % (BOARD, fkey),
                    'notes': 'footprint = a KiCad official library name, not checked against an installed library (no pcb worker yet); ref is ours'})
        for i, lab in enumerate(labels, 1):
            target = SAME_AS.get(lab, lab)
            net = bp[target]['net'] if target in bp else POWER_NETS[lab]
            pk = 'pinout.icsp' if conn == 'ICSP' else 'pinout.%s' % target if target in bp else 'pinout.power_header'
            pins.append({'name': '%s:%s:%d' % (BOARD, conn, i), 'board': BOARD, 'connector': conn, 'number': i, 'label': lab, 'net': net,
                         'board_pin': target if target in bp else '', 'fact': '%s:%s' % (BOARD, pk), 'notes': 'NC — not connected' if lab == 'NC' else ''})
    return out, pins


def hardware(usb_ids_json):
    comps = [{'ref': 'U1', 'value': 'ATmega328P-PU', 'lib': 'MCU_Microchip_ATmega', 'part': 'ATmega328P-P', 'footprint': 'Package_DIP:DIP-28_W7.62mm',
              'role': 'mcu', 'soc': SOC, 'fact': '%s:package.power_pins' % SOC},
             {'ref': 'U2', 'value': 'ATmega16U2', 'lib': '', 'part': '', 'footprint': '', 'role': 'usb-bridge', 'soc': '',
              'fact': '%s:pinout.usb_bridge' % BOARD, 'undetermined': 'package / footprint not in the cited sources'}]
    comps += [{'ref': r, 'value': c, 'lib': 'Connector', 'part': '', 'footprint': fp, 'role': 'connector', 'connector': c}
              for c, (r, _, fp, _, _) in CONNECTORS.items()]
    return {'name': BOARD, 'board': BOARD, 'components_json': json.dumps(comps),
            'power_rails_json': json.dumps([{'net': '+5V', 'volts': 5.0}, {'net': '+3V3', 'volts': 3.3, 'max_ma': 50, 'fact': '%s:pinout.max_current_3v3' % BOARD},
                                            {'net': 'VIN', 'volts': '6-20', 'fact': '%s:pinout.vin_range' % BOARD}, {'net': 'GND', 'volts': 0.0}]),
            'crystal': '16 MHz (boards.txt build.f_cpu, fact arduino-uno-r3:build.f_cpu) — crystal vs ceramic resonator is not in the cited sources',
            'usb_bridge_chip': 'ATmega16U2', 'usb_ids_json': usb_ids_json,
            'facts_json': json.dumps(['%s:pinout.usb_bridge' % BOARD, '%s:usb_serial_chip' % BOARD, '%s:build.f_cpu' % BOARD]),
            'source': 'cited: %s + boards.txt + the ATmega328P datasheet' % DOC,
            'undetermined': 'the 16U2 package and footprint; the 328P clock part (crystal or resonator); IOREF\'s voltage; the reset/power circuit (the UNO schematic was not read)',
            'notes': 'reference designators U1/U2/J1–J5 are OURS (the Arduino schematic\'s refs were not read); the 16U2 is the board\'s USB identity: '
                     'the VID:PIDs it enumerates as are the Identity row\'s usb_ids_json (boards.txt uno.vid/pid)'}


def runtime_profiles():
    base = {'board': BOARD, 'stack_bytes': 0, 'heap_bytes': 0, 'twin': '', 'clock_hz': 16000000, 'tick_hz': 0, 'notes': ''}
    no = dict(base, supported=False, peripherals_json='[]', console_uart='', config_json='[]', origin='')
    return [dict(base, name='%s:bare-c' % BOARD, runtime='bare-c', supported=True, refusal='',
                 peripherals_json=json.dumps([{'name': 'USART0', 'use': 'the SimRigState frames, 115200 Bd (UBRR0 16, U2X0)', 'fact': '%s:usart0.ubrr_115200_u2x1' % BOARD},
                                              {'name': 'TIMER0', 'use': 'PWM on PWM_PIN (D5/D6)'},
                                              {'name': 'TIMER2', 'use': 'the 1 ms tick (hal.c, CTC clk/128)', 'reserved': True},
                                              {'name': 'ADC', 'use': 'ADC_CHANNEL, AVcc reference', 'fact': '%s:adc.conversion_result' % BOARD}]),
                 console_uart='none (USART0 carries the frames)', config_json=json.dumps(['-mmcu=atmega328p', '-DF_CPU=16000000UL']),
                 twin='simavr:atmega328p', origin='brd-1 hal.c + board.custom.build CFLAGS',
                 notes='no kernel: one main loop + ISRs; the stack grows down from RAMEND and is not sized (the build counts static RAM only)'),
            dict(no, name='%s:freertos' % BOARD, runtime='freertos',
                 refusal='an S-class board (2 KB SRAM): a kernel plus per-task stacks do not fit (HARDWARE_NOCODE_PLAN §3 rule 1 — the rule hwnocode\'s knob applies)'),
            dict(no, name='%s:esp-idf' % BOARD, runtime='esp-idf', refusal='ESP-IDF targets Espressif SoCs only; the ATmega328P is not one'),
            dict(no, name='%s:zephyr' % BOARD, runtime='zephyr', origin='zephyr v4.4.2 arch/ listing (2026-10-03)',
                 refusal='no Zephyr target for the ATmega328P: Zephyr v4.4.2 has no AVR architecture (its arch/ holds arc, arm, arm64, mips, openrisc, '
                         'posix, riscv, rx, sparc, x86, xtensa — https://github.com/zephyrproject-rtos/zephyr/tree/v4.4.2/arch)')]
