"""hal_needs_selftest (hal-iso, HAL_CATOM_CATALOGUE_PLAN.md §5a) — what the hardware GIVES an isotope, per need.

- The level triggers are answered per chip from cited rules: the 328P has low (ISCn = 00) and LACKS high (cited); the C3 has both.
- Every need gets a verdict, and the three "no" verdicts are kept apart: chip-lacks (a cited chip fact), not-recorded (a gap in OUR
  tables: proved with a control that hides a role), refused.
- The isotope's own names (HAL_BUTTON_..., from its variable) are the same on every chip, and ONE isotope C source compiles
  unchanged against the header each chip generates for it (avr-gcc through the engine; the host compiler for the C3).
- A header for an isotope a chip cannot host is refused, naming each unmet need. The rows fill every HalIsotopeNeed field.
- The door answers rows and refuses picks that are not pins of the chip.
"""
import inspect
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


class _Req:
    def __init__(self, params=None):
        self._p = params or {}
        self.context = SimpleNamespace(user_info=None)

    def get_param(self, k):
        return self._p.get(k)


class _Resp:
    def __init__(self):
        self.media, self.status = None, '200 OK'


# ONE isotope source, written only against the isotope's own names (never a register, never a chip pin)
ISO_C = ('void sense_init(void) { HAL_SENSE_INPUT(); }\n'
         'unsigned char sense_now(void) { return (unsigned char)HAL_SENSE_READ(); }\n'
         'void button_init(void) { HAL_BUTTON_INPUT(); HAL_BUTTON_PULL_UP(); HAL_BUTTON_LEVEL_ENABLE_LOW(); }\n')
REQS = {'sense_pin': ['gpio.input', 'gpio.read'], 'button_pin': ['gpio.input', 'gpio.pull_up', 'int.level_enable_low']}
PINS = {'atmega328p': {'sense_pin': 'PD3', 'button_pin': 'PD2'}, 'esp32c3': {'sense_pin': 'GPIO1', 'button_pin': 'GPIO3'}}


