"""
@module hal.custom.crosscheck

EXISTING HALs AS CROSS-REFERENCES (hal-0; the user 2026-11-11: "we can use existing ones as a cross reference"). For each
binding of a unit, one HalCrossCheck row per fact a second, independent source also states:

  atmega328p  register address: avr-libc's <avr/io.h> (the snapshot, I/O address + 0x20 for I/O space) against the data-space
              address the datasheet prints beside the register (board.custom.register_fields_atmega328p.REGISTER_CITES).
              Two different documents, compared here on every read.
  esp32c3     every field's position was checked against ESP-IDF v5.5.5 components/soc/esp32c3/register/soc/*.h when it was read
              (rm-2b, board.custom.registers_esp32c3's docstring). That RECORDED check is cited, not re-run (the IDF headers are not
              in this repo).

Planned second sources (hal-2): ArduinoCore-avr variants/standard/pins_arduino.h (board pin -> port / bit / timer / PCINT) and
ESP-IDF soc/gpio_reg.h addresses, both read into committed, cited snapshots.
"""
from hal.custom import soc_rules as SR


def checks(res):
    u = res['unit'] or {}
    out = []
    for b in res['bindings']:
        if u.get('soc') == 'atmega328p':
            ds = SR.datasheet_data_address(b['register'])
            if not ds:
                out.append({'unit': u['key'], 'subject': '%s address' % b['register'], 'first': b['address'],
                            'first_source': 'avr-libc <avr/io.h> snapshot', 'second': '', 'second_source': 'DS40002061B register section',
                            'result': 'no-second-source', 'why': 'the datasheet section cited for %s prints no data-space address' % b['register']})
                continue
            same = int(ds, 16) == int(b['address'], 16)
            out.append({'unit': u['key'], 'subject': '%s address' % b['register'], 'first': b['address'],
                        'first_source': 'avr-libc <avr/io.h> snapshot (I/O + 0x20)', 'second': ds,
                        'second_source': 'DS40002061B %s' % (SR.F328.REGISTER_CITES[b['register']][1]),
                        'result': 'pass' if same else 'fail', 'why': '' if same else 'the two sources disagree'})
        elif u.get('soc') == 'esp32c3':
            out.append({'unit': u['key'], 'subject': '%s.%s position' % (b['register'], b['field']),
                        'first': 'bits %d-%d @ %s' % (b['bit_hi'], b['bit_lo'], b['address']), 'first_source': 'TRM v1.4 (%s)' % b['cite'],
                        'second': 'ESP-IDF v5.5.5 components/soc/esp32c3/register/soc/*.h',
                        'second_source': 'recorded when the TRM rows were read (rm-2b, board.custom.registers_esp32c3)',
                        'result': 'recorded', 'why': 'cited, not re-run here: the IDF headers are not in this repo'})
    return out
