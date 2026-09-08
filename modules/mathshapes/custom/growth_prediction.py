"""
@cross-cutting
@module mathshapes.custom.growth_prediction
@tags @xc:bindings, @xc:render-3d

shape-4 — PREDICTIVE root/plant growth in an aquaponic tower, with the
math-shape geometry as the CONSTRAINT. Couples three existing layers
(reuse, don't rebuild):

  - shape-2 `tower_geometry`  → each tier's GROW VOLUME = the carrying
    capacity the pot geometry provides.
  - `plant_growth_simplified.grow` (2026-07-15, was aqp-8's
    `plant_growth.grow` — renamed + rebuilt to pull its constants +
    curve from the real detailed model, plant_growth_normalized) →
    the plant's intrinsic per-part growth trajectory (unconfined),
    CAPPED here by the tier volume. This is EXACTLY the "mass
    evaluation at scale" use case the simplified model was redefined
    for — one representative trajectory applied across every tier.
  - morph-1 `confinement_assessment` → does the mature root ball fit the
    tier, the resulting dwarf factor, and whether the plant can be kept
    in that tier INDEFINITELY (+ the root-prune cadence).

`tower_growth_forecast` returns, per tier, a "fits / needs pruning /
will fail" verdict with the LIMITING FACTOR named (honest-absence;
labels travel with numbers). Duck-typed manager, stdlib only.

@consumers
  - mathshapes.tower_api (GET .../growth-forecast)
@see /MATH_SHAPES_PLAN.md (PHASE shape-4), /AQUAPONICS_POT_SHAPE_PLAN.md phase 9
"""

from aquaponics.custom import plant_growth_simplified
from mathshapes.custom.tower_analysis import tower_geometry
from plant_morphology.custom.morphology_analysis import confinement_assessment


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _has_root_model(manager, plant_name):
    return any(getattr(r, 'plant_name', '') == plant_name
              for r in _rows(manager, 'RootSystemModel'))


def _total_trajectory(growth):
    """Sum the per-part volume trajectories into a whole-plant volume vs
    time (cm³ per step)."""
    trajs = growth.get('trajectories') or {}
    if not trajs:
        return []
    length = max((len(t) for t in trajs.values()), default=0)
    total = [0.0] * length
    for series in trajs.values():
        for i, v in enumerate(series):
            total[i] += float(v)
    return total


def _tier_verdict(conf, capped, cap_cm3, mature_total):
    """Turn the confinement result + the geometric cap into a per-tier
    verdict + the limiting factor (named)."""
    ratio = conf.get('confinementRatio', 0.0)
    indefinite = conf.get('canKeepIndefinitely', False)
    cadence = conf.get('rootPruneCadenceDays', 0.0) or 0.0
    conf_limit = conf.get('limitingFactor')

    if not indefinite:
        # morph-1 says it cannot be held indefinitely — it will decline.
        return 'will fail', conf_limit or (
            'root ball outgrows the tier and the plant is not dwarfable '
            '(knob: RootSystemModel.dwarfable / enlarge the pot via '
            'shape-2 modify, or choose a dwarf variety)')
    if cadence > 0:
        return 'needs pruning', (
            f'root-bound but maintainable — root-prune every '
            f'{cadence:.0f} days to hold it in this tier indefinitely '
            f'(knob: RootSystemModel.root_prune_cadence_days)')
    if ratio < 1.0 or capped:
        # confined but tolerant/dwarfable → holds by dwarfing; note the
        # geometric cap if the mature plant would overrun the tier.
        if capped:
            return 'fits (dwarfed)', (
                f'grows to the tier capacity {cap_cm3:.0f} cm³ then holds '
                f'(dwarfed to ~{100.0 * cap_cm3 / mature_total:.0f}% of '
                f'its unconfined size) — the pot geometry is the carrying '
                f'capacity (knob: enlarge via shape-2 modify)')
        return 'fits (dwarfed)', None
    return 'fits', None


