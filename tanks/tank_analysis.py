"""
@cross-cutting
@module tanks.tank_analysis
@tags @xc:bindings

tank-1 box-model — nutrient CYCLING + harvestable YIELD + ecosystem
REGULATION for a TankSystemDefinition. Duck-typed manager (stdlib-only
selftests). An ABSTRACT ecosystem estimate (not a biological CFD) —
every rate is a flagged prior.

- nutrient_balance: sum each stocked species' daily N/P water flux
  (fish/replenishers add, macroalgae remove) + detritus removal → is
  the ecosystem SELF-REGULATING (net flux within a tolerance band, and
  detritus load handled)? excess/deficit + missing roles named.
- harvest_yield: harvestable biomass over a period → the DietaryNutrients
  it supplies — especially iodine / sodium / chloride from seaweed, the
  gap the hydroponic garden can't fill (composes into the household
  nutrition ledger).
- regulate_suggestions: knobs-and-suggestions — which species to add to
  balance N/P or fill a missing role.

@consumers
  - tanks.tank_api; nutrition fulfillment (seaweed closes the gap)
@see /SALTWATER_FOOD_FOREST_SPEC.md
"""

import json

#: Net daily N (or P) flux within ±band × stock-count is "balanced".
BALANCE_BAND_MG = 50.0
#: Roles a self-sustaining food forest should cover (spec).
REQUIRED_ROLES = ('nutrient-regulator', 'filter-feeder',
                  'detritus-eater', 'glass-cleaner')
PRIORS_NOTE = ('abstract ecosystem box-model; per-species N/P flux + '
               'detritus rates are literature-range priors, not measured')


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


def _parse(text, fallback='{}'):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)


def _stock(manager, system):
    """[(species_row, count), ...] for a system's stock."""
    stock = _parse(getattr(system, 'species_stock_json', '{}'))
    out = []
    for sp_name, count in stock.items():
        sp = _named(manager, 'AquacultureSpecies', sp_name)
        if sp is not None:
            out.append((sp, float(count)))
    return out


def nutrient_balance(manager, system_name):
    """Net N/P flux + detritus load + role coverage for the ecosystem."""
    system = _named(manager, 'TankSystemDefinition', system_name)
    if system is None:
        return {'ok': False,
                'error': f"no TankSystemDefinition named '{system_name}'"}
    stock = _stock(manager, system)
    if not stock:
        return {'ok': False,
                'error': f"system '{system_name}' has no stocked species",
                'suggestion': {
                    'knob': 'TankSystemDefinition.species_stock_json',
                    'action': 'stock the roster species',
                    'evidence': 'balance needs a population'}}

    net_n = net_p = detritus = 0.0
    roles_present = set()
    added_n = removed_n = 0.0
    for sp, count in stock:
        n = _f(sp, 'daily_n_flux_mg', 0.0) * count
        p = _f(sp, 'daily_p_flux_mg', 0.0) * count
        net_n += n
        net_p += p
        (added_n, removed_n) = (added_n + n, removed_n) if n > 0 \
            else (added_n, removed_n - n)
        detritus += _f(sp, 'daily_detritus_removal_mg', 0.0) * count
        roles_present.update(_parse(getattr(sp, 'roles_json', '[]'),
                                    '[]'))

    total_count = sum(c for _, c in stock)
    band = BALANCE_BAND_MG * max(1.0, total_count / 10.0)
    n_balanced = abs(net_n) <= band
    p_balanced = abs(net_p) <= band
    missing_roles = [r for r in REQUIRED_ROLES if r not in roles_present]

    if net_n > band:
        n_verdict = ('nitrogen ACCUMULATING — add macroalgae (nutrient '
                     'regulators) or harvest/export more')
    elif net_n < -band:
        n_verdict = ('nitrogen DEPLETING — algae outpace inputs; add '
                     'fish/replenishers or reduce algae')
    else:
        n_verdict = 'nitrogen balanced'

    self_regulating = n_balanced and p_balanced and not missing_roles
    return {
        'ok': True, 'system': system_name,
        'netNitrogenMgPerDay': round(net_n, 2),
        'netPhosphorusMgPerDay': round(net_p, 2),
        'nitrogenAddedMgPerDay': round(added_n, 2),
        'nitrogenRemovedMgPerDay': round(removed_n, 2),
        'detritusRemovedMgPerDay': round(detritus, 2),
        'balanceBandMg': round(band, 1),
        'nitrogenBalanced': n_balanced,
        'phosphorusBalanced': p_balanced,
        'nitrogenVerdict': n_verdict,
        'rolesPresent': sorted(roles_present),
        'missingRoles': missing_roles,
        'selfRegulating': self_regulating,
        'limitingFactor': None if self_regulating else (
            f'missing roles {missing_roles}' if missing_roles
            else 'nutrient flux outside the balance band'),
        'priorsFlagged': True, 'note': PRIORS_NOTE}


