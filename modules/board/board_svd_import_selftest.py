"""board_svd_import_selftest - hal-4: board.custom.svd_import on a small synthetic SVD that exercises every CMSIS-SVD feature the importer
claims, plus the refusals it promises (a refusal names the problem; nothing is guessed).

    PYTHONPATH=.:modules python3 -m board.board_svd_import_selftest      # from polari-framework/ (standalone)
"""
import os
import tempfile

_results = []

SVD = '''<?xml version="1.0" encoding="utf-8"?>
<device schemaVersion="1.3"><name>TOY</name><width>32</width><size>32</size><access>read-write</access><resetValue>0x00000000</resetValue>
 <peripherals>
  <peripheral><name>TIMG</name><baseAddress>0x60001000</baseAddress><resetValue>0x00000004</resetValue>
   <registers>
    <register><name>CONF</name><addressOffset>0x0</addressOffset><resetValue>0x80000005</resetValue>
     <fields>
      <field><name>EN</name><bitOffset>31</bitOffset><bitWidth>1</bitWidth></field>
      <field><name>DIV</name><lsb>0</lsb><msb>3</msb><enumeratedValues><enumeratedValue><name>BY1</name><value>0</value></enumeratedValue>
        <enumeratedValue><name>BY5</name><description>divide   by five</description><value>5</value></enumeratedValue></enumeratedValues></field>
      <field><name>MODE</name><bitRange>[9:8]</bitRange><access>read-only</access></field>
     </fields></register>
    <register><name>CH%s_CNT</name><addressOffset>0x10</addressOffset><dim>3</dim><dimIncrement>0x8</dimIncrement>
     <fields><field><name>CNT</name><bitOffset>0</bitOffset><bitWidth>16</bitWidth></field></fields></register>
    <register><name>CMP[%s]</name><addressOffset>0x40</addressOffset><dim>2</dim><dimIncrement>4</dimIncrement><dimIndex>A,B</dimIndex>
     <access>write-only</access><fields><field><name>V</name><bitOffset>0</bitOffset><bitWidth>8</bitWidth></field></fields></register>
    <cluster><name>T%s</name><addressOffset>0x80</addressOffset><dim>2</dim><dimIncrement>0x20</dimIncrement><dimIndex>3-4</dimIndex>
     <register><name>LOAD</name><addressOffset>0x4</addressOffset><fields><field><name>GO</name><bitOffset>0</bitOffset><bitWidth>1</bitWidth></field></fields></register>
    </cluster>
   </registers></peripheral>
  <peripheral derivedFrom="TIMG"><name>TIMG1</name><baseAddress>0x60002000</baseAddress></peripheral>
 </peripherals></device>'''


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  ' + str(extra)[:300]) if (extra and not cond) else ''))


def _load(text):
    from board.custom import svd_import as S
    fd, path = tempfile.mkstemp(suffix='.svd')
    with os.fdopen(fd, 'w') as fh:
        fh.write(text)
    try:
        return S.load(path)
    finally:
        os.unlink(path)


def _refused(text, words):
    from board.custom import svd_import as S
    try:
        _load(text)
    except S.SvdRefused as e:
        return words in str(e)
    return False


def proof_checks():
    """hal-4 proof 1, as recorded by tools/hal_evidence/c3_svd_import_proof.py (needs the full SVD): the report must describe TODAY's rows (a row
    change makes it stale -> regenerate), every hal-3a field must be exact, and every other difference must be one the report explains -
    IO_MUX's per-pad resets (TRM Table 5.12-1 p.174 per pad; the SVD has one resetValue for all 22) and IO_MUX MCU_DRV (no SVD field)."""
    import json
    from board.custom import registers_esp32c3 as R
    doc = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom', 'evidence', 'esp32c3_svd_import_proof.json')))
    check('proof 1 is current: it covers today\'s %d registers / %d fields (a row change makes it stale: rerun c3_svd_import_proof.py)'
          % (len(R.REGISTERS), len(R.FIELDS)), doc['rows'] == {'registers': len(R.REGISTERS), 'fields': len(R.FIELDS)}
          and sum(doc['counts'].values()) == len(R.FIELDS), doc['rows'])
    _, hal = R.part('hal-3a')
    check('proof 1: the importer reproduces every hal-3a field exactly (%d: bits + field reset)' % len(hal),
          doc['counts'].get('hal-3a: exact; field reset agrees') == len(hal) and not [x for x in doc['findings'] if x['part'] == 'hal-3a'])
    odd = [x for x in doc['findings'] if 'inside a wider SVD field; field reset agrees' not in x['class']
           and not (x['register'].startswith('IO_MUX_GPIO') and (x['field'] == 'MCU_DRV' or 'DIFFERS' in x['class']))]
    check('proof 1: every other disagreement is explained - per-pad bits inside the SVD\'s wider field, IO_MUX\'s per-pad resets (the SVD\'s one '
          'resetValue 0xB00 vs TRM Table 5.12-1), IO_MUX MCU_DRV [6:5] absent from the SVD', not odd, [(x['register'], x['field'], x['class']) for x in odd[:3]])


