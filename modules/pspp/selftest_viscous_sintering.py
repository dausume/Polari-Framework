"""
Self-test for the mtt-2 glass core, viscous-sintering half: the
reduced viscous work Λ (checked against its closed-form isothermal
value), the Frenkel early stage (with its validity refusal naming the
asks), the Mackenzie-Shuttleworth final stage from a measured
checkpoint, the amorphous L2 structure plan (no grain row — glass has
no grains), and the master-curve read path.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_viscous_sintering
"""

import math
import sys

from pspp.glass_refinement import fit_vft
from pspp.viscous_sintering import (
    DEFAULT_SURFACE_TENSION, FRENKEL_MAX_SHRINKAGE, MS_MIN_DENSITY,
    frenkel_density, ms_final_stage, plan_viscous_structure,
    viscous_fire, viscous_work,
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


#: Coarse frit + a mild soak — inside Frenkel validity.
COARSE = 100.0
SOAK = [{'hold_c': 650.0, 'minutes': 60.0}]


def test_lambda_closed_form():
    print('[Λ matches the isothermal closed form]')
    fit = fit_vft()
    eta = 10.0 ** (fit['A'] + fit['B_K']
                   / (650.0 - fit['T0_C']))
    gamma = DEFAULT_SURFACE_TENSION['value_n_per_m']
    expected = gamma / (eta * COARSE * 1e-6) * 3600.0
    got = viscous_work(SOAK, COARSE)
    check('viscous work ok', got['ok'])
    check('Λ == closed form to 1e-9 relative',
          abs(got['lambda'] - expected) <= 1e-9 * expected)
    check('log10Lambda consistent',
          abs(got['log10Lambda'] - math.log10(expected)) < 1e-9)
    check('the γ default is surfaced in assumptions (cited, not '
          'silent)',
          any('Scholze' in a for a in got['assumptions']))
    hotter = viscous_work([{'hold_c': 700.0, 'minutes': 60.0}],
                          COARSE)
    check('hotter soak does more viscous work',
          hotter['lambda'] > got['lambda'])
    finer = viscous_work(SOAK, 1.0)
    check('finer frit does more viscous work (1/r)',
          abs(finer['lambda'] - got['lambda'] * 100.0)
          <= 1e-9 * finer['lambda'])


def test_work_refusals():
    print('[Λ refusals: schedule, radius, γ, span]')
    check('empty schedule refuses',
          viscous_work([], COARSE)['ok'] is False)
    check('missing particle radius refuses (Λ scales as 1/r)',
          viscous_work(SOAK, None)['ok'] is False)
    check('nonpositive radius refuses',
          viscous_work(SOAK, -3.0)['ok'] is False)
    check('nonpositive γ refuses',
          viscous_work(SOAK, COARSE, gamma_n_per_m=0)['ok'] is False)
    hot = viscous_work([{'hold_c': 1500.0, 'minutes': 10.0}], COARSE)
    check('schedule above the viscosity fit span refuses (no '
          'invented high-T viscosity)',
          hot['ok'] is False and 'no invented' in hot['refusal'])
    cold = viscous_work(
        [{'ramp_from_c': 25.0, 'ramp_to_c': 400.0, 'minutes': 60.0}],
        COARSE)
    check('time entirely below the rigid floor accumulates ZERO Λ',
          cold['ok'] and cold['lambda'] == 0.0)


def test_frenkel():
    print('[Frenkel early stage: densify, then refuse honestly]')
    lam = viscous_work(SOAK, COARSE)['lambda']
    got = frenkel_density(lam, 0.60)
    check('early-stage densification ok', got['ok'])
    check('density rises from green', got['relativeDensity'] > 0.60)
    check('shrinkage is (3/8)Λ',
          abs(got['linearShrinkage'] - 0.375 * lam) < 1e-12)
    check('no green density -> refuses (measure, don\'t assume)',
          frenkel_density(lam, None)['ok'] is False)
    big = frenkel_density(FRENKEL_MAX_SHRINKAGE * 8.0 / 3.0 + 0.1,
                          0.60)
    check('past validity refuses', big['ok'] is False)
    check('the refusal names BOTH ways onward (master curve + '
          'measured checkpoint)',
          'master-curve' in big['suggestion']
          and 'Mackenzie' in big['suggestion'])
    check('fine frit at 700C blows past Frenkel validity '
          '(physically real - frit sinters in minutes)',
          frenkel_density(
              viscous_work([{'hold_c': 700.0, 'minutes': 60.0}],
                           1.0)['lambda'], 0.60)['ok'] is False)


def test_ms_final_stage():
    print('[MS final stage: from a MEASURED checkpoint only]')
    got = ms_final_stage(SOAK, 0.92, 10.0)
    check('final stage ok from measured closed-pore state',
          got['ok'])
    check('density rises toward full', 1.0 > got['relativeDensity']
          > 0.92)
    lam_pore = viscous_work(SOAK, 10.0)['lambda']
    expected = 1.0 - (1.0 - 0.92) * math.exp(-1.5 * lam_pore)
    check('MS closed form exact',
          abs(got['relativeDensity'] - expected) < 1e-12)
    check('no measured checkpoint -> refuses',
          ms_final_stage(SOAK, None, None)['ok'] is False)
    check(f'open-pore density (< {MS_MIN_DENSITY}) refuses',
          ms_final_stage(SOAK, 0.7, 10.0)['ok'] is False)


def test_structure_plan():
    print('[amorphous L2 plan: matrix + pores, NO grain row]')
    plan = plan_viscous_structure('soda-lime-frit#sintered', 0.95,
                                  particle_radius_um=COARSE)
    check('plan ok', plan['ok'])
    kinds = [r['domain_type'] for r in plan['proposedRows']]
    check('rows are amorphous-matrix + capillary-pore',
          kinds == ['amorphous-matrix', 'capillary-pore'])
    check('NO grain-domain row (glass has no grains)',
          'grain-domain' not in kinds)
    check('porosity = 1 - rho',
          abs(plan['totalPorosity'] - 0.05) < 1e-9)
    check('matrix phaseFractions declare amorphous',
          plan['proposedRows'][0]['descriptors_json']
          ['phaseFractions'] == {'amorphous': 1.0})
    check('no state_key refuses',
          plan_viscous_structure('', 0.95)['ok'] is False)
    check('bad density refuses',
          plan_viscous_structure('x#y', 1.5)['ok'] is False)


def test_fire_orchestration():
    print('[viscous_fire: honest in place, refusals rendered]')
    out = viscous_fire(SOAK, COARSE, green_density=0.60,
                       state_key='soda-lime-frit#test')
    check('fire ok with Λ + Frenkel ρ + structure plan',
          out['ok'] and out['work']['ok'] and out['density']['ok']
          and len(out['structurePlan']['proposedRows']) == 2)
    hot = viscous_fire([{'hold_c': 700.0, 'minutes': 60.0}], 1.0,
                       green_density=0.60)
    check('fine/hot: Λ computes but ρ refuses in place '
          '(past Frenkel validity)',
          hot['ok'] and hot['work']['ok']
          and hot['density']['ok'] is False)
    ms = viscous_fire(SOAK, COARSE, green_density=0.60,
                      measured={'density': 0.92,
                                'poreRadiusUm': 10.0},
                      state_key='soda-lime-frit#final')
    check('measured checkpoint runs the MS final stage',
          ms['finalStage']['ok'])
    check('structure plan follows the final stage when it exists',
          abs(ms['structurePlan']['relativeDensity']
              - round(ms['finalStage']['relativeDensity'], 6))
          < 1e-9)
    curve = {
        'name': 'test-frit-curve', 'status': 'ready',
        'independentVariables': ['log10Lambda'],
        'dependentVariables': ['relativeDensity'],
        'interpolationPolicy': 'linear',
        'extrapolationPolicy': 'UNSUPPORTED',
        'validityDomain': {}, 'sourceConditions': {},
        'digitizationError': '', 'sourceReference': 'test row',
        'digitizationMethod': 'synthetic selftest points',
        'points': [{'log10Lambda': -3.0, 'relativeDensity': 0.62},
                   {'log10Lambda': 0.0, 'relativeDensity': 0.9},
                   {'log10Lambda': 1.0, 'relativeDensity': 0.99}],
    }
    mc = viscous_fire(SOAK, COARSE, master_curve=curve)
    check('a ready master curve reads ρ (stage master-curve)',
          mc['density']['ok']
          and mc['density']['stage'] == 'master-curve'
          and 0.62 < mc['density']['relativeDensity'] < 0.99)


def main():
    test_lambda_closed_form()
    test_work_refusals()
    test_frenkel()
    test_ms_final_stage()
    test_structure_plan()
    test_fire_orchestration()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
