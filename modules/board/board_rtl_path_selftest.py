"""board_rtl_path_selftest - hal-4: the "our own RTL" path. custom/evidence/toy_rtl/toyperiph.rdl (SystemRDL, one field of each access kind)
is read DIRECTLY by board.custom.rdl_import (a reader for the SystemRDL subset our RTL uses; anything outside it refused in words), and every
field gets its HAL access word from the RDL alone, cited to its line: go -> w-strobe (singlepulse), done -> r-w1c (woclr). pol's decision
2026-11-13: own silicon is read from SystemRDL, because CMSIS-SVD has no singlepulse form. toyperiph.expected.svd (HAND-WRITTEN: the SVD we
expect peakrdl-cmsis to emit; regenerate with the real tool and diff once installing PeakRDL is allowed) is the cross-check that the two
paths agree on everything an SVD CAN say - and from the SVD alone go is only a plain store 'w'.

    PYTHONPATH=.:modules python3 -m board.board_rtl_path_selftest      # from polari-framework/ (standalone)
"""
import os
import re
import tempfile

_results = []
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom', 'evidence', 'toy_rtl')


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  ' + str(extra)[:300]) if (extra and not cond) else ''))


def agree(rdl_rows, svd_rows):
    """the RDL path vs the SVD path on everything an SVD can say: the same registers at the same offsets, the same fields at the same bits
    with the same reset, and access words that agree - where the RDL says w-strobe the SVD can only say w (no singlepulse form), and
    where it says rw-sc the SVD can only say rw (no hwclr form)
    -> [] or the differences"""
    (rr, rf), (sr, sf) = rdl_rows, svd_rows
    why = []
    ro, so = {r['register']: r['offset'] for r in rr}, {r['register']: r['offset'] for r in sr}
    if ro != so:
        why.append('registers / offsets differ: %s vs %s' % (sorted(ro.items()), sorted(so.items())))
    a = {(f['register'], f['field']): f for f in rf}
    b = {(f['register'], f['field']): f for f in sf}
    for k in sorted(set(a) | set(b)):
        x, y = a.get(k), b.get(k)
        if not x or not y:
            why.append('%s.%s only in the %s path' % (k[0], k[1], 'RDL' if x else 'SVD'))
            continue
        if (x['bit_lo'], x['width'], x['reset_value']) != (y['bit_lo'], y['width'], y['reset_value']):
            why.append('%s.%s bits / reset %s vs %s' % (k[0], k[1], (x['bit_lo'], x['width'], x['reset_value']), (y['bit_lo'], y['width'], y['reset_value'])))
        if not (x['access_word'] == y['access_word'] or (x['access_word'], y['access_word']) in (('w-strobe', 'w'), ('rw-sc', 'rw'))):
            why.append('%s.%s access RDL %s vs SVD %s' % (k[0], k[1], x['access_word'], y['access_word']))
    return why


def _load(text):
    from board.custom import svd_import as S
    fd, path = tempfile.mkstemp(suffix='.svd')
    with os.fdopen(fd, 'w') as fh:
        fh.write(text)
    try:
        return S.load(path)
    finally:
        os.unlink(path)


def _rdl(text):
    from board.custom import rdl_import as D
    fd, path = tempfile.mkstemp(suffix='.rdl')
    with os.fdopen(fd, 'w') as fh:
        fh.write(text)
    try:
        return D.load(path)
    finally:
        os.unlink(path)


def _refused(text, words):
    from board.custom import rdl_import as D
    try:
        _rdl(text)
    except D.RdlRefused as e:
        return words in str(e)
    return False


UNIT = """// a comment
addrmap unit { /* block comment */
    default sw = rw;
    reg { field { desc = "a"; } a[4] = 4'h9; field { sw = r; } b[4] = 'd3; field { } c[8:8]; } r0 @ 0x0;
    reg { field { sw = rw; hwclr; onwrite = woclr; } wc[4:4] = 0; field { sw = r; hwclr; } rh[5:5] = 0;
          field { sw = rw; onread = rclr; } rc[0:0] = 0; field { sw = rw; singlepulse; } sp[1:1] = 0;
          field { sw = rw; onwrite = woset; } ws[2:2] = 0; field { sw = w; singlepulse = true; } go[3:3] = 0; } r1 @ 0x4;
    reg { regwidth = 16; field { sw = r; } v[15:0] = 0x1234; } arr[3] @ 0x10 += 0x8;
};
"""


