"""
@cross-cutting
@module aquaponics.custom.plant_growth_simplified
@tags @xc:bindings

THE SIMPLIFIED / AGGREGATE growth model (renamed + rebuilt 2026-07-15,
was aqp-8's `plant_growth.py`) — Dustin's own framing, verbatim:
"we should have only one model for plant growth and it should be the
more robust one which I think would be normalized plant growth... The
other plant growth model may be the 'simplified model'... for mass
evaluations at higher scales, where we are taking constants that are
based on the real growth model, and simplify them. Like approximation
by aged growth. We can know from the original model that after a
certain amount of time it most likely is fully grown, and the
simplified model pulls from the isolated single-plant model what the
average constants would be at different ages to say: 'If we had a
whole forest with a lot of these fully grown, what yield are we
getting based on what we know about the singular case.'"

There is now ONE real growth model:
`aquaponics.plant_growth_normalized_basis` — per-part normalized growth,
Free-Soil-Constants/Constrained-Limits, real per-part stress equations
(atmosphere/water/soil/light), real source-sink nutrient TRANSPORT
between parts (phase 9). That module is the single source of truth
for every growth-rate/ceiling CONSTANT and for the closed-form growth
CURVE itself.

THIS module no longer runs its own independent simulation — it has NO
growth-rate model, NO species-flux Liebig computation, NO volume-
scaled interaction priors of its own. It is a thin, fast WRAPPER:

  1. Pulls the REAL per-part rate/ceiling constants straight from
     plant_growth_normalized.free_soil_constants() (the unconfined,
     single-plant reference — "what we know about the singular case").
  2. Evaluates plant_growth_normalized.closed_form_logistic() DIRECTLY
     at each requested age — an EXACT evaluation (the closed form is
     time-invariant/autonomous, so this is mathematically identical
     to iterating the detailed model tick-by-tick under a CONSTANT
     condition, just far cheaper: one closed-form call per age point,
     no per-tick stress/light/transport machinery at all).
  3. `supply_factor`/`supply_factor_by_part` are SIMPLE overall
     scalars (0-1, "how favorable are conditions, roughly") — NOT the
     detailed model's per-species-flux/per-stress-type machinery. This
     IS the simplification: skip the per-tick real-condition cost,
     accept a coarser, constant-for-the-whole-run approximation.
  4. `count` scales the result by a POPULATION SIZE — identical
     individuals at the same age/conditions, multiplied — "if we had
     a whole forest of these... what yield are we getting," a single
     representative trajectory times count, never count independent
     detailed simulations.

`estimate_interactions()`/`PART_INTERACTIONS` (the old volume-scaled
part-to-part priors) are KEPT, unchanged in spirit, as a cheap
ABSTRACT cross-check available at this aggregate scale — but they are
explicitly NOT the real mechanism anymore now that real transport
exists; the docstring says so plainly, pointing at the real thing.

@consumers
  - aquaponics.plant_growth_simplified_api (aggregate scoring reads)
  - mathshapes.custom.growth_prediction (tower_growth_forecast — per-tier
    forecasts across many identical individuals)
  - nutrition.custom.harvest_analysis (realized-vs-mature harvest yield)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 9
"""

from aquaponics.plant_growth_normalized_basis import (
    closed_form_logistic, free_soil_constants,
)

CONDITIONS = ('healthy', 'stressed', 'failed')

#: supply_factor at/above this = healthy (full rate); below this but
#: above FAIL_THRESHOLD = stressed (reduced rate); below FAIL_THRESHOLD
#: = failed (treated as never establishing — no growth from the seed
#: state). A coarser 2-cut version of the detailed model's per-tick
#: streak tracking, since this module evaluates a CONSTANT condition
#: across the whole run rather than iterating — a real, stated
#: simplification, not a hidden loss of fidelity.
STRESS_THRESHOLD = 0.6
FAIL_THRESHOLD = 0.3

