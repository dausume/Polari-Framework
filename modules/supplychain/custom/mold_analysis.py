"""
@module supplychain.custom.mold_analysis

Mold-strategy economics (mold-1, Dustin 2026-07-28): what should the
mold BE — printed wax, cast geopolymer, or fired ceramic — and what
happens when it dies?

Materials-honesty ledger:
  - fresh geopolymer BONDS to cured geopolymer (same aluminosilicate
    chemistry): a geopolymer-in-geopolymer mold NEEDS a release agent
    — costed per cast (oil ~ cheap consumable; wax coat = our blend);
  - a geopolymer mold can be FIRED into a ceramic mold (the tech
    tree's geopolymer->ceramic Table 8.8 conversion) — one-way
    upgrade, kiln energy EXCLUDED v1 and said loudly;
  - geopolymer molds for ceramic SLIP casting are REFUSED: slip
    casting needs a capillary-porous mold (plaster standard); our
    dense geopolymer has no proven capillarity here — pressing/
    hand-forming of clay against geopolymer molds is fine;
  - cycle-life numbers are ESTIMATES from formwork/kiln-furniture
    practice until MoldLifecycleRecord rows measure them;
  - end-of-life: crushed molds re-enter NEW geopolymer as aggregate
    (the loopback) — credited at the cited aggregate price the crush
    displaces; crushing energy excluded v1.

Duck-typed; every cost resolves through the cited/cascaded stack.
"""

from supplychain.custom.formula_analysis import _best_unit_price, make_cost
from supplychain.custom.sourcing_analysis import _rows

#: Engineering priors, every one FLAGGED until lifecycle rows land.
MOLD_STRATEGY_PRIORS = {
    'wax-printed': {
        'mold_mass_kg': 0.35, 'cycles_est': 10,
        'release_per_cast_kg': 0.0,
        'end_of_life': 'melt-off reclaim (see reclaim_analysis — '
                       'the wax pool, not aggregate)',
        'basis': 'wax-mold-goods scenario prior (0.1 mold/pot)'},
    'geopolymer-cast': {
        'mold_mass_kg': 1.5, 'cycles_est': 50,
        'release_per_cast_kg': 0.005,
        'end_of_life': 'crush-to-aggregate',
        'basis': 'concrete formwork practice 30-100 reuses; '
                 'RELEASE AGENT MANDATORY (geopolymer bonds to '
                 'geopolymer)'},
    'ceramic-fired': {
        'mold_mass_kg': 1.35, 'cycles_est': 200,
        'release_per_cast_kg': 0.005,
        'end_of_life': 'crush-to-aggregate (fired grog)',
        'basis': 'kiln-furniture practice; = a geopolymer mold '
                 'FIRED (Table 8.8 upgrade path); KILN ENERGY '
                 'EXCLUDED v1'},
}

#: Release-agent cost basis: cooking-grade oil is not in the citation
#: stack yet, so the wax coat (cited via the blend) is the default;
#: oil rides as an explicit prior until cited.
OIL_RELEASE_USD_PER_KG_EST = 2.0


def _geopolymer_cost(manager, policy_name=''):
    made = make_cost(manager, 'geopolymer-mix',
                     policy_name=policy_name)
    if made:
        return {'via': 'made', 'usdPerKg': made['usdPerKg'],
                'ref': made['formula']}
    cited = _best_unit_price(manager, 'geopolymer-kit',
                             policy_name=policy_name)
    if cited:
        return {'via': 'cited', 'usdPerKg': cited['normalized'],
                'ref': cited['citation']}
    return None


def _wax_cost(manager, policy_name=''):
    made = make_cost(manager, 'natural-print-wax-blend',
                     policy_name=policy_name)
    return ({'via': 'made', 'usdPerKg': made['usdPerKg'],
             'ref': made['formula']} if made else None)