def unit():
    from board.custom import rdl_import as D
    a = _rdl(UNIT)
    regs = {r['register']: r for r in a['registers']}
    r0 = {f['field']: f for f in regs['R0']['fields']}
    check('comments are skipped; a WIDTH-only field is packed at the next free bit (lsb0): a[3:0], b[7:4], then c[8:8] given explicitly',
          [(r0[k]['bit_hi'], r0[k]['bit_lo']) for k in ('A', 'B', 'C')] == [(3, 0), (7, 4), (8, 8)], r0)
    check('numbers: 4\'h9 -> 9, \'d3 -> 3, 0x1234; a field with no reset says so (never a number)',
          (r0['A']['reset_value'], r0['B']['reset_value'], regs['ARR0']['fields'][0]['reset_value']) == ('9', '3', '4660')
          and r0['C']['reset_value'].startswith('undefined'), (r0['A']['reset_value'], r0['B']['reset_value'], r0['C']['reset_value']))
    check('`default sw = rw` applies to fields that do not set sw (a, c), a field\'s own wins (b sw = r)', (r0['A']['sw'], r0['B']['sw'], r0['C']['sw']) == ('rw', 'r', 'rw'))
    check('an array reg arr[3] @ 0x10 += 0x8 -> ARR0 / ARR1 / ARR2 at 0x10 / 0x18 / 0x20, regwidth 16 kept',
          [(regs['ARR%d' % i]['offset'], regs['ARR%d' % i]['regwidth']) for i in range(3)] == [(0x10, 16), (0x18, 16), (0x20, 16)])
    R, F, left = D.rows(a, block='U', prefix='U')
    w = {(f['register'], f['field']): f['access_word'] for f in F}
    lw = {(x['register'], x['field']): x['why'] for x in left}
    check('access words: sw = w + singlepulse -> w-strobe; sw = r -> r; sw = rw -> rw (each cited to its RDL line)',
          w[('U_R1_REG', 'GO')] == 'w-strobe' and w[('U_R0_REG', 'B')] == 'r' and w[('U_R0_REG', 'A')] == 'rw'
          and all(f['access_cite'].startswith('tmp') or '.rdl line' in f['access_cite'] for f in F if f['access_word']), w)
    check('NO word, said: onread = rclr (a read side effect), singlepulse on a READABLE field, onwrite = woset (no agreed word yet)',
          set(lw) == {('U_R1_REG', 'RC'), ('U_R1_REG', 'SP'), ('U_R1_REG', 'WS')} and w[('U_R1_REG', 'WC')] == 'r-w1c' and w[('U_R1_REG', 'RH')] == 'r' and 'onread = rclr' in lw[('U_R1_REG', 'RC')]
          and 'only a write-only singlepulse' in lw[('U_R1_REG', 'SP')] and 'woset' in lw[('U_R1_REG', 'WS')], lw)
    good = 'addrmap m { reg { field { } f[0:0] = 0; } r @ 0x0; };'
    for label, text, words in (
            ('parameters', 'addrmap m { reg #(longint W = 8) { field { } f[0:0]; } r @ 0x0; };', 'parameters'),
            ('a named reg definition', 'addrmap m { reg myreg { field { } f[0:0]; }; myreg r @ 0x0; };', 'named reg definition'),
            ('an enum', 'addrmap m { enum e { A = 0; }; };', 'enum is outside'),
            ('a regfile', 'addrmap m { regfile { }; };', 'regfile is outside'),
            ('a user-defined property', 'addrmap m { property p { type = boolean; }; };', 'a user-defined property'),
            ('a dynamic property assignment', 'addrmap m { reg { field { } f[0:0]; } r @ 0x0; r.f->reset = 1; };', 'outside the subset'),
            ('a property outside the subset (swmod)', 'addrmap m { reg { field { swmod; } f[0:0]; } r @ 0x0; };', "property 'swmod' is not in the subset"),
            ('a reg without @ (automatic addressing)', 'addrmap m { reg { field { } f[0:0]; } r; };', 'no @ offset'),
            ('overlapping fields', 'addrmap m { reg { field { } a[3:0]; field { } b[2:2]; } r @ 0x0; };', 'overlaps'),
            ('overlapping registers', 'addrmap m { reg { field { } a[0:0]; } r @ 0x0; reg { field { } b[0:0]; } s @ 0x2; };', 'overlaps R at byte'),
            ('a reversed (msb0) range', 'addrmap m { reg { field { } a[0:3]; } r @ 0x0; };', 'msb0'),
            ('a reset that does not fit', 'addrmap m { reg { field { } a[1:0] = 7; } r @ 0x0; };', 'does not fit'),
            ('a nested addrmap', 'addrmap m { addrmap n { }; };', 'nested addrmap'),
            ('sw = rw1 (not a SystemRDL value in the subset)', 'addrmap m { reg { field { sw = rw1; } a[0:0]; } r @ 0x0; };', 'outside the subset')):
        check('refused in words: %s' % label, _refused(text, words), text)
    check('control: the minimal good file reads (so the refusals above are about their one change)', _rdl(good)['registers'][0]['register'] == 'R')


