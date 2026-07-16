"""
@cross-cutting
@module aquaponics.water_level
@tags @xc:bindings

Plant-growth-sim phase 11 (2026-07-15) — Dustin: "so we can see how
long it takes it to be absorbed or dissapate due to heat and
atmosphere or other factors and the plant absorbing the water
obviously." A real water-LEVEL trajectory during a batch's "sit"
period (aquaponics.water_batch, phase 10), decomposed into THREE
named, independently-computed loss mechanisms — never one lumped
"water disappears" number:

  1. DRAINAGE — gravity through the pot's own output hole. Reuses
     aquaponics.hydraulics.reservoir_model()/build_darcy_payload()
     UNCHANGED (the same physics the water-flow visualization, phase
     3, already uses) — just re-evaluated at each simulated level.
  2. EVAPORATION — from the standing water's own surface, driven by
     REAL vapour-pressure-deficit (aquaponics.atmosphere_analysis.
     saturation_vapour_pressure_kpa, Tetens equation — the SAME VPD
     computation atmosphere_state() already exposes as a finding
     driver, reused here as a rate driver instead).
  3. TRANSPIRATION — "the plant absorbing the water" — driven by the
     SAME VPD, scaled by the plant's REAL current leaf surface area
     (aquaponics.plant_growth_normalized.current_canopy_profile) and
     gated by a real light-driven stomatal-activity proxy (reusing
     phase 8's light_field absorption, since stomata open in response
     to light) — the water a plant actually draws through its roots is
     lost to the pot precisely because it's being pulled through the
     plant, the same mechanism as XYLEM transport in phase 9's own
     module docstring, now given a real volumetric magnitude.

1mm of depth over 1 m^2 of surface = 1 L exactly — the standard
agronomic ET/irrigation-depth shortcut, used throughout instead of a
separate area/volume conversion constant.

Real, stated v1 simplifications: EVAPORATION_MM_PER_DAY_PER_KPA and
TRANSPIRATION_MM_PER_DAY_PER_KPA are documented, APPROXIMATE
empirical coefficients (real open-water and crop-canopy evaporative
rates under moderate VPD commonly cited in agronomy references) — not
a full Penman-Monteith energy-balance solve (which would need wind
speed / net radiation data this codebase doesn't model). Integration
is simple explicit stepping at `sample_hours` resolution (rates change
slowly relative to an hour, the same "repeated independent solve"
pragmatism already used for the water-flow animation, phase 3).

@consumers
  - aquaponics.plant_growth_normalized.transport_factor (a bound
    system's CURRENT water level, resolved from the active batch's
    elapsed hold time, becomes a real water-availability multiplier on
    root capacity — a fourth input alongside size/nutrient factor)
  - aquaponics.water_level_api (diagnostic reads)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 11
"""

import math

#: Approximate open-water evaporation rate per unit VPD (mm/day per
#: kPa) — a commonly-cited agronomic ballpark, not a full energy-
#: balance solve. See module docstring.
EVAPORATION_MM_PER_DAY_PER_KPA = 3.0
#: Approximate canopy transpiration rate per unit VPD (mm/day per
#: kPa, at fully-open stomata) — somewhat higher than bare-water
#: evaporation (active stomatal pumping), scaled down by the real
#: light-driven stomatal factor below. See module docstring.
TRANSPIRATION_MM_PER_DAY_PER_KPA = 4.0
#: A leaf blade is not a perfect rectangle — a standard loose shape
#: factor for length x width -> real blade area.
LEAF_SHAPE_FACTOR = 0.6


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


def _pot_surface_area_m2(payload):
    """Circular water-surface cross-section (m^2) — payload['geometry']
    ['width_m'] IS the inner diameter, per build_darcy_payload's own
    2-D cross-section convention (reused unchanged)."""
    radius_m = payload['geometry']['width_m'] / 2.0
    return math.pi * radius_m * radius_m


def _leaf_area_m2(canopy_profile):
    """Real current total leaf blade area (m^2) from
    current_canopy_profile — sums length x width x LEAF_SHAPE_FACTOR x
    count across every leaf-type organ (not stem/branch, which don't
    transpire meaningfully through a blade surface)."""
    total_mm2 = 0.0
    for organ in canopy_profile.get('organs', []):
        if organ.get('organ') != 'leaf':
            continue
        total_mm2 += (organ.get('currentLengthMm', 0.0)
                     * organ.get('currentWidthMm', 0.0)
                     * LEAF_SHAPE_FACTOR
                     * organ.get('currentCount', 0))
    return total_mm2 / 1_000_000.0