def main():
    from hal.custom import generate as G
    from hal.custom import needs as N
    from hal.custom import soc_rules as SR
    from hal.objects.hal.HalIsotopeNeed import HalIsotopeNeed
    from hal.hal_api import HalAPI

    print('-- the level triggers, per chip')
    u = G.unit('atmega328p', 'int.level_enable_low', 'PD2')
    check('328P PD2 level low resolves: EICRA.ISC0 = 0 (Table 13-2: 00 = the low level of INT0), flag cleared, INT0 unmasked',
          u['unit']['status'] == 'resolved' and [(b['register'], b['field'], str(b['value'])) for b in u['bindings']][0] == ('EICRA', 'ISC0', '0'),
          [(b['register'], b['field'], b['value']) for b in u['bindings']])
    u = G.unit('atmega328p', 'int.level_enable_high', 'PD2')
    check('328P level high: unsupported, the chip lacks it, cited (Tables 13-1 / 13-2 list four settings)',
          u['unit']['status'] == 'unsupported' and 'no high_level setting' in u['unit']['why'] and 'Tables 13-1' in u['unit']['why'], u['unit']['why'])
    check('the lacks step is in the trace with its cite', any(s['step'] == 'value' and s['output'].startswith('unsupported') for s in u['steps']))
    lv = {op: G.unit('esp32c3', op, 'GPIO3') for op in ('int.level_enable_low', 'int.level_enable_high')}
    check('C3 GPIO3 level low = INT_TYPE 4, high = INT_TYPE 5 (TRM Register 5.14)',
          [str(lv[o]['bindings'][0]['value']) for o in ('int.level_enable_low', 'int.level_enable_high')] == ['4', '5']
          and all(lv[o]['bindings'][0]['field'] == 'INT_TYPE' for o in lv))
    u = G.unit('atmega328p', 'int.level_enable_low', 'PD4')
    check('328P PD4 level low: chip lacks (no INTn function on the pin)', u['unit']['status'] == 'unsupported' and 'INTn' in u['unit']['why'])

    print('-- verdicts per need')
    a = N.rows('read-button', 'ext-interrupt', 'atmega328p', 'PD2')
    check('read-button:ext-interrupt on PD2: every need fits; the vector need yields INT0_vect and signum 0',
          a and all(r['verdict'] == 'fits' for r in a) and any('INT0_vect' in r['yields'] for r in a) and any('signum = 0' in r['yields'] for r in a))
    fe = next(r for r in a if r['operation'] == 'int.edge_enable_falling')
    check('the falling-edge need says what plays it: EICRA.ISC0 = 2 via rmw-field, EIFR.INTF0 via w1c-flag, EIMSK.INT0 via avr-io-bit, with cites',
          fe['settings'] == 'EICRA.ISC0 = 2 via rmw-field; EIFR.INTF0 via w1c-flag; EIMSK.INT0 via avr-io-bit' and '§13.2.1' in fe['cites'], fe['settings'])
    b = N.rows('read-button', 'ext-interrupt', 'esp32c3', 'GPIO3')
    v = {r['operation']: r for r in b}
    check('the same isotope on the C3: the pin needs fit, the per-pin vector is chip-lacks (the interrupt matrix), said why',
          v['int.edge_enable_falling']['verdict'] == 'fits' and v['int.edge_vector']['verdict'] == 'chip-lacks' and 'interrupt matrix' in v['int.edge_vector']['why'])
    c = {r['operation']: r['verdict'] for r in N.rows('read-button', 'ext-interrupt', 'atmega328p', 'PD4')}
    check('on PD4 (no INTn) the edge needs are chip-lacks, the pin needs still fit',
          c['gpio.input'] == 'fits' and c['int.edge_enable_falling'] == 'chip-lacks' and c['int.edge_vector'] == 'chip-lacks', c)
    saved = SR.RULES['esp32c3']['roles'].pop('level_sense')
    try:
        ctl = N.answer('esp32c3', {'button_pin': ['int.level_enable_low']}, {'button_pin': 'GPIO3'})['needs'][0]
    finally:
        SR.RULES['esp32c3']['roles']['level_sense'] = saved
    check('CONTROL: with the C3 level rule hidden, the need reads not-recorded (a gap in our data), never chip-lacks',
          ctl['verdict'] == 'not-recorded', ctl['verdict'])
    check('and with it restored the same need fits',
          N.answer('esp32c3', {'button_pin': ['int.level_enable_low']}, {'button_pin': 'GPIO3'})['needs'][0]['verdict'] == 'fits')
    nopin = N.answer('esp32c3', {'button_pin': ['gpio.input']}, {})['needs'][0]
    check('a need with no pin chosen is refused, said why', nopin['verdict'] == 'refused' and 'no pin chosen' in nopin['why'])

    print('-- the isotope\'s own names, the same C on both chips')
    names = {soc: sorted(n['name'] for n in N.answer(soc, REQS, PINS[soc])['needs']) for soc in PINS}
    check('the need names are identical on both chips (HAL_<ROLE>_<OP>, role from the variable)',
          names['atmega328p'] == names['esp32c3'] and 'HAL_BUTTON_LEVEL_ENABLE_LOW' in names['esp32c3'], names)
    hdr = {soc: N.header(soc, REQS, PINS[soc]) for soc in PINS}
    check('each header holds only the isotope\'s units (5 needs, 5 units) and every need name as a role line',
          all(len(h['units']) == 5 and all(('#define %s(' % n) in h['text'] for n in names[soc]) for soc, h in hdr.items()),
          {s: len(h['units']) for s, h in hdr.items()})
    cc = shutil.which('cc') or shutil.which('gcc')
    if not cc:
        print('  [SKIP] host C compiler for the C3 header: none on PATH')
    else:
        with tempfile.TemporaryDirectory() as d:
            open(d + '/polari_hal_esp32c3.h', 'w').write(hdr['esp32c3']['text'])
            open(d + '/iso.c', 'w').write('#include "polari_hal_esp32c3.h"\n' + ISO_C)
            p = subprocess.run([cc, '-std=c99', '-Wall', '-Werror', '-fsyntax-only', d + '/iso.c'], capture_output=True, text=True)
        check('the isotope C compiles against the C3 header (-std=c99 -Wall -Werror, host %s)' % cc.split('/')[-1], p.returncode == 0, p.stderr[:300])
    try:
        from board.custom import engine_run
        res = engine_run.run('avr-gcc', ['-mmcu=atmega328p', '-Os', '-std=gnu99', '-Wall', '-Werror', '-S', '-o', 'iso.s', 'iso.c'],
                             {'iso.c': ('#include "polari_hal_atmega328p.h"\n' + ISO_C).encode(),
                              'polari_hal_atmega328p.h': hdr['atmega328p']['text'].encode()}, timeout=120)
        asm = (res.get('files') or {}).get('iso.s') or ''
        asm = asm.decode('utf-8', 'replace') if isinstance(asm, bytes) else asm
        why = '' if asm else 'rc %s: %s' % (res.get('returncode'), (res.get('stderr') or '')[:200])
    except Exception as e:  # noqa: BLE001
        asm, why = '', 'engine unavailable: %s' % str(e)[:160]
    if not asm and 'unavailable' in why:
        print('  [SKIP] avr-gcc for the 328P header: %s' % why)
    else:
        check('the SAME isotope C compiles against the 328P header (avr-gcc -Os -Wall -Werror)', bool(asm), why)
        check('and on the 328P the level-low button arms INT0 (EIMSK bit 0 set: sbi 0x1d,0)', 'sbi 0x1d,0' in asm)

    print('-- refusal, rows, door')
    try:
        N.header('esp32c3', {'button_pin': ['gpio.input', 'int.edge_vector']}, {'button_pin': 'GPIO3'})
        refused = ''
    except N.NeedsRefused as e:
        refused = str(e)
    check('a header for a need the chip lacks is refused, naming the need and its verdict',
          'int.edge_vector' in refused and 'chip-lacks' in refused, refused[:200])
    fields = set(inspect.signature(HalIsotopeNeed.__init__).parameters) - {'self', 'manager'}
    check('the rows fill exactly the HalIsotopeNeed fields', all(set(r) == fields for r in a), sorted(set(a[0]) ^ fields))
    api = HalAPI(polServer=None, manager=None)
    rs = _Resp(); api.on_get_isotope_needs(_Req({'soc': 'atmega328p', 'pin': 'PD2'}), rs, 'read-button:ext-interrupt')
    check('/api/hal/isotopes/{key}/needs answers the rows and viable', rs.media['ok'] and rs.media['count'] == 4 and rs.media['viable'] is True, rs.media.get('count'))
    rs = _Resp(); api.on_get_isotope_needs(_Req({'soc': 'atmega328p', 'pin': 'GPIO3'}), rs, 'read-button:ext-interrupt')
    check('a pin of another chip answers no rows with a note', rs.media['rows'] == [] and 'not a pin' in rs.media['note'])
    rs = _Resp(); api.on_get_isotope_needs(_Req({'soc': 'atmega328p'}), rs, 'read-button:ext-interrupt')
    check('nothing picked answers no rows with a note', rs.media['rows'] == [] and rs.media['note'])

    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
