"""
Selftest — aqp-7: worm-compost enrichment (kinetics, two modes,
coupling, honest priors).

Run from polari-framework/:
    python3 -m aquaponics.selftest_vermicompost

Covers: steady release scales with maturity/moisture/worms; k_min
temperature-responsive (Q10); mineralization monotonic; leaching never
exceeds the pool; direct mode = steady, periodic mode = pulses that
recharge between windows (higher peak, lower/comparable total);
enrichment raises the coupled water profile; compare-modes recommends
with evidence; every result flags abstract priors.
"""

from types import SimpleNamespace

from aquaponics.vermicompost_analysis import (
    compare_modes, enriched_water_profile, k_min_at, simulate_enrichment,
    steady_release, PRIOR_RANGES,
)
from aquaponics.vermicompost_seed import (
    SEED_COMPOST_BINS, SEED_COMPOST_LOOPS, SEED_VERMICOMPOST_PROFILES,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


# A minimal water + profile + pot system so coupling has a target.
WATERS = [{'name': 'tilapia-aquaponic-loop', 'flow_rate_l_per_hr': 1.5,
           'nutrient_profile_name': 'tilapia-aquaponic'}]
NUTRIENT_PROFILES = [{'name': 'tilapia-aquaponic',
                      'concentrations_json':
                          '{"nitrate-n": 40.0, "phosphorus-p": 8.0}'}]
POT_SYSTEMS = [{'name': 'basil-aquaponic-tent',
                'water_name': 'tilapia-aquaponic-loop'}]


def _mgr(bins=None):
    return SimpleNamespace(objectTables={
        'CompostBinDefinition': _rows(bins if bins is not None
                                      else SEED_COMPOST_BINS),
        'VermicompostProfile': _rows(SEED_VERMICOMPOST_PROFILES),
        'CompostLoopDefinition': _rows(SEED_COMPOST_LOOPS),
        'WaterDefinition': _rows(WATERS),
        'NutrientProfile': _rows(NUTRIENT_PROFILES),
        'PotSystemDefinition': _rows(POT_SYSTEMS),
    })


if __name__ == '__main__':
    manager = _mgr()

    print('steady release')
    release = steady_release(manager, 'kitchen-worm-bin')
    check('release ok + names species', release['ok']
          and 'nitrate-n' in release['releaseMgPerKgBed'])
    check('priors flagged + literature ranges carried',
          release['priorsFlagged']
          and release['priorsNote'] == PRIOR_RANGES)
    # Drier bed -> lower activity -> lower release.
    dry_bins = [dict(SEED_COMPOST_BINS[0], name='dry-bin',
                     moisture_target=0.3)]
    dry_mgr = _mgr(bins=SEED_COMPOST_BINS + dry_bins)
    dry = steady_release(dry_mgr, 'dry-bin')
    check('drier bed releases less',
          dry['releaseMgPerKgBed']['nitrate-n']
          < release['releaseMgPerKgBed']['nitrate-n'])
    check('missing profile -> honest refusal',
          not steady_release(_mgr(bins=[
              dict(SEED_COMPOST_BINS[0], name='b2',
                   release_profile_name='')]), 'b2').get('ok'))

    print('temperature response (Q10)')
    profile = SimpleNamespace(**SEED_VERMICOMPOST_PROFILES[0])
    check('k_min rises with temperature',
          k_min_at(profile, 30.0) > k_min_at(profile, 20.0)
          > k_min_at(profile, 10.0))
    check('Q10=2 doubles k_min per +10C',
          abs(k_min_at(profile, 30.0)
              / k_min_at(profile, 20.0) - 2.0) < 1e-9)

    print('direct mode (steady)')
    direct = simulate_enrichment(manager, 'kitchen-worm-bin',
                                 mode='direct', hours=24.0)
    check('direct ok + leaches nitrogen', direct['ok']
          and direct['cumulativeLeachedMg']['nitrate-n'] > 0)
    check('water flows every step',
          all(step['flowing'] for step in direct['timeline']))
    # Leaching never exceeds the available pool (bed mass × release).
    bed_pool = (release['releaseMgPerKgBed']['nitrate-n']
                * SEED_COMPOST_BINS[0]['bed_mass_kg'])
    check('leached <= bed pool (conservation)',
          direct['cumulativeLeachedMg']['nitrate-n'] <= bed_pool + 1e-6)

    print('periodic mode (pulses + recharge)')
    periodic = simulate_enrichment(manager, 'kitchen-worm-bin',
                                   mode='periodic', hours=24.0)
    flowing_steps = [s for s in periodic['timeline'] if s['flowing']]
    check('periodic flows only part of the time',
          0 < len(flowing_steps) < len(periodic['timeline']))
    check('periodic peak > direct peak (pulse concentration)',
          periodic['pulsePeakMgPerL']['nitrate-n']
          > direct['pulsePeakMgPerL']['nitrate-n'])
    # Recharge: a flowing step AFTER an off-window delivers more than
    # steady direct flow would at that pool (pulse effect).
    check('periodic delivers less TOTAL than direct (less contact)',
          periodic['cumulativeLeachedMg']['nitrate-n']
          <= direct['cumulativeLeachedMg']['nitrate-n'] + 1e-9)

    print('coupling out (enriches the pot water)')
    enriched = enriched_water_profile(manager, 'basil-loop-direct',
                                      hours=24.0)
    check('enriched profile ok', enriched['ok'])
    check('nitrate uplift raises the base water concentration',
          enriched['enrichedMgPerL']['nitrate-n']
          > enriched['baseMgPerL']['nitrate-n'])
    check('flow sourced from the bound water definition',
          'WaterDefinition' in enriched['flowSource'])

    print('compare-modes recommendation')
    comparison = compare_modes(manager, 'kitchen-worm-bin', hours=24.0)
    check('compare ok + names a recommendation',
          comparison['ok']
          and comparison['recommendation'] in ('direct', 'periodic'))
    check('recommendation carries evidence + the mode knob',
          len(comparison['why']) > 20
          and 'mode' in comparison['knob'])
    check('both modes reported with peaks',
          'pulsePeakMgPerL' in comparison['direct']
          and 'pulsePeakMgPerL' in comparison['periodic'])

    print('honest priors')
    check('simulate flags abstract priors',
          direct['priorsFlagged'] and 'box-model' in direct['note'])

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
