"""@module aquaponics.objects.plant_growth_normalized._shared — what the plant_growth_normalized row classes share (constants, seeds, helpers); split from plant_growth_normalized_basis.py (sap-2c)."""
from datetime import datetime, timezone
import json
import math

SANE_MAX_LINEAR_MM = 250_000.0
GROWTH_SEED_EPSILON = 0.02
SEED_RESERVE_FLOOR = 0.15
REFERENCE_SATURATING_PPFD = 600.0
ORGAN_TO_PART = {
    'root-visible': 'root',
    'branch': 'stem',
}
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
def _clamp_linear_mm(value, label, warnings):
    """The SANE_MAX_LINEAR_MM safety valve — never silent."""
    if value > SANE_MAX_LINEAR_MM:
        warnings.append(
            f'{label} = {value:.0f} mm exceeds the sane ceiling '
            f'({SANE_MAX_LINEAR_MM:.0f} mm, ~2x the tallest known '
            'living tree) — clamped. This is a compute/geometry '
            'safety valve, not a botanical judgement about the '
            'species; raise SANE_MAX_LINEAR_MM if a real use case '
            'genuinely needs more.')
        return SANE_MAX_LINEAR_MM
    return value
def organ_part_name(organ):
    """Which PLANT_PARTS name this OrganModel.organ value's growth
    tracks under — see ORGAN_TO_PART."""
    return ORGAN_TO_PART.get(organ, organ)
def free_soil_constants(manager, plant_name):
    """The species' UNCONFINED reference maximums, PER PART — everything
    a per-part vector shape/growth equation needs. Gathered from
    EXISTING rows, not a new source of truth; the only new fields are
    RootSystemModel's taper/soil-density additions (2026-07-15) and
    the PlantDefinition.normalized_growth_rate_per_day FALLBACK rate
    (used only for a part with no PlantGrowthModel row of its own —
    PlantGrowthModel.growth_rate, aqp-8's existing per-part field, is
    the primary source, per Dustin's "vector growth... per unit time
    based on the plant part the vector defines")."""
    plant = _named(manager, 'PlantDefinition', plant_name)
    if plant is None:
        return {'ok': False,
                'error': f"no PlantDefinition named '{plant_name}'"}
    root = None
    for r in _rows(manager, 'RootSystemModel'):
        if getattr(r, 'plant_name', '') == plant_name:
            root = r
            break
    if root is None:
        return {'ok': False,
                'error': f"no RootSystemModel for plant '{plant_name}'",
                'suggestion': {
                    'knob': 'RootSystemModel (plant_name)',
                    'action': 'seed a root-system stand-in for this '
                              'species before running growth'}}

    warnings = []
    root_depth_mm = _clamp_linear_mm(
        _f(root, 'natural_depth_mm', 200.0),
        f"{plant_name} RootSystemModel.natural_depth_mm", warnings)
    root_spread_mm = _clamp_linear_mm(
        _f(root, 'natural_spread_radius_mm', 120.0),
        f"{plant_name} RootSystemModel.natural_spread_radius_mm",
        warnings)
    mature_height_mm = _clamp_linear_mm(
        _f(plant, 'mature_height_mm', 400.0),
        f"{plant_name} PlantDefinition.mature_height_mm", warnings)
    mature_canopy_mm = _clamp_linear_mm(
        _f(plant, 'mature_canopy_mm', 300.0),
        f"{plant_name} PlantDefinition.mature_canopy_mm", warnings)

    fallback_rate = _f(plant, 'normalized_growth_rate_per_day', 0.045)
    parts = [p for p in _rows(manager, 'PlantPart')
             if getattr(p, 'plant_name', '') == plant_name]
    growth_models = {getattr(g, 'part_name', ''): g
                     for g in _rows(manager, 'PlantGrowthModel')}

    # PER-PART reference: max volume + growth rate, one entry per
    # PlantPart row (root/stem/leaf/...) — the vector growth equation's
    # own knobs, keyed exactly the way a bone's `kind` will look them up.
    part_refs = {}
    for part in parts:
        part_name = getattr(part, 'part', '')
        gm = growth_models.get(getattr(part, 'name', ''))
        max_v = _f(gm, 'max_volume_cm3', 0.0) if gm else 0.0
        if max_v <= 0:
            max_v = _f(part, 'mature_volume_cm3', 0.0)
        rate = _f(gm, 'growth_rate', 0.0) if gm else 0.0
        if rate <= 0:
            rate = fallback_rate
        part_refs[part_name] = {
            'maxVolumeCm3': round(max_v, 2),
            'growthRatePerDay': rate,
            'growthRateSource': 'PlantGrowthModel' if (gm and _f(
                gm, 'growth_rate', 0.0) > 0) else 'PlantDefinition '
                'fallback (normalized_growth_rate_per_day)',
        }
    max_whole_plant_volume_cm3 = sum(
        r['maxVolumeCm3'] for r in part_refs.values())

    root_ball_cm3 = ((2.0 / 3.0) * math.pi * root_spread_mm
                     * root_spread_mm * root_depth_mm
                     * _f(root, 'root_ball_fraction', 0.5)) / 1000.0
    if 'root' in part_refs:
        part_refs['root']['denseRootBallVolumeCm3'] = round(
            root_ball_cm3, 2)

    return {
        'ok': True,
        'plant': plant_name,
        'partRefs': part_refs,
        'root': {
            'pattern': getattr(root, 'pattern', ''),
            'maxDepthMm': round(root_depth_mm, 1),
            'maxSpreadRadiusMm': round(root_spread_mm, 1),
            'denseRootBallVolumeCm3': round(root_ball_cm3, 2),
            'maxVolumeCm3': part_refs.get('root', {}).get(
                'maxVolumeCm3', 0.0),
            'soilRootDensityGPerCm3': _f(
                root, 'soil_root_density_g_per_cm3', 0.02),
            'coreDiameterMm': _f(root, 'root_core_diameter_mm', 3.0),
            'taperExponent': _f(root, 'root_taper_exponent', 1.6),
            'hairDiameterMm': _f(root, 'root_hair_diameter_mm', 0.2),
        },
        'canopy': {
            'maxHeightMm': round(mature_height_mm, 1),
            'maxCanopySpreadMm': round(mature_canopy_mm, 1),
        },
        'maxWholePlantVolumeCm3': round(max_whole_plant_volume_cm3, 2),
        'fallbackGrowthRatePerDay': fallback_rate,
        'warnings': warnings,
        'note': 'unconfined references — infinite free soil, no '
                'container boundary. partRefs is keyed by PLANT_PARTS '
                'name (plant_basis.PLANT_PARTS); an OrganModel row maps '
                'to one via organ_part_name(). See constrained_limits() '
                'for what a specific pot actually allows.',
    }
