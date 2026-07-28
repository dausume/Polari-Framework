"""
@module supplychain.selftest_formulas

src-2 selftests: requirement coverage (cited candidates + honest
research gaps), formula costing against the REAL 2026-07-28 citations
(exact math), feasibility refusals, the cheapest-blend optimizer, and
the material-cost-per-kg scoring-term block.

Run from polari-framework/: python3 -m supplychain.selftest_formulas
"""

import json
import types

from supplychain.formula_analysis import (
    cheapest_blend, formula_cost, formulas_catalog,
    product_cost_comparison, requirement_coverage,
)
from supplychain.sourcing_seed import (
    SEED_PRICE_CITATIONS, SEED_PRODUCT_FORMULAS,
    SEED_PRODUCT_REQUIREMENTS, SEED_SOURCE_POLICIES,
    SEED_SUPPLY_SOURCES,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _rows(seed_list):
    return {s['name']: types.SimpleNamespace(**s) for s in seed_list}


def _mgr():
    return types.SimpleNamespace(objectTables={
        'SupplySourceProfile': _rows(SEED_SUPPLY_SOURCES),
        'PriceCitation': _rows(SEED_PRICE_CITATIONS),
        'SourcePreferencePolicy': _rows(SEED_SOURCE_POLICIES),
        'ProductInputRequirement': _rows(SEED_PRODUCT_REQUIREMENTS),
        'ProductFormula': _rows(SEED_PRODUCT_FORMULAS),
    })


def _formula(components, name='test-blend'):
    return types.SimpleNamespace(
        name=name, product_item_ref='natural-print-wax-blend',
        components_json=json.dumps(components))


# Real normalized prices from the seeds (USD/kg).
SOY = 4.8061
BEESWAX = 19.8195
CARNAUBA = 34.5507


if __name__ == '__main__':
    mgr = _mgr()

    print('== suite: requirement coverage ==')
    out = requirement_coverage(mgr, 'natural-print-wax-blend')
    roles = {r['role']: r for r in out['roles']}
    check('three roles mapped', out.get('ok')
          and set(roles) == {'base-wax', 'toughener', 'hardener'})
    base = {c['item']: c for c in roles['base-wax']['candidates']}
    check('cited candidate carries price + citation + date',
          base['soy-wax']['cited']
          and abs(base['soy-wax']['usdPerKg'] - SOY) < 0.001
          and base['soy-wax']['citation']
          and base['soy-wax']['observedAt'])
    check('uncited candidates are RESEARCH GAPS, not omissions',
          not base['rice-bran-wax']['cited']
          and any(g['item'] == 'candelilla-wax'
                  for g in out['researchGaps'])
          and any(g['item'] == 'stearic-acid'
                  for g in out['researchGaps']))
    check('unknown product refuses naming the requirement knob',
          not requirement_coverage(mgr, 'unobtainium').get('ok'))

    print('== suite: formula cost (real 2026-07-28 numbers) ==')
    v0 = _rows(SEED_PRODUCT_FORMULAS)['natural-print-wax-v0']
    out = formula_cost(mgr, v0)
    expected = round(0.70 * SOY + 0.20 * BEESWAX + 0.10 * CARNAUBA,
                     4)
    check('v0 blend costs 10.78/kg from citations',
          out.get('ok') and abs(out['usdPerKg'] - expected) < 0.001
          and abs(out['usdPerKg'] - 10.7834) < 0.01)
    check('breakdown carries per-component source + citation',
          len(out['breakdown']) == 3
          and all(b['citation'] and b['source']
                  for b in out['breakdown']))
    check('scoring term emitted: material-cost-per-kg, '
          'cheaper-is-better',
          out['scoreTerm']['term'] == 'material-cost-per-kg'
          and out['scoreTerm']['is_positive'] is False
          and out['scoreTerm']['value'] == out['usdPerKg']
          and out['scoreTerm']['evidence'])
    check('carnauba pick is the CHEAPER of the two sources',
          next(b for b in out['breakdown']
               if b['item'] == 'carnauba-wax')['source']
          == 'aroma-depot')

    print('== suite: feasibility refusals ==')
    bad = _formula([{'item_ref': 'soy-wax', 'role': 'base-wax',
                     'fraction': 0.5},
                    {'item_ref': 'beeswax', 'role': 'toughener',
                     'fraction': 0.2}])
    check('fractions not summing to 1.0 refused',
          'sum' in formula_cost(mgr, bad).get('refusal', ''))
    bad = _formula([{'item_ref': 'soy-wax', 'role': 'base-wax',
                     'fraction': 0.9},
                    {'item_ref': 'beeswax', 'role': 'toughener',
                     'fraction': 0.05},
                    {'item_ref': 'carnauba-wax', 'role': 'hardener',
                     'fraction': 0.05}])
    check('role outside its fraction range refused',
          'outside' in formula_cost(mgr, bad).get('refusal', ''))
    bad = _formula([{'item_ref': 'beeswax', 'role': 'base-wax',
                     'fraction': 0.75},
                    {'item_ref': 'beeswax', 'role': 'toughener',
                     'fraction': 0.15},
                    {'item_ref': 'carnauba-wax', 'role': 'hardener',
                     'fraction': 0.10}])
    check('non-candidate item for a role refused (extend the '
          'requirement deliberately)',
          'not a candidate' in formula_cost(mgr, bad)
          .get('refusal', ''))
    bad = _formula([{'item_ref': 'candelilla-wax', 'role': 'base-wax',
                     'fraction': 0.75},
                    {'item_ref': 'beeswax', 'role': 'toughener',
                     'fraction': 0.15},
                    {'item_ref': 'carnauba-wax', 'role': 'hardener',
                     'fraction': 0.10}])
    out = formula_cost(mgr, bad)
    check('uncited component refuses with a citation suggestion',
          not out.get('ok')
          and 'candelilla-wax' in out['refusal']
          and 'cite' in out['suggestion']['action'])

    print('== suite: cheapest feasible blend ==')
    out = cheapest_blend(mgr, 'natural-print-wax-blend')
    comp = {c['item_ref']: c['fraction'] for c in out['components']}
    check('optimizer maxes the cheapest role within its range '
          '(soy 0.85 / beeswax 0.10 / carnauba 0.05)',
          out.get('ok') and comp == {'soy-wax': 0.85,
                                     'beeswax': 0.10,
                                     'carnauba-wax': 0.05})
    expected_cheap = round(0.85 * SOY + 0.10 * BEESWAX
                           + 0.05 * CARNAUBA, 4)
    check('cheapest blend 7.79/kg beats v0 10.78/kg',
          abs(out['usdPerKg'] - expected_cheap) < 0.001
          and out['usdPerKg'] < 10.78)
    check('optimizer output is a SUGGESTION demanding '
          'print-validation',
          'print-validate' in out['suggestion']['action'])
    check('research gaps ride along (cheaper candidates may exist '
          'uncited)', len(out['researchGaps']) >= 3)
    # verify the suggested blend round-trips through formula_cost
    suggested = _formula(out['components'], name='cheapest-check')
    round_trip = formula_cost(mgr, suggested)
    check('suggested blend is feasible by the same validator',
          round_trip.get('ok')
          and abs(round_trip['usdPerKg'] - out['usdPerKg']) < 0.001)

    print('== suite: substitute comparison (MachinableWax) ==')
    out = product_cost_comparison(mgr, 'natural-print-wax-blend')
    kinds = {r['kind'] for r in out['rows']}
    check('comparison spans formulas + optimizer + substitute',
          out.get('ok')
          and kinds == {'formula', 'optimized-blend', 'substitute'})
    sub = next(r for r in out['rows'] if r['kind'] == 'substitute')
    check('machinable wax priced ~22.05/kg from the flagged '
          'citation', sub['name'] == 'machinable-wax'
          and abs(sub['usdPerKg'] - 22.0461) < 0.01
          and sub['anyEstimate'] is True)
    check('substitute caveats travel WITH the price (plastics, '
          'fumes, non-eco)',
          any('plastic' in c for c in sub['caveats'])
          and any('fume' in c for c in sub['caveats'])
          and sub.get('ecoFriendly') is False)
    check('rows sorted cheapest-first, substitute is the DEAREST '
          'priced row',
          out['rows'][0]['kind'] == 'optimized-blend'
          and out['rows'][-1]['kind'] == 'substitute')
    verdict = out['verdict']
    check('verdict: our blend beats the substitute by ~64.6%',
          verdict['ours']['name'] == 'cheapest-feasible-blend'
          and abs(verdict['oursCheaperPct'] - 64.6) < 0.5)
    check('verdict keeps the substitute honest (caveats attached)',
          verdict['substitute']['caveats'])

    print('== suite: catalog ==')
    cat = formulas_catalog(mgr)
    check('catalog costs the seeded v0 formula',
          cat.get('ok')
          and cat['formulas'][0]['name'] == 'natural-print-wax-v0'
          and abs(cat['formulas'][0]['usdPerKg'] - 10.7834) < 0.01)

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)
