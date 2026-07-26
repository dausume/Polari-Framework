"""
Self-test for mtt-2 Part B sinter-1/2: the Master Sintering Curve
engine — the work-of-sintering integral (checked against its
closed-form isothermal value), the Θ->ρ master-curve mapping (with
its honest refusals), and mean-field grain growth (also analytically
checked).

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_sintering_engine
"""

import math
import sys

from pspp.sintering_engine import (
    C_TO_K, R_GAS, grain_size, relative_density, work_of_sintering,
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


# A plausible-order apparent activation energy (J/mol) — used only to
# exercise the math; the engine invents none of its own.
Q = 5.0e5
QG = 4.0e5


def test_isothermal_closed_form():
    print('[sinter-1: Θ matches the isothermal closed form]')
    T_C, minutes = 1200.0, 120.0
    T_K = T_C + C_TO_K
    dur_s = minutes * 60.0
    expected = dur_s * (1.0 / T_K) * math.exp(-Q / (R_GAS * T_K))
    got = work_of_sintering([{'hold_c': T_C, 'minutes': minutes}], Q)
    check('isothermal Θ ok', got['ok'])
    check('numeric Θ == closed form to 1e-9 relative',
          abs(got['theta'] - expected) <= 1e-9 * expected)
    check('logTheta reported', got['logTheta'] is not None)


def test_ramp_monotonic_and_additive():
    print('[sinter-1: ramp integration is sane]')
    ramp = work_of_sintering(
        [{'ramp_from_c': 25.0, 'ramp_to_c': 1200.0, 'minutes': 200.0}],
        Q)
    check('ramp Θ ok and positive', ramp['ok'] and ramp['theta'] > 0)
    # A hotter hold accumulates more work than a cooler one, same time.
    hot = work_of_sintering([{'hold_c': 1400.0, 'minutes': 60.0}], Q)
    cool = work_of_sintering([{'hold_c': 1000.0, 'minutes': 60.0}], Q)
    check('hotter hold accumulates more Θ (Arrhenius)',
          hot['theta'] > cool['theta'])
    # Θ of two concatenated holds == sum of each (additivity).
    a = work_of_sintering([{'hold_c': 1200.0, 'minutes': 30.0}], Q)
    b = work_of_sintering([{'hold_c': 1300.0, 'minutes': 45.0}], Q)
    ab = work_of_sintering(
        [{'hold_c': 1200.0, 'minutes': 30.0},
         {'hold_c': 1300.0, 'minutes': 45.0}], Q)
    check('schedule Θ is additive over segments',
          abs(ab['theta'] - (a['theta'] + b['theta']))
          <= 1e-9 * ab['theta'])


def test_work_refusals():
    print('[sinter-1: Θ refusals — no invented Q, honest schedule]')
    check('missing Q refuses, naming the fit requirement',
          work_of_sintering([{'hold_c': 1200, 'minutes': 60}],
                            None)['ok'] is False)
    check('non-positive Q refuses',
          work_of_sintering([{'hold_c': 1200, 'minutes': 60}],
                            -5)['ok'] is False)
    check('empty schedule refuses',
          work_of_sintering([], Q)['ok'] is False)
    check('malformed segment refuses',
          work_of_sintering([{'minutes': 60}], Q)['ok'] is False)
    check('zero-duration segment refuses',
          work_of_sintering([{'hold_c': 1200, 'minutes': 0}],
                            Q)['ok'] is False)


def _ready_master_curve():
    """A synthetic READY master curve ρ(log10 Θ) so the mapping can be
    tested; live seeding ships a provisional (refusing) row."""
    return {
        'name': 'test-master-curve', 'status': 'ready',
        'sourceReference': 'synthetic test curve', 'notes': '',
        'independentVariables': ['log10Theta'],
        'dependentVariables': ['relativeDensity'],
        'units': {'log10Theta': 'log10(s/K)',
                  'relativeDensity': 'fraction'},
        'sourceConditions': {}, 'interpolationPolicy': 'linear',
        'extrapolationPolicy': 'UNSUPPORTED',
        'validityDomain': {}, 'digitizationMethod': 'synthetic test',
        'digitizationError': '',
        'points': [
            {'log10Theta': -30.0, 'relativeDensity': 0.55},
            {'log10Theta': -25.0, 'relativeDensity': 0.72},
            {'log10Theta': -20.0, 'relativeDensity': 0.90},
            {'log10Theta': -15.0, 'relativeDensity': 0.97},
            {'log10Theta': -12.0, 'relativeDensity': 0.99},
        ],
        'qualitativeShape': '',
    }


def test_density_mapping_and_refusal():
    print('[sinter-1: ρ needs the master curve — honest split]')
    schedule = [{'ramp_from_c': 25.0, 'ramp_to_c': 1400.0,
                 'minutes': 240.0},
                {'hold_c': 1400.0, 'minutes': 120.0}]
    no_curve = relative_density(schedule, Q)
    check('no master curve -> Θ returned but ρ refused',
          no_curve['ok'] is False and no_curve.get('theta') is not None)
    curve = _ready_master_curve()  # domain covers this schedule's Θ
    work = work_of_sintering(schedule, Q)
    mapped = relative_density(schedule, Q, master_curve=curve)
    check('in-range ρ read from the curve (0<ρ<=1)',
          mapped['ok'] and 0.0 < mapped['relativeDensity'] <= 1.0)
    check('ρ carries the curve evidence + Θ',
          mapped['ok'] and mapped['evidence'] is not None
          and mapped['theta'] is not None)
    # Θ outside the curve's domain must refuse (no extrapolation).
    hot = [{'hold_c': 2200.0, 'minutes': 600.0}]
    over = relative_density(hot, Q, master_curve=curve)
    check('Θ past the curve domain refuses ρ, still returns Θ',
          over['ok'] is False and over.get('logTheta') is not None)
    # A provisional master curve always refuses.
    prov = dict(curve, status='provisional-low-confidence', points=[])
    check('provisional master curve refuses ρ',
          relative_density(schedule, Q, master_curve=prov)['ok']
          is False)


def test_grain_growth():
    print('[sinter-2: grain growth matches its isothermal closed '
          'form + refuses without kinetics]')
    T_C, minutes, d0, n, k0 = 1400.0, 120.0, 0.5, 3.0, 1.0e3
    T_K = T_C + C_TO_K
    dur_s = minutes * 60.0
    expected = (d0 ** n
                + k0 * math.exp(-QG / (R_GAS * T_K)) * dur_s) ** (1.0 / n)
    got = grain_size([{'hold_c': T_C, 'minutes': minutes}],
                     d0, n, k0, QG)
    check('grain growth ok', got['ok'])
    check('grain size == isothermal closed form to 1e-9 relative',
          abs(got['grainSizeUm'] - expected) <= 1e-9 * expected)
    check('grain grows from the initial size', got['grainSizeUm'] > d0)
    check('missing kinetics refuses (no invented growth law)',
          grain_size([{'hold_c': T_C, 'minutes': minutes}],
                     d0, None, k0, QG)['ok'] is False)
    check('longer firing grows larger grains',
          grain_size([{'hold_c': T_C, 'minutes': 240}],
                     d0, n, k0, QG)['grainSizeUm'] > got['grainSizeUm'])


def main():
    test_isothermal_closed_form()
    test_ramp_monotonic_and_additive()
    test_work_refusals()
    test_density_mapping_and_refusal()
    test_grain_growth()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
