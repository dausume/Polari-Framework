"""board_chipdesc_provider_selftest - hal-4: a chip that exists only as a chip description gets HAL units from the UNCHANGED generator.
toyperiph (custom/evidence/toy_rtl, our own-RTL stand-in) is read by board.custom.rdl_import, registered by board.custom.chipdesc_provider
as a third soc beside the ATmega328P and the ESP32-C3 (pol's provider interface, hal.custom.soc_rules), and hal.custom.generate /
render produce its units and header. The same chip registered from the SVD path gives the same code wherever an SVD can say the same
thing, and refuses the strobe it cannot know. Every registration is undone: the built-in providers are exactly as before.

    PYTHONPATH=.:modules python3 -m board.board_chipdesc_provider_selftest      # from polari-framework/ (standalone)
"""
import os

_results = []
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom', 'evidence', 'toy_rtl')
RDL = 'toyperiph.rdl'


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  ' + str(extra)[:300]) if (extra and not cond) else ''))


def meta():
    """the HAND-WRITTEN, cited part of toyperiph's chip description: identity, C facts, pins, roles (plan §4d)"""
    return {'title': 'toyperiph (own-RTL stand-in)', 'arch': 'riscv', 'reg_width': 32, 'base': 0x40000000,
            'source': 'board.custom.rdl_import(%s)' % RDL, 'cite': 'toyperiph: the stand-in places it at 0x40000000 (a hand-written fact of this test chip)',
            'pins': {'TOY_OUT%d' % k: ('TOYPERIPH_GPIO_OUT_REG', 'OUT', k) for k in range(8)},
            'roles': {'output': {'registers': ['TOYPERIPH_GPIO_OUT_REG'], 'cite': '%s line 10: gpio_out.out[8], sw = rw (one bit per pin TOY_OUT0-7)' % RDL},
                      'direction': {'registers': [], 'cite': '', 'missing': 'toyperiph has no direction register: TOY_OUT0-7 are outputs only (%s)' % RDL},
                      'input': {'registers': [], 'cite': '', 'missing': 'toyperiph has no input register (%s)' % RDL}},
            'c': {'ctype': 'uint32_t', 'mask': '(1UL << {bit})', 'field_forms': {'fmask': '0x{m:X}UL', 'fval': '((uint32_t){v} << {lo})'},
                  'includes': ['<stdint.h>'], 'header_includes': [], 'access_style': 'address',
                  'prelude': ['#ifndef POLARI_HAL_ATOMIC', '/* {guard_why} */', '#define POLARI_HAL_ATOMIC(stmt) do {{ stmt }} while (0)', '#endif'],
                  'guard': 'POLARI_HAL_ATOMIC(%s);', 'guard_include': '',
                  'guard_why': 'POLARI_HAL_ATOMIC defaults to the bare statement; a firmware whose ISR shares the register defines it as a critical section',
                  'init_rule': 'an _INIT form drops the guard', 'init_cite': 'the caller decides'}}


def _rdl_rows():
    from board.custom import rdl_import as D
    R, F, _left = D.rows(D.load(os.path.join(HERE, RDL)), block='TOYPERIPH', prefix='TOYPERIPH')
    return R, F


def _svd_rows():
    from board.custom import access_overlay as O
    from board.custom import svd_import as S
    R, F = S.rows(S.load(os.path.join(HERE, 'toyperiph.expected.svd')), 'TOYPERIPH', block='TOYPERIPH', name_prefix='TOYPERIPH')
    return R, O.apply_svd(F)[0]