def constrained_limits(manager, pot_name, plant_name):
    """Stage 1's free-soil references, run through THIS pot's actual
    geometry. Reuses plant_morphology.custom.morphology_analysis.
    confinement_assessment() unchanged for the dwarf factor + the
    survives/doesn't-survive verdict — this function reframes that
    result as each part's normalized-growth CEILING, it does not
    recompute confinement math independently (two implementations of
    the same survival question would be a real drift risk). The SAME
    dwarf factor currently applies to every part uniformly (a whole-
    plant-dwarfs-together simplification, stated plainly — real plants
    likely dwarf roots most directly and canopy secondarily; a per-
    part confinement response is future work, not hidden as if already
    modeled)."""
    constants = free_soil_constants(manager, plant_name)
    if not constants.get('ok'):
        return constants

    from plant_morphology.custom.morphology_analysis import confinement_assessment
    confinement = confinement_assessment(manager, plant_name,
                                         pot_name=pot_name)
    if not confinement.get('ok'):
        return confinement

    dwarf_factor = float(confinement['dwarfFactor'])
    survives = bool(confinement['canKeepIndefinitely'])
    root = constants['root']
    canopy = constants['canopy']

    part_ceilings = {}
    for part_name, ref in constants['partRefs'].items():
        part_ceilings[part_name] = {
            'growthRatePerDay': ref['growthRatePerDay'],
            'normalizedGrowthCeiling': round(dwarf_factor, 4),
            'limitVolumeCm3': round(
                ref['maxVolumeCm3'] * dwarf_factor ** 3, 2),
        }

    return {
        'ok': True,
        'plant': plant_name,
        'pot': pot_name,
        # THE headline: does the plant stabilize and survive at the
        # limits this pot imposes, or does confinement break it?
        'survivesConfinement': survives,
        'limitingFactor': confinement.get('limitingFactor'),
        'rootPruneCadenceDays': confinement.get('rootPruneCadenceDays'),
        # dwarf_factor doubles as EVERY part's normalized_growth
        # CEILING for now (see docstring) — already the geometric
        # ratio^(1/3)-derived realized-size fraction confinement_
        # assessment computes, volume->linear, not reapplied here.
        'normalizedGrowthCeiling': round(dwarf_factor, 4),
        'partCeilings': part_ceilings,
        'confinementRatio': confinement.get('confinementRatio'),
        'root': {
            'limitDepthMm': round(root['maxDepthMm'] * dwarf_factor, 1),
            'limitSpreadRadiusMm': round(
                root['maxSpreadRadiusMm'] * dwarf_factor, 1),
            'limitVolumeCm3': round(
                root['maxVolumeCm3'] * dwarf_factor ** 3, 2),
        },
        'canopy': {
            'limitHeightMm': round(
                canopy['maxHeightMm'] * dwarf_factor, 1),
            'limitCanopySpreadMm': round(
                canopy['maxCanopySpreadMm'] * dwarf_factor, 1),
        },
        'freeSoilConstants': constants,
        'note': confinement.get(
            'note', 'confinement-scaled from the free-soil references '
                    'above; survivesConfinement is the real stabilize-'
                    'or-decline verdict, not a cosmetic dwarf estimate.'),
    }