def _evaporation_rate_ml_hr(vpd_kpa, surface_area_m2):
    mm_per_day = EVAPORATION_MM_PER_DAY_PER_KPA * max(0.0, vpd_kpa)
    l_per_day = mm_per_day * surface_area_m2   # 1mm over 1m^2 = 1L
    return l_per_day * 1000.0 / 24.0


def _transpiration_rate_ml_hr(vpd_kpa, leaf_area_m2, stomatal_factor):
    mm_per_day = (TRANSPIRATION_MM_PER_DAY_PER_KPA * max(0.0, vpd_kpa)
                 * max(0.0, min(1.0, stomatal_factor)))
    l_per_day = mm_per_day * leaf_area_m2
    return l_per_day * 1000.0 / 24.0


def water_level_trajectory(manager, planting_name, hours,
                           sample_hours=1.0, water_name_override=None):
    """The full decomposed water-level simulation for a planting's
    pot, starting FULL (build_darcy_payload's own maintained-level
    default), over `hours` at `sample_hours` resolution. Always
    returns a result dict (never raises) — an unresolvable input is an
    honest 'ok: False' naming the missing knob."""
    from aquaponics.hydraulics import build_darcy_payload, reservoir_model
    from aquaponics.atmosphere_analysis import atmosphere_state
    from aquaponics.light_field import per_part_absorption
    from aquaponics.plant_growth_normalized import (
        REFERENCE_SATURATING_PPFD, current_canopy_profile,
    )

    planting = _named(manager, 'PotPlanting', planting_name)
    if planting is None:
        return {'ok': False,
                'error': f"no PotPlanting named '{planting_name}'"}
    system = _named(manager, 'PotSystemDefinition',
                    getattr(planting, 'system_name', ''))
    if system is None:
        return {'ok': False,
                'error': f"PotPlanting '{planting_name}' has no "
                         'resolvable PotSystemDefinition — nothing to '
                         'simulate against'}

    water_name = water_name_override or getattr(system, 'water_name', '')
    atm = atmosphere_state(manager, getattr(system, 'atmosphere_name', ''))
    if not atm.get('ok'):
        return atm
    built = build_darcy_payload(manager, planting.pot_name,
                                getattr(system, 'soil_name', ''))
    if not built.get('ok'):
        return built
    payload = dict(built['payload'])
    level_m = float(payload['water_level_m'])
    surface_area_m2 = _pot_surface_area_m2(payload)
    vpd_kpa = atm['vapourPressureDeficitKpa']

    canopy = current_canopy_profile(manager, planting_name)
    leaf_area_m2 = _leaf_area_m2(canopy) if canopy.get('ok') else 0.0

    stomatal_factor = 1.0
    if getattr(system, 'light_source_name', ''):
        light_result = per_part_absorption(
            manager, planting_name, system.light_source_name)
        if light_result.get('ok'):
            leaf_ppfd = light_result.get(
                'partAbsorptionPpfd', {}).get('leaf')
            if leaf_ppfd is not None:
                stomatal_factor = max(
                    0.0, min(1.0, leaf_ppfd / REFERENCE_SATURATING_PPFD))

    steps = max(1, int(round(float(hours) / float(sample_hours))))
    trajectory = []
    cumulative = {'drainageMl': 0.0, 'evaporationMl': 0.0,
                 'transpirationMl': 0.0}
    time_to_empty_hours = None
    start_level_mm = level_m * 1000.0
    for i in range(steps):
        t_hr = i * sample_hours
        payload['water_level_m'] = level_m
        drain_result = reservoir_model(payload)
        drain_ml_hr = (drain_result.get('outflowRateMlS', 0.0) * 3600.0
                       if drain_result.get('ok') else 0.0)
        evap_ml_hr = _evaporation_rate_ml_hr(vpd_kpa, surface_area_m2)
        transp_ml_hr = _transpiration_rate_ml_hr(
            vpd_kpa, leaf_area_m2, stomatal_factor)
        trajectory.append({
            'hours': round(t_hr, 2),
            'waterLevelMm': round(level_m * 1000.0, 3),
            'drainageMlHr': round(drain_ml_hr, 3),
            'evaporationMlHr': round(evap_ml_hr, 3),
            'transpirationMlHr': round(transp_ml_hr, 3),
        })
        if level_m <= 0.0 and time_to_empty_hours is None:
            time_to_empty_hours = round(t_hr, 2)
        total_ml = (drain_ml_hr + evap_ml_hr + transp_ml_hr) \
            * sample_hours
        cumulative['drainageMl'] += drain_ml_hr * sample_hours
        cumulative['evaporationMl'] += evap_ml_hr * sample_hours
        cumulative['transpirationMl'] += transp_ml_hr * sample_hours
        level_drop_m = (total_ml / 1_000_000.0) / max(
            surface_area_m2, 1e-9)   # mL -> m^3, over the surface area
        level_m = max(0.0, level_m - level_drop_m)
    if level_m <= 0.0 and time_to_empty_hours is None:
        time_to_empty_hours = round(steps * sample_hours, 2)

    return {
        'ok': True,
        'planting': planting_name,
        'waterName': water_name,
        'startWaterLevelMm': round(start_level_mm, 3),
        'endWaterLevelMm': round(level_m * 1000.0, 3),
        'trajectory': trajectory,
        'cumulativeLossMl': {
            k: round(v, 2) for k, v in cumulative.items()},
        'timeToEmptyHours': time_to_empty_hours,
        'vpdKpa': round(vpd_kpa, 4),
        'leafAreaM2': round(leaf_area_m2, 5),
        'surfaceAreaM2': round(surface_area_m2, 5),
        'stomatalFactor': round(stomatal_factor, 4),
        'note': 'drainage reuses aquaponics.hydraulics.reservoir_model '
                'unchanged; evaporation/transpiration are VPD-driven '
                '(Tetens equation) with documented approximate rate '
                'coefficients, not a full energy-balance solve. '
                'Explicit stepping at sample_hours resolution.',
    }


