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


#: Stage-0 exploration variants (the "try different products"
#: axiom as data) — market price prior scales from the scenario's
#: 18.00 at the 1 L class. mag-8 adds the magnetic-goods variants:
#: `material_ref` overrides the cast material (default
#: geopolymer-mix), `price_ref` overrides the scaled price prior
#: (small technical parts do not price like planters — still a
#: PRIOR until MarketSessionRecord rows land),
#: `magnetics_option_ref` names the catalog row whose realization
#: gate decides whether SELLING is open (numbers always shown),
#: and `excluded_note` states costs this plan does NOT include.
PRESTAGE_VARIANTS = [
    {'variant': 'small-pot', 'volume_l': 0.5},
    {'variant': 'planter-1l', 'volume_l': 1.0},
    {'variant': 'large-planter', 'volume_l': 4.0},
    # --- mag-8 magnetic goods (same casting workflow, magnetic
    # castable, wax molds unchanged) ---
    {'variant': 'inductor-core-toroid', 'volume_l': 0.05,
     'material_ref': 'magnetic-geopolymer-mix',
     'magnetics_option_ref': 'opt-geopolymer-ferrite',
     'price_ref': 4.0},
    {'variant': 'sensor-core-set', 'volume_l': 0.02,
     'material_ref': 'magnetic-geopolymer-mix',
     'magnetics_option_ref': 'opt-geopolymer-ferrite',
     'price_ref': 6.0},
    {'variant': 'flux-guide-set', 'volume_l': 0.2,
     'material_ref': 'magnetic-geopolymer-mix',
     'magnetics_option_ref': 'opt-geopolymer-ferrite',
     'price_ref': 12.0},
    {'variant': 'motor-kit-m0-clock', 'volume_l': 0.1,
     'material_ref': 'magnetic-geopolymer-mix',
     'magnetics_option_ref': 'opt-bonded-hexaferrite-geopolymer',
     'price_ref': 25.0,
     'excluded_note': 'castings only — magnet wire, 1 Hz driver '
                      'and hardware are EXCLUDED from this '
                      'number; the kit BOM lives in the motor '
                      'design build_requirements '
                      '(/api/motors/materials/clock-lavet-m0)'},
]
MARKET_PRICE_REF = 18.0
WAX_MOLD_CYCLES = 10


def _magnetics_gate(manager, option_ref):
    """Realization gate for a magnetic variant, read at DATA level
    (bizops does not import magnetics — the table is simply absent
    when the module is off, and the gate says so honestly).
    Selling opens only at made-and-measured; the plan's numbers
    show either way."""
    if not option_ref:
        return None
    table = (getattr(manager, 'objectTables', None) or {}).get(
        'MagneticMaterialOption') or {}
    opt = next((row for row in table.values()
                if getattr(row, 'name', '') == option_ref), None)
    if opt is None:
        return {'option': option_ref, 'businessAllowed': False,
                'note': 'magnetics module off (or option row '
                        'missing) — realization gate unassessed; '
                        'numbers are planning-only'}
    level = getattr(opt, 'realization_level', 'theoretical')
    made = level == 'made-and-measured'
    return {'option': option_ref, 'realizationLevel': level,
            'businessAllowed': made,
            'note': ('made-and-measured — selling open' if made
                     else f'realization "{level}" — numbers shown, '
                          'SELLING gated until measured batches '
                          '(qa-wound-core-inductance / '
                          'qa-magnet-remanence) earn '
                          'made-and-measured')}


def _sell_through(manager, business_name):
    """Per-variant sell-through from MarketSessionRecord rows —
    the stage-0 learning; None when no sessions exist yet."""
    offered, sold = {}, {}
    for rec in _rows(manager, 'MarketSessionRecord'):
        if getattr(rec, 'business_ref', '') != business_name:
            continue
        for variant, n in _loads(rec, 'offered_json', {}).items():
            offered[variant] = offered.get(variant, 0) + n
        for variant, n in _loads(rec, 'sold_json', {}).items():
            sold[variant] = sold.get(variant, 0) + n
    if not offered:
        return None
    return {v: (sold.get(v, 0) / offered[v]) if offered[v] else 0.0
            for v in offered}