def run():
    from board.custom import access_overlay as O
    from board.custom import rdl_import as D
    from board.custom import svd_import as S
    unit()
    svd_text = open(os.path.join(HERE, 'toyperiph.expected.svd')).read()
    amap = D.load(os.path.join(HERE, 'toyperiph.rdl'))
    rr, rf, left = D.rows(amap, block='TOY', prefix='TOY')
    words = {(f['register'], f['field']): f['access_word'] for f in rf}
    check('toyperiph.rdl READ DIRECTLY: every field gets its HAL access word from the RDL alone, cited to its line - out / en / mode rw, done r-w1c '
          '(sw = rw; onwrite = woclr), go w-strobe (sw = w; singlepulse), start rw-sc (sw = rw; hwclr), count r', not left and words == {
              ('TOY_GPIO_OUT_REG', 'OUT'): 'rw', ('TOY_CTRL_REG', 'EN'): 'rw', ('TOY_CTRL_REG', 'MODE'): 'rw', ('TOY_CTRL_REG', 'START'): 'rw-sc',
              ('TOY_STATUS_REG', 'DONE'): 'r-w1c',
              ('TOY_CMD_REG', 'GO'): 'w-strobe', ('TOY_COUNT_REG', 'COUNT'): 'r'}
          and all(f['access_source'] == 'rdl' and f['access_cite'].startswith('toyperiph.rdl line ') for f in rf), words)
    go = next(f for f in rf if f['field'] == 'GO')
    check('the cite names the line and the properties that decided it (go: "toyperiph.rdl line 27: sw = w; hw = r; singlepulse")',
          go['access_cite'] == 'toyperiph.rdl line 27: sw = w; hw = r; singlepulse', go['access_cite'])
    check('the hand SVD says it is hand-written and that the singlepulse form is UNVERIFIED (until the real tool regenerates it)',
          'HAND-WRITTEN' in svd_text and 'UNVERIFIED' in svd_text and 'NOT generated by the tool' in svd_text)
    chip = S.load(os.path.join(HERE, 'toyperiph.expected.svd'))
    sr, sf = S.rows(chip, 'TOYPERIPH', block='TOY', name_prefix='TOY')
    sf, sleft = O.apply_svd(sf)
    why = agree((rr, rf), (sr, sf))
    check('the two paths agree on everything an SVD can say (registers, offsets, bits, resets, access) - the RDL\'s w-strobe is the SVD\'s plain w',
          not why and not sleft, why)
    check('FINDING kept: from the SVD alone go is a plain store \'w\' (no singlepulse form), from the RDL it is \'w-strobe\' - own silicon is read from SystemRDL',
          next(f for f in sf if f['field'] == 'GO')['access_word'] == 'w' and go['access_word'] == 'w-strobe')
    start = next(f for f in rf if f['field'] == 'START')
    check('rw-sc (pol 2026-11-13: the hardware clear is what `wait` polls): ctrl.start (sw = rw; hwclr) -> rw-sc from the RDL, cited with hwclr; '
          'from the SVD alone only rw (no hwclr form)', start['access_word'] == 'rw-sc' and start['access_cite'].endswith('sw = rw; hw = r; hwclr')
          and next(f for f in sf if f['field'] == 'START')['access_word'] == 'rw', start['access_cite'])
    dropped = _load(svd_text.replace('<modifiedWriteValues>oneToClear</modifiedWriteValues>', ''))
    dr, df = S.rows(dropped, 'TOYPERIPH', block='TOY', name_prefix='TOY')
    df, _ = O.apply_svd(df)
    check('control: an SVD that drops the RDL\'s woclr disagrees with the RDL path (done r-w1c vs rw) and is caught', agree((rr, rf), (dr, df)) != [])
    ra = _load(svd_text.replace('<access>read-only</access>', '<access>read-only</access><readAction>clear</readAction>'))
    w, why_ra = O.from_svd(next(f for f in S.rows(ra, 'TOYPERIPH')[1] if f['field'] == 'COUNT'))
    check('control: an SVD field with a readAction (clear-on-read) gets NO word and says why', w is None and 'readAction clear' in why_ra, why_ra)
    total, ok = len(_results), sum(_results)
    print('\n%d/%d checks passed' % (ok, total))
    return ok == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if run() else 1)
