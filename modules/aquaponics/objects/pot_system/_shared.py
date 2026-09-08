"""@module aquaponics.objects.pot_system._shared — what the pot_system row classes share (constants, seeds, helpers); split from pot_system_basis.py (sap-2c)."""
from aquaponics.custom.atmosphere_analysis import (
    atmosphere_state, environment_gas_exchange, LOW_LIGHT_PPFD,
)
import json
from aquaponics.custom.plant_analysis import (
    CO2_PER_CARBON, plant_gas_nutrient_budget, plant_lifetime_capture,
)

SURVIVAL_STATUSES = ('met', 'marginal', 'deficient')
def _by_name(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    rows = table.values() if isinstance(table, dict) else table
    return {getattr(r, 'name', ''): r for r in rows}
def _f(row, attr, default=0.0):
    try:
        return float(getattr(row, attr, default))
    except (TypeError, ValueError):
        return default
def _parse(text, fallback):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)
def _system(manager, system_name):
    system = _by_name(manager, 'PotSystemDefinition').get(system_name)
    if system is None:
        return None, {
            'ok': False,
            'error': f"no PotSystemDefinition named '{system_name}'",
            'knownSystems': sorted(
                _by_name(manager, 'PotSystemDefinition'))}
    return system, None
def system_survival(manager, system_name):
    """Supply-vs-demand for every input the plant needs; the limiting
    factor named. The 'survival conditions' assessment."""
    system, refusal = _system(manager, system_name)
    if refusal:
        return refusal
    plant_name = getattr(system, 'plant_name', '')
    budget = plant_gas_nutrient_budget(manager, plant_name)
    if not budget.get('ok'):
        return {'ok': False,
                'error': f"plant budget unavailable: "
                         f"{budget.get('error')}"}
    waters = _by_name(manager, 'WaterDefinition')
    water = waters.get(getattr(system, 'water_name', ''))
    profiles = _by_name(manager, 'NutrientProfile')
    profile = profiles.get(
        getattr(water, 'nutrient_profile_name', '')) \
        if water is not None else None
    conc = _parse(getattr(profile, 'concentrations_json', '{}'), '{}') \
        if profile is not None else {}
    flow = _f(water, 'flow_rate_l_per_hr') if water is not None else 0.0
    do_supply_mg_day = (_f(water, 'dissolved_oxygen_mg_l') * flow * 24.0
                        if water is not None else 0.0)

    def status(supply, needed, minimum):
        if supply < minimum:
            return 'deficient'
        if supply < needed:
            return 'marginal'
        return 'met'

    factors, limiting = [], []
    # Nutrient inputs delivered by the water flow (mg/day).
    for sp in budget['species']:
        name = sp['species']
        if name in ('co2', 'o2') or sp['direction'] != 'net-in':
            continue
        needed = sp['netDailyMg']
        minimum = sp['survivalBandMgDay']['min']
        supply = float(conc.get(name, 0) or 0) * flow * 24.0
        st = status(supply, needed, minimum)
        factors.append({
            'factor': name, 'kind': 'nutrient',
            'supplyMgDay': round(supply, 3),
            'neededMgDay': needed, 'minMgDay': minimum,
            'status': st,
            'evidence': f'water delivers {supply:.1f} mg/day '
                        f'({conc.get(name, 0)} mg/L x {flow} L/hr x '
                        f'24); plant needs {needed} (min {minimum})'})
        if st == 'deficient':
            limiting.append(name)

    # Root-zone O2 from dissolved oxygen.
    o2_root = next((s for s in budget['species']
                    if s['species'] == 'o2'
                    and s['direction'] == 'net-in'), None)
    if o2_root is None:
        # o2 net could be net-out for the whole plant; use root demand.
        o2_needed = next((abs(s['byPart'][0]['needed'])
                          for s in budget['species']
                          if s['species'] == 'o2'), 0.0)
    else:
        o2_needed = o2_root['netDailyMg']
    # Root O2 need = sum of 'in' o2 across parts.
    o2_in = sum(p['needed'] for s in budget['species']
                if s['species'] == 'o2'
                for p in s['byPart'] if p['direction'] == 'in')
    o2_min = sum((p.get('min') or 0) for s in budget['species']
                 if s['species'] == 'o2'
                 for p in s['byPart'] if p['direction'] == 'in')
    st = status(do_supply_mg_day, o2_in, o2_min)
    factors.append({
        'factor': 'root-dissolved-oxygen', 'kind': 'gas',
        'supplyMgDay': round(do_supply_mg_day, 3),
        'neededMgDay': round(o2_in, 3), 'minMgDay': round(o2_min, 3),
        'status': st,
        'evidence': f'dissolved O2 delivers {do_supply_mg_day:.1f} '
                    f'mg/day; roots need {o2_in:.0f} (min {o2_min:.0f})'})
    if st == 'deficient':
        limiting.append('root-dissolved-oxygen')

    # CO2 from the atmosphere gas-exchange verdict.
    exchange = environment_gas_exchange(
        manager, plant_name, getattr(system, 'atmosphere_name', ''))
    co2_ok = exchange.get('verdict') in (
        'open-air-unlimited', 'ventilation-sustains', 'sealed-stable')
    factors.append({
        'factor': 'atmospheric-co2', 'kind': 'gas',
        'status': 'met' if co2_ok else 'deficient',
        'evidence': f"gas-exchange verdict: {exchange.get('verdict')}"
                    + (f" (steady ~{exchange.get('steadyStateCo2Ppm')}"
                       ' ppm)' if exchange.get('steadyStateCo2Ppm')
                       else '')})
    if not co2_ok:
        limiting.append('atmospheric-co2')

    # Light + VPD from the atmosphere state.
    atm_state = atmosphere_state(
        manager, getattr(system, 'atmosphere_name', ''))
    if atm_state.get('ok'):
        light_ok = atm_state['lightPpfd'] >= LOW_LIGHT_PPFD
        factors.append({
            'factor': 'light', 'kind': 'environment',
            'status': 'met' if light_ok else 'marginal',
            'evidence': f"PPFD {atm_state['lightPpfd']:.0f} umol/m2/s"})
        if not light_ok:
            limiting.append('light')
        vpd = atm_state['vapourPressureDeficitKpa']
        vpd_ok = 0.8 <= vpd <= 1.2
        factors.append({
            'factor': 'vapour-pressure-deficit', 'kind': 'environment',
            'status': 'met' if vpd_ok else 'marginal',
            'evidence': f'VPD {vpd:.2f} kPa'})

    deficient = [f for f in factors if f['status'] == 'deficient']
    marginal = [f for f in factors if f['status'] == 'marginal']
    verdict = ('fails' if deficient else
               'stressed' if marginal else 'survives')
    # Survival margin: worst supply/need ratio across rate factors.
    ratios = [f['supplyMgDay'] / f['neededMgDay']
              for f in factors
              if f.get('neededMgDay') and f['neededMgDay'] > 0]
    margin = round(min(ratios), 3) if ratios else None
    return {
        'ok': True,
        'system': system_name,
        'plant': plant_name,
        'verdict': verdict,
        'limitingFactors': limiting,
        'survivalMargin': margin,
        'factors': factors,
        'note': 'supply is a DELIVERY RATE (flow x concentration) vs '
                'the plant per-part min/needed band; the limiting '
                'factor is the first that falls short. Concentration '
                'adequacy for uptake kinetics is a separate media '
                'finding (see /nutrient-profiles/analyze).',
    }
