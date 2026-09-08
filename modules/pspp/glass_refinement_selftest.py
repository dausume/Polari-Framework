"""
Self-test for the mtt-2 glass core, refinement half: viscosity
reference points as data, the EXACT closed-form VFT fit (passes
through its anchors, honest residuals elsewhere, refuses outside its
span), the fining/forming/annealing/devit windows, and the process
map that grades them at a temperature.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.glass_refinement_selftest
"""

import sys

from pspp.custom.glass_refinement import (
    GLASS_DIGITIZED_DATASETS, GLASS_THRESHOLD_WINDOWS,
    GLASS_TRANSITION_C, LIQUIDUS_C, REFERENCE_POINTS, fit_vft,
    process_map, refinement_report, viscosity_at,
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


def test_reference_points():
    print('[fixed points: definitions + cited temperatures]')
    check('5 reference points seeded', len(REFERENCE_POINTS) == 5)
    logs = [p['log10ViscosityPaS'] for p in REFERENCE_POINTS]
    check('fixed-point log viscosities are the standard definitions',
          logs == [1.0, 3.0, 6.6, 12.0, 13.5])
    temps = [p['temperatureC'] for p in REFERENCE_POINTS]
    check('temperatures fall monotonically as viscosity rises',
          temps == sorted(temps, reverse=True))
    ds = {d['name']: d for d in GLASS_DIGITIZED_DATASETS}
    check('viscosity points dataset is READY with points',
          ds['soda-lime-viscosity-reference-points']['status']
          == 'ready'
          and ds['soda-lime-viscosity-reference-points']['points_json']
          != '[]')
    check('devit TTT dataset is provisional + points-empty (refuses)',
          ds['soda-lime-devitrification-ttt']['status']
          == 'provisional-low-confidence'
          and ds['soda-lime-devitrification-ttt']['points_json']
          == '[]')
    check('viscous master curve dataset is provisional + '
          'points-empty (refuses)',
          ds['glass-frit-viscous-sintering-master-curve']['status']
          == 'provisional-low-confidence')
    check('every dataset names its DATA ASK or upgrade path',
          all('DATA ASK' in d['notes']
              for d in GLASS_DIGITIZED_DATASETS))


def test_vft_fit():
    print('[VFT: exact through anchors, honest residuals, physical]')
    fit = fit_vft()
    check('fit succeeds on the seeds', fit['ok'])
    check('anchor residuals are exactly zero',
          all(abs(r['residual']) < 1e-9 for r in fit['residuals']
              if r['temperatureC'] in fit['anchorsC']))
    check('non-anchor residuals are reported and small '
          '(< 0.6 log units)',
          all(abs(r['residual']) < 0.6 for r in fit['residuals']))
    check('solved constants are classic soda-lime territory '
          '(A ~ -3, B ~ 5000 K, T0 ~ 200 C)',
          -4.0 < fit['A'] < -2.0 and 4000 < fit['B_K'] < 6000
          and 150 < fit['T0_C'] < 300)
    check('too few points refuse',
          fit_vft([{'temperatureC': 500, 'log10ViscosityPaS': 13},
                   {'temperatureC': 700, 'log10ViscosityPaS': 7}])
          ['ok'] is False)
    check('malformed points refuse',
          fit_vft([{'temperatureC': 'x'}])['ok'] is False)


def test_viscosity_reads():
    print('[viscosity_at: in-span reads, out-of-span refusals]')
    v = viscosity_at(725.0)
    check('softening point reads back its defined viscosity',
          v['ok'] and abs(v['log10ViscosityPaS'] - 6.6) < 1e-9)
    check('working point reproduces within the fit residual',
          abs(viscosity_at(1025.0)['log10ViscosityPaS'] - 3.0) < 0.2)
    check('viscosity falls monotonically with temperature',
          viscosity_at(600.0)['log10ViscosityPaS']
          > viscosity_at(900.0)['log10ViscosityPaS']
          > viscosity_at(1400.0)['log10ViscosityPaS'])
    check('below the strain point refuses (UNSUPPORTED)',
          viscosity_at(200.0)['ok'] is False)
    check('above practical melting refuses (UNSUPPORTED)',
          viscosity_at(1600.0)['ok'] is False)
    check('non-numeric temperature refuses',
          viscosity_at('hot')['ok'] is False)


def test_windows():
    print('[windows: gates as data, devit zone bounded]')
    check('4 banded windows seeded',
          len(GLASS_THRESHOLD_WINDOWS) == 4)
    check('all are condition-gates (they open/close operations)',
          all(w['window_role'] == 'condition-gate'
              for w in GLASS_THRESHOLD_WINDOWS))
    from pspp.threshold_windows_basis import (
        banded_window_dict, validate_banded_window,
    )
    check('every window validates (ordered/contiguous/full-cover)',
          all(validate_banded_window(banded_window_dict(w))['ok']
              for w in GLASS_THRESHOLD_WINDOWS))
    check('devit zone spans glass transition -> liquidus',
          GLASS_TRANSITION_C < LIQUIDUS_C)


def test_process_map():
    print('[process map: the right operations open at each T]')
    working = process_map(1025.0)
    gates = {g['window']: g for g in working['gates']}
    check('at the working point forming is OPEN',
          gates['silicate-glass:forming-gate']['open'])
    check('at the working point fining is CLOSED',
          not gates['silicate-glass:fining-gate']['open'])
    check('at the working point devit risk is flagged (marginal)',
          gates['soda-lime-glass:devitrification-risk']['grade']
          == 'marginal')
    anneal = {g['window']: g for g in process_map(530.0)['gates']}
    check('at 530C the annealing window is OPEN',
          anneal['silicate-glass:annealing-gate']['open'])
    check('at 530C forming is CLOSED',
          not anneal['silicate-glass:forming-gate']['open'])
    melt = {g['window']: g for g in process_map(1450.0)['gates']}
    check('at practical melting fining is OPEN',
          melt['silicate-glass:fining-gate']['open'])
    check('above the liquidus devit risk clears (crystals '
          'redissolve)',
          melt['soda-lime-glass:devitrification-risk']['grade']
          == 'ideal')
    cold = process_map(200.0)
    cold_gates = [g for g in cold['gates']
                  if g['window'].startswith('silicate-glass')]
    check('out-of-span temperature: viscosity gates refuse in '
          'place, not fake',
          all(g.get('ok') is False for g in cold_gates))


def test_report():
    print('[refinement report: one honest payload]')
    rep = refinement_report()
    check('report carries points + fit + windows + devit ask',
          rep['ok'] and len(rep['referencePoints']) == 5
          and rep['vftFit']['ok'] and len(rep['windows']) == 4
          and 'REFUSED' in rep['devitrification']['kinetics'])


def main():
    test_reference_points()
    test_vft_fit()
    test_viscosity_reads()
    test_windows()
    test_process_map()
    test_report()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
