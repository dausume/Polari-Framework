"""
Self-test for the pspp-V3 benchmark overlay: measured-vs-predicted
sections with honest verdicts (match where engines predict, refusal
where laws are absent, recorded elsewhere).

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_benchmark_cases
"""

import sys

from pspp.benchmark_cases import (
    SEED_BENCHMARK_CASES, benchmark_catalog, benchmark_overlay_by_name,
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


def _sections(name):
    overlay = benchmark_overlay_by_name(None, name)
    return overlay, {s['aspect']: s for s in overlay['sections']}


def main():
    print('[catalog]')
    catalog = benchmark_catalog(None)
    check('three benchmark cases seeded with citations',
          len(catalog['benchmarks']) == 3
          and all(b['source'] for b in catalog['benchmarks']))
    check('unknown case refused',
          benchmark_overlay_by_name(None, 'ghost')['ok'] is False)

    print('[mk750-na-pss-mr182 — the flagship validation]')
    overlay, by = _sections('mk750-na-pss-mr182')
    check('windows verdict is match (inside all Table A ranges)',
          by['windows']['verdict'] == 'match')
    check('frameworks match: observed nepheline+albite subset of '
          'predicted open routes',
          by['frameworks']['verdict'] == 'match')
    predicted = {f['framework'] for f in
                 by['frameworks']['predicted']['reachableFrameworks']}
    check('phillipsite correctly NOT predicted at MR=1.82 (Q0 gate '
          'closed)', 'framework-phillipsite' not in predicted)
    check('cure section is an honest refusal (off-table MR, no law)',
          by['cure']['verdict'] == 'refusal')
    check('as-printed anomaly preserved in inputs',
          'never reconciled silently'
          in overlay['inputs']['as_printed_discrepancy'])

    print('[mk750-k-silicate-kalsilite-mixture — K validation]')
    overlay, by = _sections('mk750-k-silicate-kalsilite-mixture')
    check('K ratios grade match through the BANDED p.193 windows',
          by['windows']['verdict'] == 'match'
          and any(g.get('windowKind') == 'banded'
                  for g in by['windows']['predicted']['graded']))
    check('kalsilite reachable via the K ortho-sialate twin rule',
          by['frameworks']['verdict'] == 'match')
    predicted = {f['framework'] for f in
                 by['frameworks']['predicted']['reachableFrameworks']}
    check('leucite correctly NOT predicted at MR=1.80 (Q0 gate)',
          'framework-leucite' not in predicted)

    print('[mk750-na-silicate-mr170-curing-series]')
    overlay, by = _sections('mk750-na-silicate-mr170-curing-series')
    check('cure refusal sits beside the measured dataset pointer',
          by['cure']['verdict'] == 'refusal'
          and by['cure']['measured']['datasets']
          == ['mk750-strength-ph-vs-curing-time'])
    check('measured strength series recorded as-printed',
          'series' in by['cure']['measured'])

    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
