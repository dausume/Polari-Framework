"""
@module supplychain.selftest_sourcing

src-1 selftests: the preference ladder over overlap-capable flags,
unit normalization, cross-source price comparison (spread + what
preference costs), preferred-source with develop-the-potential
suggestions, citation honesty, and scenario price drift against the
REAL 2026-07-28 citations.

Run from polari-framework/: python3 -m supplychain.selftest_sourcing
"""

import json
import types

from supplychain.sourcing_analysis import (
    normalized_price, preferred_source, price_compare, rank_source,
    scenario_price_drift, source_catalog,
)
from supplychain.sourcing_seed import (
    SEED_PRICE_CITATIONS, SEED_SOURCE_POLICIES, SEED_SUPPLY_SOURCES,
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
    })


if __name__ == '__main__':
    mgr = _mgr()
    policy = list(mgr.objectTables['SourcePreferencePolicy']
                  .values())[0]

    print('== suite: the ladder (first-match over overlap flags) ==')
    by_name = mgr.objectTables['SupplySourceProfile']
    check('polari open-source local -> rank 1',
          rank_source(by_name['polari-waxprint-lab'], policy)[0] == 1)
    check('local commercial (hydroponics farm) -> rank 4, '
          'NOT rank 3 despite eco flag',
          rank_source(by_name['local-hydroponics-farm'],
                      policy)[0] == 4)
    check('general commercial -> rank 5',
          rank_source(by_name['aztec-candle-soap'], policy)[0] == 5)
    check('eco-claim commercial (GPI) still rank 5 '
          '(closed-source, non-local)',
          rank_source(by_name['geopolymer-international'],
                      policy)[0] == 5)
    os_nonpolari = types.SimpleNamespace(
        is_polari=False, is_open_source=True, is_local=False,
        is_commercial=False, is_eco_friendly=True)
    check('open-source non-polari eco -> rank 3',
          rank_source(os_nonpolari, policy)[0] == 3)
    os_not_eco = types.SimpleNamespace(
        is_polari=False, is_open_source=True, is_local=False,
        is_commercial=False, is_eco_friendly=False)
    check('open-source non-eco falls PAST rank 3 (the if-eco '
          'condition is real)',
          rank_source(os_not_eco, policy)[0] == policy.default_rank)

    print('== suite: catalog + overlaps + the mutual loop ==')
    cat = source_catalog(mgr)
    rows = {r['name']: r for r in cat['sources']}
    check('catalog ranked, polari lab first',
          cat['sources'][0]['name'] == 'polari-waxprint-lab')
    check('overlap visible: farm is local AND commercial AND eco',
          set(rows['local-hydroponics-farm']['categories'])
          >= {'local', 'commercial', 'eco_friendly'})
    check('the farm DEMANDS self-watering pots + shelves '
          '(customer side of the loop)',
          set(rows['local-hydroponics-farm']['demands'])
          == {'geopolymer-self-watering-pot', 'geopolymer-pot-shelf'})
    check('farm supplies wax-source biomass as a POTENTIAL business '
          'model', rows['local-hydroponics-farm']['availability']
          == 'potential'
          and rows['local-hydroponics-farm']['businessModelRef']
          == 'hydroponic-wax-source-farm')

    print('== suite: normalization ==')
    soy = mgr.objectTables['PriceCitation'][
        'aztec-lp402-soy-50lb-2026-07-28']
    value, unit = normalized_price(soy)
    check('50 lb case at $109 -> 4.806 USD/kg',
          unit == 'USD/kg' and abs(value - 4.8061) < 0.001)
    bad = types.SimpleNamespace(price=10.0, amount=0.0,
                                amount_unit='kg')
    check('zero amount refuses to normalize',
          normalized_price(bad)[0] is None)

    print('== suite: price comparison ==')
    out = price_compare(mgr, 'carnauba-wax')
    check('two carnauba sources compared', out.get('ok')
          and len(out['rows']) == 2)
    spread = out['spread'][0]
    check('spread cheapest=aroma-depot, ~18.7%% apart',
          spread['cheapest']['source'] == 'aroma-depot'
          and abs(spread['spreadPct'] - 18.7) < 0.2)
    out = price_compare(mgr, 'geopolymer-kit')
    kg = {r['citation']: r['normalized'] for r in out['rows']}
    check('GPI bulk discount visible (50lb cheaper per kg than '
          '10lb kit)',
          kg['gpi-geocement-50lb-2026-07-28']
          < kg['gpi-geocement-10lb-2026-07-28'])
    check('estimates FLAGGED on the range-mapped GPI prices',
          all(r['isEstimate'] for r in out['rows']))
    check('every row carries date + citation URL',
          all(r['observedAt'] and r['citationUrl']
              for r in out['rows']))
    check('unknown item refuses with citation suggestion',
          not price_compare(mgr, 'unobtainium').get('ok'))

    print('== suite: preferred source + potential suggestions ==')
    out = preferred_source(mgr, 'soy-wax')
    check('preferred available soy source = the commercial one '
          '(nothing better is real yet)',
          out.get('ok')
          and out['preferred']['source'] == 'aztec-candle-soap')
    mgr2 = _mgr()
    # make the polari lab a cited soy supplier (potential) to see the
    # develop-suggestion fire
    lab_cit = types.SimpleNamespace(
        name='lab-soy-est', source_ref='polari-waxprint-lab',
        item_ref='soy-wax', price=4.0, currency='USD', amount=1.0,
        amount_unit='kg', observed_at='2026-07-28T10:00:00',
        citation_url='', citation_note='internal estimate',
        is_estimate=True)
    mgr2.objectTables['PriceCitation']['lab-soy-est'] = lab_cit
    out = preferred_source(mgr2, 'soy-wax')
    check('potential rank-1 source surfaces as a SUGGESTION, not a '
          'pick', out['preferred']['source'] == 'aztec-candle-soap'
          and 'polari-waxprint-lab'
          in out['suggestion']['action'])

    print('== suite: scenario price drift (real numbers) ==')
    scn = types.SimpleNamespace(
        name='wax-mold-goods-v1',
        seed_spec_json=json.dumps({'products': [
            {'ref': 'soy-wax-pellets', 'item_ref': 'soy-wax'},
            {'ref': 'geopolymer-drymix',
             'item_ref': 'geopolymer-kit'}]}),
        driver_spec_json=json.dumps({'per_cycle': {'purchases': [
            {'lines': [{'ref': 'soy-wax-pellets', 'qty': 10.0,
                        'price_unit': 6.0}]},
            {'lines': [{'ref': 'geopolymer-drymix', 'qty': 40.0,
                        'price_unit': 1.8}]}]}}))
    out = scenario_price_drift(mgr, scn)
    findings = {f['product']: f for f in out.get('findings', [])}
    check('drift detected on the drymix (1.8 pinned vs ~4.85 '
          'cited = +169%)', out.get('ok') and out['inDrift']
          and 'geopolymer-drymix' in findings
          and abs(findings['geopolymer-drymix']['driftPct']
                  - 169.4) < 1.0)
    check('soy pinned 6.0 vs cited 4.81 also flagged (-19.9%)',
          'soy-wax-pellets' in findings
          and abs(findings['soy-wax-pellets']['driftPct']
                  + 19.9) < 0.5)
    check('drift is a SUGGESTION naming a deliberate edit',
          'never automatic'
          in findings['geopolymer-drymix']['action'])

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)