def harvest_yield(manager, system_name, days=30.0,
                  harvest_period_days=30.0):
    """Harvestable biomass + the DietaryNutrients it supplies over the
    period — the alternate nutrient source (seaweed → iodine/sodium/
    chloride; fish → protein)."""
    system = _named(manager, 'TankSystemDefinition', system_name)
    if system is None:
        return {'ok': False,
                'error': f"no TankSystemDefinition named '{system_name}'"}
    stock = _stock(manager, system)
    harvests = max(1.0, float(days) / float(harvest_period_days))

    nutrients = {}
    biomass_g = 0.0
    per_species = []
    for sp, count in stock:
        if not bool(getattr(sp, 'edible', False)):
            continue
        grams = _f(sp, 'harvest_biomass_g', 0.0) * count * harvests
        if grams <= 0:
            continue
        biomass_g += grams
        content = _parse(getattr(sp, 'harvest_nutrients_json', '{}'))
        contribution = {}
        for nutrient, per_100g in content.items():
            amount = float(per_100g) * grams / 100.0
            nutrients[nutrient] = round(
                nutrients.get(nutrient, 0.0) + amount, 3)
            contribution[nutrient] = round(amount, 3)
        per_species.append({'species': getattr(sp, 'name', ''),
                            'harvestG': round(grams, 1),
                            'nutrients': contribution})
    return {
        'ok': True, 'system': system_name, 'days': float(days),
        'harvests': round(harvests, 2),
        'totalEdibleBiomassG': round(biomass_g, 1),
        'nutrientsSupplied': nutrients,
        'perSpecies': per_species,
        'gapNutrientsCovered': sorted(
            n for n in nutrients
            if n in ('iodine', 'sodium', 'chloride')),
        'priorsFlagged': True,
        'note': 'seaweed supplies the iodine/sodium/chloride the '
                'hydroponic garden cannot — composes into the household '
                'nutrition ledger. ' + PRIORS_NOTE}


def regulate_suggestions(manager, system_name):
    """Evidence-bearing species suggestions to balance/complete the
    ecosystem (knobs-and-suggestions — recommend, never auto-apply)."""
    balance = nutrient_balance(manager, system_name)
    if not balance.get('ok'):
        return balance
    suggestions = []
    for role in balance['missingRoles']:
        candidates = [getattr(s, 'name', '')
                      for s in _rows(manager, 'AquacultureSpecies')
                      if role in _parse(getattr(s, 'roles_json', '[]'),
                                        '[]')]
        suggestions.append({
            'gap': f'missing role: {role}',
            'knob': 'TankSystemDefinition.species_stock_json',
            'addOneOf': candidates,
            'evidence': f'no stocked species fills {role}'})
    if balance['netNitrogenMgPerDay'] > balance['balanceBandMg']:
        regulators = [getattr(s, 'name', '')
                      for s in _rows(manager, 'AquacultureSpecies')
                      if 'nutrient-regulator'
                      in _parse(getattr(s, 'roles_json', '[]'), '[]')]
        suggestions.append({
            'gap': 'nitrogen accumulating',
            'knob': 'stock more macroalgae or harvest more often',
            'addOneOf': regulators,
            'evidence': f"net N {balance['netNitrogenMgPerDay']} mg/day "
                        f"> band {balance['balanceBandMg']}"})
    return {'ok': True, 'system': system_name,
            'selfRegulating': balance['selfRegulating'],
            'suggestions': suggestions,
            'note': 'recommendations only — tune the stock knob.'}