def prestage_plan(manager, business_name, budget_usd=100.0,
                  horizon_days=30):
    """The STAGE-0 planner (Dustin's refinement): no orders — the
    business produces what it can AFFORD with what it HAS, spreads
    the batch across DIFFERENT products, then tries to sell.
    Allocation is even across variants until MarketSessionRecord
    sell-through exists to weight it — speculation first, learning
    second, never a demand forecast pulled from nowhere."""
    biz = _named(manager, 'BusinessProfile', business_name)
    if biz is None:
        return {'ok': False,
                'refusal': f'no BusinessProfile named '
                           f'"{business_name}"'}
    stage = _named(manager, 'BusinessStageDefinition',
                   getattr(biz, 'current_stage', ''))
    work_mode = getattr(stage, 'work_mode', 'order-driven')         if stage else 'order-driven'
    geo_cost = make_cost(manager, 'geopolymer-mix')
    wax_cost = make_cost(manager, 'natural-print-wax-blend')
    cast_wf = _named(manager, 'ProcessWorkflowDefinition',
                     'geopolymer-cast-workflow')
    print_wf = _named(manager, 'ProcessWorkflowDefinition',
                      'wax-mold-print-workflow')
    if None in (geo_cost, wax_cost, cast_wf, print_wf):
        return {'ok': False,
                'refusal': 'costs or workflows unresolvable — the '
                           'cited stack and workflow seeds must '
                           'exist first'}
    # Per-material make-costs (mag-8): variants may override the
    # cast material; an unresolvable override refuses THAT variant,
    # never the whole plan.
    mat_costs = {'geopolymer-mix': geo_cost}
    for var in PRESTAGE_VARIANTS:
        ref = var.get('material_ref', 'geopolymer-mix')
        if ref not in mat_costs:
            mat_costs[ref] = make_cost(manager, ref)
    weekly = getattr(biz, 'weekly_hours', 10.0)
    hours_budget = weekly * horizon_days / 7.0
    weights = _sell_through(manager, business_name)
    shares = {}
    for var in PRESTAGE_VARIANTS:
        if weights:
            w = weights.get(var['variant'], 0.34)
            shares[var['variant']] = max(w, 0.1)  # keep exploring
        else:
            shares[var['variant']] = 1.0
    total_w = sum(shares.values())
    batch = []
    spent = 0.0
    hours_used = 0.0
    for var in PRESTAGE_VARIANTS:
        vol = var['volume_l']
        scale = _scale(vol)
        share = shares[var['variant']] / total_w
        b_share = budget_usd * share
        h_share = hours_budget * share
        mat_ref = var.get('material_ref', 'geopolymer-mix')
        mat_cost = mat_costs.get(mat_ref)
        gate = _magnetics_gate(manager,
                               var.get('magnetics_option_ref', ''))
        if mat_cost is None or not mat_cost.get('usdPerKg'):
            batch.append({'variant': var['variant'],
                          'volumeL': vol, 'units': 0,
                          'material': mat_ref,
                          'refusal': f'make-cost for "{mat_ref}" '
                                     'unresolvable — its recipe/'
                                     'citations must seed first '
                                     '(magnetic seeds ride the '
                                     'supplychain mag-1 lists)'})
            continue
        unit_kg = PLAN_PRIORS['product_mass_kg_ref'] * scale
        unit_cost = unit_kg * mat_cost['usdPerKg']
        unit_h = (getattr(cast_wf, 'hours_per_unit_ref', 0.8)
                  * scale)
        mold_kg = PLAN_PRIORS['wax_mold_mass_kg_ref'] * scale
        mold_cost = mold_kg * wax_cost['usdPerKg']
        mold_h = getattr(print_wf, 'hours_per_mold_ref', 2.0) * scale
        # afford: units bounded by budget (incl molds) AND hours
        units = 0
        while True:
            n = units + 1
            molds = max(1, -(-n // WAX_MOLD_CYCLES))
            cost = n * unit_cost + molds * mold_cost
            hours = n * unit_h + molds * mold_h
            if cost > b_share or hours > h_share:
                break
            units = n
        if units == 0:
            batch.append({'variant': var['variant'],
                          'volumeL': vol, 'units': 0,
                          'sellThroughWeight': round(
                              shares[var['variant']] / total_w, 3),
                          'refusal': 'share of budget/hours too '
                                     'small for even one unit — '
                                     'the exploration floor kept '
                                     'its claim; it lands when '
                                     'budget grows'})
            continue
        molds = max(1, -(-units // WAX_MOLD_CYCLES))
        cost = round(units * unit_cost + molds * mold_cost, 2)
        hours = round(units * unit_h + molds * mold_h, 1)
        price = round(var.get('price_ref')
                      or MARKET_PRICE_REF * scale, 2)
        spent += cost
        hours_used += hours
        entry = {
            'variant': var['variant'], 'volumeL': vol,
            'units': units, 'molds': molds,
            'material': mat_ref,
            'materialCost': cost, 'laborHours': hours,
            'marketPriceEach': price,
            'revenueIfAllSells': round(units * price, 2),
            'marginIfAllSells': round(units * price - cost, 2),
            'sellThroughWeight': round(shares[var['variant']]
                                       / total_w, 3)}
        if gate is not None:
            entry['businessGate'] = gate
        if var.get('excluded_note'):
            entry['excludedNote'] = var['excluded_note']
        batch.append(entry)
    return {
        'ok': True, 'business': business_name,
        'workMode': work_mode,
        'workModeNote': ('this IS the stage-0 mode' if work_mode
                         == 'pre-staged-speculative' else
                         'business is past pre-staged mode — the '
                         'order planner is primary; this batch '
                         'plan still works for market stock'),
        'budgetUsd': budget_usd,
        'budgetSpent': round(spent, 2),
        'hoursBudget': round(hours_budget, 1),
        'hoursUsed': round(hours_used, 1),
        'batch': batch,
        'learning': ('sell-through weighting ACTIVE from market '
                     'sessions' if weights else
                     'no MarketSessionRecord rows yet — EVEN split '
                     'across variants (pure exploration); log '
                     'sessions to let the batch learn'),
        'assumptions': [
            'SPECULATIVE: revenue/margin lines assume everything '
            'sells — unsold stock is the stage-0 tuition',
            f'market price prior {MARKET_PRICE_REF} at 1 L scaled '
            'V^(2/3) — replace with real session prices as they '
            'log',
            'wax molds at ' + str(WAX_MOLD_CYCLES)
            + ' casts each; hour priors are estimates',
            'exploration floor keeps every variant >= 10% weight '
            'even when it has not sold — trying different products '
            'IS the strategy',
        ]}


def measured_rates(manager, business_name):
    """MEASURED hours/unit per variant from ProductionRunRecord rows
    (mold hours tracked separately). None per variant until timed
    runs exist — priors never masquerade as measurements."""
    agg = {}
    for r in _rows(manager, 'ProductionRunRecord'):
        if getattr(r, 'business_ref', '') != business_name:
            continue
        v = getattr(r, 'variant', '') or '?'
        a = agg.setdefault(v, {'units': 0, 'hours': 0.0,
                               'molds': 0, 'moldHours': 0.0,
                               'runs': 0,
                               'volumeL': getattr(r, 'unit_volume_l',
                                                  1.0)})
        a['units'] += getattr(r, 'units_made', 0)
        a['hours'] += getattr(r, 'attended_hours', 0.0)
        a['molds'] += getattr(r, 'molds_made', 0)
        a['moldHours'] += getattr(r, 'mold_hours', 0.0)
        a['runs'] += 1
    out = {}
    for v, a in agg.items():
        if a['units'] > 0:
            out[v] = {
                'hoursPerUnit': round(a['hours'] / a['units'], 3),
                'hoursPerMold': round(a['moldHours'] / a['molds'],
                                      3) if a['molds'] else None,
                'unitsMeasured': a['units'], 'runs': a['runs'],
                'volumeL': a['volumeL']}
    return out


READINESS_LEVELS = ('concept', 'produced', 'market-proven',
                    'advance-orderable')


def product_readiness(manager, business_name, made_threshold=1,
                      sold_threshold=None):
    """Per-variant readiness LADDER (Dustin): concept -> produced
    (timed runs exist) -> market-proven (MADE AND SOLD past the
    threshold) -> advance-orderable (market-proven + measured
    rates). Escalation is EARNED by rows, never declared."""
    biz = _named(manager, 'BusinessProfile', business_name)
    if biz is None:
        return {'ok': False,
                'refusal': f'no BusinessProfile named '
                           f'"{business_name}"'}
    threshold = (getattr(biz, 'readiness_sold_threshold', 1)
                 if sold_threshold is None else int(sold_threshold))
    rates = measured_rates(manager, business_name)
    sold = {}
    for rec in _rows(manager, 'MarketSessionRecord'):
        if getattr(rec, 'business_ref', '') != business_name:
            continue
        for variant, n in _loads(rec, 'sold_json', {}).items():
            sold[variant] = sold.get(variant, 0) + n
    variants = sorted(set(list(rates) + list(sold))
                      | {v['variant'] for v in PRESTAGE_VARIANTS})
    rows = []
    for v in variants:
        made = rates.get(v, {}).get('unitsMeasured', 0)
        n_sold = sold.get(v, 0)
        if made >= made_threshold and n_sold >= threshold                 and v in rates:
            level = 'advance-orderable'
            next_step = 'quote advance orders (lead_time_quote)'
        elif made >= made_threshold and n_sold >= threshold:
            level = 'market-proven'
            next_step = 'log timed runs to unlock quoting'
        elif made >= made_threshold:
            level = 'produced'
            next_step = (f'sell >= {threshold} at market '
                         '(MarketSessionRecord) to prove it')
        else:
            level = 'concept'
            next_step = ('produce it in a pre-staged batch '
                         '(ProductionRunRecord logs the making)')
        rows.append({'variant': v, 'level': level,
                     'unitsMade': made, 'unitsSold': n_sold,
                     'soldThreshold': threshold,
                     'nextEscalation': next_step})
    return {'ok': True, 'business': business_name,
            'soldThreshold': threshold,
            'variants': rows,
            'rule': 'a product escalates only after it has been '
                    'MADE and SOLD past the threshold — readiness '
                    'is earned by rows, never declared'}


def lead_time_quote(manager, business_name, variant='',
                    unit_volume_l=1.0, quantity=1,
                    lead_limit_days=None):
    """'Based on our backlog, if you place this order we estimate
    it will take THIS long to arrive.' Advance orders are GATED on
    measured production records for the variant — no timed runs, no
    customer promise (sell from stock until the records exist).
    The promise ceiling defaults to the business's lead_limit_days
    (30 unless adjusted) and is overridable per call."""
    biz = _named(manager, 'BusinessProfile', business_name)
    if biz is None:
        return {'ok': False,
                'refusal': f'no BusinessProfile named '
                           f'"{business_name}"'}
    limit = (getattr(biz, 'lead_limit_days', 30)
             if lead_limit_days is None else int(lead_limit_days))
    readiness = product_readiness(manager, business_name)
    r_row = next((r for r in readiness.get('variants', [])
                  if r['variant'] == variant), None)
    if r_row is None or r_row['level'] != 'advance-orderable':
        level = r_row['level'] if r_row else 'concept'
        return {'ok': False,
                'refusal': f'"{variant}" is not advance-orderable '
                           f'yet (readiness: {level}) — a product '
                           'escalates only after it has been MADE '
                           'and SOLD past the threshold, with '
                           'timed runs logged',
                'readiness': r_row,
                'suggestion': {
                    'evidence': 'customer promises need earned '
                                'readiness, never declarations',
                    'knob': 'ProductionRunRecord + '
                            'MarketSessionRecord (+ BusinessProfile'
                            '.readiness_sold_threshold)',
                    'action': (r_row['nextEscalation'] if r_row
                               else 'produce it first')}}
    rates = measured_rates(manager, business_name)
    rate = rates.get(variant)
    weekly = getattr(biz, 'weekly_hours', 10.0)
    daily_hours = weekly / 7.0
    # backlog: accepted+requested orders, measured rates where they
    # exist, priors (flagged) where they do not.
    backlog_hours = 0.0
    backlog_flagged = False
    for o in _rows(manager, 'ProductOrder'):
        if getattr(o, 'status', '') not in ('requested', 'accepted'):
            continue
        ov = getattr(o, 'variant_note', '') or ''
        oq = getattr(o, 'quantity', 0)
        orate = rates.get(ov)
        if orate:
            backlog_hours += oq * orate['hoursPerUnit']
        else:
            backlog_hours += (oq * 0.8
                              * _scale(getattr(o, 'unit_volume_l',
                                               1.0)))
            backlog_flagged = True
    order_hours = quantity * rate['hoursPerUnit']
    molds = max(1, -(-quantity // WAX_MOLD_CYCLES))
    if rate['hoursPerMold'] is not None:
        order_hours += molds * rate['hoursPerMold']
    cure_buffer_days = 1.0  # passive cure on the last batch
    est_days = round((backlog_hours + order_hours) / daily_hours
                     + cure_buffer_days, 1)
    within = est_days <= limit
    out = {
        'ok': True, 'business': business_name, 'variant': variant,
        'quantity': quantity,
        'measuredRate': rate,
        'backlogHours': round(backlog_hours, 1),
        'orderHours': round(order_hours, 1),
        'dailyHours': round(daily_hours, 2),
        'estimatedLeadDays': est_days,
        'leadLimitDays': limit,
        'withinLimit': within,
        'quote': (f'based on our backlog, this order is estimated '
                  f'to take ~{est_days} days'
                  if within else
                  f'~{est_days} days — BEYOND our {limit}-day '
                  'promise window; we should not accept it as-is'),
    }
    if backlog_flagged:
        out['backlogNote'] = ('part of the backlog is estimated '
                              'from priors (no timed runs for some '
                              'variants) — the quote is only as '
                              'measured as the backlog is')
    if not within:
        out['suggestion'] = {
            'evidence': f'{est_days}d > {limit}d at '
                        f'{round(daily_hours, 1)}h/day',
            'knob': 'BusinessProfile.lead_limit_days (adjustable) '
                    '/ the upgrade flows',
            'action': 'decline, split the order, extend the limit '
                      'WITH the customer, or take the commit-hours/'
                      'hire-caster upgrade — the flow report has '
                      'the gates'}
    return out


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
