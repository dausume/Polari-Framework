"""
@module supplychain.selftest_magnetic_sourcing

mag-1 selftests: the magnetic-materials sourcing layer — pottery-
channel hexaferrite feedstocks, currency-refusal honesty, the six
magnetic recipes costing through the cascade, and the make-vs-buy
benchmarks (ring magnets, sintered toroids).

Run from polari-framework/:
    python3 -m supplychain.selftest_magnetic_sourcing
"""

import types

from supplychain.formula_analysis import (
    cascaded_cost, formula_cost, requirement_coverage,
)
from supplychain.sourcing_analysis import normalized_price
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


def _mgr():
    m = types.SimpleNamespace()
    m.objectTables = {
        'SupplySourceProfile': {
            s['name']: types.SimpleNamespace(**s)
            for s in SEED_SUPPLY_SOURCES},
        'PriceCitation': {
            c['name']: types.SimpleNamespace(**c)
            for c in SEED_PRICE_CITATIONS},
        'ProductInputRequirement': {
            r['name']: types.SimpleNamespace(**r)
            for r in SEED_PRODUCT_REQUIREMENTS},
        'ProductFormula': {
            f['name']: types.SimpleNamespace(**f)
            for f in SEED_PRODUCT_FORMULAS},
        'SourcePreferencePolicy': {
            p['name']: types.SimpleNamespace(**p)
            for p in SEED_SOURCE_POLICIES},
    }
    return m


mgr = _mgr()
cites = mgr.objectTables['PriceCitation']
formulas = mgr.objectTables['ProductFormula']

print('== suite: mag-1 seed presence ==')
mag_sources = [s for s in SEED_SUPPLY_SOURCES
               if s.get('provenance_id') == 'mag-1']
mag_cites = [c for c in SEED_PRICE_CITATIONS
             if c.get('provenance_id') == 'mag-1']
check('14 mag-1 sources seeded', len(mag_sources) == 14,
      extra=str(len(mag_sources)))
check('24 mag-1 citations seeded', len(mag_cites) == 24,
      extra=str(len(mag_cites)))
check('every mag-1 citation names a seeded source',
      all(any(s['name'] == c['source_ref']
              for s in SEED_SUPPLY_SOURCES) for c in mag_cites))
check('every mag-1 citation carries a URL + observed_at',
      all(c['citation_url'] and c['observed_at'] for c in mag_cites))

print('== suite: pottery-channel prices (exact math) ==')
v, u = normalized_price(cites['clayking-srco3-50lb-2026-07-28'])
check('cheapest SrCO3 = Clay King 50 lb tier ~5.67 USD/kg',
      u == 'USD/kg' and abs(v - 5.6659) < 0.01, extra=f'{v} {u}')
v, u = normalized_price(cites['clayking-fe2o3-5lb-2026-07-28'])
check('cheapest Fe2O3 = Clay King 5 lb tier ~12.21 USD/kg',
      u == 'USD/kg' and abs(v - 12.2136) < 0.01, extra=f'{v} {u}')
v, u = normalized_price(cites['evans-srco3-1lb-2026-07-28'])
check('Evans 1 lb SrCO3 ~8.27 USD/kg (small-lot premium visible)',
      u == 'USD/kg' and abs(v - 8.2673) < 0.01, extra=f'{v} {u}')

print('== suite: currency honesty ==')
v, u = normalized_price(cites['simplefoc-shield-v2-eur-2026-07-28'])
check('EUR citation REFUSES normalization (no invented fx rate)',
      v is None)
v, u = normalized_price(cites['nanographenex-srfe12o19-25g-2026-07-28'])
check('GBP citation REFUSES normalization', v is None)
v, u = normalized_price(cites['vxb-608-10pack-2026-07-28'])
check('piece-priced USD citation still normalizes per unit',
      u == 'USD/unit' and abs(v - 1.999) < 0.001, extra=f'{v} {u}')

print('== suite: the §1b Rung-1 honest headline ==')
out = formula_cost(mgr, formulas['srfe12o19-solidstate-v0'])
check('solid-state hexaferrite feed costs (~11.81/kg, kiln '
      'excluded-loud)',
      out.get('ok') and abs(out['usdPerKg'] - 11.8085) < 0.02,
      extra=str(out.get('usdPerKg')))