def _part_growth(planting):
    try:
        return json.loads(getattr(planting, 'part_growth_json', '') or '{}')
    except Exception:
        return {}
def part_normalized_growth(planting, part_name):
    """One part's current normalized_growth, honestly defaulted to the
    seed epsilon if that part has never been advanced yet."""
    return float(_part_growth(planting).get(part_name,
                                            GROWTH_SEED_EPSILON))
def overall_normalized_growth(manager, planting_name):
    """Volume-weighted mean across parts — a single convenience number
    for a UI badge/summary. NOT the state itself (that's per-part) —
    purely a derived read, recomputed on demand, never stored."""
    planting = _named(manager, 'PotPlanting', planting_name)
    if planting is None:
        return {'ok': False,
                'error': f"no PotPlanting named '{planting_name}'"}
    constants = free_soil_constants(manager, planting.plant_name)
    if not constants.get('ok'):
        return constants
    growth = _part_growth(planting)
    total_weight, weighted = 0.0, 0.0
    for part_name, ref in constants['partRefs'].items():
        weight = max(ref['maxVolumeCm3'], 1e-6)
        total_weight += weight
        weighted += weight * growth.get(part_name, GROWTH_SEED_EPSILON)
    overall = (weighted / total_weight) if total_weight > 0 else 0.0
    return {'ok': True, 'planting': planting_name,
            'overallNormalizedGrowth': round(overall, 5),
            'partGrowth': growth,
            'note': 'volume-weighted mean across parts — a summary '
                    'read, not a tracked state; each part\'s own value '
                    'is the real state (advance_growth).'}
def closed_form_logistic(g0, effective_rate, ceiling, dt_days):
    """Exact logistic-with-ceiling solve for one tick (not Euler-
    stepped — stable regardless of dt_days magnitude, and each tick's
    supply_factor is already an independent-per-tick snapshot, same
    "repeated independent solve" pragmatism as the water simulation).
    dg/dt = effective_rate * g * (ceiling - g).

    Public (not module-private) since this is autonomous/time-
    invariant — its own closed form is exact for ANY elapsed dt_days
    from a given start, not just one small tick — so
    aquaponics.custom.plant_growth_simplified (2026-07-15) reuses it
    DIRECTLY to evaluate a trajectory at many ages without iterating,
    "pulling from the isolated single-plant model what the average
    constants would be at different ages" per Dustin's own framing,
    rather than re-deriving its own separate growth curve."""
    g0 = max(GROWTH_SEED_EPSILON * ceiling, min(g0, ceiling))
    if effective_rate <= 0 or dt_days <= 0:
        return g0
    ratio = (ceiling - g0) / g0
    denom = 1.0 + ratio * math.exp(-effective_rate * ceiling * dt_days)
    return ceiling / denom
def _size_fraction(growth, part_name, ceiling):
    """Current normalized_growth as a fraction of that part's own
    ceiling — "how much of this part's apparatus currently exists,"
    the SIZE half of a transport capacity signal."""
    if ceiling <= 0:
        return 0.0
    g = float(growth.get(part_name, GROWTH_SEED_EPSILON))
    return max(0.0, min(1.0, g / ceiling))
