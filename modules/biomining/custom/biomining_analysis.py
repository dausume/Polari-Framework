"""
@cross-cutting
@module biomining.custom.biomining_analysis
@tags @xc:bindings

biomine-1 model — element extraction yield, the refinement pathway, and
the nutrient-recovery transfer, for a BiomineSystemDefinition. Duck-typed
manager (a lazy tanks read resolves a coupled system's N surplus for the
nutrient-recovery variant; a supply override keeps selftests stdlib-only).
Abstract box-model, flagged priors.

  potential  = Σ agent uptake_rate × biomass × selectivity   (mg elem/day)
  supply     = source element available/day (feedstock knob, or a tank's
               net-N surplus for nutrient recovery)
  effective  = min(potential, supply, extraction_cap)         (mg elem/day)
  product    = effective × element_to_product_yield           (mg/day)

Safety: extraction is bounded by BOTH the source supply (can't pull what
isn't there) and the cap (the regulation knob). Over-extraction of a
LIVING parent (nutrient recovery from a tank) is prevented by capping at
the surplus — same idiom as the algae reactor. For metals/carbon from a
feedstock stream, pulling up to the supply is bioremediation, not a
collapse risk; the model flags only over-PROVISIONED cultures (more
biomass than the feedstock supports).

@consumers
  - biomining.biomining_api
@see materialsScience/ (product material_ref), [[microalgae-reactors]]
"""

import json

PRIORS_NOTE = ('abstract bioextraction box-model; uptake rates + '
               'refinement yields are literature-range priors')


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


def _source_supply(manager, system, override):
    """Available target element per day + how it was resolved."""
    if override is not None:
        return float(override), 'explicit override'
    knob = _f(system, 'source_element_supply_mg_per_day', 0.0)
    kind = getattr(system, 'source_kind', 'feedstock')
    if kind == 'tank' and getattr(system, 'variant', '') \
            == 'nutrient-recovery':
        # recover excess N from the coupled tank's surplus (live).
        try:
            from tanks.custom.tank_analysis import nutrient_balance
            bal = nutrient_balance(
                manager, getattr(system, 'source_system_name', ''))
            if bal.get('ok'):
                return (max(0.0, float(bal['netNitrogenMgPerDay'])),
                        'tank net-N surplus (nutrient recovery)')
        except Exception:
            pass
    return knob, ('source_element_supply_mg_per_day knob'
                  if knob > 0 else 'no source supply set')


def extraction_yield(manager, system_name, days=30.0,
                     supply_override=None):
    """Element recovered + refined product over the period, bounded by
    supply + cap. Names the over-provisioning / depletion risk."""
    system = _named(manager, 'BiomineSystemDefinition', system_name)
    if system is None:
        return {'ok': False,
                'error': f"no BiomineSystemDefinition named "
                         f"'{system_name}'"}
    stock = _parse(getattr(system, 'agent_stock_json', '{}'))
    if not stock:
        return {'ok': False,
                'error': f"'{system_name}' has no agent culture",
                'suggestion': {'knob': 'agent_stock_json',
                               'action': 'stock BioextractionAgent '
                                         'biomass',
                               'evidence': 'extraction needs agents'}}
    potential = 0.0
    element = None
    per_agent = []
    for agent_name, biomass in stock.items():
        agent = _named(manager, 'BioextractionAgent', agent_name)
        if agent is None:
            continue
        rate = (_f(agent, 'uptake_rate_mg_per_g_per_day', 0.0)
                * float(biomass) * _f(agent, 'selectivity', 0.8))
        potential += rate
        element = element or getattr(agent, 'target_element', '')
        per_agent.append({'agent': agent_name,
                          'biomassG': float(biomass),
                          'uptakeMgPerDay': round(rate, 2),
                          'element': getattr(agent, 'target_element', '')})

    supply, supply_source = _source_supply(manager, system,
                                           supply_override)
    cap = _f(system, 'extraction_cap_mg_per_day', 0.0)
    supply_bound = supply if supply > 0 else potential
    effective = min(potential, supply_bound)
    if cap > 0:
        effective = min(effective, cap)

    product = _named(manager, 'BiomineralProduct',
                     getattr(system, 'product_name', ''))
    yield_factor = _f(product, 'element_to_product_yield', 1.0) \
        if product else 1.0
    product_mg_day = effective * yield_factor

    variant = getattr(system, 'variant', '')
    over_provisioned = supply > 0 and potential > supply * 1.05
    depletes_parent = (variant == 'nutrient-recovery'
                       and cap <= 0 and potential > supply and supply > 0)
    if depletes_parent:
        risk = ('uncapped recovery would draw the coupled system beyond '
                'its surplus — cap the extraction (knob: '
                'extraction_cap_mg_per_day <= the surplus)')
    elif over_provisioned:
        risk = (f'culture over-provisioned: agents could take '
                f'{potential:.0f} mg/day but only {supply:.0f} is '
                f'available — extraction is supply-limited (grow less '
                f'biomass or raise the feedstock)')
    else:
        risk = None

    return {
        'ok': True, 'system': system_name, 'variant': variant,
        'targetElement': element,
        'potentialUptakeMgPerDay': round(potential, 2),
        'sourceSupplyMgPerDay': round(supply, 2),
        'sourceSupplySource': supply_source,
        'extractionCapMgPerDay': cap,
        'effectiveExtractionMgPerDay': round(effective, 2),
        'elementRecoveredMg': round(effective * days, 2),
        'refinedProductMgPerDay': round(product_mg_day, 2),
        'refinedProductMg': round(product_mg_day * days, 2),
        'product': getattr(product, 'name', '') if product else '',
        'productKind': getattr(product, 'product_kind', '')
        if product else '',
        'perAgent': per_agent, 'days': float(days),
        'riskFactor': risk, 'priorsFlagged': True, 'note': PRIORS_NOTE}


