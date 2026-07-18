"""
Selftest — aqp-5: atmospheric conditions + plant↔air gas exchange.

Run from polari-framework/:
    python3 -m aquaponics.selftest_atmosphere

Covers: VPD by Tetens with in/out-of-band findings; open air =
unlimited CO2; a sealed chamber depletes toward the photosynthesis
floor (days-to-floor hand-checked against the basil budget); a
ventilated tent settles to a steady CO2 that sustains; refusals.
"""

from types import SimpleNamespace

from aquaponics.atmosphere_analysis import (
    atmosphere_state, environment_gas_exchange,
    saturation_vapour_pressure_kpa,
)
from aquaponics.atmosphere_seed import SEED_ATMOSPHERES
from aquaponics.plant_seed import SEED_PLANTS, SEED_PLANT_PARTS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr():
    return SimpleNamespace(objectTables={
        'AtmosphereDefinition': _rows(SEED_ATMOSPHERES),
        'PlantDefinition': _rows(SEED_PLANTS),
        'PlantPart': _rows(SEED_PLANT_PARTS),
    })


if __name__ == '__main__':
    print('\naqp-5: atmosphere + gas exchange\n')

    print('atmospheric state (VPD, light)')
    m = _mgr()
    report = atmosphere_state(m, 'open-greenhouse')
    # T=24 RH=65 → VPD ~ 1.04 kPa, in band → no VPD finding.
    check('open greenhouse VPD ~1.04 kPa, in the healthy band',
          report['ok']
          and abs(report['vapourPressureDeficitKpa'] - 1.044) < 0.01
          and not any(f['kind'].startswith('vpd')
                      for f in report['findings']))
    report = atmosphere_state(m, 'ventilated-grow-tent')
    # T=25 RH=55 → VPD ~1.43 kPa → vpd-high.
    check('dry tent flags vpd-high',
          any(f['kind'] == 'vpd-high' for f in report['findings']))
    check('CO2 mass density = ppm * 1.8 mg/m3',
          report['co2MassDensityMgM3'] == round(420.0 * 1.8, 2))
    check('Tetens es monotonic in temperature',
          saturation_vapour_pressure_kpa(30)
          > saturation_vapour_pressure_kpa(20))
    report = atmosphere_state(m, 'no-such')
    check('unknown atmosphere honest 404',
          not report['ok'] and 'knownAtmospheres' in report)

    print('\nplant <-> air gas exchange')
    m = _mgr()
    report = environment_gas_exchange(m, 'sweet-basil',
                                      'open-greenhouse')
    check('open air = unlimited CO2 verdict',
          report['ok'] and report['verdict'] == 'open-air-unlimited')
    report = environment_gas_exchange(m, 'sweet-basil',
                                      'sealed-chamber')
    # usable = (800-200)*1.8*0.5 = 540 mg; net draw 710/day →
    # 0.761 days to floor.
    check('sealed chamber depletes, ~0.76 days to the CO2 floor',
          report['verdict'] == 'sealed-depleting'
          and abs(report['daysToPhotosynthesisFloor'] - 540 / 710)
          < 1e-3,
          str(report['daysToPhotosynthesisFloor']))
    check('the depletion suggestion names the ventilation knob',
          report['suggestion']['knob'] == 'air_exchange_per_hour')
    report = environment_gas_exchange(m, 'sweet-basil',
                                      'ventilated-grow-tent')
    # vent cap = 2*1.2*24*1.8 = 103.68 mg/ppm/day; steady =
    # 420 - 710/103.68 = 413.2 ppm >= 200 floor → sustains.
    check('ventilated tent settles to a sustaining steady CO2 '
          '(~413 ppm)',
          report['verdict'] == 'ventilation-sustains'
          and abs(report['steadyStateCo2Ppm'] - 413.2) < 0.5,
          str(report['steadyStateCo2Ppm']))
    report = environment_gas_exchange(m, 'no-such-plant',
                                      'open-greenhouse')
    check('unknown plant refused honestly', not report['ok'])

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