def transport_factor(growth, limits, light_absorption_by_part,
                     nutrient_factor=1.0, water_level_factor=1.0):
    """Phase 9 (2026-07-15) — the whole-plant source-sink coupling
    factor: min(root uptake capacity, leaf photosynthesis capacity),
    floored at SEED_RESERVE_FLOOR (a germinating seed's own stored
    reserves bootstrap initial growth before root/leaf apparatus
    exists — without this floor a fresh planting could never leave
    GROWTH_SEED_EPSILON, since size_fraction is ~0 for every part at
    t=0). Returns (factor, evidence_dict). See the module-level
    SEED_RESERVE_FLOOR/REFERENCE_SATURATING_PPFD docstring for the
    full design rationale + stated simplifications.

    nutrient_factor (phase 10, 2026-07-15): a real, concentration-
    driven Liebig's-Law factor from aquaponics.custom.nutrient_uptake.
    nutrient_availability_factor() — multiplies root capacity
    alongside its SIZE fraction, the same way leaf capacity already
    combines SIZE with a real light-magnitude signal.

    water_level_factor (phase 11, 2026-07-15): the pot's REAL current
    standing-water fraction (aquaponics.custom.water_level.
    current_water_level_fraction — drainage + evaporation +
    transpiration all resolved and decayed forward from the active
    batch's last fill) — a root sitting in a nearly-empty pot has less
    to draw from regardless of that water's nutrient concentration or
    the root's own size, a genuinely separate axis from both.

    Both default to 1.0 (neutral, "not modeled here") when the caller
    has no water source/level to resolve — never a guessed penalty.

    Public (not a `_`-prefixed helper) — aquaponics.plant_stress_basis or a
    future diagnostic endpoint may want to inspect this independent of
    a full advance_growth() call."""
    part_ceilings = limits.get('partCeilings', {})
    if 'root' not in part_ceilings or 'leaf' not in part_ceilings:
        # A species missing either part (e.g. no distinguishable leaf
        # row) has no transport bottleneck to model — honest no-op,
        # never a guessed penalty.
        return 1.0, None

    root_ceiling = float(part_ceilings['root']['normalizedGrowthCeiling'])
    leaf_ceiling = float(part_ceilings['leaf']['normalizedGrowthCeiling'])
    root_capacity = _size_fraction(growth, 'root', root_ceiling) \
        * max(0.0, min(1.0, nutrient_factor)) \
        * max(0.0, min(1.0, water_level_factor))
    leaf_size = _size_fraction(growth, 'leaf', leaf_ceiling)
    leaf_ppfd = light_absorption_by_part.get('leaf')
    light_factor = (max(0.0, min(1.0, leaf_ppfd
                                 / REFERENCE_SATURATING_PPFD))
                    if leaf_ppfd is not None else 1.0)
    leaf_capacity = leaf_size * light_factor

    raw = min(root_capacity, leaf_capacity)
    factor = max(SEED_RESERVE_FLOOR, raw)
    # Two INDEPENDENT facts, never conflated: which raw capacity was
    # smaller (a diagnostic label, true regardless of the floor) vs
    # whether the floor actually determined the applied factor (a
    # separate boolean) — reporting only one or the other would hide
    # real information (e.g. a badly stunted leaf still deserves to be
    # NAMED as the bottleneck even while the floor is what's actually
    # keeping growth alive).
    limiting_capacity = 'root-uptake' if root_capacity < leaf_capacity \
        else 'leaf-photosynthesis'
    evidence = {
        'rootCapacity': round(root_capacity, 4),
        'leafCapacity': round(leaf_capacity, 4),
        'leafLightFactor': round(light_factor, 4),
        'rootNutrientFactor': round(max(0.0, min(1.0, nutrient_factor)), 4),
        'rootWaterLevelFactor': round(
            max(0.0, min(1.0, water_level_factor)), 4),
        'limitingCapacity': limiting_capacity,
        'flooredBySeedReserve': raw < SEED_RESERVE_FLOOR,
        'transportFactor': round(factor, 4),
    }
    return factor, evidence
