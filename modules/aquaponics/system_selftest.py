"""
Selftest — aqp-6: bound pot-system survival + environmental impact +
the scoring bridge.

Run from polari-framework/:
    python3 -m aquaponics.system_selftest

Covers: survival supply-vs-demand (nutrients delivered by flow meet
the plant; the ventilated tent survives, the sealed chamber FAILS on
CO2 with the limiting factor named); lifetime impact (permanent
carbon, N/P removed from the loop, water throughput) matching the
seeded snapshot; and the context-scoring engine ranking the two
systems live through the objectRef seam into impact_result_json.
"""

from types import SimpleNamespace

from aquaponics.atmosphere_seed import SEED_ATMOSPHERES
from aquaponics.growth_media_basis import (  # noqa: F401 (registered types)
    NutrientProfile,
)
from aquaponics.media_seed import (
    SEED_NUTRIENT_PROFILES, SEED_WATERS,
)
from aquaponics.plant_seed import SEED_PLANTS, SEED_PLANT_PARTS
from aquaponics.pot_seed import SEED_POTS, SEED_POT_HOLES
from aquaponics.pot_system_basis import system_impact, system_survival
from aquaponics.pot_system_seed import (
    SEED_AQP_CONTEXTUALIZED_VALUES, SEED_AQP_SCORE_CONCEPTS,
    SEED_AQP_SCORE_SUBJECTS, SEED_AQP_SCORE_TERMS, SEED_POT_SYSTEMS,
)
from scoring.custom.scoring_engine import score_concept

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**{'pre_normalized_value': None, **r})
            for i, r in enumerate(seed_list)}


def _mgr():
    return SimpleNamespace(objectTables={
        'PotDefinition': _rows(SEED_POTS),
        'PotHole': _rows(SEED_POT_HOLES),
        'WaterDefinition': _rows(SEED_WATERS),
        'NutrientProfile': _rows(SEED_NUTRIENT_PROFILES),
        'PlantDefinition': _rows(SEED_PLANTS),
        'PlantPart': _rows(SEED_PLANT_PARTS),
        'AtmosphereDefinition': _rows(SEED_ATMOSPHERES),
        'PotSystemDefinition': _rows(SEED_POT_SYSTEMS),
        'ScoreTerm': _rows(SEED_AQP_SCORE_TERMS),
        'ScoreSubject': _rows(SEED_AQP_SCORE_SUBJECTS),
        'ContextualizedValue': _rows(SEED_AQP_CONTEXTUALIZED_VALUES),
        'ScoreConcept': _rows(SEED_AQP_SCORE_CONCEPTS),
        'ScoreContext': {},
    })


if __name__ == '__main__':
    print('\naqp-6: pot-system survival + impact + scoring\n')

    print('survival (supply vs the plant per-part demand)')
    m = _mgr()
    report = system_survival(m, 'basil-aquaponic-tent')
    # No deficiency, but the tent's high VPD makes it 'stressed' — the
    # honest read (marginal, not failing).
    check('ventilated tent: no deficiency (survives, VPD-stressed)',
          report['ok'] and report['verdict'] == 'stressed'
          and not report['limitingFactors'],
          str(report['limitingFactors']))
    check('the stressor is the marginal VPD (not a nutrient/gas fail)',
          any(f['factor'] == 'vapour-pressure-deficit'
              and f['status'] == 'marginal'
              for f in report['factors']))
    nutrients = {f['factor']: f for f in report['factors']
                 if f['kind'] == 'nutrient'}
    check('flow delivers nitrate well above the plant need (met)',
          nutrients['nitrate-n']['status'] == 'met'
          and nutrients['nitrate-n']['supplyMgDay'] > 20)
    co2 = next(f for f in report['factors']
               if f['factor'] == 'atmospheric-co2')
    check('CO2 met via the ventilation-sustains verdict',
          co2['status'] == 'met')
    report = system_survival(m, 'basil-aquaponic-sealed')
    check('sealed chamber: the plant FAILS on CO2 (limiting named)',
          report['verdict'] == 'fails'
          and 'atmospheric-co2' in report['limitingFactors'])

    print('\nlifetime impact')
    m = _mgr()
    report = system_impact(m, 'basil-aquaponic-tent')
    imp = report['impact']
    check('permanent carbon 1.76g + CO2e ~6.45g',
          report['ok'] and imp['permanentCarbonG'] == 1.76
          and abs(imp['co2EquivalentSequesteredG'] - 6.4533) < 1e-3)
    # N removed = (20 + 3) mg/day * 73.7 effective days = 1695.1...
    # nitrate 20 + ammonium 3 = 23/day; lifetimeNetMg each rounds
    # then sums.
    check('nitrogen removed from the loop is reported (~1694 mg)',
          abs(imp['nitrogenRemovedMg'] - 1694.1) < 5.0,
          str(imp['nitrogenRemovedMg']))
    check('water throughput = flow 1.5 L/hr x 24 x 120 days = 4320 L',
          imp['waterThroughputL'] == 4320.0)
    check('impact persisted to impact_result_json',
          'permanentCarbonG' in
          m.objectTables['PotSystemDefinition'][0].impact_result_json)
    check('the note refuses to greenwash captured as sequestered',
          'LOCKED' in report['note'])

    print('\nscoring bridge (rank systems by impact, live objectRef)')
    m = _mgr()
    score = score_concept(m, 'pot-environmental-impact')
    check('the environmental-impact concept scores both systems',
          score['ok'] and len(score['subjects']) == 2)
    bee = score['subjects'][0]
    check('permanent carbon resolves live through the objectRef seam',
          any(b.get('found') and b.get('term')
              == 'permanent-carbon-sequestered'
              and abs(b.get('raw') - 1.76) < 1e-6
              for b in bee['breakdown']))
    check('both systems produce a levelized score',
          all(s['levelizedScore'] is not None
              for s in score['subjects']))

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
