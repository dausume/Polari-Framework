"""
@cross-cutting
@module aquaponics.plant_growth
@tags @xc:bindings

aqp-8 — per-part plant growth / growth-failure dynamics. Makes the
aqp-4 PlantPart objects GROW (logistic vs a limiting resource) or FAIL
(limiting factor named), and estimates part-to-part interactions by
VOLUME (Dustin's specific ask).

PlantGrowthModel (a SIBLING row keyed to a PlantPart — extends aqp-4,
does not rebuild it) carries the growth knobs. This file holds the
integrator + interaction estimate; duck-typed manager (stdlib-only for
selftests).

Growth integrator (per part, per timestep):
    dV/dt = growth_rate · V · (1 − V/V_max) · supply_factor
  supply_factor ∈ [0,1] is the MIN across the part's required species
  of (available supply / needed) — Liebig's law of the minimum, reusing
  aqp-4's flux 'needed' bands and aqp-6's supply = flow × concentration.
  Sustained supply_factor below a threshold transitions the part's
  condition healthy → stressed → FAILURE (growth halts / regresses),
  the limiting species NAMED (honest-absence, same as aqp-6 survival).

Volume-based interaction estimate (the specific ask): a small declared
PART_INTERACTIONS table (source-part-type → target-part-type → sign +
volume-scaled magnitude) — an ABSTRACT, transparent, tunable estimate,
NOT biophysical exactness. Output ranks likely interactions with the
volumes + conditions that drove each (labels travel with numbers).

@consumers
  - aquaponics.plant_growth_api / scoring (realized per-part volume)
@see /AQUAPONICS_PHASE2_PLAN.md §aqp-8
"""

import json

CONDITIONS = ('healthy', 'stressed', 'senescing', 'failed')

#: supply_factor at/above this = comfortable; below FAIL_THRESHOLD for
#: FAIL_STEPS consecutive steps drives the part to failure.
STRESS_THRESHOLD = 0.6
FAIL_THRESHOLD = 0.3
FAIL_STEPS = 3

#: Volume-based part-to-part interaction priors (ABSTRACT, tunable).
#: source-part → target-part → {'sign': +1|-1, 'per_cm3': magnitude}.
#: Effect magnitude scales with the SOURCE part's current volume.
PART_INTERACTIONS = {
    'leaf': {
        # Bigger canopy -> more transpiration/nutrient demand on roots.
        'root': {'sign': -1, 'per_cm3': 0.0020,
                 'why': 'canopy transpiration + nutrient demand loads '
                        'the roots'},
        # Leaves photosynthesize -> carbohydrate support for fruit.
        'fruit': {'sign': +1, 'per_cm3': 0.0015,
                  'why': 'leaf photosynthate supports fruit fill'},
    },
    'root': {
        # Bigger roots -> more uptake capacity supporting shoot growth.
        'leaf': {'sign': +1, 'per_cm3': 0.0030,
                 'why': 'root uptake capacity supports shoot growth'},
        'stem': {'sign': +1, 'per_cm3': 0.0020,
                 'why': 'root uptake + anchorage supports the stem'},
    },
    'fruit': {
        # Fruit is a strong sink -> draws nutrients from the leaves.
        'leaf': {'sign': -1, 'per_cm3': 0.0025,
                 'why': 'fruit sink competition draws nutrients from '
                        'leaves'},
    },
    'stem': {
        'leaf': {'sign': +1, 'per_cm3': 0.0010,
                 'why': 'stem transport + support raises the canopy'},
    },
}


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table)


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


def _parts_of(manager, plant_name):
    return [p for p in _rows(manager, 'PlantPart')
            if getattr(p, 'plant_name', '') == plant_name]


def _growth_model_for(manager, part_name):
    for m in _rows(manager, 'PlantGrowthModel'):
        if getattr(m, 'part_name', '') == part_name:
            return m
    return None


def supply_factor(part, supply):
    """min over the part's 'in' flux species of available/needed, in
    [0,1]. Returns (factor, limiting_species). Gases (co2/o2) are taken
    as ambient-supplied unless present in `supply`."""
    flux = _parse(getattr(part, 'flux_json', '{}'))
    factor, limiting = 1.0, None
    for species, spec in flux.items():
        if spec.get('direction') != 'in':
            continue
        needed = float(spec.get('needed', 0.0) or 0.0)
        if needed <= 0:
            continue
        if species in ('co2', 'o2') and species not in supply:
            continue   # ambient gas assumed sufficient unless specified
        available = float(supply.get(species, needed))
        ratio = max(0.0, min(1.5, available / needed))
        if ratio < factor:
            factor, limiting = ratio, species
    return min(1.0, factor), limiting


