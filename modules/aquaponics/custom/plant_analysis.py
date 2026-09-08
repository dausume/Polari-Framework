"""
@cross-cutting
@module aquaponics.custom.plant_analysis
@tags @xc:bindings

Per-part carbon/nutrient capture + gas/nutrient budget (aqp-4) — the
assessment Dustin asked for, as pure functions over PlantPart rows.

Two honest distinctions carried everywhere:
  - CAPTURED-by-volume (all the carbon/nutrient a part builds into its
    structure) vs PERMANENTLY-sequestered (only the part whose FATE
    keeps it locked — harvested and senescing biomass cycles back to
    the atmosphere and is NOT sequestration). Conflating them is the
    standard greenwash; this module refuses to.
  - flux is stated AT MATURITY (a rate) and integrated over the
    lifetime with the plant's own growth-fraction curve, LABELED as a
    first-cut estimate the dynamic sim (later phases) refines.

@consumers
  - aquaponics.plant_api / aquaponics.plant_selftest
@see /AQUAPONICS_MODULE_PLAN.md
"""

import json

#: CO2 mass per unit carbon mass (44/12) — permanent C → CO2-equiv.
CO2_PER_CARBON = 44.0 / 12.0

#: Fates whose carbon stays locked (true sequestration).
PERMANENT_FATES = ('soil-incorporated', 'standing-permanent')


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _by_name(manager, class_name):
    return {getattr(r, 'name', ''): r for r in _rows(manager, class_name)}


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


def _parts_of(manager, plant_name):
    return [p for p in _rows(manager, 'PlantPart')
            if getattr(p, 'plant_name', '') == plant_name]


def part_capture(part):
    """One part's dry structural mass and the carbon + nutrients built
    into its PERMANENT structure, by its mature volume."""
    volume = _f(part, 'mature_volume_cm3')
    density = _f(part, 'dry_density_g_cm3')
    dmf = _f(part, 'dry_matter_fraction')
    perm = _f(part, 'permanent_fraction')
    comp = _parse(getattr(part, 'composition_json', '{}'), '{}')
    dry_mass_g = volume * density   # dry_density already dry basis
    structural_g = dry_mass_g * perm
    fate = getattr(part, 'fate', 'senesces')
    is_permanent = fate in PERMANENT_FATES
    captured = {el: round(structural_g * float(frac), 4)
                for el, frac in comp.items()}
    carbon_g = captured.get('carbon', 0.0)
    return {
        'part': getattr(part, 'name', ''),
        'partType': getattr(part, 'part', ''),
        'matureVolumeCm3': round(volume, 3),
        'dryMassG': round(dry_mass_g, 4),
        'structuralMassG': round(structural_g, 4),
        'fate': fate,
        'permanentlySequestered': is_permanent,
        'capturedByVolumeG': captured,
        'carbonG': round(carbon_g, 4),
        'carbonPermanentG': round(carbon_g if is_permanent else 0.0, 4),
        'co2EquivalentPermanentG': round(
            (carbon_g if is_permanent else 0.0) * CO2_PER_CARBON, 4),
        'dryMatterFraction': dmf,
    }


def plant_lifetime_capture(manager, plant_name):
    """Whole-plant permanent carbon + nutrient capture, per part by
    volume — CAPTURED vs PERMANENTLY-sequestered kept separate."""
    plants = _by_name(manager, 'PlantDefinition')
    plant = plants.get(plant_name)
    if plant is None:
        return {'ok': False,
                'error': f"no PlantDefinition named '{plant_name}'",
                'knownPlants': sorted(plants)}
    parts = _parts_of(manager, plant_name)
    if not parts:
        return {'ok': False,
                'error': f"plant '{plant_name}' has no PlantPart rows",
                'suggestion': {'knob': 'PlantPart',
                               'action': 'add part rows (root/stem/'
                                         'leaf/…) with volume, '
                                         'composition, fate'}}
    per_part = [part_capture(p) for p in parts]
    captured_total, permanent_total = {}, {}
    for pc in per_part:
        for el, g in pc['capturedByVolumeG'].items():
            captured_total[el] = captured_total.get(el, 0.0) + g
            if pc['permanentlySequestered']:
                permanent_total[el] = permanent_total.get(el, 0.0) + g
    carbon_captured = captured_total.get('carbon', 0.0)
    carbon_permanent = permanent_total.get('carbon', 0.0)
    return {
        'ok': True,
        'plant': plant_name,
        'displayName': getattr(plant, 'display_name', '')
        or plant_name,
        'lifeCycle': getattr(plant, 'life_cycle', ''),
        'lifetimeDays': _f(plant, 'lifetime_days'),
        'parts': per_part,
        'carbonCapturedG': round(carbon_captured, 4),
        'carbonPermanentlySequesteredG': round(carbon_permanent, 4),
        'co2EquivalentPermanentG': round(
            carbon_permanent * CO2_PER_CARBON, 4),
        'nutrientsCapturedG': {k: round(v, 4)
                               for k, v in sorted(captured_total.items())},
        'nutrientsPermanentG': {k: round(v, 4)
                                for k, v in sorted(permanent_total.items())},
        'sequestrationFraction': round(
            carbon_permanent / carbon_captured, 4)
        if carbon_captured else None,
        'note': 'CAPTURED = carbon/nutrient built into structure; '
                'PERMANENTLY-sequestered = only parts whose fate keeps '
                'it locked (soil-incorporated / standing). Harvested '
                'and senescing biomass cycles back — counting it as '
                'sequestration would be greenwash.',
    }