def tower_growth_forecast(manager, tower_name, plant_name, days=180.0,
                          dt_days=2.0):
    """Predict per-tier root/plant growth in a tower over `days`, with the
    tier's math-shape grow volume as the carrying capacity."""
    geo = tower_geometry(manager, tower_name)
    if not geo.get('ok'):
        return geo
    if not _has_root_model(manager, plant_name):
        return {'ok': False,
                'error': f"no RootSystemModel for plant '{plant_name}' — "
                         f"root-bound prediction needs morph-1 root data",
                'suggestion': {'knob': 'RootSystemModel (plant_name)',
                               'action': 'seed a morph-1 root model for '
                                         'the plant'}}
    # intrinsic (unconfined) growth trajectory — same for every tier.
    growth = plant_growth_simplified.grow(manager, plant_name,
                                          days=float(days),
                                          dt_days=float(dt_days))
    if not growth.get('ok'):
        return {'ok': False,
                'error': f"growth model unavailable: "
                         f"{growth.get('error')}",
                'detail': growth}
    total_traj = _total_trajectory(growth)
    mature_total = sum(p.get('finalVolumeCm3', 0.0)
                       for p in growth.get('perPart', []))
    growth_survived = growth.get('survived', True)

    per_tier = []
    verdict_counts = {}
    for tier in geo.get('perTier', []):
        cap_cm3 = tier.get('growVolumeCm3', 0.0)
        cap_l = tier.get('growVolumeL', 0.0)
        conf = confinement_assessment(manager, plant_name,
                                      container_volume_l=cap_l)
        if not conf.get('ok'):
            return {'ok': False,
                    'error': 'confinement assessment failed',
                    'detail': conf}

        capped = mature_total > cap_cm3 > 0
        realized = min(mature_total, cap_cm3) if cap_cm3 > 0 \
            else mature_total

        # time-to-carrying-capacity from the growth trajectory
        time_to_cap = None
        if cap_cm3 > 0 and total_traj:
            for i, v in enumerate(total_traj):
                if v >= cap_cm3:
                    time_to_cap = round(i * float(dt_days), 1)
                    break

        verdict, limiting = _tier_verdict(conf, capped, cap_cm3,
                                          mature_total)
        # a supply failure in the growth model overrides — name it too.
        if not growth_survived:
            verdict = 'will fail'
            fail = (growth.get('failureSummary') or [{}])[0]
            reason = fail.get('reason', 'supply factor too low')
            limiting = f"growth failure: {reason} (supply, not geometry)"

        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        per_tier.append({
            'tier': tier.get('tier'),
            'centreHeightCm': tier.get('centreHeightCm'),
            'tierGrowVolumeCm3': round(cap_cm3, 1),
            'tierGrowVolumeL': round(cap_l, 3),
            'matureUnconfinedVolumeCm3': round(mature_total, 1),
            'realizedVolumeCm3': round(realized, 1),
            'geometricallyCapped': bool(capped),
            'confinementRatio': conf.get('confinementRatio'),
            'dwarfFactor': conf.get('dwarfFactor'),
            'denseRootBallVolumeL': conf.get('denseRootBallVolumeL'),
            'timeToCarryingCapacityDays': time_to_cap,
            'canKeepIndefinitely': conf.get('canKeepIndefinitely'),
            'rootPruneCadenceDays': conf.get('rootPruneCadenceDays'),
            'verdict': verdict,
            'limitingFactor': limiting})

    return {
        'ok': True, 'tower': tower_name, 'plant': plant_name,
        'days': float(days),
        'potShape': geo.get('potShape'),
        'nTiers': geo.get('nTiers'),
        'matureUnconfinedVolumeCm3': round(mature_total, 1),
        'growthSurvived': growth_survived,
        'perTier': per_tier,
        'summary': {
            'verdictCounts': verdict_counts,
            'allTiersFit': all(t['verdict'].startswith('fits')
                               for t in per_tier),
            'anyTierFails': any(t['verdict'] == 'will fail'
                                for t in per_tier)},
        'note': 'tier carrying capacity = shape-2 grow volume; root-bound '
                'from morph-1 confinement; per-part growth from aqp-8, '
                'capped by the tier geometry. Estimates — labels travel.'}
