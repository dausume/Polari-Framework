"""hal_selftest (hal-0) — the generalized HAL: the vocabulary and mechanisms seed well-formed; the generator resolves the UNO and
ESP32-C3 GPIO units through the cited tables with the RIGHT access mechanism (port-mapped bit vs set/clear alias vs read-modify-write,
the C3's routing matrix first); refusals are said, never guessed; every step names its source; the same inputs give the same trace;
the cross-checks pass; the header is whole; the doors answer; the page has no raw JSON and reads only its own doors.
Optional engine proof: avr-gcc -Os compiles the UNO header and emits sbi / cbi exactly where the mechanism says (skipped, said, when
no avr engine resolves); the host C compiler syntax-checks the C3 header (skipped, said, when there is none)."""
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra if not cond else ''))


class _Manager:
    def __init__(self):
        self.objectTables, self.db, self.objectTypingDict, self.idList = {}, None, {}, []


class _Req:
    def __init__(self, params=None):
        self._p = params or {}
        self.context = SimpleNamespace(user_info=None)

    def get_param(self, k):
        return self._p.get(k)


class _Resp:
    def __init__(self):
        self.media, self.status = None, '200 OK'


def _u(soc, op, pin, board=''):
    from hal.custom import generate as G
    return G.unit(soc, op, pin, board)


def _engine_proof(header_text):
    """avr-gcc -Os -S over a probe that uses the UNO header -> the assembly, or (None, why)."""
    try:
        from board.custom import engine_run
    except Exception as e:  # noqa: BLE001
        return None, 'board.custom.engine_run unavailable: %s' % e
    probe = ('#include <avr/interrupt.h>\n#include "polari_hal_atmega328p.h"\n'
             'void a(void) { HAL_GPIO_SET_HIGH_PB5(); }\nvoid b(void) { HAL_GPIO_SET_LOW_PB5(); }\n'
             'void c(void) { HAL_GPIO_TOGGLE_PB5(); }\nvoid d(void) { HAL_GPIO_OUTPUT_PB5(); }\nuint8_t e(void) { return HAL_GPIO_READ_PD2(); }\n'
             'void f(void) { HAL_INT_EDGE_ENABLE_PD2_INIT(); }\nvoid g(void) { HAL_INT_PIN_CHANGE_ENABLE_PD4_INIT(); }\n'
             'ISR(HAL_INT_PIN_CHANGE_VECTOR_PD4) { HAL_GPIO_TOGGLE_PB5(); }\n'
             'void h(void) { HAL_GPIO_OUTPUT_PC0(); }\nvoid i(void) { HAL_GPIO_PULL_UP_PC0(); }\n'
             'ISR(HAL_INT_PIN_CHANGE_VECTOR_PC0) { HAL_GPIO_TOGGLE_PB5(); }\n')
    try:
        res = engine_run.run('avr-gcc', ['-mmcu=atmega328p', '-Os', '-S', '-o', 'probe.s', 'probe.c'],
                             {'probe.c': probe.encode(), 'polari_hal_atmega328p.h': header_text.encode()}, timeout=120)
    except Exception as e:  # noqa: BLE001
        return None, 'avr-gcc refused: %s' % str(e)[:160]
    files = res.get('files') or {}
    asm = files.get('probe.s') or ''
    if isinstance(asm, bytes):
        asm = asm.decode('utf-8', 'replace')
    if not asm:
        return None, 'avr-gcc ran (%s) but returned no probe.s (rc %s: %s)' % (res.get('how'), res.get('returncode'), (res.get('stderr') or '')[:160])
    return asm, res.get('how', '')


def _fn_body(asm, fn):
    lines, on = [], False
    for ln in asm.splitlines():
        s = ln.strip()
        if s == '%s:' % fn:
            on = True
            continue
        if on:
            if s.startswith('.size') or s.startswith('.global') or (s.endswith(':') and not s.startswith('.')):
                break
            if s and not s.startswith('.') and not s.startswith('/*'):
                lines.append(' '.join(s.split()))
    return lines


