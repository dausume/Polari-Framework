"""
@cross-cutting
@module microalgae.custom.reactor_analysis
@tags @xc:bindings

algae-1 model — microalgae growth, the SUSTAINABILITY (no-collapse)
assessment, and the DE-CARBONIZATION yield. Duck-typed manager (stdlib-
only selftests; a lazy tanks import resolves a coupled tank's surplus).
Abstract box-model, flagged priors.

Growth at the operating density D = target_density_fraction × optimal:
    µ = µmax · light · (1 − target_density_fraction)   (self-shading)
    new biomass/day = µ · biomass ;  biomass = D · volume
    N draw/day      = new biomass · n_per_biomass
    CO2 fixed/day   = new biomass · carbon_fraction · 44/12

Sustainability — the CORE PURPOSE. The reactor draws N from the parent
and fixes CO2. It is SUSTAINABLE only when the draw stays within the
parent's daily N SURPLUS; otherwise the parent depletes (system
collapse) or, if the draw is throttled below what the algae need to
persist, the algae crash. The nutrient_draw_cap knob models the spec's
biochar passthrough limiter: capping the draw AT OR BELOW the parent
surplus protects the parent (and is the recommended regulation).

Parent surplus:
  coupled_system_kind == 'tank'  -> the tank's net N balance (positive =
                                    accumulating N the reactor can safely
                                    consume; a fish-heavy tank is the
                                    IDEAL host, a balanced one has none).
  else                           -> the reactor's assumed_parent_surplus
                                    knob (honest prior).

@consumers
  - microalgae.reactor_api
@see /SALTWATER_FOOD_FOREST_SPEC.md
"""

import json

CO2_PER_C = 44.0 / 12.0        # g CO2 per g fixed carbon
DAYS_PER_YEAR = 365.0
#: Below this fraction of needed N, the algae starve (crash).
STARVE_FRACTION = 0.1
PRIORS_NOTE = ('abstract photobioreactor box-model; growth + '
               'stoichiometry are literature-range priors, not measured')


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table)


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _f(row, attr, default=0.0):
    value = getattr(row, attr, default)
    try:
        return float(default if value is None else value)
    except (TypeError, ValueError):
        return float(default)


def _operating_point(strain, reactor):
    """Biomass, potential growth, N need, and CO2 at the operating
    density (nutrient-replete). Returns a dict of the potentials."""
    optimal = _f(strain, 'optimal_density_g_l', 3.0)
    frac = min(0.95, max(0.05, _f(reactor, 'target_density_fraction',
                                  0.5)))
    density = optimal * frac
    biomass_g = density * _f(reactor, 'volume_l', 20.0)
    mu = (_f(strain, 'max_growth_rate_per_day', 0.9)
          * min(1.0, max(0.0, _f(reactor, 'light_intensity', 0.8)))
          * (1.0 - frac))              # self-shading term
    new_biomass = mu * biomass_g       # g/day, nutrient-replete
    n_needed = new_biomass * _f(strain, 'n_per_biomass_mg_g', 80.0)
    co2 = new_biomass * _f(strain, 'carbon_fraction', 0.5) * CO2_PER_C
    return {'density_g_l': density, 'biomass_g': biomass_g, 'mu': mu,
            'new_biomass_g_day': new_biomass, 'n_needed_mg_day': n_needed,
            'co2_g_day': co2}


def parent_surplus(manager, reactor, override=None):
    """Daily N surplus (mg) the parent can spare + how it was resolved.
    Positive = spare nutrients available; <=0 = none (coupling would
    deplete it)."""
    if override is not None:
        return float(override), 'explicit override'
    kind = getattr(reactor, 'coupled_system_kind', '')
    name = getattr(reactor, 'coupled_system_name', '')
    if kind == 'tank' and name:
        try:
            from tanks.custom.tank_analysis import nutrient_balance
            bal = nutrient_balance(manager, name)
            if bal.get('ok'):
                return (float(bal['netNitrogenMgPerDay']),
                        f'tank {name} net N balance (positive = '
                        f'accumulating surplus)')
        except Exception:
            pass
    return (_f(reactor, 'assumed_parent_surplus_mg_n_per_day', 0.0),
            'assumed_parent_surplus_mg_n_per_day (honest prior — '
            'live coupling not resolved)')


