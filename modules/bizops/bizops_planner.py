"""
@module bizops.bizops_planner

The order planner (biz-1): run the CURRENT registrar of ProductOrder
rows against a business profile and answer Dustin's three questions
with evidence:
  (1) CAN we realistically make all requested orders? (labor
      capacity vs the stage's committed hours)
  (2) DO we have supply? (v1 = the procurement manifest priced from
      the cited/cascaded stack — there is NO inventory tracking yet
      and the plan says so)
  (3) HOW do we reuse molds? (the LADDER SCALING approach: orders
      grouped into geometric SIZE RUNGS, one mold family per rung,
      strategy picked per rung volume via the mold comparison,
      reuse cycles pooled across every order on the rung)

Physical scaling: mold and shell ops scale ~V^(2/3) (shells), cast
material ~ the scenario-aligned 2.0 kg per 1 L-class unit scaled the
same way. Every prior is FLAGGED; timed runs and logged batches
replace them.
"""

import json
import math

from supplychain.formula_analysis import make_cost
from supplychain.mold_analysis import (
    MOLD_STRATEGY_PRIORS, OIL_RELEASE_USD_PER_KG_EST,
    mold_strategy_compare,
)
from supplychain.reclaim_analysis import RECLAIM_DEFAULTS
from bizops.bizops_flows import _loads, _named, _rows

#: Reference-size (1 L class) physical priors — flagged estimates.
PLAN_PRIORS = {
    'product_mass_kg_ref': 2.0,     # scenario BOM alignment
    'wax_mold_mass_kg_ref': 0.35,   # wax mold at 1 L
    'volume_exponent': 0.667,
}


def _rung_of(volume_l):
    """Geometric size ladder: rung k covers [2^k, 2^(k+1)) litres."""
    return int(math.floor(math.log2(max(volume_l, 1e-6))))


def _rung_volume(k):
    """Representative volume for a rung (geometric mid)."""
    return round(2 ** k * 1.5, 4)


def _scale(volume_l, exponent=PLAN_PRIORS['volume_exponent']):
    return (max(volume_l, 1e-6)) ** exponent


