"""board_access_overlay_selftest - hal-4: board.custom.access_overlay on synthetic manual pages built to exercise each rule (acceptance by
name AND register header, an array header's element offsets, the review queue for a name-only match, the shared SOURCE_X field, the
6-line cap that keeps a code from being borrowed, a real index never collapsing, merge's conflict report), then proof 2's recorded
report against today's rows.

    PYTHONPATH=.:modules python3 -m board.board_access_overlay_selftest      # from polari-framework/ (standalone)
"""
import json
import os

_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  ' + str(extra)[:300]) if (extra and not cond) else ''))


PAGES = [
    # p.1: an ordinary register and an array register
    '''              Register 7.1. TOY_CONF_REG (0x0000)
        TOY_EN Set this bit to enable the toy. (R/W)
        TOY_DIV This field is used to configure
            the divider. (R/W)
        TOY_GO Write 1 to start. (WT)
              Register 7.2. TOY_CHn_CNT_REG (n: 0-2) (0x0010+8*n)
        TOY_CNT_CHn The count of channel n. (RO)
''',
    # p.2: two registers printed OUT OF ORDER (the INT_ST field sits under INT_RAW's header), a unit pair, a code-less field
    '''              Register 7.4. TOY_INT_RAW_REG (0x0024)
        TOY_DONE_INT_ST This is the masked status of TOY_DONE_INT. (RO)
              Register 7.3. TOY_INT_ST_REG (0x0020)
        TOY_DONE_INT_RAW Raw bit of TOY_DONE_INT. (R/WTC/SS)
              Register 7.5. TOY_UNIT0_OP_REG (0x0030)
        TOY_UNIT0_VALID The value is valid. (R/SS/WTC)
              Register 7.6. TOY_UNIT1_OP_REG (0x0034)
        TOY_UNIT1_VALID The value is valid. (R/SS/WTC)
              Register 7.7. TOY_MYSTERY_REG (0x0038)
        TOY_MYSTERY This field has no code printed.
''',
    # p.3: a field whose code only appears 8 lines later (a run-on into another field's text must not lend it a code); a shared field
    '''              Register 7.8. TOY_LONG_REG (0x0040)
        TOY_LONG One line.
            two
            three
            four
            five
            six
            seven
            eight (R/W)
              Register 7.9. TOY_A_MAP_REG (0x0050)
              Register 7.10. TOY_B_MAP_REG (0x0054)
TOY_SOURCE_X_MAP Map the interrupt source (SOURCE_X) into one CPU interrupt. (R/W)
''']


def _rows():
    R, F = [], []
    def reg(name, off, fields, svd=None):
        rn = 'TOY_%s_REG' % name
        R.append({'register': rn, 'svd_register': svd or name, 'block': 'TOY', 'offset': off})
        for fn, lo, w, acc in fields:
            F.append({'register': rn, 'svd_register': svd or name, 'field': fn, 'bit_lo': lo, 'width': w, 'bit_hi': lo + w - 1, 'svd_access': acc,
                      'trm_access': '', 'description': '', 'page_table': 'SVD', 'notes': ''})
    reg('CONF', 0x0, [('EN', 0, 1, 'read-write'), ('DIV', 1, 4, 'read-write'), ('GO', 5, 1, 'write-only')])
    for i in range(3):
        reg('CH%d_CNT' % i, 0x10 + 8 * i, [('CNT', 0, 16, 'read-only')], svd='CH%d_CNT' % i)
    reg('INT_ST', 0x20, [('DONE_INT_ST', 0, 1, 'read-only')])
    reg('INT_RAW', 0x24, [('DONE_INT_RAW', 0, 1, 'read-write')])
    reg('UNIT0_OP', 0x30, [('UNIT0_VALID', 0, 1, 'read-only')])
    reg('UNIT1_OP', 0x34, [('UNIT1_VALID', 0, 1, 'read-only')])
    reg('MYSTERY', 0x38, [('MYSTERY', 0, 1, 'read-write')])
    reg('LONG', 0x40, [('LONG', 0, 1, 'read-write')])
    reg('A_MAP', 0x50, [('A_MAP', 0, 5, 'read-write')])
    reg('B_MAP', 0x54, [('B_MAP', 0, 5, 'read-write')])
    return R, F


