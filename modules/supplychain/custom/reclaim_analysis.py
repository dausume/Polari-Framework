"""
@module supplychain.custom.reclaim_analysis

Wax reclaim economics (wp-r): melt the printed mold off the cured
geopolymer piece, wash + filter, blend with virgin makeup, print the
next mold — the loopback that cuts the wax line item.

Honesty ledger:
  - recovery_fraction defaults to 0.85 (foundry reclaim practice runs
    0.80-0.90) — an ENGINEERING ESTIMATE until WaxReclaimBatch rows
    accumulate real recovered/melted ratios;
  - the alkaline geopolymer residue SAPONIFIES ester waxes if left
    on — the citric wash (cited) is costed in;
  - melt/wash ENERGY is excluded (v1, same as every other recipe);
  - the max reuse generation is UNKNOWN until printability is
    measured against the feedstock melt window — this module refuses
    to extrapolate a ceiling it has no data for.

Duck-typed over manager.objectTables; virgin wax cost comes from the
cited formula stack (cascaded), so the whole loop stays auditable.
"""

from supplychain.custom.formula_analysis import _best_unit_price, make_cost
from supplychain.custom.sourcing_analysis import _rows

#: Engineering priors — estimates until WaxReclaimBatch data lands.
RECLAIM_DEFAULTS = {
    'recovery_fraction': 0.85,
    'citric_kg_per_kg_reclaimed': 0.02,
}


def _virgin_wax_cost(manager, policy_name=''):
    """USD/kg for virgin print wax: the cheapest of (best cited
    blend recipe, cited purchase) — cascaded, so it uses stearic etc."""
    made = make_cost(manager, 'natural-print-wax-blend',
                     policy_name=policy_name)
    cited = _best_unit_price(manager, 'natural-print-wax-blend',
                             policy_name=policy_name)
    candidates = []
    if made:
        candidates.append(('made', made['usdPerKg'],
                           made['formula']))
    if cited:
        candidates.append(('cited', cited['normalized'],
                           cited['citation']))
    if not candidates:
        return None
    via, value, ref = min(candidates, key=lambda c: c[1])
    return {'via': via, 'usdPerKg': value, 'ref': ref}


def reclaim_steady_state(manager, wax_kg_per_mold=0.35,
                         recovery_fraction=None,
                         policy_name=''):
    """Steady-state wax cost per MOLD with the reclaim loop running:
    every cycle only the unrecovered fraction is virgin makeup, plus
    the citric wash. Compare against the no-reclaim cost."""
    r = (RECLAIM_DEFAULTS['recovery_fraction']
         if recovery_fraction is None else float(recovery_fraction))
    if not 0.0 <= r < 1.0:
        return {'ok': False,
                'refusal': f'recovery_fraction {r} outside [0, 1) — '
                           '1.0 would be a perpetual motion claim'}
    virgin = _virgin_wax_cost(manager, policy_name)
    if virgin is None:
        return {'ok': False,
                'refusal': 'no cited or makeable virgin wax cost — '
                           'cite the blend inputs first'}
    citric = _best_unit_price(manager, 'citric-acid',
                              policy_name=policy_name)
    if citric is None:
        return {'ok': False,
                'refusal': 'citric-acid uncited — the wash (which '
                           'stops residue saponification) must be '
                           'costed, not ignored'}
    wash_per_kg = (RECLAIM_DEFAULTS['citric_kg_per_kg_reclaimed']
                   * citric['normalized'])
    no_reclaim = round(wax_kg_per_mold * virgin['usdPerKg'], 4)
    makeup = round(wax_kg_per_mold * (1.0 - r)
                   * virgin['usdPerKg'], 4)
    wash = round(wax_kg_per_mold * r * wash_per_kg, 4)
    steady = round(makeup + wash, 4)
    return {
        'ok': True,
        'waxKgPerMold': wax_kg_per_mold,
        'recoveryFraction': r,
        'recoveryFractionIsEstimate': recovery_fraction is None,
        'virginWax': virgin,
        'noReclaimCostPerMold': no_reclaim,
        'steadyStateCostPerMold': steady,
        'breakdown': {'virginMakeup': makeup, 'citricWash': wash},
        'savingsPct': round(100.0 * (no_reclaim - steady)
                            / no_reclaim, 1) if no_reclaim else 0.0,
        'assumptions': [
            f'recovery fraction {r} is an engineering estimate '
            '(foundry practice 0.80-0.90) until WaxReclaimBatch '
            'rows provide measured recovered/melted ratios',
            'citric wash costed; melt/wash ENERGY excluded (v1)',
            'max reuse generations UNKNOWN — printability must be '
            'measured against the feedstock melt window; this '
            'analysis refuses to promise a ceiling',
            'alkaline residue saponifies ester waxes if unwashed — '
            'the wash is not optional',
        ]}


def reclaim_cycle_curve(manager, cycles=10, wax_kg_per_mold=0.35,
                        recovery_fraction=None, policy_name=''):
    """Cumulative average wax cost per mold over N reuse cycles
    (cycle 1 = all virgin; each later cycle = makeup + wash). Shows
    how fast the loop pays off; the curve is COST-only — quality
    gates come from WaxReclaimBatch measurements, not from math."""
    steady = reclaim_steady_state(manager, wax_kg_per_mold,
                                  recovery_fraction, policy_name)
    if not steady.get('ok'):
        return steady
    first = steady['noReclaimCostPerMold']
    per_cycle_later = steady['steadyStateCostPerMold']
    curve = []
    total = 0.0
    for n in range(1, int(cycles) + 1):
        total += first if n == 1 else per_cycle_later
        curve.append({'cycle': n,
                      'cumulativeAvgPerMold': round(total / n, 4)})
    return {'ok': True, 'curve': curve,
            'firstCycle': first, 'steadyState': per_cycle_later,
            'assumptions': steady['assumptions']}


def reclaim_pool_report(manager):
    """What the WaxReclaimBatch rows actually say: per pool, the
    generation reached, measured recovery ratio (when logged), and
    the printability verdicts — the data that will replace the
    estimates above."""
    pools = {}
    for b in _rows(manager, 'WaxReclaimBatch'):
        pool = pools.setdefault(getattr(b, 'pool_name', '') or '?', {
            'batches': 0, 'maxGeneration': 0, 'meltedKg': 0.0,
            'recoveredKg': 0.0, 'virginMakeupKg': 0.0,
            'printability': {}})
        pool['batches'] += 1
        pool['maxGeneration'] = max(pool['maxGeneration'],
                                    getattr(b, 'generation', 0))
        pool['meltedKg'] += getattr(b, 'melted_off_kg', 0.0)
        pool['recoveredKg'] += getattr(b, 'recovered_kg', 0.0)
        pool['virginMakeupKg'] += getattr(b, 'virgin_makeup_kg', 0.0)
        verdict = getattr(b, 'printability', 'untested')
        pool['printability'][verdict] = \
            pool['printability'].get(verdict, 0) + 1
    for pool in pools.values():
        if pool['meltedKg'] > 0:
            pool['measuredRecoveryFraction'] = round(
                pool['recoveredKg'] / pool['meltedKg'], 3)
    return {'ok': True, 'pools': pools,
            'note': 'no pools = no reclaim has physically happened '
                    'yet; the economics above run on estimates '
                    'until these rows exist'}