def order_plan(manager, business_name, horizon_days=30):
    biz = _named(manager, 'BusinessProfile', business_name)
    if biz is None:
        return {'ok': False,
                'refusal': f'no BusinessProfile named '
                           f'"{business_name}"'}
    orders = [o for o in _rows(manager, 'ProductOrder')
              if getattr(o, 'status', '') in ('requested',
                                              'accepted')]
    if not orders:
        return {'ok': True, 'business': business_name,
                'orders': 0,
                'note': 'the registrar is empty — nothing to plan '
                        '(orders arrive via CRUDE/UI now, the od-4 '
                        'sale.order binding later)'}
    caps = set(_loads(biz, 'capabilities_json', []))
    cast_wf = _named(manager, 'ProcessWorkflowDefinition',
                     'geopolymer-cast-workflow')
    print_wf = _named(manager, 'ProcessWorkflowDefinition',
                      'wax-mold-print-workflow')
    if cast_wf is None or print_wf is None:
        return {'ok': False,
                'refusal': 'workflow definitions missing — seed '
                           'ProcessWorkflowDefinition rows first'}

    # ---- (3) the ladder: group orders into size rungs -------------
    rungs = {}
    for o in orders:
        k = _rung_of(getattr(o, 'unit_volume_l', 1.0))
        rung = rungs.setdefault(k, {'units': 0, 'orders': []})
        rung['units'] += getattr(o, 'quantity', 0)
        rung['orders'].append(getattr(o, 'name', ''))

    geo_cost = make_cost(manager, 'geopolymer-mix')
    wax_cost = make_cost(manager, 'natural-print-wax-blend')
    if geo_cost is None or wax_cost is None:
        return {'ok': False,
                'refusal': 'geopolymer or wax recipes uncostable — '
                           'the cited stack must resolve first'}
    reclaim_on = 'wax-reclaim-loop' in caps
    recovery = RECLAIM_DEFAULTS['recovery_fraction']

    rung_plans = []
    naive_molds = 0
    planned_molds = 0
    total_hours = 0.0
    total_geo_kg = 0.0
    total_wax_kg = 0.0
    total_material_cost = 0.0
    for k in sorted(rungs):
        rung = rungs[k]
        vol = _rung_volume(k)
        units = rung['units']
        scale = _scale(vol)
        compare = mold_strategy_compare(manager, casts=units)
        if not compare.get('ok'):
            return compare
        allowed = [s for s in compare['strategies']
                   if s['strategy'] != 'ceramic-fired'
                   or 'ceramic-firing' in caps]
        pick = allowed[0]  # already sorted cheapest-first
        cycles = pick['cyclesEst']
        molds = max(1, math.ceil(units / cycles))
        naive_molds += units
        planned_molds += molds
        # masses at this rung's size
        wax_mold_kg = PLAN_PRIORS['wax_mold_mass_kg_ref'] * scale
        product_kg = PLAN_PRIORS['product_mass_kg_ref'] * scale
        # wax masters: wax strategy prints EVERY mold in wax;
        # geopolymer/ceramic molds are cast from ONE wax master
        # per rung (the ladder's whole point).
        if pick['strategy'] == 'wax-printed':
            wax_kg = molds * wax_mold_kg
            masters = 0
        else:
            masters = 1
            wax_kg = masters * wax_mold_kg
        if reclaim_on:
            wax_kg_net = round(wax_kg * (1 - recovery), 4)
        else:
            wax_kg_net = round(wax_kg, 4)
        geo_kg = round(units * product_kg
                       + (molds * pick['moldMassKg'] * scale
                          if pick['strategy'] != 'wax-printed'
                          else 0.0), 4)
        # labor: printing (per wax mold/master) + casting per unit
        print_h = ((molds if pick['strategy'] == 'wax-printed'
                    else masters)
                   * getattr(print_wf, 'hours_per_mold_ref', 2.0)
                   * scale)
        cast_h = (units
                  * getattr(cast_wf, 'hours_per_unit_ref', 0.8)
                  * scale)
        hours = round(print_h + cast_h, 2)
        material_cost = round(
            geo_kg * geo_cost['usdPerKg']
            + wax_kg_net * wax_cost['usdPerKg']
            + units * pick['releasePerCast'], 2)
        total_hours += hours
        total_geo_kg += geo_kg
        total_wax_kg += wax_kg_net
        total_material_cost += material_cost
        rung_plans.append({
            'rung': k, 'rungVolumeL': vol, 'units': units,
            'orders': rung['orders'],
            'strategy': pick['strategy'],
            'strategyCyclesEst': cycles,
            'moldsPlanned': molds,
            'waxMastersPlanned': masters,
            'geopolymerKg': geo_kg,
            'waxKgNet': wax_kg_net,
            'reclaimApplied': reclaim_on,
            'laborHours': hours,
            'materialCost': material_cost})

    # ---- (1) capacity ---------------------------------------------
    weekly = getattr(biz, 'weekly_hours', 10.0)
    available = round(weekly * horizon_days / 7.0, 1)
    feasible = total_hours <= available
    defer = []
    if not feasible:
        # suggest deferring the largest-hour rungs first — a
        # SUGGESTION with evidence, never an auto-refusal of orders
        over = total_hours - available
        for rp in sorted(rung_plans, key=lambda r: -r['laborHours']):
            if over <= 0:
                break
            defer.append({'rung': rp['rung'],
                          'orders': rp['orders'],
                          'hoursFreed': rp['laborHours']})
            over -= rp['laborHours']

    # ---- (2) supply manifest ---------------------------------------
    supply = {
        'geopolymerMixKg': round(total_geo_kg, 2),
        'geopolymerVia': geo_cost['formula'],
        'waxKgNet': round(total_wax_kg, 2),
        'waxVia': wax_cost['formula'],
        'reclaimApplied': reclaim_on,
        'estimatedMaterialCost': round(total_material_cost, 2),
        'note': 'NO inventory tracking yet — the manifest assumes '
                'buy/make everything listed; stock rows are a '
                'follow-up (or the od-4 stock.quant binding)'}

    return {
        'ok': True, 'business': business_name,
        'horizonDays': horizon_days,
        'ordersConsidered': len(orders),
        'rungs': rung_plans,
        'capacity': {
            'laborHoursNeeded': round(total_hours, 1),
            'laborHoursAvailable': available,
            'weeklyHours': weekly,
            'feasible': feasible,
            'deferSuggestions': defer},
        'supply': supply,
        'reuse': {
            'moldsNaive': naive_molds,
            'moldsPlanned': planned_molds,
            'moldSavingsPct': round(
                100.0 * (naive_molds - planned_molds)
                / naive_molds, 1) if naive_molds else 0.0,
            'ladder': 'geometric size rungs (2^k L); one mold '
                      'family per rung, cycles pooled across all '
                      'orders on the rung'},
        'assumptions': [
            'hour priors + V^(2/3) scaling are ESTIMATES until '
            'timed runs replace them',
            'mold cycle lives from MOLD_STRATEGY_PRIORS '
            '(practice-based) until MoldLifecycleRecord retirements '
            'measure them',
            'wax reclaim applied ONLY when the business has the '
            'wax-reclaim-loop capability'
            + (' (it does)' if reclaim_on else ' (it does not — '
               'the adopt-wax-reclaim-loop upgrade is the lever)'),
            'ceramic-fired strategy allowed ONLY with the '
            'ceramic-firing capability'
            + (' (it has it)' if 'ceramic-firing' in caps
               else ' (not yet — add-ceramic-firing is the '
                    'upgrade)'),
            f'release agent oil prior '
            f'{OIL_RELEASE_USD_PER_KG_EST}/kg uncited',
            'no inventory tracking — supply = procurement manifest',
        ]}
