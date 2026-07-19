"""
Self-test for pspp-1 digitized datasets + the generic interpolation
engine: exact-table reads, interpolation with honest bands, discrete
lookup policy, and the UNSUPPORTED-extrapolation refusals (invariant
I6) — hand-checked against the geopolymer book Ch.5 transcriptions.

Run from polari-framework/:
    python3 -m pspp.selftest_digitized_datasets
"""

import sys

from pspp.datasets_seed import SEED_DIGITIZED_DATASETS
from pspp.digitized_datasets import dataset_dict
from pspp.dataset_interpolation import read_dataset

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


DATASETS = {d['name']: d
            for d in (dataset_dict(s) for s in SEED_DIGITIZED_DATASETS)}


def test_seeds():
    print('[seed integrity]')
    check('seven Ch.5 datasets seeded (incl. Figs 5.4/5.5 glass Q '
          'curves)', len(DATASETS) == 7)
    check('every dataset carries a citation + UNSUPPORTED extrapolation',
          all(d['sourceReference'] and
              d['extrapolationPolicy'] == 'UNSUPPORTED'
              for d in DATASETS.values()))
    exact = ('na-silicate-solution-polymerization',
             'k-silicate-solution-polymerization',
             'na-siloxonate-glass-to-solution-q')
    check('table transcriptions carry zero digitization error',
          all(DATASETS[n]['digitizationError'] == '' for n in exact))
    q = DATASETS['na-siloxonate-glass-to-solution-q']
    check('Table 5.6: 8 rows (4 MRs x glass/solution)',
          len(q['points']) == 8)
    check('glass rows sum to exactly 100% (transcription sanity)', all(
        sum(p[f'Q{i}'] for i in range(5)) == 100
        for p in q['points'] if p['physical_state'] == 'glass'))
    sums = sorted(sum(p[f'Q{i}'] for i in range(5))
                  for p in q['points']
                  if p['physical_state'] == 'solution')
    check('solution rows kept AS PRINTED (sums 92/101/101/110 — the '
          'book anomaly is recorded, not silently rescaled)',
          sums == [92, 101, 101, 110]
          and 'sum_anomaly' in q['sourceConditions'])
    check('Q4-artifact caveat is recorded on the row',
          'artifact' in q['sourceConditions']['note'])


def test_exact_and_interpolated_reads():
    print('[Engler tables: exact + interpolated]')
    na = DATASETS['na-silicate-solution-polymerization']
    hit = read_dataset(na, {'MR': 2.09})
    check('exact MR hit returns the source row as literature evidence',
          hit['ok'] and hit['values']['molecular_weight'] == 160
          and hit['evidence']['method'] == 'literature')

    mid = read_dataset(na, {'MR': 2.0})
    check('MR=2.0 interpolates between 1.69 and 2.09 '
          '(MW=151, n~2.465)',
          mid['ok'] and abs(mid['values']['molecular_weight'] - 151) < 0.5
          and abs(mid['values']['polymerization_n'] - 2.465) < 0.005
          and mid['evidence']['method'] == 'interpolated')
    check('band spans the bracketing source points',
          mid['band']['molecular_weight'] == [120, 160])

    k = DATASETS['k-silicate-solution-polymerization']
    steep = read_dataset(k, {'MR': 3.8})
    check('K last interval (3.62-3.97) interpolates with the honestly '
          'wide band [320, 848]',
          steep['ok'] and steep['band']['molecular_weight'] == [320, 848])
    check('source note about the steep jump rides along as an '
          'assumption',
          any('3.97' in a for a in steep['assumptions']))

    low = read_dataset(na, {'MR': 0.2})
    check('below-range MR refused naming the range',
          low['ok'] is False and '[0.48, 3.3]' in low['refusal'])
    high = read_dataset(na, {'MR': 4.0})
    check('above-range MR refused (extrapolation UNSUPPORTED)',
          high['ok'] is False and 'UNSUPPORTED' in high['refusal'])


def test_discrete_lookup():
    print('[Table 5.6: discrete lookup, policy none]')
    q = DATASETS['na-siloxonate-glass-to-solution-q']
    sol = read_dataset(q, {'MR': 2.0, 'physical_state': 'solution'})
    check('MR=2.0 solution row reads exactly',
          sol['ok'] and sol['values'] ==
          {'Q0': 0, 'Q1': 25, 'Q2': 60, 'Q3': 25, 'Q4': 0})
    glass = read_dataset(q, {'MR': 3.28, 'physical_state': 'glass'})
    check('MR=3.28 glass row reads exactly',
          glass['ok'] and glass['values']['Q4'] == 43)

    between = read_dataset(q, {'MR': 1.5, 'physical_state': 'glass'})
    check('in-between MR refused (fixed reference mappings only), '
          'listing the listed MRs',
          between['ok'] is False and '1.33' in between['suggestion'])

    noState = read_dataset(q, {'MR': 2.0})
    check('missing physical_state selector refused with the options',
          noState['ok'] is False and 'glass' in noState['suggestion'])


def test_viscosity_log_linear():
    print('[Fig 5.20: log-linear over series]')
    v = DATASETS['silicate-solution-viscosity-vs-temperature']
    na = read_dataset(v, {'series': 'Na-silicate MR=2',
                          'temperature_C': 12.5})
    check('Na 12.5C log-linear between 4500 and 3000 (~3674 cP)',
          na['ok'] and abs(na['values']['viscosity_cP'] - 3674) < 1)
    kk = read_dataset(v, {'series': 'K-silicate MR=2.2',
                          'temperature_C': 5})
    check('K series exact hit 420 cP', kk['ok']
          and kk['values']['viscosity_cP'] == 420)
    check('unstated-concentration caveat rides as an assumption',
          any('NOT stated' in a for a in na['assumptions']))
    hot = read_dataset(v, {'series': 'Na-silicate MR=2',
                           'temperature_C': 40})
    check('40C refused — outside [5, 30]',
          hot['ok'] is False and '[5, 30]' in hot['refusal'])
    noSeries = read_dataset(v, {'temperature_C': 15})
    check('missing series selector refused with both series named',
          noSeries['ok'] is False and 'K-silicate' in
          str(noSeries['suggestion']))


def test_provisional_refusal():
    print('[Fig 5.22: provisional dataset refuses]')
    sol = DATASETS['na-siloxonate-solubility-vs-temperature']
    r = read_dataset(sol, {'series': 'MR=1 Na-metasilicate pentahydrate',
                           'temperature_C': 40})
    check('provisional-low-confidence dataset refused until re-shoot',
          r['ok'] is False and 'provisional' in r['refusal'])
    check('refusal suggestion points at the data-entry knob',
          'status=ready' in r['suggestion'])
    check('qualitative shape is still recorded for the page',
          'rise with temperature' in sol['qualitativeShape'])


def main():
    test_seeds()
    test_exact_and_interpolated_reads()
    test_discrete_lookup()
    test_viscosity_log_linear()
    test_provisional_refusal()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
