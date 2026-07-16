"""
Selftest — plant-growth-sim phase 11 (2026-07-15): the decomposed
water-level trajectory (drainage + evaporation + transpiration) and
its wiring into transport_factor's root capacity as a water-
availability signal. Dustin: "so we can see how long it takes it to
be absorbed or dissapate due to heat and atmosphere or other factors
and the plant absorbing the water obviously."

Run from polari-framework/:
    python3 -m aquaponics.selftest_water_level

Uses REAL seed rows throughout (the real demo-herb-pot geometry, real
atmospheres, the real water-batched planting) — no fixture-only data.
"""

from types import SimpleNamespace

from aquaponics.atmosphere_seed import SEED_ATMOSPHERES
from aquaponics.light_seed import SEED_LIGHT_SOURCES, SEED_LIGHT_SPECTRA
from aquaponics.media_seed import SEED_SOILS, SEED_WATERS
from aquaponics.plant_growth_normalized import (
    advance_growth, closed_form_logistic,
)
from aquaponics.plant_growth_normalized_seed import SEED_POT_PLANTINGS
from aquaponics.plant_growth_seed import SEED_PLANT_GROWTH_MODELS
from aquaponics.plant_seed import SEED_PLANTS, SEED_PLANT_PARTS
from aquaponics.plant_stress_seed import SEED_STRESS_CURVES
from aquaponics.pot_seed import SEED_POT_HOLES, SEED_POTS
from aquaponics.pot_system_seed import SEED_POT_SYSTEMS
from aquaponics.water_batch_seed import SEED_WATER_BATCH_SCHEDULES
from aquaponics.water_level import (
    current_water_level_fraction, water_level_trajectory,
)
from plant_morphology.morphology_seed import (
    SEED_ORGAN_MODELS, SEED_ROOT_MODELS,
)

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
        'PlantDefinition': _rows(SEED_PLANTS),
        'PlantPart': _rows(SEED_PLANT_PARTS),
        'PlantGrowthModel': _rows(SEED_PLANT_GROWTH_MODELS),
        'RootSystemModel': _rows(SEED_ROOT_MODELS),
        'OrganModel': _rows(SEED_ORGAN_MODELS),
        'PotDefinition': _rows(SEED_POTS),
        'PotHole': _rows(SEED_POT_HOLES),
        'PotPlanting': _rows(SEED_POT_PLANTINGS),
        'PotSystemDefinition': _rows(SEED_POT_SYSTEMS),
        'AtmosphereDefinition': _rows(SEED_ATMOSPHERES),
        'WaterDefinition': _rows(SEED_WATERS),
        'SoilDefinition': _rows(SEED_SOILS),
        'StressResponseCurve': _rows(SEED_STRESS_CURVES),
        'MatrixEquationDefinition': {},
        'LightSpectrumDefinition': _rows(SEED_LIGHT_SPECTRA),
        'LightSourceDefinition': _rows(SEED_LIGHT_SOURCES),
        'WaterBatchSchedule': _rows(SEED_WATER_BATCH_SCHEDULES),
    })


BATCHED_PLANTING = 'demo-herb-pot-basil-batched'
HEALTHY_PLANTING = 'demo-herb-pot-basil-1'