def refinement_pathway(manager, product_name):
    """The element→refined-form steps + whether the pathway ends at a
    real MaterialsScienceMaterial (honest when absent)."""
    product = _named(manager, 'BiomineralProduct', product_name)
    if product is None:
        return {'ok': False,
                'error': f"no BiomineralProduct named '{product_name}'"}
    material_ref = getattr(product, 'material_ref', '')
    material = _named(manager, 'MaterialsScienceMaterial', material_ref) \
        if material_ref else None
    return {
        'ok': True, 'product': product_name,
        'productKind': getattr(product, 'product_kind', ''),
        'sourceElement': getattr(product, 'source_element', ''),
        'refinedForm': getattr(product, 'refined_form', ''),
        'steps': _parse(getattr(product, 'refinement_pathway_json',
                                '[]'), '[]'),
        'elementToProductYield':
            _f(product, 'element_to_product_yield', 1.0),
        'materialRef': material_ref,
        'materialResolved': material is not None,
        'materialNote': (f"pathway ends at the '{material_ref}' "
                         f'MaterialsScienceMaterial'
                         if material is not None else
                         (f"material_ref '{material_ref}' not found — "
                          f'refine into an existing material row'
                          if material_ref else
                          'no material row linked (feedstock only)')),
        'priorsFlagged': True}


def recovery_transfer(manager, system_name, days=30.0,
                      supply_override=None):
    """nutrient-recovery variant: how much nutrient is recovered + can it
    SUPPLEMENT the target lacking system."""
    system = _named(manager, 'BiomineSystemDefinition', system_name)
    if system is None:
        return {'ok': False,
                'error': f"no BiomineSystemDefinition named "
                         f"'{system_name}'"}
    if getattr(system, 'variant', '') != 'nutrient-recovery':
        return {'ok': False,
                'error': f"'{system_name}' is not a nutrient-recovery "
                         f"variant (variant="
                         f"'{getattr(system, 'variant', '')}')"}
    yld = extraction_yield(manager, system_name, days=days,
                           supply_override=supply_override)
    if not yld.get('ok'):
        return yld
    target = getattr(system, 'supplement_target_system', '')
    return {
        'ok': True, 'system': system_name,
        'nutrientElement': yld['targetElement'],
        'recoveredMg': yld['elementRecoveredMg'],
        'recoveredMgPerDay': yld['effectiveExtractionMgPerDay'],
        'supplementTargetSystem': target,
        'canSupplement': bool(target) and yld['elementRecoveredMg'] > 0,
        'transferNote': (f"recovered {yld['elementRecoveredMg']:.0f} mg "
                         f"{yld['targetElement']} available to "
                         f"supplement '{target}'" if target else
                         'no supplement_target_system set — recovered '
                         'nutrient has no destination'),
        'riskFactor': yld['riskFactor'],
        'priorsFlagged': True, 'note': PRIORS_NOTE}