def sustainability_assessment(manager, reactor_name,
                              parent_surplus_override=None):
    """THE headline: can this reactor run coupled to its parent without
    collapsing either? Returns the verdict (sustainable / parent-
    collapse-risk / algae-crash-risk / overgrowth-risk), the CO2 it
    fixes, the nutrient draw vs surplus, and regulation suggestions."""
    reactor = _named(manager, 'AlgaeReactorDefinition', reactor_name)
    if reactor is None:
        return {'ok': False,
                'error': f"no AlgaeReactorDefinition named "
                         f"'{reactor_name}'"}
    strain = _named(manager, 'AlgaeStrain',
                    getattr(reactor, 'strain_name', ''))
    if strain is None:
        return {'ok': False,
                'error': f"reactor '{reactor_name}' has no AlgaeStrain "
                         f"(strain_name="
                         f"'{getattr(reactor, 'strain_name', '')}')",
                'suggestion': {'knob': 'AlgaeReactorDefinition.strain_name',
                               'action': 'point it at an AlgaeStrain',
                               'evidence': 'growth needs the strain'}}

    op = _operating_point(strain, reactor)
    surplus, surplus_source = parent_surplus(manager, reactor,
                                             parent_surplus_override)
    cap = _f(reactor, 'nutrient_draw_cap_mg_n_per_day', 0.0)
    n_needed = op['n_needed_mg_day']

    # Effective draw: bounded by the cap (if set) AND the parent surplus.
    draw_ceiling = surplus if cap <= 0 else min(cap, surplus)
    effective_draw = max(0.0, min(n_needed, draw_ceiling))
    supply_fraction = (effective_draw / n_needed) if n_needed > 0 else 1.0

    actual_new_biomass = op['new_biomass_g_day'] * supply_fraction
    actual_co2 = op['co2_g_day'] * supply_fraction
    growth_per_day = op['mu'] * supply_fraction
    harvest_per_day = (_f(reactor, 'harvest_fraction', 0.25)
                       / max(1e-6, _f(reactor, 'harvest_period_days',
                                      7.0)))

    suggestions = []
    # 1) Parent has no spare nutrients -> any draw depletes it.
    if surplus <= 0:
        verdict = 'parent-collapse-risk'
        limiting = (f'the coupled system has no nutrient surplus '
                    f'(surplus {surplus:.0f} mg N/day) — a reactor would '
                    f'draw the parent into depletion')
        suggestions.append({
            'knob': 'couple to a nutrient-ACCUMULATING system (e.g. a '
                    'fish-heavy tank) or add nutrient inputs',
            'evidence': f'{surplus_source}: {surplus:.0f} mg N/day'})
    # 2) Uncapped/loosely-capped draw exceeds the surplus.
    elif n_needed > surplus and (cap <= 0 or cap > surplus):
        verdict = 'parent-collapse-risk'
        limiting = (f'reactor wants {n_needed:.0f} mg N/day > parent '
                    f'surplus {surplus:.0f} mg N/day and the draw is '
                    f'{"uncapped" if cap <= 0 else "capped too high"}')
        suggestions.append({
            'knob': 'AlgaeReactorDefinition.nutrient_draw_cap_mg_n_per_day',
            'action': f'cap the draw at <= {surplus:.0f} mg N/day (the '
                      f'biochar passthrough limiter) or shrink volume_l',
            'evidence': 'the biochar cap keeps the reactor from '
                        'over-consuming the parent'})
    # 3) Draw throttled below what the algae need to persist -> crash.
    elif supply_fraction < STARVE_FRACTION:
        verdict = 'algae-crash-risk'
        limiting = (f'draw cap/surplus supplies only '
                    f'{supply_fraction * 100:.0f}% of the algae N need '
                    f'— the culture starves and crashes')
        suggestions.append({
            'knob': 'raise nutrient_draw_cap or reduce volume_l/'
                    'target_density_fraction',
            'evidence': f'need {n_needed:.0f}, supplied '
                        f'{effective_draw:.0f} mg N/day'})
    # 4) Harvest too slow -> density climbs past optimal -> shading crash.
    elif harvest_per_day < growth_per_day * 0.8:
        verdict = 'overgrowth-risk'
        limiting = (f'harvest ({harvest_per_day * 100:.1f}%/day) lags '
                    f'growth ({growth_per_day * 100:.1f}%/day) — density '
                    f'climbs to self-shading and the culture crashes')
        suggestions.append({
            'knob': 'AlgaeReactorDefinition.harvest_fraction / '
                    'harvest_period_days',
            'action': 'harvest more often to hold the operating density',
            'evidence': 'steady density needs harvest >= growth'})
    else:
        verdict = 'sustainable'
        limiting = None

    sustainable = verdict == 'sustainable'
    return {
        'ok': True, 'reactor': reactor_name,
        'strain': getattr(strain, 'name', ''),
        'verdict': verdict, 'sustainable': sustainable,
        'limitingFactor': limiting,
        'parentSurplusMgNPerDay': round(surplus, 2),
        'parentSurplusSource': surplus_source,
        'nutrientDrawNeededMgNPerDay': round(n_needed, 2),
        'effectiveDrawMgNPerDay': round(effective_draw, 2),
        'supplyFraction': round(supply_fraction, 3),
        'drawCapMgNPerDay': cap,
        'co2FixedGPerDay': round(actual_co2, 2),
        'co2FixedKgPerYear': round(actual_co2 * DAYS_PER_YEAR / 1000.0,
                                   3),
        'newBiomassGPerDay': round(actual_new_biomass, 2),
        'operatingDensityGL': round(op['density_g_l'], 2),
        'suggestions': suggestions,
        'priorsFlagged': True, 'note': PRIORS_NOTE}