def grow(manager, plant_name, days=60.0, dt_days=1.0, supply=None,
         supply_by_part=None):
    """Integrate per-part logistic growth against the limiting supply.

    supply: {species: available mg/day} applied to every part;
    supply_by_part: {part_name: {species: mg/day}} overrides per part.
    Returns per-part volume trajectory, condition transitions, failure
    verdict + limiting factor, and the interaction estimate at the end.
    """
    parts = _parts_of(manager, plant_name)
    if not parts:
        return {'ok': False,
                'error': f"no PlantParts for plant '{plant_name}'"}
    supply = supply or {}
    supply_by_part = supply_by_part or {}

    state = {}
    for part in parts:
        name = getattr(part, 'name', '')
        model = _growth_model_for(manager, name)
        part_v_max = _f(part, 'mature_volume_cm3', 100.0)
        part_density = _f(part, 'dry_density_g_cm3', 0.3)
        # 0.0 knobs mean "inherit the aqp-4 part value".
        v_max = _f(model, 'max_volume_cm3', 0.0) if model else 0.0
        v_max = v_max if v_max > 0 else part_v_max
        density = _f(model, 'volume_density_g_cm3', 0.0) if model else 0.0
        density = density if density > 0 else part_density
        start_condition = getattr(model, 'condition', 'healthy') \
            if model else 'healthy'
        state[name] = {
            'part': getattr(part, 'part', 'leaf'),
            'partRow': part,
            'vMax': v_max,
            'rate': _f(model, 'growth_rate', 0.12) if model else 0.12,
            'volume': max(0.01, 0.02 * v_max),   # seedling start
            'condition': start_condition
            if start_condition in CONDITIONS else 'healthy',
            'lowStreak': 0,
            'density': density,
        }

    steps = max(1, int(round(float(days) / float(dt_days))))
    trajectories = {name: [] for name in state}
    transitions = []
    for i in range(steps):
        day = i * dt_days
        for name, st in state.items():
            if st['condition'] == 'failed':
                trajectories[name].append(round(st['volume'], 3))
                continue
            part_supply = dict(supply)
            part_supply.update(supply_by_part.get(name, {}))
            factor, limiting = supply_factor(st['partRow'], part_supply)
            v, v_max, rate = st['volume'], st['vMax'], st['rate']
            dv = rate * v * (1.0 - v / v_max) * factor * dt_days
            if factor < FAIL_THRESHOLD:
                dv -= 0.02 * v * dt_days    # regression under starvation
            st['volume'] = max(0.001, v + dv)
            # Condition transitions (limiting factor named).
            prev = st['condition']
            if factor < FAIL_THRESHOLD:
                st['lowStreak'] += 1
                if st['lowStreak'] >= FAIL_STEPS:
                    st['condition'] = 'failed'
                else:
                    st['condition'] = 'stressed'
            elif factor < STRESS_THRESHOLD:
                st['lowStreak'] = 0
                st['condition'] = 'stressed'
            else:
                st['lowStreak'] = 0
                st['condition'] = 'healthy'
            if st['condition'] != prev:
                transitions.append({
                    'part': name, 'day': round(day, 2),
                    'from': prev, 'to': st['condition'],
                    'supplyFactor': round(factor, 3),
                    'limitingSpecies': limiting})
            st['lastFactor'] = factor
            st['lastLimiting'] = limiting
            trajectories[name].append(round(st['volume'], 3))

    per_part = []
    any_failed = False
    for name, st in state.items():
        failed = st['condition'] == 'failed'
        any_failed = any_failed or failed
        per_part.append({
            'part': name, 'partType': st['part'],
            'finalVolumeCm3': round(st['volume'], 3),
            'maxVolumeCm3': round(st['vMax'], 3),
            'fractionOfMax': round(st['volume'] / st['vMax'], 3),
            'condition': st['condition'],
            'limitingSpecies': st.get('lastLimiting'),
            'supplyFactor': round(st.get('lastFactor', 1.0), 3),
        })
    interactions = estimate_interactions(state)
    return {
        'ok': True, 'plant': plant_name, 'days': float(days),
        'perPart': per_part,
        'trajectories': trajectories,
        'conditionTransitions': transitions,
        'survived': not any_failed,
        'failureSummary': None if not any_failed else
            [t for t in transitions if t['to'] == 'failed'],
        'interactions': interactions,
        'note': 'logistic growth vs the limiting supply (Liebig); '
                'interaction magnitudes are ABSTRACT volume-scaled '
                'priors, not measured.',
    }


def estimate_interactions(state):
    """Volume-weighted part-to-part interaction estimate, ranked by
    magnitude — the volumes + conditions that drove each travel with
    it. `state` is grow()'s internal per-part dict (or any mapping with
    'part', 'volume', 'condition')."""
    # Aggregate current volume by part TYPE (multiple rows possible).
    vol_by_type, cond_by_type = {}, {}
    for st in state.values():
        ptype = st['part']
        vol_by_type[ptype] = vol_by_type.get(ptype, 0.0) + st['volume']
        # worst condition present for that type
        cond_by_type.setdefault(ptype, st['condition'])
    findings = []
    for src, targets in PART_INTERACTIONS.items():
        if src not in vol_by_type:
            continue
        src_vol = vol_by_type[src]
        # A stressed/failed source exerts a weaker effect.
        cond_scale = {'healthy': 1.0, 'stressed': 0.6,
                      'senescing': 0.4, 'failed': 0.1}.get(
            cond_by_type.get(src, 'healthy'), 1.0)
        for tgt, spec in targets.items():
            if tgt not in vol_by_type:
                continue
            magnitude = spec['sign'] * spec['per_cm3'] * src_vol \
                * cond_scale
            findings.append({
                'source': src, 'target': tgt,
                'sign': 'promotes' if spec['sign'] > 0 else 'demands/'
                        'competes',
                'magnitude': round(magnitude, 4),
                'sourceVolumeCm3': round(src_vol, 2),
                'sourceCondition': cond_by_type.get(src, 'healthy'),
                'why': spec['why']})
    findings.sort(key=lambda f: abs(f['magnitude']), reverse=True)
    return {
        'ranked': findings,
        'note': 'estimate, not measured — magnitude = sign · per_cm3 '
                'prior · source volume · source-condition scale. Tune '
                'PART_INTERACTIONS.',
    }