def plant_gas_nutrient_budget(manager, plant_name):
    """Whole-plant net daily flux at maturity (nutrients + CO2 + O2),
    the survival MIN-MAX bands per species, and a lifetime estimate
    integrated with the growth-fraction curve (labeled first-cut)."""
    plants = _by_name(manager, 'PlantDefinition')
    plant = plants.get(plant_name)
    if plant is None:
        return {'ok': False,
                'error': f"no PlantDefinition named '{plant_name}'"}
    parts = _parts_of(manager, plant_name)
    if not parts:
        return {'ok': False,
                'error': f"plant '{plant_name}' has no PlantPart rows"}

    # Net signed flux per species: 'in' positive (uptake), 'out'
    # negative (release). needed/min/max accumulate per direction.
    species_flux = {}
    for p in parts:
        flux = _parse(getattr(p, 'flux_json', '{}'), '{}')
        for sp, spec in flux.items():
            direction = spec.get('direction', 'in')
            sign = 1.0 if direction == 'in' else -1.0
            acc = species_flux.setdefault(
                sp, {'in': 0.0, 'out': 0.0, 'needed': 0.0,
                     'min': 0.0, 'max': 0.0, 'parts': []})
            rate = float(spec.get('needed', 0) or 0)
            acc['in' if sign > 0 else 'out'] += rate
            acc['needed'] += sign * rate
            acc['min'] += sign * float(spec.get('min', 0) or 0)
            acc['max'] += sign * float(spec.get('max', 0) or 0)
            acc['parts'].append({
                'part': getattr(p, 'name', ''),
                'direction': direction,
                'needed': rate,
                'min': spec.get('min'), 'max': spec.get('max')})

    # Lifetime integral: effective growing days weighted by the
    # growth-fraction curve (mean fraction over the lifecycle).
    stages = _parse(getattr(plant, 'growth_stages_json', '[]'), '[]')
    lifetime = _f(plant, 'lifetime_days')
    if stages:
        weighted = 0.0
        for s in stages:
            span = float(s.get('endDay', 0)) - float(s.get('startDay', 0))
            weighted += span * float(s.get('growthFraction', 1.0))
        effective_days = weighted
    else:
        effective_days = lifetime * 0.5   # linear-growth fallback

    species_report = []
    for sp, acc in sorted(species_flux.items()):
        net = acc['needed']
        species_report.append({
            'species': sp,
            'netDailyMg': round(net, 4),
            'direction': 'net-in' if net > 0 else
                         'net-out' if net < 0 else 'balanced',
            'uptakeMgDay': round(acc['in'], 4),
            'releaseMgDay': round(acc['out'], 4),
            'survivalBandMgDay': {'min': round(acc['min'], 4),
                                  'max': round(acc['max'], 4)},
            'lifetimeNetMg': round(net * effective_days, 2),
            'byPart': acc['parts'],
        })
    co2 = next((s for s in species_report if s['species'] == 'co2'),
               None)
    o2 = next((s for s in species_report if s['species'] == 'o2'),
              None)
    return {
        'ok': True,
        'plant': plant_name,
        'displayName': getattr(plant, 'display_name', '')
        or plant_name,
        'lifetimeDays': lifetime,
        'effectiveGrowingDays': round(effective_days, 2),
        'species': species_report,
        'netCo2FixedMgDay': round(co2['netDailyMg'], 4)
        if co2 else None,
        'netO2ReleasedMgDay': round(-o2['netDailyMg'], 4)
        if o2 else None,
        'lifetimeCo2FixedMg': round(co2['lifetimeNetMg'], 2)
        if co2 else None,
        'lifetimeO2ReleasedMg': round(-o2['lifetimeNetMg'], 2)
        if o2 else None,
        'note': 'net-in = the plant DRAWS the species (CO2 fixation, '
                'nutrient uptake); net-out = it RELEASES (O2, root '
                'respiration CO2). Survival bands are the summed '
                'per-part min/max. Lifetime figures integrate the '
                'maturity rate over the growth-fraction curve — a '
                'first-cut the dynamic simulation refines.',
    }