def advance_growth(manager, planting_name, dt_days,
                   water_supply_factor=None, soil_supply_factor=None,
                   now=None):
    """Advances EVERY part of ONE PotPlanting by dt_days of real time,
    independently. Per part: RATE this tick = that part's OWN
    PlantGrowthModel.growth_rate (or the species fallback) × a supply
    factor (conditions — how FAST); CEILING = constrained_limits()'s
    partCeilings[part] (confinement — how FAR it can ever get).
    Conditions and confinement are deliberately separate multipliers,
    never collapsed into one number.

    The supply factor comes from one of three sources, in priority
    order (phase 7, 2026-07-15 — Dustin: "these equations can vary
    based on different kinds of stress conditions... interconnected
    matrix equations... atmospheric and soil and water inputs"):

      1. water_supply_factor/soil_supply_factor EXPLICITLY passed
         (not None) — a manual override, same product-of-two-factors
         behavior as before phase 7, UNIFORM across every part. An
         explicit knob always wins over automatic computation.
      2. Neither passed + PotPlanting.system_name set — PER-PART
         stress factors auto-computed from that PotSystemDefinition's
         real atmosphere/water/soil rows via
         aquaponics.plant_stress_basis.combined_stress_factor() (Liebig's
         Law of the Minimum across whatever stress-type curves exist
         for that part). Genuinely different parts can get genuinely
         different factors here.
      3. Neither passed + no system_name — 1.0 for every part, an
         honest "no conditions data linked, no penalty applied"
         default, never a guessed penalty."""
    planting = _named(manager, 'PotPlanting', planting_name)
    if planting is None:
        return {'ok': False,
                'error': f"no PotPlanting named '{planting_name}'"}
    if dt_days < 0:
        return {'ok': False, 'error': 'dt_days must be >= 0'}

    # Computed once, up front — reused both for phase 10's water-batch
    # elapsed-time resolution below AND as the final last_advanced_at
    # stamp, so a caller-supplied `now` is honored consistently
    # throughout the whole call rather than two independent
    # datetime.now() reads potentially disagreeing by microseconds.
    now_dt = datetime.fromisoformat(now) if now else \
        datetime.now(timezone.utc)

    limits = constrained_limits(manager, planting.pot_name,
                                planting.plant_name)
    if not limits.get('ok'):
        return limits

    manual_override = (water_supply_factor is not None
                       or soil_supply_factor is not None)
    system = None
    if manual_override:
        manual_factor = (
            max(0.0, min(1.0, water_supply_factor))
            if water_supply_factor is not None else 1.0) * (
            max(0.0, min(1.0, soil_supply_factor))
            if soil_supply_factor is not None else 1.0)
        mode = 'manual'
    elif getattr(planting, 'system_name', ''):
        system = _named(manager, 'PotSystemDefinition',
                        planting.system_name)
        mode = 'stress-equations' if system is not None \
            else 'no-linkage (system_name not found)'
    else:
        mode = 'no-linkage'

    # Phase 8 (2026-07-15) — a bound LightSourceDefinition computes a
    # REAL per-part light-field absorption ONCE per tick (it walks the
    # planting's own skeleton, one live computation for every part at
    # once) rather than per-part, then overrides just the 'light'
    # stress type's input below. Local import — avoids a module-load
    # cycle through plant_skeleton -> this module.
    light_absorption_by_part = {}
    if system is not None and getattr(system, 'light_source_name', ''):
        from aquaponics.custom.light_field import per_part_absorption
        light_result = per_part_absorption(
            manager, planting_name, system.light_source_name)
        if light_result.get('ok'):
            light_absorption_by_part = light_result.get(
                'partAbsorptionPpfd', {})
        # An unresolvable light source is an honest gap, not a hard
        # failure of the whole tick — the 'light' stress curve simply
        # falls back to the static AtmosphereDefinition field below
        # (light_absorption_by_part stays empty), same as any other
        # missing-linkage case.

    # Phase 10 (2026-07-15) — resolve the ACTIVE water source. A bound
    # WaterBatchSchedule OVERRIDES the system's static water_name for
    # this tick (which batch currently governs the pot, given how long
    # it's been since planting — "go until full, then sit for N hours/
    # days," see aquaponics.water_batch_basis's own docstring); no schedule
    # bound (or it fails to resolve) falls back to water_name
    # unchanged — 100% backward compatible with phases 6-9.
    active_water_name = getattr(system, 'water_name', '') \
        if system is not None else ''
    if system is not None and getattr(
            system, 'water_batch_schedule_name', ''):
        from aquaponics.water_batch_basis import active_batch
        planted_at = getattr(planting, 'planted_at', '') or ''
        try:
            elapsed_days = max(
                0.0, (now_dt - datetime.fromisoformat(planted_at))
                .total_seconds() / 86400.0)
        except Exception:
            elapsed_days = 0.0   # honest "just planted" default, never a crash
        batch_result = active_batch(
            manager, system.water_batch_schedule_name, elapsed_days)
        if batch_result.get('ok'):
            active_water_name = batch_result['waterName']
        # An unresolvable schedule is an honest gap — falls back to
        # the system's static water_name, same pattern as light above.

    # Phase 10 — real, concentration-driven root nutrient uptake
    # (aquaponics.custom.nutrient_uptake), against whichever water source is
    # ACTIVE this tick (batch-resolved above, or the static binding).
    nutrient_result = None
    if active_water_name:
        from aquaponics.custom.nutrient_uptake import nutrient_availability_factor
        nutrient_result = nutrient_availability_factor(
            manager, active_water_name, planting.plant_name,
            planting.pot_name, 'root')

    # Phase 11 (2026-07-15) — real, decayed CURRENT water level (a
    # bound batch schedule's elapsed hold time resolved through
    # drainage + evaporation + transpiration, aquaponics.custom.water_level).
    # No schedule bound -> factor 1.0 (honest "not modeled here"), same
    # convention as light/nutrient above.
    water_level_factor_value = 1.0
    water_level_evidence = None
    if system is not None and getattr(
            system, 'water_batch_schedule_name', ''):
        from aquaponics.custom.water_level import current_water_level_fraction
        water_level_factor_value, water_level_evidence = \
            current_water_level_fraction(manager, planting_name)

    growth = _part_growth(planting)

    # Phase 9 (2026-07-15) — source-sink TRANSPORT coupling, scoped to
    # stress-equations mode only (same precedent as the light field
    # above: an additional layer of realism that activates once a real
    # system is bound, never altering the manual-override or no-
    # linkage paths). Computed ONCE per tick from the plant's CURRENT
    # size + real light absorption + real nutrient availability
    # (phase 10) + real water level (phase 11) — see transport_factor()
    # 's own docstring for the full design.
    plant_transport_factor = 1.0
    transport_evidence = None
    if system is not None:
        plant_transport_factor, transport_evidence = transport_factor(
            growth, limits, light_absorption_by_part,
            nutrient_factor=(nutrient_result.get('factor', 1.0)
                             if nutrient_result and nutrient_result.get('ok')
                             else 1.0),
            water_level_factor=water_level_factor_value)

    per_part_report = {}
    worst_condition_rank = 0   # 0 healthy, 1 stressed, 2 failed
    RANK = {'healthy': 0, 'stressed': 1, 'senescing': 1, 'failed': 2}
    uniform_factors = set()

    for part_name, ceiling_info in limits['partCeilings'].items():
        stress_evidence = None
        if manual_override:
            supply_factor = manual_factor
        elif system is not None:
            from aquaponics.plant_stress_basis import (
                combined_stress_factor, part_stress_factors,
            )
            by_type = part_stress_factors(
                manager, planting.plant_name, part_name,
                system.atmosphere_name, active_water_name,
                system.soil_name,
                light_value_override=light_absorption_by_part.get(
                    part_name))
            supply_factor, limiting_type, ok_factors = \
                combined_stress_factor(by_type)
            stress_evidence = {'limitingStressType': limiting_type,
                               'factorsByType': {
                                   k: round(v, 4)
                                   for k, v in ok_factors.items()}}
        else:
            supply_factor = 1.0
        uniform_factors.add(round(supply_factor, 6))

        ceiling = float(ceiling_info['normalizedGrowthCeiling'])
        base_rate = float(ceiling_info['growthRatePerDay'])
        # plant_transport_factor is a SEPARATE, whole-plant multiplier
        # (phase 9) — this part's OWN local conditions (supply_factor)
        # times the whole-plant source-sink bottleneck, never collapsed
        # into one number, same "conditions vs confinement" separation
        # principle this docstring already states for rate vs ceiling.
        effective_rate = base_rate * supply_factor * plant_transport_factor
        previous = float(growth.get(part_name, GROWTH_SEED_EPSILON))
        updated = closed_form_logistic(previous, effective_rate,
                                       ceiling, float(dt_days))
        growth[part_name] = updated

        if not limits['survivesConfinement'] and updated >= ceiling * 0.98:
            part_condition = 'stressed'
        elif supply_factor < 0.15 or plant_transport_factor < 0.15:
            part_condition = 'stressed'
        else:
            part_condition = 'healthy'
        worst_condition_rank = max(worst_condition_rank,
                                   RANK.get(part_condition, 0))
        per_part_report[part_name] = {
            'previousNormalizedGrowth': round(previous, 5),
            'normalizedGrowth': round(updated, 5),
            'ceiling': round(ceiling, 4),
            'baseRatePerDay': base_rate,
            'supplyFactor': round(supply_factor, 4),
            'transportFactor': round(plant_transport_factor, 4),
            'effectiveRatePerDay': round(effective_rate, 5),
            'condition': part_condition,
            **({'stressEvidence': stress_evidence}
               if stress_evidence is not None else {}),
        }

    planting.part_growth_json = json.dumps(growth)
    planting.condition = ('failed' if worst_condition_rank >= 2
                          else 'stressed' if worst_condition_rank == 1
                          else 'healthy')
    planting.last_advanced_at = now_dt.isoformat()
    try:
        manager.db.saveInstanceInDB(planting)
    except Exception:
        pass

    result = {
        'ok': True,
        'planting': planting_name,
        'mode': mode,
        'parts': per_part_report,
        'condition': planting.condition,
        'survivesConfinement': limits['survivesConfinement'],
        'limitingFactor': limits.get('limitingFactor'),
        'note': 'one independent logistic-with-ceiling solve PER PART '
                'for this dt_days — repeated calls approximate a '
                'continuous trajectory the same way the water '
                'simulation approximates a fill '
                '(see AQUAPONICS_POT_SHAPE_PLAN.md).',
    }
    if transport_evidence is not None:
        result['transport'] = transport_evidence
    if system is not None:
        result['activeWaterName'] = active_water_name
        if nutrient_result is not None:
            result['nutrientAvailability'] = nutrient_result
        if water_level_evidence is not None:
            result['waterLevel'] = water_level_evidence
    # A single top-level supplyFactor is only meaningful when every
    # part actually used the same one (manual override, or no-linkage
    # 1.0) — the whole point of stress-equations mode is that parts
    # CAN differ, so it's omitted there; read parts[*].supplyFactor.
    if len(uniform_factors) == 1:
        result['supplyFactor'] = round(next(iter(uniform_factors)), 4)
    return result
