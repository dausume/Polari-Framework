"""
Selftest — aqp-4: per-part plant carbon/nutrient capture + budget.

Run from polari-framework/:
    python3 -m aquaponics.selftest_plant

Covers: per-part structural mass + carbon capture by volume
(hand-computed); the CAPTURED vs PERMANENTLY-SEQUESTERED honesty
(basil roots are soil-incorporated → permanent; harvested stem/leaf
→ captured but not sequestered); CO2-equivalent; the gas + nutrient
budget (net CO2 fixed net-in, net O2 released net-out, survival
min-max bands, lifetime integral over the growth curve); refusals.
"""

from types import SimpleNamespace

from aquaponics.plant_analysis import (
    part_capture, plant_gas_nutrient_budget, plant_lifetime_capture,
)
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
        'PlantDefinition': _rows(SEED_PLANTS),
        'PlantPart': _rows(SEED_PLANT_PARTS),
    })


if __name__ == '__main__':
    print('\naqp-4: per-part plant capture + budget\n')

    print('per-part capture (hand-computed)')
    root = next(SimpleNamespace(**p) for p in SEED_PLANT_PARTS
                if p['name'] == 'sweet-basil-root')
    pc = part_capture(root)
    # dry mass = 40 * 0.25 = 10 g; structural = 10 * 0.40 = 4 g;
    # carbon = 4 * 0.44 = 1.76 g.
    check('root dry mass 10g, structural 4g, carbon 1.76g',
          pc['dryMassG'] == 10.0 and pc['structuralMassG'] == 4.0
          and pc['carbonG'] == 1.76)
    check('root is permanently sequestered (soil-incorporated)',
          pc['permanentlySequestered']
          and pc['carbonPermanentG'] == 1.76)
    leaf = next(SimpleNamespace(**p) for p in SEED_PLANT_PARTS
                if p['name'] == 'sweet-basil-leaf')
    pc = part_capture(leaf)
    check('harvested leaf: carbon captured but NOT sequestered',
          pc['carbonG'] > 0 and pc['carbonPermanentG'] == 0.0
          and not pc['permanentlySequestered'])

    print('\nwhole-plant capture')
    m = _mgr()
    report = plant_lifetime_capture(m, 'sweet-basil')
    # captured: 1.76 (root) + 4.05 (stem) + 1.89 (leaf) = 7.70
    check('total carbon captured 7.70g',
          report['ok']
          and abs(report['carbonCapturedG'] - 7.70) < 1e-6,
          str(report['carbonCapturedG']))
    check('carbon permanently sequestered = root only (1.76g)',
          abs(report['carbonPermanentlySequesteredG'] - 1.76) < 1e-6)
    check('CO2-equivalent of permanent carbon (1.76 * 44/12)',
          abs(report['co2EquivalentPermanentG'] - 1.76 * 44 / 12)
          < 1e-3)
    check('sequestration fraction 1.76/7.70 ~ 0.2286',
          abs(report['sequestrationFraction'] - 1.76 / 7.70) < 1e-4)
    check('the note refuses to greenwash captured as sequestered',
          'greenwash' in report['note'])
    check('per-part breakdown carries every part',
          len(report['parts']) == 3)

    print('\ngas + nutrient budget')
    report = plant_gas_nutrient_budget(m, 'sweet-basil')
    check('net CO2 fixed = 900 - 130 - 60 = 710 mg/day (net-in)',
          report['ok'] and report['netCo2FixedMgDay'] == 710.0)
    check('net O2 released = 655 - 95 - 44 = 516 mg/day',
          report['netO2ReleasedMgDay'] == 516.0)
    co2 = next(s for s in report['species'] if s['species'] == 'co2')
    check('CO2 reads net-in with uptake/release split',
          co2['direction'] == 'net-in' and co2['uptakeMgDay'] == 900.0
          and co2['releaseMgDay'] == 190.0)
    n = next(s for s in report['species']
             if s['species'] == 'nitrate-n')
    check('nitrate survival band (min 8, max 50 mg/day)',
          n['survivalBandMgDay'] == {'min': 8.0, 'max': 50.0}
          and n['netDailyMg'] == 20.0)
    # effective days = 14*0.05 + 56*0.5 + 50*0.9 = 73.7
    check('lifetime CO2 fixed = 710 * 73.7 effective days',
          abs(report['lifetimeCo2FixedMg'] - 710 * 73.7) < 1e-2
          and report['effectiveGrowingDays'] == 73.7)

    print('\nrefusals')
    report = plant_lifetime_capture(m, 'no-such')
    check('unknown plant honest 404 with known list',
          not report['ok'] and 'sweet-basil' in report['knownPlants'])
    m.objectTables['PlantPart'] = {}
    report = plant_lifetime_capture(m, 'sweet-basil')
    check('plant with no parts refuses naming the PlantPart knob',
          not report['ok']
          and report['suggestion']['knob'] == 'PlantPart')

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