def system_impact(manager, system_name, persist=True):
    """Lifetime environmental impact; persists a snapshot to
    impact_result_json for the scoring engine to bind."""
    system, refusal = _system(manager, system_name)
    if refusal:
        return refusal
    plant_name = getattr(system, 'plant_name', '')
    capture = plant_lifetime_capture(manager, plant_name)
    budget = plant_gas_nutrient_budget(manager, plant_name)
    if not capture.get('ok') or not budget.get('ok'):
        return {'ok': False,
                'error': 'plant capture/budget unavailable',
                'captureError': capture.get('error'),
                'budgetError': budget.get('error')}
    waters = _by_name(manager, 'WaterDefinition')
    water = waters.get(getattr(system, 'water_name', ''))
    plants = _by_name(manager, 'PlantDefinition')
    plant = plants.get(plant_name)
    lifetime = _f(plant, 'lifetime_days')
    flow = _f(water, 'flow_rate_l_per_hr') if water is not None else 0.0

    def lifetime_uptake(species):
        s = next((x for x in budget['species']
                  if x['species'] == species), None)
        return s['lifetimeNetMg'] if s and s['lifetimeNetMg'] > 0 \
            else 0.0

    result = {
        'permanentCarbonG': capture['carbonPermanentlySequesteredG'],
        'co2EquivalentSequesteredG': capture['co2EquivalentPermanentG'],
        'carbonCapturedG': capture['carbonCapturedG'],
        'lifetimeCo2FixedMg': budget.get('lifetimeCo2FixedMg'),
        'lifetimeO2ReleasedMg': budget.get('lifetimeO2ReleasedMg'),
        'nitrogenRemovedMg': round(
            lifetime_uptake('nitrate-n')
            + lifetime_uptake('ammonium-n'), 2),
        'phosphorusRemovedMg': round(
            lifetime_uptake('phosphorus-p'), 2),
        'potassiumRemovedMg': round(lifetime_uptake('potassium-k'), 2),
        'waterThroughputL': round(flow * 24.0 * lifetime, 1),
        'lifetimeDays': lifetime,
    }
    if persist:
        system.impact_result_json = json.dumps(result)
        try:
            manager.db.saveInstanceInDB(system)
        except Exception:
            pass  # in-memory managers (selftests) have no db
    return {
        'ok': True,
        'system': system_name,
        'displayName': getattr(system, 'display_name', '')
        or system_name,
        'plant': plant_name,
        'impact': result,
        'note': 'permanent carbon is CO2 pulled from air and LOCKED '
                '(soil-incorporated/standing parts only); N and P '
                'removed = the aquaponic bioremediation the plant does '
                'for the fish loop. Lifetime gas figures integrate the '
                'growth curve (first-cut). Persisted to '
                'impact_result_json for scoring to rank configs.',
    }
