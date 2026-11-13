"""hal_evidence.esp32c3_hal3a_facts - regenerate modules/board/custom/evidence/esp32c3_hal3a_facts.json, the trimmed SOURCE facts the
hal-3a rows of board.custom.registers_esp32c3 are checked against (board_registers_c3_facts_selftest), so the check needs neither the
3.6 MB SVD nor the full ESP-IDF dump in the tree.

    PYTHONPATH=.:modules python3 tools/hal_evidence/esp32c3_hal3a_facts.py SVD IDF_TSV TRM_PDF [OUT]

  SVD      Espressif's esp32c3.svd (espressif/svd); its sha256 is recorded
  IDF_TSV  the dump of ESP-IDF's soc/esp32c3/register/soc/*_reg.h made by idf_c3_fields.py (beside this file) on the
           prf-esp-engines image: `docker run --rm --network none -v "$PWD":/chk:ro prf-esp-engines:noble python3
           /chk/idf_c3_fields.py /opt/esp/idf > idf-c3-fields.tsv` (reads the six headers only)
  TRM_PDF  the ESP32-C3 TRM the rows cite (only its sha256 is recorded; it must match esp32c3_evidence.TRM_SHA)

Each fact is what the SOURCES say at the row's register and bit position, never what the row says: the SVD field found at
(register offset, bit_lo, width), its reset bits, its register's reset; the ESP-IDF macro with that shift and mask, and its
register's offset. A hal-3a field either source cannot place is an error, so no fact is written for it (exit 1).
"""
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

SVD_BLOCK = {'LEDC': 'LEDC', 'APB_SARADC': 'APB_SARADC', 'SYSTIMER': 'SYSTIMER', 'SYSTEM': 'SYSTEM', 'INTMTX': 'INTERRUPT_CORE0'}


def _sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def idf_names(block, register, field):
    """the ESP-IDF register macro (without _REG) and the field macros that may spell this row's field"""
    if block == 'LEDC':
        m = re.match(r'LEDC_(CH|TIMER)(\d)_(\w+)_REG$', register)
        if m and m.group(1) == 'CH':
            return 'LEDC_LSCH%s_%s' % (m.group(2), m.group(3)), ['LEDC_%s_LSCH%s' % (field, m.group(2)), 'LEDC_DUTY_LSCH%s' % m.group(2)]
        if m:
            return 'LEDC_LSTIMER%s_%s' % (m.group(2), m.group(3)), ['LEDC_%s_LSTIMER%s' % (field, m.group(2)), 'LEDC_LSTIMER%s_%s' % (m.group(2), field)]
        return 'LEDC_CONF', ['LEDC_' + field]
    if block == 'INTMTX':
        return register[:-4], [register[:-4]]
    if block == 'APB_SARADC':
        return register[:-4], ['APB_SARADC_' + field, 'APB_' + field]
    return register[:-4], [block + '_' + field]


def build(svd, tsv, trm):
    from board.custom import registers_esp32c3 as R
    root = ET.parse(svd).getroot()
    dflt = int(root.findtext('resetValue') or '0', 0)
    per = {p.findtext('name'): p for p in root.iter('peripheral')}
    layout = {}
    for block, name in SVD_BLOCK.items():
        for r in per[name].iter('register'):
            off = int(r.findtext('addressOffset'), 0)
            dim, inc = int(r.findtext('dim') or 1), int(r.findtext('dimIncrement') or '0', 0)
            rv = int(r.findtext('resetValue'), 0) if r.findtext('resetValue') else dflt
            for i in range(dim):
                for f in r.iter('field'):
                    layout[(block, off + i * inc, int(f.findtext('bitOffset')), int(f.findtext('bitWidth')))] = (f.findtext('name'), rv)
    fields, regs, head = {}, {}, {}
    for line in open(tsv):
        p = line.rstrip('\n').split('\t')
        if p[0] == '#idf':
            head['idf'] = p[1]
        elif p[0] == '#file':
            head.setdefault('idf_headers', {})[p[1]] = p[3]
        elif p[0] == 'F':
            fields.setdefault(p[2], []).append((int(p[3]), int(p[4], 0)))
        elif p[0] == 'R':
            regs[p[2]] = int(p[3], 0)
    rows = {r['register']: r for r in R.REGISTERS}
    _, hal = R.part('hal-3a')
    facts, errors = [], []
    for f in hal:
        r = rows[f['register']]
        block, off, lo, w = r['block'], r['offset'], f['bit_lo'], f['width']
        mask = (1 << w) - 1
        svd_hit = layout.get((block, off, lo, w))
        ireg, names = idf_names(block, f['register'], f['field'])
        idf_hit = next((n for n in names if (lo, mask) in fields.get(n, ())), None)
        if not svd_hit or not idf_hit or ireg not in regs:
            errors.append('%s.%s: svd %s, idf field %s, idf register %s %s' % (f['register'], f['field'], bool(svd_hit), idf_hit, ireg, ireg in regs))
            continue
        facts.append({'register': f['register'], 'field': f['field'],
                      'svd_field': svd_hit[0], 'svd_bit_lo': lo, 'svd_width': w, 'svd_reset': str((svd_hit[1] >> lo) & mask),
                      'svd_register_reset': '0x%08X' % svd_hit[1],
                      'idf_register': ireg, 'idf_offset': regs[ireg], 'idf_field': idf_hit, 'idf_shift': lo, 'idf_mask': mask})
    doc = {'what': 'the SOURCE facts the hal-3a rows of board.custom.registers_esp32c3 are checked against (regenerate with '
                   'tools/hal_evidence/esp32c3_hal3a_facts.py)',
           'sources': {'svd': {'repo': 'espressif/svd', 'commit': 'be20aa12560889d6125d144cdb48cf615ac17628', 'file': 'svd/esp32c3.svd',
                               'sha256': _sha(svd), 'license': 'Apache-2.0'},
                       'esp_idf': {'version': head.get('idf'), 'headers_sha256': head.get('idf_headers'), 'license': 'Apache-2.0',
                                   'read_with': 'tools/hal_evidence/idf_c3_fields.py on prf-esp-engines:noble'},
                       'trm': {'title': 'ESP32-C3 Technical Reference Manual v1.4', 'sha256': _sha(trm)}},
           'facts': facts}
    return doc, errors


if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.join('modules', 'board', 'custom', 'evidence', 'esp32c3_hal3a_facts.json')
    doc, errors = build(*sys.argv[1:4])
    for e in errors:
        print('NOT PLACED', e, file=sys.stderr)
    if errors:
        sys.exit(1)
    with open(out, 'w') as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write('\n')
    print('%d facts -> %s' % (len(doc['facts']), out))
