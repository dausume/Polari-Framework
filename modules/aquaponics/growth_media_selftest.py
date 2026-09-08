"""
Selftest — aqp-2: multiscale soil + water + nutrient profiles.

Run from polari-framework/:
    python3 -m aquaponics.growth_media_selftest

Covers: nutrient-profile analysis against the species vocabulary
(in/out-of-range findings, N:P:K, unknown species refused); the
aquaponic Fe-deficiency shows as a below-typical finding; soil
plant-available water + porosity derivation + multiscale descriptors;
water summary with source + dissolved-gas checks; honest refusals.
"""

from types import SimpleNamespace

from aquaponics.custom.media_analysis import (
    analyze_nutrient_profile, soil_water_capacity, water_summary,
)
from aquaponics.media_seed import (
    SEED_NUTRIENT_PROFILES, SEED_NUTRIENT_SPECIES, SEED_SOILS,
    SEED_WATERS,
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
        'NutrientSpecies': _rows(SEED_NUTRIENT_SPECIES),
        'NutrientProfile': _rows(SEED_NUTRIENT_PROFILES),
        'SoilDefinition': _rows(SEED_SOILS),
        'WaterDefinition': _rows(SEED_WATERS),
    })


if __name__ == '__main__':
    print('\naqp-2: soil + water + nutrient profiles\n')

    print('nutrient profile analysis')
    m = _mgr()
    report = analyze_nutrient_profile(m, 'leafy-greens-hydroponic')
    check('hydroponic profile resolves all species in range',
          report['ok'] and report['balanced'],
          str([f['species'] for f in report['findings']]))
    check('N:P:K computed relative to P (N=nitrate+ammonium)',
          report['npkRatio']['N'] == round(160.0 / 40.0, 2)
          and report['npkRatio']['K'] == round(210.0 / 40.0, 2))
    report = analyze_nutrient_profile(m, 'tilapia-aquaponic')
    kinds = {(f['kind'], f['species']) for f in report['findings']}
    check('aquaponic iron deficiency surfaces as below-typical',
          ('below-typical', 'iron-fe') in kinds)
    check('aquaponic low potassium surfaces too',
          ('below-typical', 'potassium-k') in kinds)
    check('the profile is flagged not balanced',
          not report['balanced'])
    # Unknown species refusal.
    m.objectTables['NutrientProfile'][99] = SimpleNamespace(
        name='bad-profile', display_name='x',
        concentrations_json='{"unobtanium-x": 5}',
        basis='water-mg-per-L', ph=6.0,
        electrical_conductivity_ds_m=1.0)
    report = analyze_nutrient_profile(m, 'bad-profile')
    check('unknown species refused naming the NutrientSpecies knob',
          not report['ok'] and 'unobtanium-x' in report['error']
          and report['suggestion']['knob'] == 'NutrientSpecies')
    report = analyze_nutrient_profile(m, 'no-such')
    check('unknown profile honest 404', not report['ok'])

    print('\nsoil capacity')
    m = _mgr()
    report = soil_water_capacity(m, 'coir-perlite-mix')
    check('plant-available water = FC - WP (0.45 - 0.10 = 0.35)',
          report['ok']
          and abs(report['plantAvailableWaterVol'] - 0.35) < 1e-9)
    check('drainable = saturation - FC (0.65 - 0.45 = 0.20)',
          abs(report['drainableVol'] - 0.20) < 1e-9)
    check('porosity derived from bulk/particle density',
          abs(report['porosity'] - (1 - 120.0 / 1500.0)) < 1e-6)
    check('multiscale descriptors travel (aggregate/pore/colloid)',
          len(report['scales']) == 3
          and report['scales'][0]['scale'] == 'aggregate')
    # Degenerate soil: FC <= WP.
    m.objectTables['SoilDefinition'][99] = SimpleNamespace(
        name='bad-soil', display_name='x', texture='clay',
        bulk_density_kg_m3=1600, particle_density_kg_m3=2650,
        porosity=None, saturation_vol=0.4, field_capacity_vol=0.15,
        wilting_point_vol=0.20, hydraulic_conductivity_mm_hr=1,
        cation_exchange_cmol_kg=30, organic_matter_fraction=0.02,
        scales_json='[]')
    report = soil_water_capacity(m, 'bad-soil')
    check('FC <= WP flagged no-available-water',
          any(f['kind'] == 'no-available-water'
              for f in report['findings']))

    print('\nwater summary')
    m = _mgr()
    report = water_summary(m, 'tilapia-aquaponic-loop')
    check('source kind + params travel',
          report['ok'] and report['sourceKind'] == 'aquaponic'
          and report['sourceParams']['fishSpecies'] == 'nile-tilapia')
    check('nutrient profile linked + read as not balanced (Fe low)',
          report['nutrientProfile'] == 'tilapia-aquaponic'
          and report['nutrientBalanced'] is False)
    check('multiscale water descriptors travel',
          any(s['scale'] == 'molecular' for s in report['scales']))
    # Low dissolved oxygen.
    m.objectTables['WaterDefinition'][99] = SimpleNamespace(
        name='stale-water', display_name='x', source_kind='aquaponic',
        source_params_json='{}', temperature_c=28, ph=7.2,
        electrical_conductivity_ds_m=1.0, dissolved_oxygen_mg_l=3.0,
        dissolved_co2_mg_l=12, flow_rate_l_per_hr=0.5,
        nutrient_profile_name='', scales_json='[]')
    report = water_summary(m, 'stale-water')
    check('low dissolved oxygen flagged',
          any(f['kind'] == 'low-dissolved-oxygen'
              for f in report['findings']))
    report = water_summary(m, 'no-such')
    check('unknown water honest 404', not report['ok'])

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