#: Volume-based part-to-part interaction priors (ABSTRACT, tunable) —
#: kept from the original aqp-8 model as a cheap aggregate-scale
#: sanity-check estimate. NOT the real mechanism — see
#: aquaponics.plant_growth_normalized_basis.transport_factor() (phase 9) for
#: the actual computed source-sink coupling in the detailed model.
#: source-part → target-part → {'sign': +1|-1, 'per_cm3': magnitude}.
PART_INTERACTIONS = {
    'leaf': {
        'root': {'sign': -1, 'per_cm3': 0.0020,
                 'why': 'canopy transpiration + nutrient demand loads '
                        'the roots'},
        'fruit': {'sign': +1, 'per_cm3': 0.0015,
                  'why': 'leaf photosynthate supports fruit fill'},
    },
    'root': {
        'leaf': {'sign': +1, 'per_cm3': 0.0030,
                 'why': 'root uptake capacity supports shoot growth'},
        'stem': {'sign': +1, 'per_cm3': 0.0020,
                 'why': 'root uptake + anchorage supports the stem'},
    },
    'fruit': {
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


def _parts_of(manager, plant_name):
    return [p for p in _rows(manager, 'PlantPart')
            if getattr(p, 'plant_name', '') == plant_name]


def grow(manager, plant_name, days=60.0, dt_days=1.0, supply_factor=1.0,
        supply_factor_by_part=None, count=1):
    """THE simplified/aggregate growth read. Pulls per-part rate/
    ceiling constants from the REAL detailed model
    (free_soil_constants) and evaluates its REAL closed-form curve
    directly at each age point — no independent growth model, no
    per-tick iteration.

    supply_factor: an overall 0-1 scalar, constant for the WHOLE run
      ("roughly how favorable are conditions") — NOT the detailed
      model's per-stress-type machinery. Defaults to 1.0 (ideal/
      unconfined), matching this module's own historical default
      behavior for callers that pass nothing.
    supply_factor_by_part: optional {PlantPart name: scalar} override,
      for a specific part.
    count: population size — the SAME single-individual trajectory,
      multiplied. "If we had a whole forest of these... what yield are
      we getting."

    Returns per-part final state, a real (closed-form, not iterated)
    trajectory, survival + failure reason, and an ABSTRACT interaction
    estimate — see module docstring for what changed vs the old
    per-tick aqp-8 model and why."""
    constants = free_soil_constants(manager, plant_name)
    if not constants.get('ok'):
        return constants
    parts = _parts_of(manager, plant_name)
    if not parts:
        return {'ok': False,
                'error': f"no PlantParts for plant '{plant_name}'"}
    supply_factor_by_part = supply_factor_by_part or {}
    count = max(1, int(count))

    steps = max(1, int(round(float(days) / float(dt_days))))
    state = {}
    for part in parts:
        name = getattr(part, 'name', '')
        ptype = getattr(part, 'part', 'leaf')
        ref = constants['partRefs'].get(ptype)
        if ref is None:
            # Honest gap: no growth-rate reference for this part TYPE
            # (free_soil_constants found no PlantGrowthModel/PlantPart
            # data for it) — skipped rather than guessed.
            continue
        factor = max(0.0, min(1.0, supply_factor_by_part.get(
            name, supply_factor)))
        state[name] = {
            'partType': ptype,
            'vMax': ref['maxVolumeCm3'],
            'rate': ref['growthRatePerDay'],
            'factor': factor,
            'condition': 'failed' if factor < FAIL_THRESHOLD
                        else 'stressed' if factor < STRESS_THRESHOLD
                        else 'healthy',
        }
    if not state:
        return {'ok': False,
                'error': f"no growth-rate reference for any PlantPart "
                         f"of '{plant_name}' (free_soil_constants "
                         'found no matching partRefs)'}

    trajectories = {name: [] for name in state}
    for i in range(steps):
        t = i * dt_days
        for name, st in state.items():
            if st['condition'] == 'failed':
                # A real simplification, stated plainly: the
                # simplified model does not simulate decay dynamics
                # under failure (the detailed per-tick model can) —
                # "no viable growth under these conditions," volume
                # stays at the seed state for the whole run.
                v = 0.02 * st['vMax']
            else:
                effective_rate = st['rate'] * st['factor']
                v = closed_form_logistic(
                    0.02 * st['vMax'], effective_rate, st['vMax'],
                    float(t))
            trajectories[name].append(round(v * count, 3))

    per_part = []
    any_failed = False
    for name, st in state.items():
        failed = st['condition'] == 'failed'
        any_failed = any_failed or failed
        final_v = (trajectories[name][-1] if trajectories[name]
                  else round(0.02 * st['vMax'] * count, 3))
        per_part.append({
            'part': name, 'partType': st['partType'],
            'finalVolumeCm3': final_v,
            'maxVolumeCm3': round(st['vMax'] * count, 3),
            'fractionOfMax': round(
                (final_v / count) / st['vMax'], 3) if st['vMax'] > 0
                else 0.0,
            'condition': st['condition'],
            'supplyFactor': round(st['factor'], 3),
        })
    interactions = estimate_interactions(
        {n: {'part': s['partType'],
            'volume': (trajectories[n][-1] if trajectories[n] else 0.0)
            / count, 'condition': s['condition']}
        for n, s in state.items()})
    return {
        'ok': True, 'plant': plant_name, 'days': float(days),
        'count': count,
        'perPart': per_part,
        'trajectories': trajectories,
        'survived': not any_failed,
        'failureSummary': None if not any_failed else [
            {'part': name, 'reason':
             f"overall supply factor {st['factor']:.2f} is below the "
             f"failure threshold ({FAIL_THRESHOLD})",
             'supplyFactor': round(st['factor'], 3)}
            for name, st in state.items() if st['condition'] == 'failed'],
        'interactions': interactions,
        'note': 'SIMPLIFIED/AGGREGATE model — constants + the growth '
                'CURVE itself are pulled directly from '
                'aquaponics.plant_growth_normalized_basis (the real, single-'
                'plant detailed model); supply_factor is a coarse '
                'overall scalar, not the detailed per-stress-type '
                'machinery; interaction magnitudes are ABSTRACT '
                'volume-scaled priors, not the real computed transport '
                '(see plant_growth_normalized.transport_factor). count '
                f'={count} scales one representative trajectory, not '
                'independent per-individual simulations.',
    }


def estimate_interactions(state):
    """Volume-weighted part-to-part interaction estimate, ranked by
    magnitude — kept from the original aqp-8 model as a cheap
    aggregate-scale sanity check. `state` maps any key to a dict with
    'part' (type), 'volume', 'condition'. NOT the real mechanism — see
    plant_growth_normalized.transport_factor() for the real, computed
    source-sink coupling in the detailed model."""
    vol_by_type, cond_by_type = {}, {}
    for st in state.values():
        ptype = st['part']
        vol_by_type[ptype] = vol_by_type.get(ptype, 0.0) + st['volume']
        cond_by_type.setdefault(ptype, st['condition'])
    findings = []
    for src, targets in PART_INTERACTIONS.items():
        if src not in vol_by_type:
            continue
        src_vol = vol_by_type[src]
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
        'note': 'ABSTRACT prior, not measured — magnitude = sign · '
                'per_cm3 prior · source volume · source-condition '
                'scale. For the REAL computed source-sink transport, '
                'see aquaponics.plant_growth_normalized_basis.'
                'transport_factor() (phase 9).',
    }