def main():
    from hal import HAL_CLASSES, HAL_SEED_PAIRS, SEED_HAL_PAGE_DISPLAYS
    from hal.hal_api import HalAPI
    from hal.custom import crosscheck as CX
    from hal.custom import generate as G
    from hal.custom import mechanisms as MX
    from hal.custom import operations as OPS
    from hal.custom import render as RD
    from hal.custom import soc_rules as SR

    print('-- seed + vocabulary')
    m = _Manager()
    for _n, cls, rows in HAL_SEED_PAIRS:
        for r in rows:
            cls(**r, manager=m)
    check('six classes; two seeded (operations, mechanisms)', len(HAL_CLASSES) == 6 and [p[0] for p in HAL_SEED_PAIRS] == ['HalOperation', 'HalAccessMechanism'])
    check('23 operations (8 GPIO + 10 interrupt + 5 pwm, hal-3b), every part\'s role and action in the vocabulary',
          len(OPS.OPERATIONS) == 23 and all(p['role'] in OPS.ROLES and p['action'] in OPS.ACTIONS for o in OPS.OPERATIONS for p in OPS.parts(o))
          and all(o['basis'] for o in OPS.OPERATIONS))
    check('every implemented access mechanism has templates for its actions and a cite',
          all(mm['cite'] and (mm['kind'] == 'setup' or not mm.get('implemented', True) or mm['templates']) for mm in MX.MECHANISMS))
    check('the unimplemented mechanisms say so (atomic-alias-window, bit-band)',
          sorted(mm['name'] for mm in MX.MECHANISMS if mm.get('implemented', True) is False) == ['atomic-alias-window', 'bit-band'])

    print('-- ATmega328P (UNO): port-mapped I/O')
    r = _u('atmega328p', 'gpio.set_high', 'D13', 'arduino-uno-r3')
    u = r['unit']
    check('UNO D13 -> PB5 (the board map), keyed by the chip pin', u['key'] == 'atmega328p:gpio.set_high:PB5' and u['board_pin'] == 'D13')
    check('set_high PB5 = PORTB bit 5 via avr-io-bit (I/O 0x05 < 0x20 -> sbi), no guard',
          [b['mechanism'] for b in r['bindings']] == ['avr-io-bit'] and r['bindings'][0]['register'] == 'PORTB' and not u['guarded']
          and u['c_text'] == '#define HAL_GPIO_SET_HIGH_PB5() do { PORTB |= _BV(5); } while (0)', u['c_text'])
    check('the trace has the board-pin step with the Arduino pinout cited',
          any(s['step'] == 'board-pin' and 'A000066' in s['cite'] for s in r['steps']))
    t = _u('atmega328p', 'gpio.toggle', 'PB5')
    check('toggle PB5 = write 1 to PINB5 (toggle-by-input-write, §14.2.2 p.85), not a read-modify-write of PORTB',
          [b['mechanism'] for b in t['bindings']] == ['toggle-by-input-write'] and 'PINB = _BV(5);' in t['unit']['c_text'])
    rd = _u('atmega328p', 'gpio.read', 'PD2')
    check('read PD2 = bit 2 of PIND (read-bit)', rd['unit']['c_text'] == '#define HAL_GPIO_READ_PD2() (uint8_t)((PIND & _BV(2)) != 0u)', rd['unit']['c_text'])
    pd = _u('atmega328p', 'gpio.pull_down', 'PD2')['unit']
    check('pull_down on the 328P is UNSUPPORTED, said why (pull-up only)', pd['status'] == 'unsupported' and 'pull-up only' in pd['why'])
    pc = _u('atmega328p', 'gpio.output', 'PC0')
    check('Port C is cited (§14.4.6 DDRC, p.100): output PC0 = DDRC bit 0', pc['unit']['status'] == 'resolved'
          and pc['unit']['c_text'] == '#define HAL_GPIO_OUTPUT_PC0() do { DDRC |= _BV(0); } while (0)'
          and any(s['step'] == 'field' and '§14.4.6 DDRC, p.100' in s['cite'] for s in pc['steps']), pc['unit'])
    rd = _u('atmega328p', 'gpio.read', 'PC3')['unit']
    check('read PC3 = PINC bit 3', rd['c_text'] == '#define HAL_GPIO_READ_PC3() (uint8_t)((PINC & _BV(3)) != 0u)', rd)
    p6 = _u('atmega328p', 'gpio.set_high', 'PC6')
    check('PC6 resolves but says it is RESET unless RSTDISBL (Table 14-6), in the unit and in the soc-pin step',
          p6['unit']['status'] == 'resolved' and 'RSTDISBL' in p6['unit']['why']
          and any(s['step'] == 'soc-pin' and 'caveat' in s['output'] for s in p6['steps']), p6['unit'])
    check('Port C has no bit 7 (reserved): PC7 is refused as no pin', _u('atmega328p', 'gpio.output', 'PC7')['unit']['status'] == 'refused')
    pu = _u('atmega328p', 'gpio.pull_up', 'PD2')
    check('pull_up PD2 = PORTD bit 2 with the input condition stated', pu['unit']['status'] == 'resolved'
          and any(s['step'] == 'role' and 'must be an input' in s['output'] for s in pu['steps']))

    print('-- ESP32-C3: memory-mapped, set/clear aliases, routing matrix')
    o = _u('esp32c3', 'gpio.output', 'GPIO8')
    bs = o['bindings']
    check('output GPIO8 = 3 bindings in order: OUT_SEL=128, MCU_SEL=1 (routing), then ENABLE_W1TS bit 8',
          [(b['register'], b['field'], b['value']) for b in bs] == [('GPIO_FUNC8_OUT_SEL_CFG_REG', 'OUT_SEL', '128'), ('IO_MUX_GPIO8_REG', 'MCU_SEL', '1'),
                                                                   ('GPIO_ENABLE_W1TS_REG', 'ENABLE_W1TS_8', '')], [(b['register'], b['field'], b['value']) for b in bs])
    check('the routing writes are rmw-field via the matrix; the enable is a w1s-alias',
          [b['mechanism'] for b in bs] == ['signal-routing-matrix / rmw-field'] * 2 + ['w1s-alias'])
    check('addresses from the TRM base + offset (0x60004574, 0x60009024, 0x60004024)',
          [b['address'] for b in bs] == ['0x60004574', '0x60009024', '0x60004024'])
    h = _u('esp32c3', 'gpio.set_high', 'GPIO8')
    check('set_high GPIO8 = one write to GPIO_OUT_W1TS (w1s-alias), no guard',
          [b['mechanism'] for b in h['bindings']] == ['w1s-alias'] and not h['unit']['guarded'] and '0x60004008u) = (1UL << 8);' in h['unit']['c_text'])
    lo = _u('esp32c3', 'gpio.set_low', 'GPIO8')
    check('set_low GPIO8 = GPIO_OUT_W1TC (w1c-alias)', [b['mechanism'] for b in lo['bindings']] == ['w1c-alias'] and '0x6000400Cu' in lo['unit']['c_text'])
    tg = _u('esp32c3', 'gpio.toggle', 'GPIO8')
    check('toggle GPIO8: no toggle alias on the C3 -> mem-rmw xor of GPIO_OUT, guarded',
          [b['mechanism'] for b in tg['bindings']] == ['mem-rmw'] and tg['unit']['guarded'] and 'POLARI_HAL_ATOMIC(' in tg['unit']['c_text'])
    check('pull_up GPIO9 = IO_MUX FUN_WPU', [b['field'] for b in _u('esp32c3', 'gpio.pull_up', 'GPIO9')['bindings']] == ['FUN_WPU'])

    print('-- interrupts (hal-1): parts, yields, vectors, init forms')
    pc = _u('atmega328p', 'int.pin_change_enable', 'PD4')
    check('pin-change enable PD4 = PCMSK2.PCINT20 set, PCIFR.PCIF2 clear, PCICR.PCIE2 set (bank 2 yielded by PCMSK2)',
          [(b['register'], b['field']) for b in pc['bindings']] == [('PCMSK2', 'PCINT20'), ('PCIFR', 'PCIF2'), ('PCICR', 'PCIE2')]
          and any(s['step'] == 'yield' and 'bank = 2' in s['output'] for s in pc['steps']))
    check('mechanisms: mem-rmw (PCMSK2 at data 0x6D), w1c-flag (PCIFR), mem-rmw (PCICR at 0x68): guarded, with an unguarded _INIT form',
          [b['mechanism'] for b in pc['bindings']] == ['mem-rmw', 'w1c-flag', 'mem-rmw'] and pc['unit']['guarded']
          and pc['unit']['c_text_init'] == '#define HAL_INT_PIN_CHANGE_ENABLE_PD4_INIT() do { PCMSK2 |= _BV(4); PCIFR = _BV(2); PCICR |= _BV(2); } while (0)',
          pc['unit']['c_text_init'])
    check('the pin-change vector of PD4 is PCINT2_vect (avr-libc vector 5)',
          _u('atmega328p', 'int.pin_change_vector', 'PD4')['unit']['c_text'] == '#define HAL_INT_PIN_CHANGE_VECTOR_PD4 PCINT2_vect')
    ee = _u('atmega328p', 'int.edge_enable', 'PD2')
    check('edge enable PD2 (INT0, matched by signal) = EICRA.ISC0 = 1 (any change), EIFR.INTF0 clear, EIMSK.INT0 set',
          [(b['register'], b['field'], b['value']) for b in ee['bindings']] == [('EICRA', 'ISC0', '1'), ('EIFR', 'INTF0', ''), ('EIMSK', 'INT0', '')]
          and [b['mechanism'] for b in ee['bindings']] == ['rmw-field', 'w1c-flag', 'avr-io-bit'])
    fe = _u('atmega328p', 'int.edge_enable_falling', 'PD2')
    check('falling-edge enable PD2 = EICRA.ISC0 = 2 (Table 13-2: 10 = falling) - what hal.c\'s INT0 button writes by hand',
          [(b['register'], b['field'], b['value']) for b in fe['bindings']][0] == ('EICRA', 'ISC0', '2')
          and fe['unit']['c_text_init'] == '#define HAL_INT_EDGE_ENABLE_FALLING_PD2_INIT() do { EICRA = (EICRA & ~(uint8_t)0x03) | (uint8_t)(2u << 0); EIFR = _BV(0); EIMSK |= _BV(0); } while (0)',
          fe['unit']['c_text_init'])
    check('C3 rising edge on GPIO9 = INT_TYPE 1', _u('esp32c3', 'int.edge_enable_rising', 'GPIO9')['bindings'][0]['value'] == '1')
    check('the edge vector of PD3 is INT1_vect', _u('atmega328p', 'int.edge_vector', 'PD3')['unit']['c_text'] == '#define HAL_INT_EDGE_VECTOR_PD3 INT1_vect')
    nx = _u('atmega328p', 'int.edge_enable', 'PD4')['unit']
    check('edge enable on PD4 is UNSUPPORTED: it has no INTn function (said, with its functions)', nx['status'] == 'unsupported' and 'PCINT20' in nx['why'])
    c3e = _u('esp32c3', 'int.edge_enable', 'GPIO9')
    check('C3 edge enable GPIO9 = GPIO_PIN9.INT_TYPE = 3, STATUS_W1TC bit 9, GPIO_PIN9.INT_ENA = 1 (bit 13)',
          [(b['register'], b['field'], b['value']) for b in c3e['bindings']] == [('GPIO_PIN9_REG', 'INT_TYPE', '3'), ('GPIO_STATUS_W1TC_REG', 'STATUS_W1TC_9', ''),
                                                                                ('GPIO_PIN9_REG', 'INT_ENA', '1')])
    c3v = _u('esp32c3', 'int.edge_vector', 'GPIO9')['unit']
    check('C3 vectors are UNSUPPORTED, said why (interrupt matrix, ESP-IDF attaches the handler)', c3v['status'] == 'unsupported' and 'INTMTX' in c3v['why'])

    print('-- every unit: refusals said, steps sourced, deterministic, mechanisms implemented')
    allu = {soc: [G.unit(soc, op['name'], p) for p in G.default_pins(soc) for op in OPS.OPERATIONS] for soc in SR.SOCS}
    gpio = {soc: [x for x in v if x['unit']['operation'].startswith('gpio.')] for soc, v in allu.items()}
    flat = [x for v in allu.values() for x in v]
    check('every unit is resolved or refused WITH a reason', all(x['unit']['status'] == 'resolved' or x['unit']['why'] for x in flat))
    check('every step names the module its data came from', all(s['source'] for x in flat for s in x['steps']))
    check('every resolved binding cites its datasheet / TRM place', all(b['cite'] for x in flat if x['unit']['status'] == 'resolved' for b in x['bindings']))
    check('every mechanism used is implemented', all(MX.by_name(b['mechanism'].split(' / ')[-1]).get('implemented', True)
                                                     for x in flat for b in x['bindings'] if b['mechanism']))
    check('the same inputs give the same trace digest', _u('esp32c3', 'gpio.output', 'GPIO8')['unit']['steps_sha256'] == o['unit']['steps_sha256'])
    n328 = [x for x in allu['atmega328p'] if x['unit']['status'] == 'resolved']
    nc3 = [x for x in allu['esp32c3'] if x['unit']['status'] == 'resolved']
    g328 = [x for x in gpio['atmega328p'] if x['unit']['status'] == 'resolved']
    check('GPIO coverage: the UNO resolves 7 ops x 23 pins (Ports B, C, D), the C3 8 ops x 22 pads',
          len(g328) == 7 * 23 and len([x for x in gpio['esp32c3'] if x['unit']['status'] == 'resolved']) == 8 * 22)
    check('interrupt coverage: UNO 4 pin-change ops x 23 pins + 6 edge ops x 2 (PD2 INT0, PD3 INT1) = 104; C3 8 ops x 22 = 176 (no vectors)',
          len([x for x in n328 if OPS.by_name(x['unit']['operation'])['family'] == 'interrupt']) == 104 and len(nc3) - 8 * 22 == 176,
          '%d / %d' % (len([x for x in n328 if OPS.by_name(x['unit']['operation'])['family'] == 'interrupt']), len(nc3) - 176))

    print('-- cross-checks')
    ck = [c for x in n328 for c in CX.checks(x)]
    check('AVR: avr-libc address == the datasheet\'s printed data address wherever the datasheet prints one (no fail)',
          ck and not [c for c in ck if c['result'] == 'fail'] and any(c['result'] == 'pass' for c in ck))
    check('PORTB: 0x25 both ways', any(c['subject'] == 'PORTB address' and c['result'] == 'pass' and c['first'] == '0x25' for c in ck))
    check('C3: the recorded ESP-IDF check is cited, said as recorded', all(c['result'] == 'recorded' for c in CX.checks(o)))

    print('-- levels + header')
    lv = RD.levels(r)
    check('levels top to bottom: operation, board pin, chip pin, binding, mechanism, C, macro, final file',
          [x['level'] for x in lv] == [1, 2, 3, 4, 5, 6, 7, 8] and lv[-1]['code'].startswith('polari_hal_atmega328p.h line'))
    hdr = RD.header('atmega328p', [x['unit']['key'] for x in n328])
    check('the UNO header: guard, SPDX, every resolved macro exactly once',
          hdr['text'].startswith('/* SPDX-License-Identifier: GPL-3.0-or-later */') and '#ifndef POLARI_HAL_ATMEGA328P_H' in hdr['text']
          and all(hdr['text'].count(x['unit']['c_text']) == 1 for x in n328))
    check('every header line that is code belongs to a unit', all(ln['unit'] for ln in hdr['lines'] if ln['text'].startswith('#define HAL_')))
    hc3 = RD.header('esp32c3', [x['unit']['key'] for x in nc3])
    check('the C3 header defines POLARI_HAL_ATOMIC once (default: the bare statement)', hc3['text'].count('#define POLARI_HAL_ATOMIC') == 1)

    print('-- doors + page')
    api = HalAPI(polServer=None, manager=m)
    rs = _Resp(); api.on_get_units(_Req(), rs, 'atmega328p')
    check('/api/hal/socs/atmega328p/units: one row per op x pin (18 x 23), 7 x 23 gpio + 104 interrupt resolved',
          rs.media['ok'] and rs.media['count'] == 23 * 23 and rs.media['resolved'] == 7 * 23 + 104 + 29, (rs.media['count'], rs.media['resolved']))
    rs = _Resp(); api.on_get_units(_Req({'board': 'arduino-uno-r3', 'pins': 'D13,D2'}), rs, 'atmega328p')
    check('?board=&pins= reads board pins', rs.media['count'] == 46 and rs.media['rows'][0]['board_pin'] == 'D13')
    for view in ('steps', 'levels', 'bindings', 'checks'):
        rs = _Resp(); api.on_get_unit(_Req({'view': view}), rs, 'esp32c3:gpio.output:GPIO8')
        check('/api/hal/units/{key}?view=%s answers rows' % view, rs.media['ok'] and rs.media['count'] > 0)
    rs = _Resp(); api.on_get_unit(_Req({'view': 'steps'}), rs, '')
    check('an empty key (nothing picked) answers no rows with a note', rs.media['ok'] and rs.media['rows'] == [] and rs.media['note'])
    rs = _Resp(); api.on_get_unit(_Req(), rs, 'nonsense')
    check('a malformed key is 422', rs.status.startswith('422'))
    rs = _Resp(); api.on_get_units(_Req(), rs, 'z80')
    check('an unknown soc is 422', rs.status.startswith('422'))
    rs = _Resp(); api.on_get_header(_Req(), rs, 'esp32c3')
    check('hal-1: /api/hal/socs/esp32c3/header with nothing picked renders NO header (the catalogue is never one file), with a note',
          rs.media['ok'] and rs.media['rows'] == [] and rs.media['units'] == 0 and 'firmware' in rs.media['note'])
    rs = _Resp(); api.on_get_header(_Req({'pins': 'GPIO8'}), rs, 'esp32c3')
    check('/api/hal/socs/esp32c3/header?pins=GPIO8 previews just that pin: the file + its lines',
          rs.media['ok'] and 0 < rs.media['units'] < 30 and rs.media['rows'][0]['line'] == 1, rs.media.get('units'))
    rs = _Resp(); api.on_get_operations(_Req(), rs)
    check('/api/hal/operations reads the loaded rows', rs.media['from'] == 'rows' and rs.media['count'] == 23)
    page = SEED_HAL_PAGE_DISPLAYS[0]
    import json as _j
    blob = page['definition']
    page = dict(page, definition=_j.loads(page['definition']))
    check('the page has no raw JSON panel', 'api-json-panel' not in blob)
    paths = [it['componentProps']['inputs'].get('dataPath', '') for tab in page['definition']['tabs'] for row in tab['rows'] for it in row['items']]
    check('every API-backed table reads a /api/hal door', all(p.startswith('/api/hal/') for p in paths if p) and len([p for p in paths if p]) == 15, len(paths))
    check('the page is linkable to one unit, isotope or firmware (scope_query)', page['definition'].get('scope_from_query') == ['unit', 'isotope', 'firmware'])
    tabs = [t.get('name') or t.get('key') or t.get('id') for t in page['definition']['tabs']]
    check('hal-1 (the user): Operations and Access mechanisms are the first two tabs; the chip tabs are catalogues; no per-chip header tab',
          tabs[:2] == ['operations', 'mechanisms'] and not any(str(t).endswith('-header') for t in tabs) and 'firmware' in tabs, tabs)

    print('-- firmware headers (hal-1) + uno/hal.c on the HAL (hal-3a)')
    from board.custom import gen as BG
    rs = _Resp(); api.on_get_firmware(_Req(), rs)
    fw = {r['variant']: r for r in rs.media['rows']}
    check('/api/hal/firmware: one row per firmware variant, each header only what THAT build needs - uno-light 9 units (hal.c led_pin + '
          'button_pin, sense:poll sense_pin), uno-light-all-pcint 12, uno-echo none (said why)',
          fw['uno-light']['units'] == 9 and fw['uno-light']['required_by'] == 'hal.c button_pin, hal.c led_pin, sense:poll sense_pin'
          and fw['uno-light-all-pcint']['units'] == 12 and fw['uno-echo']['units'] == 0 and 'no HAL units' in fw['uno-echo']['why'],
          {k: (v['units'], v['required_by']) for k, v in fw.items()})
    rs = _Resp(); api.on_get_firmware_header(_Req(), rs, 'uno-light')
    built = BG.hal_header_for('uno-light')['header']
    check('the page shows EXACTLY the header the build writes (gen.render_routes, the one function gen() and the page share)',
          rs.media['text'] == built['text'] and rs.media['units'] == 9, rs.media.get('units'))
    check('hal-3a: the header names the ROLES hal.c calls, each pointing at this build\'s unit (HAL_LED_SET_HIGH -> PD6, the INT0 vector by name)',
          '#define HAL_LED_SET_HIGH() HAL_GPIO_SET_HIGH_PD6()' in built['text'] and '#define HAL_BUTTON_EDGE_VECTOR HAL_INT_EDGE_VECTOR_PD2' in built['text']
          and '#define HAL_BUTTON_EDGE_ENABLE_FALLING() HAL_INT_EDGE_ENABLE_FALLING_PD2_INIT()' in built['text'])
    check('every unit line of that header says who required it',
          all(ln['required_by'] for ln in rs.media['rows'] if ln['unit'] and ln['text'].startswith('#define HAL_GPIO')))
    check('a firmware header holds a small slice of the catalogue, never the whole chip',
          rs.media['units'] < len(n328) // 10, len(n328))
    import os as _os
    uno_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'board', 'custom', 'firmware', 'uno')
    src = open(_os.path.join(uno_dir, 'hal.c')).read()
    import re as _re
    check('hal-3a: uno/hal.c writes no pin register by hand any more (no DDRx / PORTx / PINx / EICRA / EIFR / EIMSK statement): every pin goes through a role',
          not _re.search(r'^\s*(DDR[BCD]|PORT[BCD]|EICRA|EIFR|EIMSK)\s*[|&]?=', src, _re.M) and 'PIND &' not in src)
    check('the template\'s own polari_hal_atmega328p.h is the uno-sim-rig build\'s (as its board_config.h is): no drift',
          open(_os.path.join(uno_dir, 'polari_hal_atmega328p.h')).read() == BG.hal_header_for('uno-sim-rig')['header']['text'])
    import json as _jj
    from firmwarefaults.custom.scenarios import scenario_variants as _SVS
    from board.custom import variants as _V
    _pins = BG.board_pins('uno')[0]
    _bc = dict(next(x for x in _SVS() if x['name'] == 'uno-button-count'))
    _roles = [b['role'] + ':' + b['pin'] for b in BG.base_roles(_V.resolve(_bc, {}, base=_pins))]
    _k = _jj.loads(_bc['knobs_json']); _k['button_pin'] = 7
    try:
        _V.resolve(dict(_bc, knobs_json=_jj.dumps(_k)), {}, base=_pins); _refused = ''
    except _V.VariantRefused as e:
        _refused = str(e)
    check('the build-flag INT0 path (uno-button-count, HAL_INT0=1) gets its BUTTON role on D2; button_pin 7 on that path is REFUSED in words '
          '(hal.c\'s INT0 block is hardware-fixed to D2: the header must never put the button on another pin while the ISR listens on D2)',
          'BUTTON:PD2' in _roles and 'hardware-fixed to D2' in _refused, (_roles, _refused[-120:]))
    rs = _Resp(); api.on_get_firmware_header(_Req(), rs, 'uno-echo')
    check('a firmware with no HAL units answers no rows and says why', rs.media['rows'] == [] and 'no HAL units' in rs.media['note'])
    rs = _Resp(); api.on_get_firmware_header(_Req(), rs, 'no-such-firmware')
    check('an unknown firmware is 422 in words', rs.status.startswith('422'))

    print('-- pwm family (hal-3b: args, composite fields, derived values, wide access, fail-closed)')
    def _ct(op, pin):
        x = G.unit('atmega328p', op, pin)['unit']
        return x['status'], x.get('c_text_init') or x.get('c_text') or x.get('why', '')
    st, txt = _ct('pwm.init_fast', 'PD6')
    check('pwm.init_fast on D6 (OC0A): Timer0, the cited mode table gives fast PWM 8-bit = mode 3 (WGM01:00 = 11 in TCCR0A, WGM02 = 0 in '
          'TCCR0B), the clock code is DERIVED from Table 15-9 as a C conditional over the prescaler argument',
          st == 'resolved' and '(uint8_t)(3u << 0)' in txt and '(uint8_t)(0u << 3)' in txt and '== 64u ? 3u' in txt and '(prescaler)' in txt, txt[:200])
    st, txt = _ct('pwm.init_fast', 'PB1')
    check('pwm.init_fast on D9 (OC1A): Timer1, fast PWM 8-bit = mode 5 split WGM11:10 = 01 / WGM13:12 = 01 (Table 16-4)',
          st == 'resolved' and 'TCCR1A' in txt and '(uint8_t)(1u << 0)' in txt and '(uint8_t)(1u << 3)' in txt, txt[:200])
    st, txt = _ct('pwm.init_phase', 'PB3')
    check('pwm.init_phase on D11 (OC2A): Timer2\'s OWN clock table (Table 18-9) has /32 and /128, so /128 -> 5 there (Timer0/1 have no /128)',
          st == 'resolved' and '== 128u ? 5u' in txt and '== 32u ? 3u' in txt, txt[:200])
    st, txt = 'resolved', G.unit('atmega328p', 'pwm.set_duty', 'PB1')['unit']['c_text']
    check('pwm.set_duty on D9 writes the 16-bit OCR1A through its wide symbol (TEMP: guarded), on D6 one store to OCR0A',
          st == 'resolved' and 'OCR1A = (uint16_t)' in txt and 'ATOMIC_BLOCK' in txt and _ct('pwm.set_duty', 'PD6')[1].endswith('OCR0A = (uint8_t)((level)); } while (0)'), txt)
    check('pwm on D2 is unsupported (no OCnx function, said); pwm.set_duty on D3 is undetermined (OCR2B not cited yet: a table gap, never a guess)',
          _ct('pwm.connect', 'PD2')[0] == 'unsupported' and _ct('pwm.set_duty', 'PD3')[0] == 'undetermined')
    pu = G.unit('atmega328p', 'pwm.set_duty', 'PD6')
    check('the 328P\'s pwm_update role is INHERENT (OCRnx double-buffered by the timer): nothing emitted, and the trace says why',
          any(st_['output'].startswith('inherent:') for st_ in pu['steps']))
    keys = ['atmega328p:pwm.init_fast:PD6', 'atmega328p:pwm.connect:PD6', 'atmega328p:pwm.set_duty:PD6', 'atmega328p:pwm.init_fast:PB1',
            'atmega328p:pwm.set_duty:PB1', 'atmega328p:pwm.init_phase:PB3']
    hp = RD.header('atmega328p', keys)
    good = ('#include <avr/io.h>\n#include "polari_hal_atmega328p.h"\n'
            'void a(void){ HAL_PWM_INIT_FAST_PD6_INIT(64u); HAL_PWM_CONNECT_PD6_INIT(); }\nvoid b(uint8_t x){ HAL_PWM_SET_DUTY_PD6(x); }\n'
            'void c(void){ HAL_PWM_INIT_FAST_PB1_INIT(64u); }\nvoid d(uint16_t x){ HAL_PWM_SET_DUTY_PB1(x); }\nvoid e(void){ HAL_PWM_INIT_PHASE_PB3_INIT(128u); }\n')
    try:
        from board.custom import engine_run as _ER
        def _cc(src):
            r_ = _ER.run('avr-gcc', ['-mmcu=atmega328p', '-Os', '-std=gnu99', '-Wall', '-Werror', '-S', '-o', 'p.s', 'p.c'],
                         {'p.c': src.encode(), 'polari_hal_atmega328p.h': hp['text'].encode()}, timeout=120)
            a_ = (r_.get('files') or {}).get('p.s') or b''
            return r_.get('returncode'), a_.decode() if isinstance(a_, bytes) else a_
        rc, asm = _cc(good)
    except Exception as e:  # noqa: BLE001
        rc, asm = None, str(e)
    if rc is None:
        print('  [SKIP] avr-gcc proof of the pwm units: %s' % asm[:160])
    else:
        fa, fb, fd = ('\n'.join(_fn_body(asm, x)) for x in 'abd')
        check('avr-gcc (-Wall -Werror): D6 fast PWM /64 + connect = TCCR0A |= 3, TCCR0B WGM02 cleared + CS0 = 3, COM0A = 10 (andi 63 / ori -128); '
              'the duty is ONE out to OCR0A (0x27); D9\'s 16-bit duty writes the high byte (136+1) before the low, with interrupts off',
              rc == 0 and 'ori r24,lo8(3)' in fa and 'andi r24,lo8(63)' in fa and 'ori r24,lo8(-128)' in fa and fb.strip().splitlines()[0].strip() == 'out 0x27,r24'
              and 'cli' in fd and fd.index('136+1') < fd.index('sts 136,'), (fa[:200], fb[:80], fd[:200]))
        rc2, _ = _cc(good + 'void z(void){ HAL_PWM_INIT_FAST_PD6_INIT(100u); }\n')
        check('an unlisted prescaler (100) does NOT COMPILE: the derived divider is a negative array size, never a silent wrong clock code',
              rc2 not in (0, None), rc2)

    print('-- the access table + chip independence (hal-3b slice 2a, econ\'s review)')
    from hal.custom import mechanisms as _MX
    def _ch(action, acc, **kw):
        f = dict({'action': action, 'access': acc, 'width': 1, 'space': 'mem', 'io_addr': None, 'reg_width': 32, 'lo': 0, 'bit_instr_window': None}, **kw)
        return _MX.choose(f)[0]
    check('econ\'s probes, fixed: write + rw-sc -> field-write; clear + r-w1c -> w1c-flag (a store of the mask); clear + w with a clear-by-store role '
          '-> w1c-flag; write + fifo -> w-store and read_value + fifo -> read-reg (by action)',
          _ch('write', 'rw-sc', width=1, lo=31) == 'field-write' and _ch('clear', 'r-w1c') == 'w1c-flag' and _ch('clear', 'w', clear_by_store=True) == 'w1c-flag'
          and _ch('write', 'fifo', width=8) == 'w-store' and _ch('read_value', 'fifo', width=8) == 'read-reg')
    check('fail closed: strobe on a plain w is REFUSED (self-clear not known), strobe on w-strobe -> strobe, clear on a plain w without the role is '
          'refused, any action on `missing` is refused',
          _ch('strobe', 'w') is None and _ch('strobe', 'w-strobe') == 'strobe' and _ch('clear', 'w') is None
          and all(_ch(a_, 'missing') is None for a_ in ('set', 'clear', 'read', 'write', 'read_value')))
    check('no 8-bit default: a whole-register store needs the field to span reg_width (an 8-bit field at lo 0 of a 32-bit register is a field-write)',
          _ch('write', 'rw', width=8, lo=0, reg_width=32) == 'field-write' and _ch('write', 'rw', width=32, lo=0, reg_width=32) == 'reg-write')
    check('the AVR single-bit window is a CHIP FACT: with no bit_instr_window an I/O-space bit is a mem-rmw, with the 328P\'s it is avr-io-bit',
          _ch('set', 'rw', space='io', io_addr=0x05) == 'mem-rmw'
          and _ch('set', 'rw', space='io', io_addr=0x05, bit_instr_window=SR.RULES['atmega328p']['c']['bit_instr_window']) == 'avr-io-bit')
    # rows shaped exactly as econ's hal-c3-rows (trm_access verbatim, the lossy word beside it); the real rows fold in at the 88
    # integration, where this same table reads them
    _row = lambda code, lossy='rw', **kw: dict({'register': 'R', 'field': 'F', 'access': lossy, 'trm_access': code}, **kw)
    check('the access table reads the CITED code, never the lossy word: R/W/SC -> rw-sc (LEDC DUTY_START), R/SS/WTC and R/WTC/SS -> r-w1c '
          '(SYSTIMER VALUE_VALID, UART INT_RAW), WT -> w-strobe, WO -> w, RO -> r; an empty code (TICK_SEL, review queue) and an unknown '
          'code -> missing; an alias / FIFO register keeps its specific word (GPIO_OUT_W1TS w1-set, UART_FIFO fifo); own RTL\'s access_word wins',
          SR.access_word(_row('R/W/SC'))[0] == 'rw-sc' and SR.access_word(_row('R/SS/WTC', 'r'))[0] == 'r-w1c'
          and SR.access_word(_row('R/WTC/SS', 'r'))[0] == 'r-w1c' and SR.access_word(_row('WT', 'w-strobe'))[0] == 'w-strobe'
          and SR.access_word(_row('WO', 'w-strobe'))[0] == 'w' and SR.access_word(_row('RO', 'r'))[0] == 'r'
          and SR.access_word(_row('', 'rw'))[0] == 'missing' and SR.access_word(_row('R/WC/SS'))[0] == 'missing'
          and SR.access_word(_row('WT', 'w1-set'))[0] == 'w1-set' and SR.access_word(_row('RO', 'fifo'))[0] == 'fifo'
          and SR.access_word(_row('', '', access_word='w-strobe', access_source='rdl', access_cite='toy.rdl line 27'))[0] == 'w-strobe'
          and SR.access_word({'access': 'w1c'})[0] == 'w1c')
    check('the C3 provider serves its rows through the access table, and its existing units are unchanged (GPIO_OUT_W1TS stays w1-set)',
          next(x for x in SR.fields('esp32c3') if x['register'] == 'GPIO_OUT_W1TS_REG')['access'] == 'w1-set'
          and all('access_why' in x for x in SR.fields('esp32c3')))
    zu = G.unit('toychip', 'gpio.output', 'PA0')['unit']
    check('an UNKNOWN soc is refused in words (no implicit else: a third chip never gets another chip\'s fields, addresses or pads)',
          zu['status'] == 'refused' and 'no HAL provider' in zu['why'], zu['why'])

    print('-- isotope fit (hal-2)')
    from hal.custom import isotopes as ISO
    rs = _Resp(); api.on_get_isotopes(_Req(), rs)
    pci = next(r for r in rs.media['rows'] if r['key'] == 'read-button:pin-change-interrupt')
    check('read-button/pin-change-interrupt requires 5 HAL operations on button_pin and fits all 23 UNO chip pins (Port C cited)',
          pci['requires'].count(',') == 4 and pci['atmega328p_fits'] == '23 of 23 pins', pci)
    check('isotopes not yet written against the HAL say so', any(r['atmega328p_fits'] == 'not written against the HAL yet' for r in rs.media['rows']))
    rs = _Resp(); api.on_get_isotope_fit(_Req({'soc': 'esp32c3'}), rs, 'read-button:pin-change-interrupt')
    check('on the C3 it fits no pad, and the only missing operation is the vector (interrupt matrix: an ESP-IDF isotope is the way)',
          rs.media['fits'] == 0 and {r['missing'] for r in rs.media['rows']} == {'int.pin_change_vector'})
    rs = _Resp(); api.on_get_isotope_fit(_Req({'soc': 'atmega328p'}), rs, '')
    check('an empty isotope key answers no rows with a note', rs.media['rows'] == [] and rs.media['note'])

    print('-- engine proof (optional)')
    asm, how = _engine_proof(RD.header('atmega328p', [x['unit']['key'] for x in n328])['text'])
    if asm is None:
        print('  [SKIP] avr-gcc compile of the UNO header: %s' % how)
    else:
        check('avr-gcc -Os (%s): set_high PB5 = one sbi 0x5,5' % how, _fn_body(asm, 'a')[:1] == ['sbi 0x5,5'], _fn_body(asm, 'a'))
        check('set_low PB5 = one cbi 0x5,5', _fn_body(asm, 'b')[:1] == ['cbi 0x5,5'], _fn_body(asm, 'b'))
        check('toggle PB5 = a write to PINB (out 0x3)', any(x.startswith('out 0x3,') for x in _fn_body(asm, 'c')), _fn_body(asm, 'c'))
        check('output PB5 = one sbi 0x4,5 (DDRB)', _fn_body(asm, 'd')[:1] == ['sbi 0x4,5'], _fn_body(asm, 'd'))
        f = _fn_body(asm, 'f')
        check('edge enable PD2 init: EIMSK.INT0 set = one sbi 0x1d,0 (I/O 0x1D < 0x20)', 'sbi 0x1d,0' in f, f)
        g = _fn_body(asm, 'g')
        def at(addr):   # avr-gcc reaches data-space registers by lds/sts (0x6d) or through Z (lo8(109))
            return any(('0x%x' % addr) in x or ('lo8(%d)' % addr) in x for x in g)
        check('pin-change enable PD4 init: PCMSK2 (0x6D) and PCICR (0x68) read-modify-written in data space, PCIFR by one out 0x1b',
              at(0x6D) and at(0x68) and any(x.startswith('out 0x1b,') for x in g), g)
        check('ISR(HAL_INT_PIN_CHANGE_VECTOR_PD4) compiles to the PCINT2 vector (__vector_5)', '__vector_5:' in asm)
        check('Port C: output PC0 = one sbi 0x7,0 (DDRC, §14.4.6)', _fn_body(asm, 'h')[:1] == ['sbi 0x7,0'], _fn_body(asm, 'h'))
        check('Port C: pull_up PC0 = one sbi 0x8,0 (PORTC, §14.4.5)', 'sbi 0x8,0' in _fn_body(asm, 'i'), _fn_body(asm, 'i'))
        check('ISR(HAL_INT_PIN_CHANGE_VECTOR_PC0) compiles to the PCINT1 vector (__vector_4)', '__vector_4:' in asm)
    cc = shutil.which('cc') or shutil.which('gcc')
    if not cc:
        print('  [SKIP] host C compiler for the C3 header: none on PATH')
    else:
        with tempfile.TemporaryDirectory() as d:
            open(d + '/polari_hal_esp32c3.h', 'w').write(hc3['text'])
            open(d + '/probe.c', 'w').write('#include "polari_hal_esp32c3.h"\nvoid a(void){HAL_GPIO_OUTPUT_GPIO8(); HAL_GPIO_SET_HIGH_GPIO8(); '
                                            'HAL_GPIO_TOGGLE_GPIO8();}\nunsigned char b(void){return HAL_GPIO_READ_GPIO8();}\n')
            p = subprocess.run([cc, '-std=c99', '-Wall', '-Werror', '-fsyntax-only', d + '/probe.c'], capture_output=True, text=True)
        check('the C3 header compiles clean (-std=c99 -Wall -Werror, syntax only, host %s)' % cc.split('/')[-1], p.returncode == 0, p.stderr[:300])

    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
