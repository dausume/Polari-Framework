"""hal_evidence.c3_overlay_proof - hal-4 proof 2: import esp32c3.svd (board.custom.svd_import), overlay the TRM's access codes
(board.custom.access_overlay) on six chapters and merge, then compare every resulting trm_access with the hand-cited rows of
board.custom.registers_esp32c3 by (block, offset, bits). Writes modules/board/custom/evidence/esp32c3_overlay_proof.json.

    PYTHONPATH=.:modules python3 tools/hal_evidence/c3_overlay_proof.py SVD TRM_TXT TRM_PDF [OUT]
      TRM_TXT = `pdftotext -layout` of the TRM (pages split on form feeds); TRM_PDF only for its sha256
"""
import hashlib
import json
import os
import re
import sys

CHAPTERS = {   # block: (SVD peripheral, first page, last page, the TRM's field prefix, spelling alias)
    'LEDC': ('LEDC', 836, 848, 'LEDC_', None),
    'APB_SARADC': ('APB_SARADC', 877, 900, 'APB_SARADC_', 'saradc'),
    'SYSTIMER': ('SYSTIMER', 277, 290, 'SYSTIMER_', None),
    'UART0': ('UART0', 571, 600, 'UART_', None),
    'INTMTX': ('INTERRUPT_CORE0', 213, 218, 'INTERRUPT_CORE0_', None),
    'SYSTEM': ('SYSTEM', 434, 460, 'SYSTEM_', None),
}
#: the SAR ADC's three sources spell one bit three ways (TRM + ESP-IDF APB_SARADC_ADC1_DONE_INT_ENA, SVD APB_SARADC1_DONE_INT_ENA)
ALIASES = {'saradc': lambda x: re.sub(r'^ADC(\d)_', r'\1_', re.sub(r'^(?:APB_)?SARADC_?', '', x))}


def prove(svd, txt, pdf):
    from board.custom import access_overlay as O
    from board.custom import registers_esp32c3 as R
    from board.custom import svd_import as S
    pages = open(txt).read().split('\f')
    chip = S.load(svd)
    merged, chapters, conflicts = {}, {}, []
    for blk, (per, a, b, pre, alias) in CHAPTERS.items():
        regs, fields = S.rows(chip, per, block=blk)
        ov = O.overlay(pages, {'first': a, 'last': b, 'prefix': pre}, fields, regs, canon=ALIASES.get(alias))
        out, conf = O.merge(fields, ov, 'ESP32-C3 TRM v1.4')
        conflicts += conf
        off = {r['register']: r['offset'] for r in regs}
        for f in out:
            merged[(blk, off[f['register']], f['bit_lo'], f['width'])] = f
        chapters[blk] = {'pages': [a, b], 'accepted': len(ov['accepted']), 'review': len(ov['review']), 'no_code': len(ov['no_code']),
                         'unmatched': len(ov['unmatched']), 'ambiguous': len(ov['ambiguous'])}
    regs = {r['register']: r for r in R.REGISTERS}
    counts, findings = {}, []
    for f in R.FIELDS:
        r = regs[f['register']]
        if r['block'] not in CHAPTERS:
            continue
        m = merged.get((r['block'], r['offset'], f['bit_lo'], f['width']))
        got = m['trm_access'] if m else None
        cls = ('no imported field' if m is None else ('same code' if f['trm_access'] else 'missing in both') if got == f['trm_access'] else
               'overlay missing, hand cited' if not got else 'overlay cited, hand missing' if not f['trm_access'] else 'DIFFERENT code')
        key = '%s: %s' % (f['part'], cls)
        counts[key] = counts.get(key, 0) + 1
        if cls not in ('same code',):
            findings.append({'part': f['part'], 'register': f['register'], 'field': f['field'], 'class': cls, 'hand': f['trm_access'], 'overlay': got,
                             'hand_cite': f['page_table']})
    return {'what': 'hal-4 proof 2: svd_import + access_overlay (TRM text) vs the hand-cited trm_access of board.custom.registers_esp32c3',
            'svd_sha256': hashlib.sha256(open(svd, 'rb').read()).hexdigest(), 'trm_sha256': hashlib.sha256(open(pdf, 'rb').read()).hexdigest(),
            'trm_text_sha256': hashlib.sha256(open(txt, 'rb').read()).hexdigest(), 'rows': {'registers': len(R.REGISTERS), 'fields': len(R.FIELDS)},
            'chapters': chapters, 'counts': dict(sorted(counts.items())), 'findings': findings,
            'conflicts': sorted(conflicts, key=lambda c: (c['register'], c['field']))}


if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.join('modules', 'board', 'custom', 'evidence', 'esp32c3_overlay_proof.json')
    doc = prove(*sys.argv[1:4])
    with open(out, 'w') as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write('\n')
    for k, v in doc['counts'].items():
        print('%5d  %s' % (v, k))
    print('conflicts (TRM code vs SVD word, merged + reported): %s' % [(c['register'], c['field'], c['trm'], c['svd']) for c in doc['conflicts']])
    print('%d findings -> %s' % (len(doc['findings']), out))