def run():
    from board.custom import chipdesc_provider as CP
    from hal.custom import generate as G
    from hal.custom import mechanisms as MX
    from hal.custom import render as RD
    from hal.custom import soc_rules as SR
    before = (sorted(SR.PROVIDERS), sorted(SR.RULES), sorted(SR.DOCS))
    u0 = G.unit('toyperiph', 'gpio.set_high', 'TOY_OUT3')['unit']
    check('before registration the generator refuses the chip in words (no default provider)', u0['status'] == 'refused' and 'no HAL provider' in u0['why'], u0['why'])
    from hal.custom import crosscheck as CX
    R, F = _rdl_rows()
    R2, F2 = _svd_rows()
    try:
        CP.register('toyperiph', R, F, dict(meta(), second_source={'fields': F2, 'source': 'board.custom.svd_import(toyperiph.expected.svd) + access_overlay'}))
        check('the registered chip is listed and documented through the interface: SR.socs() has it, SR.doc() is its chip description, SR.DOCS is untouched',
              'toyperiph' in SR.socs() and SR.doc('toyperiph') == meta()['source'] and 'toyperiph' not in SR.DOCS, (SR.socs(), SR.doc('toyperiph')))
        u = {(op, pin): G.unit('toyperiph', op, pin)['unit'] for op, pin in (('gpio.set_high', 'TOY_OUT3'), ('gpio.set_low', 'TOY_OUT0'), ('gpio.toggle', 'TOY_OUT7'),
                                                                             ('gpio.output', 'TOY_OUT3'), ('gpio.read', 'TOY_OUT3'), ('gpio.set_high', 'PB5'))}
        hi = u[('gpio.set_high', 'TOY_OUT3')]
        check('registered from the RDL, the UNCHANGED generator resolves gpio.set_high TOY_OUT3 -> a guarded read-modify-write of bit 3 at 0x40000000',
              hi['status'] == 'resolved' and hi['c_text'] == '#define HAL_GPIO_SET_HIGH_TOY_OUT3() do { POLARI_HAL_ATOMIC((*(volatile uint32_t *)0x40000000u) |= (1UL << 3);); } while (0)',
              hi['c_text'] or hi['why'])
        check('set_low TOY_OUT0 and toggle TOY_OUT7 resolve too (&= ~, ^=)', u[('gpio.set_low', 'TOY_OUT0')]['status'] == 'resolved'
              and '&= ~(1UL << 0)' in u[('gpio.set_low', 'TOY_OUT0')]['c_text'] and '^= (1UL << 7)' in u[('gpio.toggle', 'TOY_OUT7')]['c_text'])
        check('what the chip does not have is unsupported, in the chip description\'s words: gpio.output (no direction register), gpio.read (no input register)',
              u[('gpio.output', 'TOY_OUT3')]['status'] == 'unsupported' and 'no direction register' in u[('gpio.output', 'TOY_OUT3')]['why']
              and u[('gpio.read', 'TOY_OUT3')]['status'] == 'unsupported' and 'no input register' in u[('gpio.read', 'TOY_OUT3')]['why'])
        check('another chip\'s pin is refused (PB5 is not a toyperiph pin)', u[('gpio.set_high', 'PB5')]['status'] == 'refused', u[('gpio.set_high', 'PB5')]['why'])
        h = RD.header('toyperiph', [G.key('toyperiph', 'gpio.set_high', 'TOY_OUT3'), G.key('toyperiph', 'gpio.toggle', 'TOY_OUT7')])
        check('render.header writes polari_hal_toyperiph.h: the C facts from the chip description (stdint, POLARI_HAL_ATOMIC prelude), both macros',
              '#include <stdint.h>' in h['text'] and '#define POLARI_HAL_ATOMIC(stmt)' in h['text'] and 'HAL_GPIO_SET_HIGH_TOY_OUT3()' in h['text']
              and 'HAL_GPIO_TOGGLE_TOY_OUT7()' in h['text'] and not h['refused'], h['refused'])
        check('the header\'s "Facts from:" line names the chip description (SR.doc), not a copied cite',
              ' * Chip: toyperiph (own-RTL stand-in). Facts from: %s.' % meta()['source'] in h['text'], [l for l in h['text'].splitlines() if 'Facts from' in l])
        cx = CX.checks(G.unit('toyperiph', 'gpio.set_high', 'TOY_OUT3'))
        check('crosscheck: the RDL and the SVD agree on set_high TOY_OUT3\'s field (bit 3 of OUT, rw) -> one pass row naming both sources',
              len(cx) == 1 and cx[0]['result'] == 'pass' and 'svd_import' in cx[0]['second_source'] and 'rdl_import' in cx[0]['first_source']
              and cx[0]['second'].startswith('TOYPERIPH_GPIO_OUT_REG.OUT bits 7-0 rw'), cx)
        go = next(f for f in SR.fields('toyperiph') if f['field'] == 'GO')
        xgo = SR.PROVIDERS['toyperiph']['crosscheck']({'key': 'probe'}, {'register': go['register'], 'field': 'GO', 'bit_lo': go['bit_lo'],
                                                                       'bit_hi': go['bit_hi'], 'access': go['access']})
        xno = SR.PROVIDERS['toyperiph']['crosscheck']({'key': 'probe'}, {'register': 'TOYPERIPH_GPIO_OUT_REG', 'field': 'X', 'bit_lo': 8, 'bit_hi': 8, 'access': 'rw'})
        check('...and says where they differ: GO is w-strobe from the RDL but w from the SVD -> fail, "access: w there, w-strobe here"; bits the SVD lacks -> no-second-source',
              xgo['result'] == 'fail' and 'access: w there, w-strobe here' in xgo['why'] and xno['result'] == 'no-second-source', (xgo, xno))
        rows = {(f['register'], f['field']): f for f in SR.fields('toyperiph')}
        words = {k[1]: f['access'] for k, f in rows.items() if k[1] in ('OUT', 'DONE', 'GO', 'START', 'COUNT', 'OUT_3')}
        check('the access table reads the RDL\'s words: OUT / OUT_3 rw, DONE r-w1c, GO w-strobe, START rw-sc, COUNT r (the lossy word is not used)',
              words == {'OUT': 'rw', 'OUT_3': 'rw', 'DONE': 'r-w1c', 'GO': 'w-strobe', 'START': 'rw-sc', 'COUNT': 'r'}, words)
        out3 = rows[('TOYPERIPH_GPIO_OUT_REG', 'OUT_3')]
        check('a pin\'s view is one bit of the declared field, cited as such (OUT_3 = bit 3 of OUT, affects_pin TOY_OUT3, reset bit 3)',
              (out3['bit_lo'], out3['width'], out3['affects_pin'], out3['reset_value']) == (3, 1, 'TOY_OUT3', '0') and 'bit 3 of TOYPERIPH_GPIO_OUT_REG.OUT' in out3['page_table'])
        base = {'arch': 'riscv', 'space': 'mem', 'io_addr': None, 'reg_width': 32, 'bit_instr_window': None, 'clear_by_store': False}
        def pick(field, action):
            f = rows[('TOYPERIPH_%s_REG' % field[0], field[1])]
            return MX.choose(dict(base, action=action, access=f['access'], width=f['width'], lo=f['bit_lo']))[0]
        mech = {'clear DONE': pick(('STATUS', 'DONE'), 'clear'), 'strobe GO': pick(('CMD', 'GO'), 'strobe'), 'write START': pick(('CTRL', 'START'), 'write'),
                'read_value COUNT': pick(('COUNT', 'COUNT'), 'read_value'), 'read DONE': pick(('STATUS', 'DONE'), 'read')}
        check('choose() over the RDL\'s words: clear DONE -> w1c-flag, strobe GO -> strobe, write START -> field-write, read_value COUNT -> read-reg / read-field, '
              'read DONE -> read-bit', mech['clear DONE'] == 'w1c-flag' and mech['strobe GO'] == 'strobe' and mech['write START'] == 'field-write'
              and mech['read_value COUNT'] in ('read-field', 'read-reg') and mech['read DONE'] == 'read-bit', mech)
        CP.register('toyperiph_svd', R2, F2, dict(meta(), title='toyperiph via its SVD', source='board.custom.svd_import(toyperiph.expected.svd)'))
        hi2 = G.unit('toyperiph_svd', 'gpio.set_high', 'TOY_OUT3')['unit']
        check('the same chip registered from the SVD path gives the SAME code where an SVD can say the same thing (set_high TOY_OUT3)',
              hi2['status'] == 'resolved' and hi2['c_text'].replace('TOYPERIPH', '') == hi['c_text'].replace('TOYPERIPH', ''), hi2['c_text'] or hi2['why'])
        check('a chip registered with no second source has no crosscheck fn and gets no rows (never another chip\'s rule)',
              'crosscheck' not in SR.PROVIDERS['toyperiph_svd'] and CX.checks(G.unit('toyperiph_svd', 'gpio.set_high', 'TOY_OUT3')) == [])
        go2 = next(f for f in SR.fields('toyperiph_svd') if f['field'] == 'GO')
        check('...and the strobe it cannot know stays refused: from the SVD, GO is w, and choose(strobe, w) refuses (decision ii)',
              go2['access'] == 'w' and MX.choose(dict(base, action='strobe', access='w', width=1, lo=0))[0] is None)
        refusals = []
        for label, m in (('a missing meta fact (reg_width)', {k: v for k, v in meta().items() if k != 'reg_width'}),
                         ('a missing C fact (ctype)', dict(meta(), c={k: v for k, v in meta()['c'].items() if k != 'ctype'})),
                         ('a pin on a field the chip does not have', dict(meta(), pins={'X': ('TOYPERIPH_GPIO_OUT_REG', 'NOPE', 0)})),
                         ('a pin bit outside its field', dict(meta(), pins={'X': ('TOYPERIPH_GPIO_OUT_REG', 'OUT', 8)}))):
            try:
                CP.provider_parts('toyx', R, F, m)
                refusals.append((label, 'NOT refused'))
            except CP.ChipdescRefused as e:
                refusals.append((label, str(e)))
        check('refused in words: a missing meta fact, a missing C fact (never copied from another chip), a pin on an unknown field, a pin bit outside its field',
              all(r != 'NOT refused' for _l, r in refusals) and 'reg_width' in refusals[0][1] and 'c.ctype' in refusals[1][1]
              and 'NOPE' in refusals[2][1] and 'bit 8' in refusals[3][1], refusals)
        try:
            CP.register('toyperiph', R, F, meta())
            dup = 'NOT refused'
        except CP.ChipdescRefused as e:
            dup = str(e)
        try:
            CP.unregister('esp32c3')
            builtin = 'NOT refused'
        except CP.ChipdescRefused as e:
            builtin = str(e)
        check('a chip is never silently replaced (a second toyperiph is refused) and a built-in provider cannot be unregistered',
              'already registered' in dup and 'built-in' in builtin, (dup, builtin))
    finally:
        CP.unregister('toyperiph')
        CP.unregister('toyperiph_svd')
    check('unregistered chips leave SR.socs() as the built-ins', SR.socs() == SR.SOCS, SR.socs())
    after = (sorted(SR.PROVIDERS), sorted(SR.RULES), sorted(SR.DOCS))
    check('every registration undone: PROVIDERS / RULES / DOCS are exactly as before (%s)' % ', '.join(after[0]), after == before, (before, after))
    total, ok = len(_results), sum(_results)
    print('\n%d/%d checks passed' % (ok, total))
    return ok == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if run() else 1)