check('the pre-hunt "<$5/kg" was WRONG and the row says so: feed '
      'costs MORE than bought magnetite 9.70',
      out.get('ok') and out['usdPerKg'] > 9.70)
out2 = formula_cost(mgr, formulas['srfe12o19-solgel-v0'])
check('citrate sol-gel route costs (~16.94/kg; nanoscale at kiln '
      'temps is what the premium buys)',
      out2.get('ok') and abs(out2['usdPerKg'] - 16.9417) < 0.02,
      extra=str(out2.get('usdPerKg')))
check('scoring-term block rides the hexaferrite cost',
      out.get('scoreTerm', {}).get('term') == 'material-cost-per-kg')

print('== suite: magnetic composites cascade onto self-made '
      'intermediaries ==')
cc = cascaded_cost(mgr, formulas['magnetic-geopolymer-35vol-v0'])
check('magnetic geopolymer 35vol cascades (~6.09/kg) with '
      'geopolymer-mix SELF-MADE',
      cc.get('ok') and abs(cc['usdPerKg'] - 6.0898) < 0.02
      and any('geopolymer-mix' in str(m)
              for m in cc['madeIntermediates']),
      extra=str(cc.get('usdPerKg')))
cc = cascaded_cost(mgr, formulas['magnetic-solgel-25vol-v0'])
check('magnetic sol-gel mortar cascades (~10.22/kg) via self-made '
      'xerogel',
      cc.get('ok') and abs(cc['usdPerKg'] - 10.2213) < 0.02,
      extra=str(cc.get('usdPerKg')))
cc = cascaded_cost(mgr, formulas['wax-ferrite-30vol-v0'])
check('wax-ferrite feedstock cascades (~10.01/kg) via the blend',
      cc.get('ok') and abs(cc['usdPerKg'] - 10.0113) < 0.02,
      extra=str(cc.get('usdPerKg')))
cc = cascaded_cost(mgr, formulas['ferrite-cnt-solgel-mortar-v0'])
check('ferrite-CNT mortar cascades (~9.96/kg) with TWO made '
      'intermediates (xerogel + CNT dispersion)',
      cc.get('ok') and abs(cc['usdPerKg'] - 9.9631) < 0.02
      and len(cc['madeIntermediates']) == 2,
      extra=str(cc.get('usdPerKg')))

print('== suite: plain formula_cost refuses where buy-side is '
      'unpriced (cascade is the true cost) ==')
out = formula_cost(mgr, formulas['magnetic-geopolymer-35vol-v0'])
check('buy-everything costing refuses (geopolymer-mix has no '
      'citation — it is MADE)',
      not out.get('ok') and 'geopolymer-mix' in out.get('refusal', ''))

print('== suite: requirement coverage + benchmarks ==')
cov = requirement_coverage(mgr, 'srfe12o19-powder')
check('hexaferrite coverage answers', cov.get('ok'))
subs = None
for r in mgr.objectTables['ProductInputRequirement'].values():
    if r.product_item_ref == 'srfe12o19-powder':
        import json as _json
        subs = _json.loads(r.substitutes_json)
check('ceramic ring magnet = the finished-magnet substitute '
      'benchmark, caveats attached',
      subs and subs[0]['item_ref'] == 'ceramic-ring-magnet'
      and len(subs[0]['caveats']) >= 2)
check('BaCO3 alternate carries the toxicity caveat AS DATA',
      'toxic' in cites['clayking-baco3-1lb-2026-07-28']
      .citation_note.lower())
check('SimpleFOC official board availability=potential (out of '
      'stock), clone channel available',
      next(s for s in SEED_SUPPLY_SOURCES
           if s['name'] == 'simplefoc-shop')['availability']
      == 'potential'
      and next(s for s in SEED_SUPPLY_SOURCES
               if s['name'] == 'ebay-simplefoc-clone-listing')
      ['availability'] == 'available')
check('est-flags honest: AS5600/clone/graphite/remington/'
      'rmcybernetics/nanographenex are estimates',
      all(cites[n].is_estimate for n in (
          'ebay-as5600-5pack-2026-07-28',
          'ebay-simplefoc-clone-2026-07-28',
          'walmart-graphite-1lb-2026-07-28',
          'remington-magnetwire-26awg-1lb-2026-07-28',
          'rmcybernetics-mnzn-1kg-2026-07-28',
          'nanographenex-srfe12o19-25g-2026-07-28')))

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