def current_root_profile(manager, planting_name, n_samples=12):
    """The root envelope + a sampled taper curve AT THE ROOT PART'S
    CURRENT normalized_growth — the SHAPE equation a branching
    generator evaluates for root-kind vectors. Linear dimensions scale
    by normalized_growth**(1/3) (normalized growth is a VOLUME
    fraction; volume -> linear is a cube root, same scaling law
    confinement_assessment already uses for its dwarf factor)."""
    planting = _named(manager, 'PotPlanting', planting_name)
    if planting is None:
        return {'ok': False,
                'error': f"no PotPlanting named '{planting_name}'"}
    limits = constrained_limits(manager, planting.pot_name,
                                planting.plant_name)
    if not limits.get('ok'):
        return limits

    ceiling_info = limits['partCeilings'].get('root')
    if ceiling_info is None:
        return {'ok': False,
                'error': f"plant '{planting.plant_name}' has no "
                         "'root' PlantPart — can't shape a root "
                         'vector without it'}
    g = part_normalized_growth(planting, 'root')
    ceiling = float(ceiling_info['normalizedGrowthCeiling'])
    frac = (g / ceiling) if ceiling > 0 else 0.0
    linear = frac ** (1.0 / 3.0)

    root = limits['root']
    root_ref = limits['freeSoilConstants']['root']
    depth_mm = root['limitDepthMm'] * linear
    spread_mm = root['limitSpreadRadiusMm'] * linear
    core_d = root_ref['coreDiameterMm'] * linear
    exponent = root_ref['taperExponent']
    hair_d = root_ref['hairDiameterMm']

    samples = []
    extent = max(depth_mm, 1e-6)
    for i in range(n_samples):
        distance_mm = extent * i / max(1, n_samples - 1)
        taper = max(0.0, 1.0 - distance_mm / extent)
        diameter_mm = max(hair_d, core_d * (taper ** exponent))
        samples.append({'distanceMm': round(distance_mm, 2),
                        'diameterMm': round(diameter_mm, 3)})

    return {
        'ok': True,
        'planting': planting_name,
        'part': 'root',
        'normalizedGrowth': round(g, 5),
        'growthFractionOfCeiling': round(frac, 4),
        'currentDepthMm': round(depth_mm, 1),
        'currentSpreadRadiusMm': round(spread_mm, 1),
        'currentVolumeCm3': round(root['limitVolumeCm3'] * frac, 2),
        'soilRootDensityGPerCm3': root_ref['soilRootDensityGPerCm3'],
        'taperSamples': samples,
        'randomSeed': int(planting.random_seed),
        'note': 'linear dims scale as growthFractionOfCeiling**(1/3) — '
                'normalized_growth is a volume fraction.',
    }
