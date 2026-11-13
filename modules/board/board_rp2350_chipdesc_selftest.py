"""board_rp2350_chipdesc_selftest - hal-4 proof 2: the RP2350 (Hazard3 RISC-V side) gets GPIO units from the UNCHANGED generator, read
only from Raspberry Pi's own CMSIS-SVD (pico-sdk 2.2.0, BSD-3-Clause; the GPIO extract in custom/evidence/rp2350) through
board.custom.chipdesc_rp2350 -> board.custom.chipdesc_provider. Every registration is undone.

    PYTHONPATH=.:modules python3 -m board.board_rp2350_chipdesc_selftest      # from polari-framework/ (standalone)
"""
import hashlib

_results = []
EXTRACT_SHA = '615d14a0046866d3af48294e221c0199ea2715f6566b33fc2f7c548599e88387'


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  ' + str(extra)[:300]) if (extra and not cond) else ''))


def run():
    from board.custom import chipdesc_provider as CP
    from board.custom import chipdesc_rp2350 as RP
    from hal.custom import generate as G
    from hal.custom import render as RD
    from hal.custom import soc_rules as SR
    before = (sorted(SR.PROVIDERS), sorted(SR.RULES), sorted(SR.DOCS))
    raw = open(RP.SVD, 'rb').read()
    check('the committed extract is the one recorded (sha256 %s...) and keeps the vendor\'s BSD-3-Clause SPDX header and its source sha' % EXTRACT_SHA[:12],
          hashlib.sha256(raw).hexdigest() == EXTRACT_SHA and b'SPDX-License-Identifier: BSD-3-Clause' in raw[:400]
          and b'f1180d39bbc0e7c01b1a418bc61493c8450e25732f33bf2b0df381255078014c' in raw[:1200], hashlib.sha256(raw).hexdigest())
    R, F, bases = RP.rows()
    check('the bases are the SVD\'s own: SIO 0xD0000000, IO_BANK0 0x40028000, PADS_BANK0 0x40038000',
          bases == {'SIO': 0xD0000000, 'IO_BANK0': 0x40028000, 'PADS_BANK0': 0x40038000}, {k: hex(v) for k, v in bases.items()})
    acc = {(f['register'], f['field']): (f['access_word'], f['access_source']) for f in F}
    check('access words: the four SET / CLR aliases from their own SVD description text (svd-description), GPIO_OUT / GPIO_OE rw and GPIO_IN r '
          'from the SVD, the XOR aliases plain w (no HAL word for an atomic xor yet)',
          acc[('SIO_GPIO_OUT_SET_REG', 'GPIO_OUT_SET')] == ('w1-set', 'svd-description') and acc[('SIO_GPIO_OUT_CLR_REG', 'GPIO_OUT_CLR')] == ('w1-clear', 'svd-description')
          and acc[('SIO_GPIO_OE_SET_REG', 'GPIO_OE_SET')] == ('w1-set', 'svd-description') and acc[('SIO_GPIO_OE_CLR_REG', 'GPIO_OE_CLR')] == ('w1-clear', 'svd-description')
          and acc[('SIO_GPIO_OUT_REG', 'GPIO_OUT')] == ('rw', 'svd') and acc[('SIO_GPIO_IN_REG', 'GPIO_IN')] == ('r', 'svd')
          and acc[('SIO_GPIO_OUT_XOR_REG', 'GPIO_OUT_XOR')] == ('w', 'svd'), acc)
    refused = []
    for label, FF in (('changed text', [dict(f, description='Perform a bit-set') if f['field'] == 'GPIO_OUT_SET' else f for f in F]),
                      ('missing alias', [f for f in F if f['field'] != 'GPIO_OE_CLR'])):
        try:
            RP.refine(FF)
            refused.append('NOT refused')
        except RP.Rp2350Refused as e:
            refused.append(str(e))
    check('an alias whose SVD text is not the cited text, or a missing alias, is refused, not guessed',
          'refused, not guessed' in refused[0] and 'GPIO_OE_CLR' in refused[1], refused)
    try:
        CP.register('rp2350', R, F, RP.meta(bases))
        u = {op: G.unit('rp2350', op, 'GPIO25') for op in ('gpio.set_high', 'gpio.set_low', 'gpio.toggle', 'gpio.output', 'gpio.input', 'gpio.read')}
        st = {op: x['unit']['status'] for op, x in u.items()}
        check('registered, the UNCHANGED generator resolves all six GPIO operations on GPIO25', set(st.values()) == {'resolved'}, st)
        ct = {op: x['unit']['c_text'] for op, x in u.items()}
        check('set_high / set_low are ONE store to the atomic aliases (no read, no guard): GPIO_OUT_SET 0xD0000018, GPIO_OUT_CLR 0xD0000020',
              ct['gpio.set_high'] == '#define HAL_GPIO_SET_HIGH_GPIO25() do { (*(volatile uint32_t *)0xD0000018u) = (1UL << 25); } while (0)'
              and ct['gpio.set_low'] == '#define HAL_GPIO_SET_LOW_GPIO25() do { (*(volatile uint32_t *)0xD0000020u) = (1UL << 25); } while (0)', ct)
        check('toggle falls through to GPIO_OUT (0xD0000010) read-modify-write under the guard - correct, not atomic: the XOR alias has no HAL word yet',
              [b['mechanism'] for b in u['gpio.toggle']['bindings']] == ['mem-rmw'] and '0xD0000010u) ^= (1UL << 25)' in ct['gpio.toggle'] and 'POLARI_HAL_ATOMIC' in ct['gpio.toggle'])
        out = [(b['register'], b['field'], b['address']) for b in u['gpio.output']['bindings']]
        check('output = setup FUNCSEL 5 (SIO) at IO_BANK0 GPIO25_CTRL 0x400280CC, release ISO at PADS GPIO25 0x40038068, then OE_SET 0xD0000038 - in that order',
              out == [('IO_BANK0_GPIO25_CTRL_REG', 'FUNCSEL', '0x400280CC'), ('PADS_BANK0_GPIO25_REG', 'ISO', '0x40038068'), ('SIO_GPIO_OE_SET_REG', 'GPIO_OE_SET_25', '0xD0000038')], out)
        inp = [(b['register'], b['field'], b['value']) for b in u['gpio.input']['bindings']]
        check('input = FUNCSEL 5, IE 1, ISO 0, then OE_CLR (0xD0000040)', inp == [('IO_BANK0_GPIO25_CTRL_REG', 'FUNCSEL', '5'), ('PADS_BANK0_GPIO25_REG', 'IE', '1'),
                                                                               ('PADS_BANK0_GPIO25_REG', 'ISO', '0'), ('SIO_GPIO_OE_CLR_REG', 'GPIO_OE_CLR_25', '')], inp)
        check('read = bit 25 of GPIO_IN (0xD0000004)', ct['gpio.read'] == '#define HAL_GPIO_READ_GPIO25() (uint8_t)(((*(volatile uint32_t *)0xD0000004u) & (1UL << 25)) != 0u)', ct['gpio.read'])
        g0 = G.unit('rp2350', 'gpio.set_high', 'GPIO0')['unit']
        check('every pin is its own bit: GPIO0 -> (1UL << 0) at the same alias; PB5 (another chip\'s pin) is refused',
              g0['status'] == 'resolved' and '(1UL << 0)' in g0['c_text'] and G.unit('rp2350', 'gpio.set_high', 'PB5')['unit']['status'] == 'refused')
        h = RD.header('rp2350', [G.key('rp2350', o, 'GPIO25') for o in u])
        check('render.header writes polari_hal_rp2350.h with all six macros, "Facts from:" the vendor SVD, nothing refused',
              not h['refused'] and all(('HAL_%s_GPIO25(' % o.upper().replace('.', '_')) in h['text'] for o in u) and 'Facts from: board.custom.svd_import(Raspberry Pi pico-sdk 2.2.0' in h['text'],
              h['refused'])
    finally:
        CP.unregister('rp2350')
    after = (sorted(SR.PROVIDERS), sorted(SR.RULES), sorted(SR.DOCS))
    check('every registration undone (%s)' % ', '.join(after[0]), after == before and SR.socs() == SR.SOCS, (before, after))
    total, ok = len(_results), sum(_results)
    print('\n%d/%d checks passed' % (ok, total))
    return ok == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if run() else 1)
