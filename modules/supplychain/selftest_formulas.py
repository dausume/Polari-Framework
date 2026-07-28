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
    cascaded_cost, cheapest_blend, effective_unit_price,
    formula_cost, formulas_catalog, make_cost,
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
    check('uncited candidates are RESEARCH GAPS, not omissions '
          '(candelilla + stearic got cited src-7 — only rice-bran '
          'remains)',
          not base['rice-bran-wax']['cited']
          and {g['item'] for g in out['researchGaps']}
          == {'rice-bran-wax'})
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
    bad = _formula([{'item_ref': 'rice-bran-wax', 'role': 'base-wax',
                     'fraction': 0.75},
                    {'item_ref': 'beeswax', 'role': 'toughener',
                     'fraction': 0.15},
                    {'item_ref': 'carnauba-wax', 'role': 'hardener',
                     'fraction': 0.10}])
    out = formula_cost(mgr, bad)
    check('uncited component refuses with a citation suggestion',
          not out.get('ok')
          and 'rice-bran-wax' in out['refusal']
          and 'cite' in out['suggestion']['action'])

    print('== suite: cheapest feasible blend ==')
    out = cheapest_blend(mgr, 'natural-print-wax-blend')
    comp = {c['item_ref']: c['fraction'] for c in out['components']}
    STEARIC = 17.7208
    check('optimizer switched hardener to STEARIC once cited '
          '(soy 0.85 / beeswax 0.10 / stearic 0.05)',
          out.get('ok') and comp == {'soy-wax': 0.85,
                                     'beeswax': 0.10,
                                     'stearic-acid': 0.05})
    expected_cheap = round(0.85 * SOY + 0.10 * BEESWAX
                           + 0.05 * STEARIC, 4)
    check('cheapest blend 6.95/kg beats v0 10.78/kg (new citations '
          'lowered the floor)',
          abs(out['usdPerKg'] - expected_cheap) < 0.001
          and out['usdPerKg'] < 7.0)
    check('optimizer output is a SUGGESTION demanding '
          'print-validation',
          'print-validate' in out['suggestion']['action'])
    check('research gaps ride along (rice-bran still uncited)',
          len(out['researchGaps']) >= 1)
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
    check('verdict: our blend beats the substitute by ~68.5% '
          '(stearic hardener)',
          verdict['ours']['name'] == 'cheapest-feasible-blend'
          and abs(verdict['oursCheaperPct'] - 68.5) < 0.5)
    check('verdict keeps the substitute honest (caveats attached)',
          verdict['substitute']['caveats'])

    print('== suite: geopolymer — DIY raw cost vs buying the kit ==')
    out = requirement_coverage(mgr, 'geopolymer-mix')
    check('4 geopolymer roles; fly-ash + slag are honest gaps',
          out.get('ok') and len(out['roles']) == 4
          and {g['item'] for g in out['researchGaps']}
          == {'fly-ash-class-f', 'ggbfs-slag'})
    v0g = _rows(SEED_PRODUCT_FORMULAS)['geopolymer-castable-v0']
    cost = formula_cost(mgr, v0g)
    check('DIY castable v0 costs ~2.65/kg (volume-tier metakaolin)',
          cost.get('ok') and abs(cost['usdPerKg'] - 2.653) < 0.02)
    check('DIY cost flags estimates (metakaolin + waterglass mass '
          'are inferred)', cost['anyEstimate'] is True)
    out = product_cost_comparison(mgr, 'geopolymer-mix')
    sub = next(r for r in out['rows'] if r['kind'] == 'substitute')
    check('GPI kit is the substitute at ~4.85/kg',
          sub['name'] == 'geopolymer-kit'
          and abs(sub['usdPerKg'] - 4.8502) < 0.01)
    check('substitute caveats cut BOTH ways (hydroxide-free '
          'friendliness on the kit side)',
          any('hydroxide-free' in c for c in sub['caveats']))
    verdict = out['verdict']
    check('verdict: making beats buying — cascaded recipe wins '
          '(~1.11/kg, ~77% cheaper: metakaolin joined the cascade)',
          'self-made' in verdict['ours']['name']
          and abs(verdict['ours']['usdPerKg'] - 1.110) < 0.02
          and abs(verdict['oursCheaperPct'] - 77.1) < 1.5)
    cheap = cheapest_blend(mgr, 'geopolymer-mix')
    comp = {c['item_ref']: c['fraction'] for c in cheap['components']}
    check('optimizer pours the remainder into sand then metakaolin '
          '(0.34/0.10/0.01/0.55)',
          comp == {'metakaolin': 0.34,
                   'sodium-silicate-solution': 0.10,
                   'sodium-hydroxide-lye': 0.01,
                   'silica-sand': 0.55})

    print('== suite: waterglass — the makeable intermediary ==')
    wg = _rows(SEED_PRODUCT_FORMULAS)['waterglass-hydrothermal-v0']
    cost = formula_cost(mgr, wg)
    check('make-waterglass recipe costs ~1.54/kg from citations '
          '(sand+NaOH+tap water)',
          cost.get('ok') and abs(cost['usdPerKg'] - 1.539) < 0.01)
    made = make_cost(mgr, 'sodium-silicate-solution')
    check('make_cost resolves from the seeded recipe (not the '
          'optimizer)', made is not None
          and made['formula'] == 'waterglass-hydrothermal-v0'
          and abs(made['usdPerKg'] - 1.539) < 0.01)
    eff = effective_unit_price(mgr, 'sodium-silicate-solution')
    check('effective price picks MAKE over BUY (1.54 vs 8.85 '
          'purchased)', eff['via'] == 'made'
          and abs(eff['normalized'] - 1.539) < 0.01)
    check('sand stays cheaper to buy than to make (no formula -> '
          'cited)', effective_unit_price(mgr, 'silica-sand')['via']
          == 'cited')

    print('== suite: cascaded geopolymer (self-made waterglass) ==')
    out = cascaded_cost(mgr, v0g)
    check('cascaded v0 drops to ~1.11/kg — waterglass AND '
          'metakaolin both self-made now',
          out.get('ok') and abs(out['usdPerKg'] - 1.110) < 0.01)
    check('BOTH made intermediates declared WITH energy caveats',
          {m['item'] for m in out['madeIntermediates']}
          == {'sodium-silicate-solution', 'metakaolin'}
          and all('energy' in m['caveat']
                  for m in out['madeIntermediates']))
    check('breakdown tags via made/cited per component',
          {b['via'] for b in out['breakdown']} == {'made', 'cited'})
    comp_g = product_cost_comparison(mgr, 'geopolymer-mix')
    casc_row = next((r for r in comp_g['rows']
                     if r['kind'] == 'formula-with-made-'
                                     'intermediates'), None)
    check('comparison surfaces the cascaded row, cheapest of all '
          'named recipes', casc_row is not None
          and abs(casc_row['usdPerKg'] - 1.110) < 0.01)
    check('verdict vs GPI kit now ~77% cheaper (kaolin-calcining '
          'joined the cascade)',
          abs(comp_g['verdict']['oursCheaperPct'] - 77.1) < 1.5)

    print('== suite: sol-gel — two-level cascade ==')
    sg = _rows(SEED_PRODUCT_FORMULAS)['solgel-community-v0']
    plain = formula_cost(mgr, sg)
    check('xerogel with BOUGHT waterglass: ~35.79/kg output '
          '(yield 0.16 applied)',
          plain.get('ok') and abs(plain['usdPerKg'] - 35.786) < 0.05
          and plain['yieldFraction'] == 0.16
          and abs(plain['inputBlendCostPerKg'] - 5.726) < 0.01)
    casc = cascaded_cost(mgr, sg)
    check('xerogel with SELF-MADE waterglass: ~10.67/kg — the '
          'two-level cascade (xerogel <- waterglass <- sand/NaOH)',
          casc.get('ok') and abs(casc['usdPerKg'] - 10.668) < 0.05
          and casc['madeIntermediates'][0]['item']
          == 'sodium-silicate-solution')

    print('== suite: ferrite — citation landed, BUY still wins ==')
    mag = _rows(SEED_PRODUCT_FORMULAS)['magnetite-coprecipitation-v0']
    out = formula_cost(mgr, mag)
    check('coprecipitation COSTS now (~20.11/kg, ferrous sulfate '
          'cited)', out.get('ok')
          and abs(out['usdPerKg'] - 20.108) < 0.05
          and out['anyEstimate'] is True)
    eff = effective_unit_price(mgr, 'magnetite-powder')
    check('effective magnetite = BOUGHT pigment 9.70/kg — make '
          'costs 2x, buying honestly wins',
          eff['via'] == 'cited'
          and abs(eff['normalized'] - 9.6959) < 0.01)

    print('== suite: CNTs — synthesis far off, dispersion near ==')
    check('NO make route for CNT powder (assumption on record)',
          make_cost(mgr, 'mwcnt-powder') is None
          and make_cost(mgr, 'swcnt-powder') is None)
    check('grade ladder on record: SWCNT ~500000/kg vs MWCNT '
          '375/kg (orders of magnitude)',
          abs(effective_unit_price(mgr, 'swcnt-powder')['normalized']
              - 500000.0) < 1
          and abs(effective_unit_price(mgr, 'mwcnt-powder')
                  ['normalized'] - 375.0) < 0.01)
    disp = _rows(SEED_PRODUCT_FORMULAS)['mwcnt-dispersion-2wt-v0']
    out = formula_cost(mgr, disp)
    check('2wt% MWCNT dispersion from bought powder: ~7.50/kg',
          out.get('ok') and abs(out['usdPerKg'] - 7.503) < 0.01)
    eff = effective_unit_price(mgr, 'cnt-water-dispersion')
    check('dispersion: MAKE beats BUY (7.50 vs 185 market, ~96%)',
          eff['via'] == 'made'
          and abs(eff['normalized'] - 7.503) < 0.01)
    cheap = cheapest_blend(mgr, 'cnt-water-dispersion')
    check('optimizer picks MWCNT, never SWCNT, for the cnt role',
          all(c['item_ref'] != 'swcnt-powder'
              for c in cheap['components']))

    print('== suite: catalog ==')
    cat = formulas_catalog(mgr)
    by_name = {f['name']: f for f in cat['formulas']}
    check('catalog costs all EIGHT seeded formulas',
          cat.get('ok') and len(cat['formulas']) == 8
          and abs(by_name['natural-print-wax-v0']['usdPerKg']
                  - 10.7834) < 0.01
          and abs(by_name['geopolymer-castable-v0']['usdPerKg']
                  - 2.653) < 0.02
          and abs(by_name['waterglass-hydrothermal-v0']['usdPerKg']
                  - 1.539) < 0.01
          and abs(by_name['solgel-community-v0']['usdPerKg']
                  - 35.786) < 0.05
          and abs(by_name['mwcnt-dispersion-2wt-v0']['usdPerKg']
                  - 7.503) < 0.01
          and abs(by_name['magnetite-coprecipitation-v0']['usdPerKg']
                  - 20.108) < 0.05
          and abs(by_name['metakaolin-calcined-v0']['usdPerKg']
                  - 1.1023) < 0.01
          and abs(by_name['rha-burned-v0']['usdPerKg']
                  - 7.349) < 0.02)

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)