def current_canopy_profile(manager, planting_name):
    """Each OrganModel's CURRENT (scaled) dimensions + count — the
    SHAPE equation for stem/leaf/branch/etc.-kind vectors, evaluated
    at THAT organ's OWN mapped part's current normalized_growth
    (organ_part_name()), not one global fraction. OrganModel's own
    stored dimensions are already "at full maturity" (no age-scaling
    exists anywhere in plant_morphology today), so this is the first
    place that ever produces a SUB-mature organ size."""
    planting = _named(manager, 'PotPlanting', planting_name)
    if planting is None:
        return {'ok': False,
                'error': f"no PotPlanting named '{planting_name}'"}
    limits = constrained_limits(manager, planting.pot_name,
                                planting.plant_name)
    if not limits.get('ok'):
        return limits

    organs = [o for o in _rows(manager, 'OrganModel')
             if getattr(o, 'plant_name', '') == planting.plant_name]
    if not organs:
        return {'ok': False,
                'error': f"no OrganModel rows for plant "
                         f"'{planting.plant_name}'"}
    current = []
    canopy_linear_max = 0.0
    for o in organs:
        organ_kind = getattr(o, 'organ', '')
        part_name = organ_part_name(organ_kind)
        ceiling_info = limits['partCeilings'].get(part_name)
        if ceiling_info is None:
            # Honest gap: this organ's part has no growth reference —
            # render it at zero rather than guessing a fraction.
            g, ceiling = 0.0, 1.0
        else:
            g = part_normalized_growth(planting, part_name)
            ceiling = float(ceiling_info['normalizedGrowthCeiling'])
        frac = (g / ceiling) if ceiling > 0 else 0.0
        linear = frac ** (1.0 / 3.0)
        canopy_linear_max = max(canopy_linear_max, linear)
        mature_count = int(_f(o, 'count', 1))
        current.append({
            'organ': organ_kind,
            'part': part_name,
            'shapePrimitive': getattr(o, 'shape_primitive', 'ellipsoid'),
            'arrangement': getattr(o, 'arrangement', 'opposite'),
            'normalizedGrowth': round(g, 5),
            'growthFractionOfCeiling': round(frac, 4),
            'currentCount': max(0, round(mature_count * frac)),
            'matureCount': mature_count,
            'currentLengthMm': round(_f(o, 'length_mm', 40.0) * linear, 2),
            'currentWidthMm': round(_f(o, 'width_mm', 20.0) * linear, 2),
            'currentThicknessMm': round(
                _f(o, 'thickness_mm', 3.0) * linear, 2),
        })
    return {
        'ok': True,
        'planting': planting_name,
        'currentHeightMm': round(
            limits['canopy']['limitHeightMm'] * canopy_linear_max, 1),
        'currentCanopySpreadMm': round(
            limits['canopy']['limitCanopySpreadMm'] * canopy_linear_max,
            1),
        'organs': current,
        'randomSeed': int(planting.random_seed),
        'note': 'each organ scaled by ITS OWN mapped part\'s '
                'growthFractionOfCeiling (organ_part_name) — a leaf and '
                'a stem can genuinely be at different progress. '
                'currentHeightMm/currentCanopySpreadMm use the fastest-'
                'growing part as a whole-canopy envelope estimate.',
    }
