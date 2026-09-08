"""
Self-test for the Q-distribution engines (pspp-7 Tier 2/3) — glass
curves anchored by Table 5.6 + p.90 text, the glass→solution
transform, and the honest refusals.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.q_distribution_selftest
"""

import sys

from pspp.custom.q_distribution import glass_to_solution_q, q_glass_distribution

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


def test_glass_curves():
    print('[glass Q distributions (Figs 5.4/5.5)]')
    na1 = q_glass_distribution('Na', 1.0)
    check('Na MR=1.0 returns the exact Table 5.6 glass row',
          na1['ok'] and na1['values'] ==
          {'Q0': 1, 'Q1': 14, 'Q2': 68, 'Q3': 17, 'Q4': 0}
          and na1['evidence']['method'] == 'literature')
    na4 = q_glass_distribution('Na', 4.0)
    check('Na MR=4.0 anchor: Q3/Q4 at 50% each (p.90 text)',
          na4['ok'] and na4['values']['Q3'] == 50
          and na4['values']['Q4'] == 50)
    mid = q_glass_distribution('Na', 1.5)
    check('Na MR=1.5 interpolates between exact rows with a band',
          mid['ok'] and mid['evidence']['method'] == 'interpolated'
          and mid['band']['Q3'] == [46, 75])
    k2 = q_glass_distribution('K', 2.0)
    check('K MR=2.0 anchor: virtually only Q3 (78) small Q2/Q4',
          k2['ok'] and k2['values']['Q3'] == 78)
    check('out-of-range MR refused (UNSUPPORTED)',
          q_glass_distribution('Na', 4.5)['ok'] is False)
    check('unknown cation family refused naming the available ones',
          'Na' in q_glass_distribution('Li', 2.0)['suggestion'])


def test_transform():
    print('[glass → solution (Table 5.6)]')
    t = glass_to_solution_q(2.0)
    check('MR=2.0 maps glass (Q3=75) to solution (Q2=60)',
          t['ok'] and t['glass']['Q3'] == 75
          and t['solution']['Q2'] == 60)
    check('Q4-artifact caveat rides on every transform',
          any('artifact' in a for a in t['assumptions']))
    between = glass_to_solution_q(1.5)
    check('between-MR transform refused — fixed reference mappings '
          'only', between['ok'] is False)


def main():
    test_glass_curves()
    test_transform()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
