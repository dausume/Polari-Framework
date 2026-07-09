"""
Selftest — algae-1: microalgae reactor growth, sustainability (no-
collapse) verdicts, and decarbonization yield.

Run from polari-framework/:
    python3 -m microalgae.selftest_reactor

Covers: operating-point growth + CO2 scale with light/volume; a
well-capped reactor on a nutrient-rich parent is SUSTAINABLE and fixes
CO2; a parent with NO surplus -> parent-collapse-risk; an uncapped
over-draw -> parent-collapse-risk (suggests the biochar cap); a draw
throttled below the algae need -> algae-crash-risk; harvest lagging
growth -> overgrowth-risk; decarbonization yield is caveated when not
sustainable; edible strain yields harvest nutrients; honest refusals.
The parent surplus is injected via override so the test is stdlib-only.
"""

from types import SimpleNamespace

from microalgae.reactor_analysis import (
    _operating_point, decarbonization_yield, recommend_reactor_for,
    sustainability_assessment,
)
from microalgae.reactor_seed import SEED_ALGAE_REACTORS, SEED_ALGAE_STRAINS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr(reactors=None):
    return SimpleNamespace(objectTables={
        'AlgaeStrain': _rows(SEED_ALGAE_STRAINS),
        'AlgaeReactorDefinition': _rows(
            reactors if reactors is not None else SEED_ALGAE_REACTORS),
    })


def _reactor(**over):
    base = dict(name='r', strain_name='chlorella-vulgaris',
                volume_l=20.0, light_intensity=0.8,
                coupled_system_kind='hydroponic',
                nutrient_draw_cap_mg_n_per_day=900.0,
                assumed_parent_surplus_mg_n_per_day=1000.0,
                target_density_fraction=0.5, harvest_fraction=0.35,
                harvest_period_days=1.0)
    base.update(over)
    return base


if __name__ == '__main__':
    strain = next(SimpleNamespace(**s) for s in SEED_ALGAE_STRAINS
                  if s['name'] == 'chlorella-vulgaris')

    print('operating point / growth')
    op_dim = _operating_point(strain, SimpleNamespace(
        volume_l=20.0, light_intensity=0.4, target_density_fraction=0.5))
    op_bright = _operating_point(strain, SimpleNamespace(
        volume_l=20.0, light_intensity=0.8, target_density_fraction=0.5))
    check('more light -> more CO2 fixed',
          op_bright['co2_g_day'] > op_dim['co2_g_day'])
    op_big = _operating_point(strain, SimpleNamespace(
        volume_l=40.0, light_intensity=0.8, target_density_fraction=0.5))
    check('bigger reactor -> more biomass + CO2',
          op_big['co2_g_day'] > op_bright['co2_g_day'])
    check('N draw scales with biomass growth',
          op_big['n_needed_mg_day'] > op_bright['n_needed_mg_day'] > 0)

    print('sustainable: rich parent, well capped, harvested')
    mgr = _mgr(reactors=[_reactor()])
    ok = sustainability_assessment(mgr, 'r', parent_surplus_override=1000.0)
    check('verdict sustainable', ok['sustainable']
          and ok['verdict'] == 'sustainable')
    check('fixes CO2 (>0 g/day, >0 kg/year)',
          ok['co2FixedGPerDay'] > 0 and ok['co2FixedKgPerYear'] > 0)
    check('effective draw within surplus',
          ok['effectiveDrawMgNPerDay'] <= ok['parentSurplusMgNPerDay'])

    print('parent-collapse: no surplus')
    none = sustainability_assessment(mgr, 'r', parent_surplus_override=0.0)
    check('no surplus -> parent-collapse-risk',
          none['verdict'] == 'parent-collapse-risk'
          and not none['sustainable'])
    check('limiting factor names the depletion', none['limitingFactor']
          and 'surplus' in none['limitingFactor'])

    print('parent-collapse: uncapped over-draw')
    mgr_unc = _mgr(reactors=[_reactor(
        name='u', nutrient_draw_cap_mg_n_per_day=0.0)])
    over = sustainability_assessment(mgr_unc, 'u',
                                     parent_surplus_override=200.0)
    check('uncapped draw > surplus -> parent-collapse-risk',
          over['verdict'] == 'parent-collapse-risk')
    check('suggests the biochar draw cap',
          any('draw_cap' in s.get('knob', '')
              for s in over['suggestions']))

    print('proper biochar cap protects the parent')
    mgr_cap = _mgr(reactors=[_reactor(
        name='c', nutrient_draw_cap_mg_n_per_day=180.0)])
    capped = sustainability_assessment(mgr_cap, 'c',
                                       parent_surplus_override=200.0)
    check('capping at <= surplus avoids parent collapse',
          capped['verdict'] != 'parent-collapse-risk'
          and capped['effectiveDrawMgNPerDay'] <= 200.0)

    print('algae-crash: draw throttled below need')
    mgr_tiny = _mgr(reactors=[_reactor(
        name='t', nutrient_draw_cap_mg_n_per_day=5.0)])
    crash = sustainability_assessment(mgr_tiny, 't',
                                      parent_surplus_override=1000.0)
    check('tiny cap starves the culture -> algae-crash-risk',
          crash['verdict'] == 'algae-crash-risk')

    print('overgrowth: harvest lags growth')
    mgr_og = _mgr(reactors=[_reactor(
        name='o', harvest_fraction=0.25, harvest_period_days=7.0)])
    og = sustainability_assessment(mgr_og, 'o',
                                   parent_surplus_override=1000.0)
    check('weekly harvest vs fast growth -> overgrowth-risk',
          og['verdict'] == 'overgrowth-risk'
          and any('harvest' in s.get('knob', '')
                  for s in og['suggestions']))

    print('decarbonization yield')
    yld = decarbonization_yield(mgr, 'r', days=365.0,
                                parent_surplus_override=1000.0)
    check('sustainable yield: CO2 kg > 0, no caveat',
          yld['sustainable'] and yld['co2FixedKg'] > 0
          and yld['caveat'] is None)
    check('edible strain yields harvest nutrients (protein)',
          yld['harvestNutrients'].get('protein', 0) > 0)
    bad_yld = decarbonization_yield(mgr, 'r', days=365.0,
                                    parent_surplus_override=0.0)
    check('non-sustainable yield carries a caveat',
          not bad_yld['sustainable'] and bad_yld['caveat'])

    print('recommend reactor for a system')
    rich = recommend_reactor_for(_mgr(), 'hydroponic', 'x')
    # (fake reactor assumed surplus 0 -> would NOT help by default)
    check('recommend runs + reports surplus + rationale',
          rich['ok'] and 'reactorWouldHelp' in rich
          and rich['rationale'])

    print('honest refusals')
    check('unknown reactor refuses',
          not sustainability_assessment(mgr, 'nope').get('ok'))
    no_strain = _mgr(reactors=[_reactor(name='ns', strain_name='')])
    check('reactor without a strain refuses with the knob',
          not sustainability_assessment(
              no_strain, 'ns').get('ok'))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