def run():
    from board.custom import svd_import as S
    chip = _load(SVD)
    t = {r['register']: r for r in chip['peripherals']['TIMG']['registers']}
    conf = {f['field']: f for f in t['CONF']['fields']}
    check('device + peripherals: TOY, TIMG at 0x60001000, TIMG1 derived from it at its own base 0x60002000 with the same registers',
          chip['device'] == 'TOY' and chip['peripherals']['TIMG']['base'] == 0x60001000 and chip['peripherals']['TIMG1']['base'] == 0x60002000
          and chip['peripherals']['TIMG1']['derived_from'] == 'TIMG' and len(chip['peripherals']['TIMG1']['registers']) == len(t), sorted(t))
    check('three bit-range forms: bitOffset/bitWidth (EN 31), lsb/msb (DIV 3:0), bitRange "[9:8]" (MODE)',
          (conf['EN']['bit_lo'], conf['EN']['width']) == (31, 1) and (conf['DIV']['bit_lo'], conf['DIV']['bit_hi']) == (0, 3)
          and (conf['MODE']['bit_lo'], conf['MODE']['bit_hi']) == (8, 9), conf)
    check('field resets come from the register reset (0x80000005: EN 1, DIV 5, MODE 0); a register without one inherits the peripheral\'s (0x4)',
          (conf['EN']['reset_value'], conf['DIV']['reset_value'], conf['MODE']['reset_value']) == ('1', '5', '0') and t['CH0_CNT']['reset'] == 4,
          (conf['EN']['reset_value'], conf['DIV']['reset_value'], t['CH0_CNT']['reset']))
    check('access inherits device -> register -> field: MODE read-only (its own), CMPA write-only (the register\'s), EN read-write (the device\'s)',
          conf['MODE']['svd_access'] == 'read-only' and t['CMPA']['fields'][0]['svd_access'] == 'write-only' and conf['EN']['svd_access'] == 'read-write')
    check('enumeratedValues -> values, the description\'s whitespace collapsed', conf['DIV']['values'] == {'0': 'BY1', '5': 'BY5: divide by five'}, conf['DIV']['values'])
    check('dim %s: CH0..2_CNT at 0x10 / 0x18 / 0x20', [(n, t[n]['offset']) for n in ('CH0_CNT', 'CH1_CNT', 'CH2_CNT')] == [('CH0_CNT', 0x10), ('CH1_CNT', 0x18), ('CH2_CNT', 0x20)])
    check('dim [%s] with a dimIndex list: CMPA 0x40, CMPB 0x44', (t['CMPA']['offset'], t['CMPB']['offset']) == (0x40, 0x44))
    check('a dimmed cluster with a dimIndex range: T3_LOAD 0x84, T4_LOAD 0xA4 (cluster offset + element + register offset)',
          (t['T3_LOAD']['offset'], t['T4_LOAD']['offset']) == (0x84, 0xA4), sorted(t))
    R, F = S.rows(chip, 'TIMG', block='TIMG')
    check('rows(): the generator\'s shape - <PERIPH>_<NAME>_REG, every field trm_access \'\' (missing until an overlay cites a code), the SVD word kept as svd_access',
          R[0]['register'] == 'TIMG_CONF_REG' and all(f['trm_access'] == '' and f['svd_access'] for f in F) and S.address(chip, 'TIMG1', 0x84) == 0x60002084)
    base = SVD.replace('<register><name>CH%s_CNT</name>', '<register derivedFrom="CONF"><name>CH%s_CNT</name>')
    check('refused: a register derivedFrom (not supported, said)', _refused(base, 'derivedFrom register is not supported'))
    check('refused: dim without dimIncrement', _refused(SVD.replace('<dimIncrement>0x8</dimIncrement>', ''), 'dim without dimIncrement'))
    check('refused: a dimIndex that names a different count than dim', _refused(SVD.replace('<dimIndex>A,B</dimIndex>', '<dimIndex>A,B,C</dimIndex>'), 'names 3 elements, dim says 2'))
    check('refused: a peripheral derivedFrom an unknown one', _refused(SVD.replace('derivedFrom="TIMG"', 'derivedFrom="NOPE"'), 'derivedFrom unknown NOPE'))
    proof_checks()
    total, ok = len(_results), sum(_results)
    print('\n%d/%d checks passed' % (ok, total))
    return ok == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if run() else 1)