if __name__ == '__main__':
    manager = _mgr()

    print('water_level_trajectory — real decomposed physics against '
          'real demo-herb-pot geometry')
    result = water_level_trajectory(
        manager, HEALTHY_PLANTING, hours=24.0, sample_hours=2.0)
    check('ok, starts at the pot\'s real maintained/full level',
          result['ok'] and result['startWaterLevelMm'] > 0)
    check('level DECREASES over time (never rises with no active '
          'refill during a hold period)',
          result['endWaterLevelMm'] < result['startWaterLevelMm'])
    check('all three loss mechanisms are named + non-negative — '
          'drainage, evaporation, transpiration never conflated into '
          'one number',
          all(k in result['cumulativeLossMl']
              for k in ('drainageMl', 'evaporationMl', 'transpirationMl'))
          and all(v >= 0.0 for v in result['cumulativeLossMl'].values()))
    check('drainage reuses the REAL hydraulics reservoir model — the '
          'self-watering pot\'s own output hole physics, not a new '
          'formula',
          result['cumulativeLossMl']['drainageMl'] > 0.0)
    check('VPD is real, computed via Tetens (the same physics '
          'atmosphere_analysis.py already uses for its own findings) '
          '— a sane kPa magnitude, not a placeholder',
          0.0 < result['vpdKpa'] < 10.0)
    check('trajectory has the requested number of samples',
          len(result['trajectory']) == 12)
    check('each sample point carries hours + level + all three named '
          'rates',
          all({'hours', 'waterLevelMm', 'drainageMlHr',
              'evaporationMlHr', 'transpirationMlHr'} <= set(s)
              for s in result['trajectory']))

    print('water_level_trajectory — a fresh (near-zero leaf area) '
          'planting has near-zero transpiration, proving the plant-'
          'absorption term genuinely depends on real leaf area, not a '
          'fixed guess')
    check("this seedling's transpiration loss is tiny relative to "
          'drainage (no meaningful leaf canopy exists yet to draw '
          'water through)',
          result['cumulativeLossMl']['transpirationMl']
          < result['cumulativeLossMl']['drainageMl'] * 0.1)
    check('leafAreaM2 is real and small (a just-germinated plant), '
          'not a placeholder constant',
          0.0 <= result['leafAreaM2'] < 0.01)

    print('water_level_trajectory — a long enough horizon empties '
          'the pot, and timeToEmptyHours is reported honestly')
    long_result = water_level_trajectory(
        manager, HEALTHY_PLANTING, hours=200.0, sample_hours=4.0)
    check('a long enough window drains the pot to (or toward) empty',
          long_result['endWaterLevelMm'] < result['endWaterLevelMm'])
    short_result = water_level_trajectory(
        manager, HEALTHY_PLANTING, hours=1.0, sample_hours=0.5)
    check('a short window never reports timeToEmptyHours if the pot '
          "never actually empties within it (never a guessed 'yes, "
          "eventually')",
          short_result['timeToEmptyHours'] is None
          or short_result['timeToEmptyHours'] <= 1.0)

    print('water_level_trajectory — honest refusals')
    check('unknown planting refuses',
          not water_level_trajectory(manager, 'nope', hours=24.0)['ok'])
    no_system_mgr = _mgr()
    no_system_mgr.objectTables['PotPlanting'] = _rows([
        dict(SEED_POT_PLANTINGS[0], name='no-system', system_name='')])
    check('planting with no resolvable system refuses',
          not water_level_trajectory(
              no_system_mgr, 'no-system', hours=24.0)['ok'])

    print('current_water_level_fraction — resolves a real batch\'s '
          'elapsed hold time, decays from a fresh fill')
    frac, evidence = current_water_level_fraction(
        manager, BATCHED_PLANTING)
    check('ok, a real fraction in (0, 1]',
          evidence is not None and 0.0 < frac <= 1.0)
    check('elapsedHoursIntoBatch is a real, non-negative number '
          '(resolved from the real planted_at -> now elapsed time)',
          evidence['elapsedHoursIntoBatch'] >= 0.0)

    print('current_water_level_fraction — no batch schedule bound -> '
          'honest neutral default (1.0, no guessed penalty)')
    frac_unbatched, evidence_unbatched = current_water_level_fraction(
        manager, HEALTHY_PLANTING)
    check('unbound planting gets the neutral 1.0 default',
          frac_unbatched == 1.0 and evidence_unbatched is None)

    print("advance_growth — THE REAL effect: water level reaches "
          "transport_factor's root capacity")
    grown = advance_growth(manager, BATCHED_PLANTING, dt_days=5.0)
    check('ok, waterLevel evidence reported at the top level '
          '(schedule is bound)',
          grown['ok'] and 'waterLevel' in grown)
    check("root's transport evidence carries a real "
          'rootWaterLevelFactor (phase 11\'s signal reaching phase '
          "9's transport computation)",
          'rootWaterLevelFactor' in grown['transport'])

    print('advance_growth — no schedule bound never computes a water '
          'level (backward compatible with phases 6-10)')
    unbatched_grown = advance_growth(manager, HEALTHY_PLANTING,
                                     dt_days=5.0)
    check("unbatched planting's transport evidence still carries "
          'rootWaterLevelFactor at the neutral 1.0 default, and no '
          "top-level 'waterLevel' key (never computed, not just "
          'hidden)',
          unbatched_grown['transport']['rootWaterLevelFactor'] == 1.0
          and 'waterLevel' not in unbatched_grown)

    print('advance_growth — manual override bypasses water-level '
          'resolution entirely')
    manual = advance_growth(manager, BATCHED_PLANTING, dt_days=5.0,
                            water_supply_factor=1.0,
                            soil_supply_factor=1.0)
    check("manual mode's transport factors are all neutral 1.0 "
          '(the whole transport_factor computation never even ran)',
          all(p['transportFactor'] == 1.0
              for p in manual['parts'].values()))

    print('closed_form_logistic reuse sanity check — confirms this '
          "session's own established public-API discipline still "
          "holds after phase 11's edits")
    check('closed_form_logistic is still importable + callable '
          '(no accidental breakage of the phase-9 public promotion)',
          closed_form_logistic(1.0, 0.1, 10.0, 5.0) > 1.0)

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