def current_water_level_fraction(manager, planting_name):
    """The pot's water level RIGHT NOW, as a fraction of full — resolves
    the planting's active batch's elapsed hold time (aquaponics.
    water_batch, phase 10) and simulates forward from a fresh fill for
    that long. Returns (fraction, evidence_dict); (1.0, None) when
    there's nothing to resolve (no bound system / no batch schedule /
    zero-height pot) — an honest 'not modeled here' default, never a
    guessed penalty."""
    from datetime import datetime, timezone

    planting = _named(manager, 'PotPlanting', planting_name)
    if planting is None:
        return 1.0, None
    system = _named(manager, 'PotSystemDefinition',
                    getattr(planting, 'system_name', ''))
    if system is None:
        return 1.0, None
    schedule_name = getattr(system, 'water_batch_schedule_name', '')
    if not schedule_name:
        # No batch schedule bound -> nothing to resolve elapsed hold
        # time FROM — an honest neutral default, never a guessed
        # penalty (and never runs a throwaway simulation just to
        # arrive back at ~1.0, unlike an earlier version of this
        # function).
        return 1.0, None

    from aquaponics.water_batch import active_batch
    planted_at = getattr(planting, 'planted_at', '') or ''
    try:
        elapsed_days = max(0.0, (
            datetime.now(timezone.utc)
            - datetime.fromisoformat(planted_at)
        ).total_seconds() / 86400.0)
    except Exception:
        elapsed_days = 0.0
    batch = active_batch(manager, schedule_name, elapsed_days)
    if not batch.get('ok'):
        return 1.0, None
    elapsed_hours = batch['timeIntoBatchDays'] * 24.0
    water_override = batch['waterName']

    result = water_level_trajectory(
        manager, planting_name, hours=max(elapsed_hours, 0.01),
        sample_hours=max(0.25, elapsed_hours / 20.0 if elapsed_hours
                         else 1.0),
        water_name_override=water_override)
    if not result.get('ok') or result['startWaterLevelMm'] <= 0:
        return 1.0, None
    fraction = max(0.0, min(
        1.0, result['endWaterLevelMm'] / result['startWaterLevelMm']))
    return fraction, {
        'waterLevelFraction': round(fraction, 4),
        'endWaterLevelMm': result['endWaterLevelMm'],
        'startWaterLevelMm': result['startWaterLevelMm'],
        'elapsedHoursIntoBatch': round(elapsed_hours, 3),
        'timeToEmptyHours': result.get('timeToEmptyHours'),
    }