def mold_strategy_compare(manager, casts=100, policy_name=''):
    """Cost PER CAST for each mold strategy at a production volume,
    with the crush-to-aggregate credit and every estimate flagged."""
    geo = _geopolymer_cost(manager, policy_name)
    wax = _wax_cost(manager, policy_name)
    aggregate = _best_unit_price(manager, 'silica-sand',
                                 policy_name=policy_name)
    if geo is None or wax is None:
        return {'ok': False,
                'refusal': 'geopolymer or wax cost unresolvable '
                           'from the cited stack — cite/define '
                           'their inputs first'}
    strategies = []
    for name, p in MOLD_STRATEGY_PRIORS.items():
        mold_cost = (wax['usdPerKg'] if name == 'wax-printed'
                     else geo['usdPerKg']) * p['mold_mass_kg']
        release_per_cast = (p['release_per_cast_kg']
                            * OIL_RELEASE_USD_PER_KG_EST)
        crush_credit = 0.0
        if p['end_of_life'] == 'crush-to-aggregate' \
                or 'grog' in p['end_of_life']:
            crush_credit = (p['mold_mass_kg']
                            * (aggregate['normalized']
                               if aggregate else 0.0))
        lifetime_casts = min(int(casts), p['cycles_est'])
        molds_needed = max(1, -(-int(casts) // p['cycles_est']))
        total = (molds_needed * (mold_cost - crush_credit)
                 + int(casts) * release_per_cast)
        strategies.append({
            'strategy': name,
            'moldMassKg': p['mold_mass_kg'],
            'moldCost': round(mold_cost, 4),
            'cyclesEst': p['cycles_est'],
            'cyclesIsEstimate': True,
            'moldsNeeded': molds_needed,
            'releasePerCast': round(release_per_cast, 4),
            'crushCreditPerMold': round(crush_credit, 4),
            'costPerCast': round(total / int(casts), 4),
            'endOfLife': p['end_of_life'],
            'basis': p['basis'],
            'lifetimeCastsUsed': lifetime_casts})
    strategies.sort(key=lambda s: s['costPerCast'])
    return {
        'ok': True, 'casts': int(casts),
        'inputs': {'geopolymer': geo, 'wax': wax,
                   'aggregateCredit': aggregate['normalized']
                   if aggregate else None,
                   'oilReleaseEstPerKg': OIL_RELEASE_USD_PER_KG_EST},
        'strategies': strategies,
        'refused': [{
            'strategy': 'geopolymer-mold-for-ceramic-SLIP-casting',
            'refusal': 'slip casting needs a capillary-porous mold '
                       '(plaster standard) — dense geopolymer has '
                       'no proven capillarity here; pressing/'
                       'hand-forming clay against geopolymer molds '
                       'is fine, slip casting is not claimed'}],
        'assumptions': [
            'ALL cycle lives are practice-based estimates until '
            'MoldLifecycleRecord rows measure them',
            'release agent MANDATORY on geopolymer/ceramic molds — '
            'fresh geopolymer bonds to cured aluminosilicate; oil '
            f'prior {OIL_RELEASE_USD_PER_KG_EST}/kg (uncited), wax '
            'coat is the cited alternative',
            'kiln energy for the ceramic-fired upgrade EXCLUDED '
            '(v1) — the sintering engine can cost schedules later',
            'crush-to-aggregate credited at the displaced sand '
            'price; crushing energy excluded',
            'wax-printed molds do not crush-recycle — they MELT '
            'back into the wax pool (reclaim_analysis)']}


def mold_fleet_report(manager):
    """What the MoldLifecycleRecord rows actually say: measured
    casts per material, retirement reasons, and how much crushed
    aggregate the dead molds returned to the loop."""
    fleets = {}
    for m in _rows(manager, 'MoldLifecycleRecord'):
        mat = getattr(m, 'mold_material', '?')
        fleet = fleets.setdefault(mat, {
            'molds': 0, 'inService': 0, 'retired': 0,
            'castsTotal': 0, 'castsMax': 0,
            'crushedKgRecovered': 0.0, 'retiredReasons': {}})
        fleet['molds'] += 1
        casts = getattr(m, 'casts_completed', 0)
        fleet['castsTotal'] += casts
        fleet['castsMax'] = max(fleet['castsMax'], casts)
        if getattr(m, 'condition', '') == 'retired':
            fleet['retired'] += 1
            reason = getattr(m, 'retired_reason', '') or '?'
            fleet['retiredReasons'][reason] = \
                fleet['retiredReasons'].get(reason, 0) + 1
        else:
            fleet['inService'] += 1
        fleet['crushedKgRecovered'] += getattr(
            m, 'crushed_kg_recovered', 0.0)
    for fleet in fleets.values():
        if fleet['retired']:
            retired_casts = fleet['castsTotal']
            fleet['measuredMeanCastsAtRetirement'] = round(
                retired_casts / max(1, fleet['retired']), 1)
    return {'ok': True, 'fleets': fleets,
            'note': 'measured casts-at-retirement replace the '
                    'MOLD_STRATEGY_PRIORS estimates once molds '
                    'actually retire'}
