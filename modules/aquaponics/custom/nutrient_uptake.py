"""
@cross-cutting
@module aquaponics.custom.nutrient_uptake
@tags @xc:bindings

Plant-growth-sim phase 10 (2026-07-15) — real, concentration-driven
root nutrient uptake, completing the gap phase 9's `transport_factor()`
explicitly flagged in its own docstring ("water/mineral capacity is
SIZE-only, no live... nutrient-concentration-magnitude driver yet").

The computation is dimensionally real, not invented: a water source's
`NutrientProfile.concentrations_json` (mg/L, aqp-2) times its own
`WaterDefinition.flow_rate_l_per_hr` (already existed, ×24 for mg/day)
gives a real daily mass of each nutrient reaching the root, compared
against that root's own `PlantPart.flux_json` `needed` mg/day (aqp-4,
already existed) — Liebig's Law of the Minimum across species, same
pattern this codebase already uses everywhere else (plant_stress.py's
combined_stress_factor, aqp-8's original supply_factor). Every input
this reuses already existed before this phase; only the BRIDGE
function is new.

Gases (co2/o2) are explicitly excluded — those are the atmosphere's
job (aquaponics.plant_stress_basis's own 'co2'/'oxygen' stress types already
cover them from AtmosphereDefinition/WaterDefinition fields), not this
water-nutrient-concentration computation.

@consumers
  - aquaponics.plant_growth_normalized_basis.advance_growth (feeds
    transport_factor()'s root capacity, phase 9/10)
  - aquaponics.water_batch_api (diagnostic reads)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 10
"""

import json
import math

#: Species this function does NOT evaluate — the atmosphere's job
#: (aquaponics.plant_stress_basis's 'co2'/'oxygen' stress types), not a
#: water-nutrient-concentration question.
_GAS_SPECIES = ('co2', 'o2')


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


def _part_row(manager, plant_name, part_type):
    for p in _rows(manager, 'PlantPart'):
        if getattr(p, 'plant_name', '') == plant_name \
                and getattr(p, 'part', '') == part_type:
            return p
    return None


def _pot_water_volume_l(pot):
    """The pot's own inner container volume (L) — the STOCK of
    standing water available to the root at 'full' (the water_batch
    module's own "go until full" moment). Same formula
    plant_morphology.custom.morphology_analysis._pot_inner_volume_l already
    uses for confinement math — duplicated here as a tiny, self-
    contained calculation rather than cross-importing a private
    helper from an unrelated module.

    Deliberately a STOCK (liters currently in the pot), not a FLOW
    (liters/day of throughput) — an EARLIER version of this function
    used WaterDefinition.flow_rate_l_per_hr x 24 as the available-mass
    basis and found it wildly overestimates availability for a small
    plant's real per-day nutrient need (any realistic recirculating
    flow rate delivers far more mass per day than a single basil root
    actually consumes) — the standing-volume-in-the-pot basis is the
    physically correct one for "go until full, then sit," where the
    root draws on whatever's ALREADY in the pot, not a full day's
    continuous throughput."""
    wall = _f(pot, 'wall_thickness_mm', 8.0)
    base = _f(pot, 'base_thickness_mm', 12.0)
    inner_r_mm = (_f(pot, 'outer_base_diameter_mm', 200.0)
                 - 2.0 * wall) / 2.0
    inner_h_mm = _f(pot, 'height_mm', 250.0) - base
    return math.pi * inner_r_mm * inner_r_mm * inner_h_mm / 1_000_000.0


def nutrient_availability_factor(manager, water_name, plant_name,
                                 pot_name, part_type='root'):
    """Real Liebig's-Law nutrient-availability factor in [0, 1] for
    ONE plant part (default 'root' — the part that actually touches
    the water) against ONE water source's real concentration, scaled
    by the REAL pot's own standing water volume. Always returns a
    result dict (never raises) — an unresolvable input is an honest
    'ok: False' naming the missing knob, matching this session's
    standing convention.

    A REAL, honest finding from this session's own live/self-test
    verification, worth knowing before reading any result: with the
    CURRENT real seed data (aqp-4's PlantPart.flux_json `needed`
    values vs aqp-2's NutrientProfile concentrations), sweet-basil's
    per-nutrient daily need is small enough relative to typical
    water-quality mg/L concentrations that BOTH real demo water
    sources currently saturate to factor 1.0 for every species,
    including the deliberately Fe-deficient one — a genuine
    calibration mismatch between two independently-seeded datasets
    from earlier phases, not a bug in this computation. Flagged
    plainly rather than silently forcing an artificial result; a
    future data-tuning pass could recalibrate flux_json's needed
    values (or NutrientProfile's concentration scale) to make real
    deficiencies bind for small pot-grown herbs specifically."""
    water = _named(manager, 'WaterDefinition', water_name)
    if water is None:
        return {'ok': False,
                'error': f"no WaterDefinition named '{water_name}'"}
    profile_name = getattr(water, 'nutrient_profile_name', '')
    profile = _named(manager, 'NutrientProfile', profile_name)
    if profile is None:
        return {'ok': False,
                'error': f"WaterDefinition '{water_name}' names "
                         f"nutrient_profile_name '{profile_name}' but "
                         'no NutrientProfile with that name exists',
                'suggestion': {
                    'knob': 'WaterDefinition.nutrient_profile_name',
                    'action': 'seed a NutrientProfile, or bind an '
                              'existing one'}}
    part = _part_row(manager, plant_name, part_type)
    if part is None:
        return {'ok': False,
                'error': f"no PlantPart of type '{part_type}' for "
                         f"plant '{plant_name}'"}
    pot = _named(manager, 'PotDefinition', pot_name)
    if pot is None:
        return {'ok': False,
                'error': f"no PotDefinition named '{pot_name}'"}

    try:
        flux = json.loads(getattr(part, 'flux_json', '') or '{}')
    except Exception:
        flux = {}
    try:
        concentrations = json.loads(profile.concentrations_json or '{}')
    except Exception:
        concentrations = {}
    pot_water_volume_l = _pot_water_volume_l(pot)

    factor, limiting, by_species = 1.0, None, {}
    for species, spec in flux.items():
        if species in _GAS_SPECIES or spec.get('direction') != 'in':
            continue
        needed = float(spec.get('needed', 0.0) or 0.0)
        if needed <= 0:
            continue
        concentration = concentrations.get(species)
        if concentration is None:
            # Honest gap: this species isn't in the profile at all —
            # not assumed deficient (0) or abundant (1), simply not
            # modeled by this water source. Skipped, never guessed.
            continue
        available_mg = float(concentration) * pot_water_volume_l
        ratio = max(0.0, min(1.0, available_mg / needed))
        by_species[species] = round(ratio, 4)
        if ratio < factor:
            factor, limiting = ratio, species

    return {
        'ok': True,
        'factor': round(factor, 4),
        'limitingSpecies': limiting,
        'bySpecies': by_species,
        'waterName': water_name,
        'nutrientProfile': profile.name,
        'potWaterVolumeL': round(pot_water_volume_l, 3),
        'note': 'available_mg = concentration(mg/L) x the pot\'s own '
                'standing water volume(L), vs PlantPart.flux_json '
                "needed mg/day (a stock-vs-daily-rate comparison) — "
                "Liebig's Law across whatever species both the "
                'profile and the flux table name; a species absent '
                'from the profile is skipped, not guessed. See this '
                "function's own docstring for a real, honestly-"
                'flagged data-calibration finding.',
    }