def decarbonization_yield(manager, reactor_name, days=365.0,
                          parent_surplus_override=None):
    """CO2 fixed + biomass (and its harvest nutrients) over a period,
    at the reactor's SUSTAINABLE operating point. Names the verdict so
    the yield is never reported as if a collapsing reactor delivered
    it."""
    assess = sustainability_assessment(manager, reactor_name,
                                       parent_surplus_override)
    if not assess.get('ok'):
        return assess
    co2_day = assess['co2FixedGPerDay']
    biomass_day = assess['newBiomassGPerDay']
    strain = _named(manager, 'AlgaeStrain', assess['strain'])
    content = {}
    try:
        content = json.loads(
            getattr(strain, 'harvest_nutrients_json', '{}') or '{}')
    except Exception:
        content = {}
    harvest_g = biomass_day * days
    nutrients = {n: round(float(v) * harvest_g / 100.0, 3)
                 for n, v in content.items()} \
        if bool(getattr(strain, 'edible', False)) else {}
    return {
        'ok': True, 'reactor': reactor_name, 'days': float(days),
        'verdict': assess['verdict'], 'sustainable': assess['sustainable'],
        'co2FixedKg': round(co2_day * days / 1000.0, 3),
        'co2FixedGPerDay': co2_day,
        'harvestBiomassG': round(harvest_g, 1),
        'harvestNutrients': nutrients,
        'edibleProduct': getattr(strain, 'product', 'biomass')
        if bool(getattr(strain, 'edible', False)) else 'non-food biomass',
        'caveat': None if assess['sustainable'] else
            f"NOT sustainable ({assess['verdict']}): "
            f"{assess['limitingFactor']} — yield shown is the operating-"
            f"point rate, not a stable long-run figure",
        'priorsFlagged': True, 'note': PRIORS_NOTE}


def recommend_reactor_for(manager, system_kind, system_name):
    """Given a parent system, would an algae reactor HELP (consume excess
    N + fix CO2)? Reads the parent's surplus and reports the headroom."""
    fake = type('R', (), {
        'coupled_system_kind': system_kind,
        'coupled_system_name': system_name,
        'assumed_parent_surplus_mg_n_per_day': 0.0})()
    surplus, source = parent_surplus(manager, fake)
    helps = surplus > 0
    return {'ok': True, 'system': system_name, 'kind': system_kind,
            'nutrientSurplusMgNPerDay': round(surplus, 2),
            'reactorWouldHelp': helps,
            'rationale': ('excess nitrogen is available for an algae '
                          'reactor to consume while fixing CO2 — a good '
                          'decarbonization host' if helps else
                          'no nutrient surplus — a reactor would draw the '
                          'system into depletion; balance/feed it first'),
            'surplusSource': source, 'priorsFlagged': True}
