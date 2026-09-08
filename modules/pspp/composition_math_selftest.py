"""
Self-test for pspp composition math — hand-checked numbers, with the
book's own p.84 conversion constants (MR = 1.032·WR Na, 1.568·WR K)
as independent cross-checks of the molar-mass derivation.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.composition_math_selftest
"""

import sys

from pspp.custom.composition_math import (
    COMMERCIAL_SILICATE_MR, baume_from_sg, mr_from_solution,
    mr_from_wr, oxide_ratios, ratios_from_moles, sg_from_baume,
    wr_from_mr,
)

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def close(a, b, tol=1e-3):
    return a is not None and abs(a - b) <= tol


def test_mr_wr():
    print('[MR/WR — book p.84 cross-checks]')
    na = mr_from_wr(1.0, 'Na')
    check('Na factor reproduces the book: 1.032',
          na['ok'] and close(na['MR'], 1.032, 0.001))
    k = mr_from_wr(1.0, 'K')
    check('K factor reproduces the book: 1.568',
          k['ok'] and close(k['MR'], 1.568, 0.001))
    check('round trip WR -> MR -> WR',
          close(wr_from_mr(mr_from_wr(3.176, 'Na')['MR'], 'Na')['WR'],
                3.176, 1e-9))
    check('unknown cation refused',
          mr_from_wr(1.0, 'Cs')['ok'] is False)

    # Typical grade-3.3 waterglass: 27% SiO2, 8.5% Na2O.
    grade33 = mr_from_solution({'SiO2': 27.0, 'Na2O': 8.5, 'H2O': 64.5})
    check('grade-3.3 waterglass: WR 3.176 -> MR ~3.277',
          grade33['ok'] and close(grade33['WR'], 3.176, 0.001)
          and close(grade33['MR'], 3.277, 0.002))
    check('MR inside the practical range carries no caution',
          'caution' not in grade33)
    extreme = mr_from_solution({'SiO2': 45.0, 'Na2O': 5.0, 'H2O': 50.0})
    check('MR outside [0.4, 4.0] carries the p.84 caution',
          extreme['ok'] and 'caution' in extreme)
    check('missing alkali oxide refused',
          mr_from_solution({'SiO2': 30.0, 'H2O': 70.0})['ok'] is False)


def test_table_5_1():
    print('[Table 5.1 commercial presets]')
    check('metasilicate MR=1.0, polysilicate MR=3.30',
          COMMERCIAL_SILICATE_MR['sodium-metasilicate']['MR'] == 1.0
          and COMMERCIAL_SILICATE_MR['sodium-polysilicate']['MR'] == 3.30)
    check('orthosilicate 0.5, disilicate 2.0 present',
          COMMERCIAL_SILICATE_MR['sodium-orthosilicate']['MR'] == 0.5
          and COMMERCIAL_SILICATE_MR['sodium-disilicate']['MR'] == 2.0)


def test_baume():
    print('[Baume <-> SG]')
    b = baume_from_sg(1.5)
    check('SG 1.5 -> 48.33 Be', b['ok'] and close(b['baume'], 48.333,
                                                  0.001))
    check('round trip', close(
        sg_from_baume(baume_from_sg(1.38)['baume'])['sg'], 1.38, 1e-9))
    check('Baume >= 145 refused (asymptote)',
          sg_from_baume(145.0)['ok'] is False)


def test_oxide_ratios():
    print('[derived composition descriptors (Ch.8 set)]')
    r = oxide_ratios({'SiO2': 55.0, 'Al2O3': 25.0, 'Na2O': 10.0,
                      'H2O': 10.0})
    check('SiO2/Al2O3 molar ~3.734',
          r['ok'] and close(r['ratios']['SiO2/Al2O3'], 3.734, 0.002))
    check('M2O/SiO2 ~0.176',
          close(r['ratios']['M2O/SiO2'], 0.1762, 0.001))
    check('H2O/M2O ~3.441',
          close(r['ratios']['H2O/M2O'], 3.441, 0.002))
    check('atomic Si/Al ~1.867 (half the oxide ratio: Al2O3 carries '
          '2 Al)', close(r['ratios']['Si/Al'], 1.867, 0.002))
    check('Na/K with no K is None + named absent denominator',
          r['ratios']['Na/K'] is None
          and any('Na/K' in n for n in r['absentDenominators']))
    check('unknown oxide refused with the known list',
          oxide_ratios({'SiO2': 50.0, 'XyO9': 50.0})['ok'] is False)

    # p.183 benchmark: 1.1Na2O:4SiO2:Al2O3:17H2O (MK-750, MR=1.82).
    bench = ratios_from_moles({'Na2O': 1.1, 'SiO2': 4.0,
                               'Al2O3': 1.0, 'H2O': 17.0})
    check('p.183 benchmark formula reproduces the printed ratios: '
          'SiO2/Al2O3=4.0(~4.02), Na2O/SiO2=0.275(~0.28), '
          'Na2O/Al2O3=1.10, Si:Al=2',
          bench['ok']
          and close(bench['ratios']['SiO2/Al2O3'], 4.0, 1e-9)
          and close(bench['ratios']['M2O/SiO2'], 0.275, 1e-9)
          and close(bench['ratios']['M2O/Al2O3'], 1.10, 1e-9)
          and close(bench['ratios']['Si/Al'], 2.0, 1e-9))
    check('formula H2O/M2O = 15.45 (the book PRINTS 17.20 in the '
          'ratio list — as-printed discrepancy recorded in the '
          'benchmark JSON, never reconciled silently)',
          close(bench['ratios']['H2O/M2O'], 15.4545, 0.001))


def main():
    test_mr_wr()
    test_table_5_1()
    test_baume()
    test_oxide_ratios()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
