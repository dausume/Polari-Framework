"""
Selftest — algae-2: integrated excess-source + reactor loops, judged on
balance AND resilience, for both design modes.

Run from polari-framework/:
    python3 -m microalgae.selftest_integrated

Covers: a modest surplus matched to a right-sized reactor -> resilient-
balanced (fails safe); a big excess balanced only by the reactor ->
reactor-load-bearing (fragile, flagged) with the advice to shrink the
base; too-small a reactor -> net-accumulating; too-big -> reactor-
oversized (starve); no source surplus -> the reactor would deplete the
base; design-mode-tailored sizing advice; honest refusals. Source
surplus is injected via override so the test is stdlib-only.
"""

from types import SimpleNamespace

from microalgae.integrated_analysis import (
    RESILIENCE_BAND_MG_N, chained_balance,
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


def _loop(name, mode, reactors, sources=('src',)):
    import json
    return {'name': name, 'design_mode': mode, 'source_kind': 'tank',
            'source_system_names_json': json.dumps(list(sources)),
            'reactor_names_json': json.dumps(list(reactors))}


def _mgr(loops):
    return SimpleNamespace(objectTables={
        'AlgaeStrain': _rows(SEED_ALGAE_STRAINS),
        'AlgaeReactorDefinition': _rows(SEED_ALGAE_REACTORS),
        'IntegratedLoopDefinition': _rows(loops)})


if __name__ == '__main__':
    # polish-reactor needs ~162 mg N/day (chlorella, 4 L).
    mgr = _mgr([
        _loop('resilient', 'reactor-first', ['polish-reactor']),
        _loop('fragile', 'add-on', ['nanno-saltforest-reactor']),
        _loop('undersized', 'reactor-first', ['polish-reactor']),
        _loop('oversized', 'reactor-first', ['nanno-saltforest-reactor']),
        _loop('nosurplus', 'add-on', ['polish-reactor']),
    ])

    print('resilient-balanced (modest surplus ~ reactor need)')
    r = chained_balance(mgr, 'resilient', source_surplus_override=165.0)
    check('verdict resilient-balanced',
          r['verdict'] == 'resilient-balanced'
          and r['balanced'] and r['resilient'])
    check('fixes CO2 + composite near zero',
          r['co2FixedGPerDay'] > 0
          and abs(r['compositeNetMgNPerDay']) <= 100.0)
    check('fail-safe note says passive crew holds it',
          'hold it' in r['failSafeNote'])

    print('reactor-load-bearing (big excess, fragile)')
    # nanno needs ~1029; source 1030 -> composite ~0 but base >> band.
    f = chained_balance(mgr, 'fragile', source_surplus_override=1030.0)
    check('balanced but NOT resilient -> reactor-load-bearing',
          f['verdict'] == 'reactor-load-bearing'
          and f['balanced'] and not f['resilient'])
    check('flags fragility + advises shrinking the base',
          'toxic' in (f['limitingFactor'] or '')
          and any('reduce' in s.get('knob', '')
                  for s in f['suggestions']))
    check('base surplus exceeds the resilience band',
          f['baseSurplusMgNPerDay'] > RESILIENCE_BAND_MG_N)

    print('net-accumulating (reactor too small)')
    u = chained_balance(mgr, 'undersized', source_surplus_override=800.0)
    check('excess remains -> net-accumulating',
          u['verdict'] == 'net-accumulating'
          and u['compositeNetMgNPerDay'] > 0)

    print('reactor-oversized (starves)')
    o = chained_balance(mgr, 'oversized', source_surplus_override=50.0)
    check('reactor needs >> source -> reactor-oversized',
          o['verdict'] == 'reactor-oversized'
          and o['supplyFraction'] < 0.1)

    print('no source surplus')
    n = chained_balance(mgr, 'nosurplus', source_surplus_override=0.0)
    check('no excess -> reactor would deplete the base',
          n['verdict'] == 'no-source-surplus')

    print('design-mode tailored advice (modest base, undersized source '
          '-> a suggestion fires)')
    addon = chained_balance(
        _mgr([_loop('a', 'add-on', ['polish-reactor'])]),
        'a', source_surplus_override=5.0)
    check('add-on mode advises introducing headroom surplus',
          any('headroom' in s.get('knob', '')
              or 'headroom' in s.get('action', '')
              for s in addon['suggestions']))
    rf = chained_balance(
        _mgr([_loop('b', 'reactor-first', ['polish-reactor'])]),
        'b', source_surplus_override=5.0)
    check('reactor-first mode advises stocking the base to the reactor',
          any('reactor-first' in s.get('knob', '')
              or 'stock the source' in s.get('action', '')
              for s in rf['suggestions']))

    print('honest refusals')
    check('unknown loop refuses',
          not chained_balance(mgr, 'nope').get('ok'))
    noreact = chained_balance(
        _mgr([_loop('e', 'add-on', [])]), 'e',
        source_surplus_override=100.0)
    check('loop with no reactors refuses',
          not noreact.get('ok'))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
