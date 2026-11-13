"""hal_evidence.c3_svd_import_proof - hal-4 proof 1: import Espressif's esp32c3.svd with board.custom.svd_import and compare it, field for
field by (block, register offset, bit position), with EVERY hand-cited row of board.custom.registers_esp32c3 (drawing set + hal-3a).
Writes modules/board/custom/evidence/esp32c3_svd_import_proof.json: the counts per class and every disagreement by name, so a
difference is a finding in one of the two, never silently resolved.

    PYTHONPATH=.:modules python3 tools/hal_evidence/c3_svd_import_proof.py SVD [OUT]
"""
import hashlib
import json
import os
import sys

BLOCKS = {'LEDC': 'LEDC', 'APB_SARADC': 'APB_SARADC', 'SYSTIMER': 'SYSTIMER', 'SYSTEM': 'SYSTEM', 'INTMTX': 'INTERRUPT_CORE0', 'UART0': 'UART0',
          'GPIO': 'GPIO', 'IO_MUX': 'IO_MUX', 'RTC_CNTL': 'RTC_CNTL'}


def _num(x):
    try:
        return int(str(x), 0)
    except ValueError:
        return None


def prove(svd):
    from board.custom import registers_esp32c3 as R
    from board.custom import svd_import as S
    chip = S.load(svd)
    byreg = {(b, r['offset']): r for b, p in BLOCKS.items() for r in chip['peripherals'][p]['registers']}
    regs = {r['register']: r for r in R.REGISTERS}
    counts, findings = {}, []
    for f in R.FIELDS:
        r = regs[f['register']]
        sr = byreg.get((r['block'], r['offset']))
        if sr is None:
            cls = 'no SVD register at this offset'
        else:
            exact = [x for x in sr['fields'] if (x['bit_lo'], x['width']) == (f['bit_lo'], f['width'])]
            inside = [x for x in sr['fields'] if x['bit_lo'] <= f['bit_lo'] and f['bit_hi'] <= x['bit_hi']]
            expect = (sr['reset'] >> f['bit_lo']) & ((1 << f['width']) - 1)
            fr = _num(f['reset_value'])
            shape = 'exact' if exact else 'inside a wider SVD field' if inside else 'no SVD field covers these bits'
            cls = '%s; field reset %s' % (shape, 'agrees' if fr == expect else 'not a number in the row' if fr is None else 'DIFFERS')
            if shape != 'exact' or fr != expect:
                findings.append({'part': f['part'], 'register': f['register'], 'field': f['field'], 'class': cls, 'bits': [f['bit_hi'], f['bit_lo']],
                                 'row_reset': f['reset_value'], 'svd_reset': expect, 'svd_register': sr['register'], 'svd_register_reset': '0x%08X' % sr['reset'],
                                 'svd_fields_here': sorted('%s[%d:%d]' % (x['field'], x['bit_hi'], x['bit_lo']) for x in (exact or inside))})
        key = '%s: %s' % (f['part'], cls)
        counts[key] = counts.get(key, 0) + 1
    return {'what': 'hal-4 proof 1: svd_import(esp32c3.svd) vs every hand-cited row of board.custom.registers_esp32c3, by (block, offset, bits)',
            'svd': {'repo': 'espressif/svd', 'commit': 'be20aa12560889d6125d144cdb48cf615ac17628', 'sha256': hashlib.sha256(open(svd, 'rb').read()).hexdigest()},
            'rows': {'registers': len(R.REGISTERS), 'fields': len(R.FIELDS)}, 'counts': dict(sorted(counts.items())), 'findings': findings}


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join('modules', 'board', 'custom', 'evidence', 'esp32c3_svd_import_proof.json')
    doc = prove(sys.argv[1])
    with open(out, 'w') as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write('\n')
    for k, v in doc['counts'].items():
        print('%5d  %s' % (v, k))
    print('%d findings -> %s' % (len(doc['findings']), out))