def unit():
    from board.custom import access_overlay as O
    R, F = _rows()
    ov = O.overlay(PAGES, {'first': 1, 'last': 3, 'prefix': 'TOY_'}, F, R)
    acc = ov['accepted']
    check('accepted when the NAME and the register header agree: CONF.EN R/W, CONF.GO WT, and DIV across a line break (its code on the next line)',
          acc.get(('TOY_CONF_REG', 'EN'), {}).get('code') == 'R/W' and acc.get(('TOY_CONF_REG', 'GO'), {}).get('code') == 'WT'
          and acc.get(('TOY_CONF_REG', 'DIV'), {}).get('code') == 'R/W', sorted(acc))
    check('an array header "(n: 0-2) (0x0010+8*n)" covers every element: CH0 / CH1 / CH2_CNT.CNT all RO (CHn ~ CH0..2)',
          all(acc.get(('TOY_CH%d_CNT_REG' % i, 'CNT'), {}).get('code') == 'RO' for i in range(3)), sorted(acc))
    rev = {(x['register'], x['field']) for x in ov['review']}
    check('two registers printed out of order: a field whose NAME says one register but whose header says the other goes to REVIEW, not accepted '
          '(INT_ST.DONE_INT_ST under INT_RAW\'s header; INT_RAW.DONE_INT_RAW under INT_ST\'s)',
          rev == {('TOY_INT_ST_REG', 'DONE_INT_ST'), ('TOY_INT_RAW_REG', 'DONE_INT_RAW')} and ('TOY_INT_ST_REG', 'DONE_INT_ST') not in acc, (rev, sorted(acc)))
    check('a real index never collapses: UNIT0_VALID and UNIT1_VALID each get their own register\'s code, no ambiguity',
          acc.get(('TOY_UNIT0_OP_REG', 'UNIT0_VALID'), {}).get('code') == 'R/SS/WTC' and acc.get(('TOY_UNIT1_OP_REG', 'UNIT1_VALID'), {}).get('code') == 'R/SS/WTC'
          and not ov['ambiguous'], ov['ambiguous'])
    check('a field printed with no code is no_code (MYSTERY), and a code 8 lines down is NOT taken (the 6-line cap): LONG stays uncited',
          'TOY_MYSTERY' in ov['no_code'] and ('TOY_LONG_REG', 'LONG') not in acc and 'TOY_LONG' in ov['no_code'], (ov['no_code'], sorted(acc)))
    check('one field described for a run of registers (TOY_SOURCE_X_MAP) is each register\'s own: A_MAP and B_MAP R/W',
          acc.get(('TOY_A_MAP_REG', 'A_MAP'), {}).get('code') == 'R/W' and acc.get(('TOY_B_MAP_REG', 'B_MAP'), {}).get('code') == 'R/W', sorted(acc))
    out, conf = O.merge(F, ov, 'TOY manual')
    m = {(f['register'], f['field']): f for f in out}
    check('merge: an accepted code becomes trm_access with the manual\'s sentence and cite; a reviewed / uncited field stays trm_access \'\' (missing)',
          m[('TOY_CONF_REG', 'GO')]['trm_access'] == 'WT' and m[('TOY_CONF_REG', 'GO')]['page_table'].startswith('Register 7.1 TOY_CONF_REG, p.1')
          and m[('TOY_CONF_REG', 'GO')]['description'] == 'Write 1 to start.' and m[('TOY_INT_ST_REG', 'DONE_INT_ST')]['trm_access'] == ''
          and m[('TOY_MYSTERY_REG', 'MYSTERY')]['trm_access'] == '', m[('TOY_CONF_REG', 'GO')])
    check('merge reports a conflict, never resolves it silently: UNIT0/1_VALID R/SS/WTC (writable) against the SVD\'s read-only - merged AND reported',
          sorted((c['register'], c['trm'], c['svd']) for c in conf) == [('TOY_UNIT0_OP_REG', 'R/SS/WTC', 'read-only'), ('TOY_UNIT1_OP_REG', 'R/SS/WTC', 'read-only')]
          and m[('TOY_UNIT0_OP_REG', 'UNIT0_VALID')]['trm_access'] == 'R/SS/WTC', conf)


def proof():
    """hal-4 proof 2 as recorded by tools/hal_evidence/c3_overlay_proof.py (needs the SVD + TRM): import + overlay reproduces the hand
    rows' trm_access; the only gaps are the ones the hand rows explain."""
    from board.custom import registers_esp32c3 as R
    doc = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom', 'evidence', 'esp32c3_overlay_proof.json')))
    check('proof 2 is current: it covers today\'s %d registers / %d fields (a row change makes it stale: rerun c3_overlay_proof.py)' % (len(R.REGISTERS), len(R.FIELDS)),
          doc['rows'] == {'registers': len(R.REGISTERS), 'fields': len(R.FIELDS)}, doc['rows'])
    check('proof 2: no field gets a DIFFERENT code from the overlay than from the hand rows, and none the overlay cites that the hand rows leave missing',
          not [x for x in doc['findings'] if x['class'] in ('DIFFERENT code', 'overlay cited, hand missing', 'no imported field')],
          [x for x in doc['findings'] if x['class'] in ('DIFFERENT code', 'overlay cited, hand missing')][:3])
    gaps = [x for x in doc['findings'] if x['class'] == 'overlay missing, hand cited']
    check('proof 2: every field the overlay leaves missing but the hand rows cite was read from the RENDERED page (LEDC_INT_*, pp.840-841, %d)' % len(gaps),
          gaps and all(x['register'].startswith('LEDC_INT_') and 'rendered page' in x['hand_cite'] for x in gaps), gaps[:2])
    both = [x for x in doc['findings'] if x['class'] == 'missing in both']
    check('proof 2: missing in both = only LEDC TICK_SEL (in the SVD and ESP-IDF, not in TRM v1.4)', both and all(x['field'] == 'TICK_SEL' for x in both), both[:2])
    check('proof 2: the conflicts merged + reported are exactly the two the C3 work found - SYSTIMER UNITn VALUE_VALID R/SS/WTC vs the SVD\'s read-only, '
          'UART_FIFO RXFIFO_RD_BYTE RO vs read-write (by action, §26.4.2)',
          sorted((c['field'], c['trm'], c['svd']) for c in doc['conflicts']) == [('RXFIFO_RD_BYTE', 'RO', 'read-write'),
                                                                               ('TIMER_UNIT0_VALUE_VALID', 'R/SS/WTC', 'read-only'),
                                                                               ('TIMER_UNIT1_VALUE_VALID', 'R/SS/WTC', 'read-only')], doc['conflicts'])


def run():
    unit()
    proof()
    total, ok = len(_results), sum(_results)
    print('\n%d/%d checks passed' % (ok, total))
    return ok == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if run() else 1)
