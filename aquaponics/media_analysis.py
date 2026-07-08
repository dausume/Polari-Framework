"""
@cross-cutting
@module aquaponics.media_analysis
@tags @xc:bindings

Analysis of soil / water / nutrient profiles (aqp-2) — pure functions
over the growth_media rows. Every derived quantity travels with its
basis, every out-of-range value is a finding naming its knob, and
unknown nutrient species REFUSE (semantics are never invented — the
data_ingestion honesty idiom).

@consumers
  - aquaponics.media_api / aquaponics.selftest_growth_media
@see /AQUAPONICS_MODULE_PLAN.md
"""

import json


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _by_name(manager, class_name):
    return {getattr(r, 'name', ''): r for r in _rows(manager, class_name)}


def _f(row, attr, default=None):
    v = getattr(row, attr, default)
    try:
        return float(v) if v is not None and v != '' else default
    except (TypeError, ValueError):
        return default


def _parse(text, fallback):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)


def analyze_nutrient_profile(manager, profile_name):
    """Resolve a profile against the species vocabulary: unknown
    species refuse, in/out-of-range concentrations are findings, and
    the N:P:K balance + total dissolved nutrients are reported."""
    profiles = _by_name(manager, 'NutrientProfile')
    profile = profiles.get(profile_name)
    if profile is None:
        return {'ok': False,
                'error': f"no NutrientProfile named '{profile_name}'",
                'knownProfiles': sorted(profiles)}
    species = _by_name(manager, 'NutrientSpecies')
    conc = _parse(getattr(profile, 'concentrations_json', '{}'), '{}')
    unknown = sorted(set(conc) - set(species))
    if unknown:
        return {'ok': False,
                'error': f'unknown nutrient species: {unknown}',
                'knownSpecies': sorted(species),
                'suggestion': {
                    'knob': 'NutrientSpecies',
                    'action': 'add these species rows (name, role, '
                              'unit, typical range) before profiling '
                              '— concentrations are never invented'}}

    entries, findings = [], []
    for name, value in conc.items():
        sp = species[name]
        lo, hi = _f(sp, 'typical_min'), _f(sp, 'typical_max')
        try:
            v = float(value)
        except (TypeError, ValueError):
            findings.append({'kind': 'non-numeric', 'species': name,
                             'evidence': f"value '{value}' is not a "
                                         'number'})
            continue
        status = 'in-range'
        if lo is not None and v < lo:
            status = 'low'
            findings.append({
                'kind': 'below-typical', 'species': name,
                'evidence': f'{v} {getattr(sp, "unit", "")} < typical '
                            f'min {lo}',
                'suggestion': {'knob': 'NutrientProfile.'
                                       'concentrations_json',
                               'action': f'raise {name} toward '
                                         f'[{lo}, {hi}]'}})
        elif hi is not None and v > hi:
            status = 'high'
            findings.append({
                'kind': 'above-typical', 'species': name,
                'evidence': f'{v} {getattr(sp, "unit", "")} > typical '
                            f'max {hi}',
                'suggestion': {'knob': 'NutrientProfile.'
                                       'concentrations_json',
                               'action': f'lower {name} toward '
                                         f'[{lo}, {hi}]'}})
        entries.append({'species': name,
                        'symbol': getattr(sp, 'symbol', ''),
                        'role': getattr(sp, 'role', ''),
                        'value': v, 'unit': getattr(sp, 'unit', ''),
                        'typicalMin': lo, 'typicalMax': hi,
                        'status': status})

    # N:P:K balance (total N = nitrate-N + ammonium-N).
    n = sum(float(conc.get(s, 0) or 0)
            for s in ('nitrate-n', 'ammonium-n'))
    p = float(conc.get('phosphorus-p', 0) or 0)
    k = float(conc.get('potassium-k', 0) or 0)
    npk = None
    if p > 0:
        npk = {'N': round(n / p, 2), 'P': 1.0, 'K': round(k / p, 2),
               'basis': 'relative to P; N = nitrate-N + ammonium-N'}
    macro_total = sum(
        e['value'] for e in entries if e['role'] in
        ('macronutrient', 'secondary'))
    return {
        'ok': True,
        'profile': profile_name,
        'displayName': getattr(profile, 'display_name', '')
        or profile_name,
        'basis': getattr(profile, 'basis', ''),
        'ph': _f(profile, 'ph'),
        'ecDsM': _f(profile, 'electrical_conductivity_ds_m'),
        'species': entries,
        'npkRatio': npk,
        'macronutrientTotal': round(macro_total, 3),
        'findings': findings,
        'balanced': not findings,
        'note': 'ranges are the NutrientSpecies typical bands (edit '
                'those rows to recalibrate); N:P:K is by mass relative '
                'to phosphorus',
    }


def soil_water_capacity(manager, soil_name):
    """Plant-available water + drainage character of a soil."""
    soils = _by_name(manager, 'SoilDefinition')
    soil = soils.get(soil_name)
    if soil is None:
        return {'ok': False,
                'error': f"no SoilDefinition named '{soil_name}'",
                'knownSoils': sorted(soils)}
    fc = _f(soil, 'field_capacity_vol')
    wp = _f(soil, 'wilting_point_vol')
    sat = _f(soil, 'saturation_vol')
    bulk = _f(soil, 'bulk_density_kg_m3')
    particle = _f(soil, 'particle_density_kg_m3')
    porosity = _f(soil, 'porosity')
    if porosity is None and bulk and particle:
        porosity = 1.0 - bulk / particle
    findings = []
    available = None
    if fc is not None and wp is not None:
        available = fc - wp
        if available <= 0:
            findings.append({
                'kind': 'no-available-water',
                'evidence': f'field capacity {fc} <= wilting point '
                            f'{wp} — no plant-available water',
                'suggestion': {'knob': 'field_capacity_vol / '
                                       'wilting_point_vol',
                               'action': 'field capacity must exceed '
                                         'wilting point'}})
    if sat is not None and fc is not None and sat < fc:
        findings.append({
            'kind': 'saturation-below-capacity',
            'evidence': f'saturation {sat} < field capacity {fc}',
            'suggestion': {'knob': 'saturation_vol',
                           'action': 'saturation should be >= field '
                                     'capacity'}})
    return {
        'ok': True,
        'soil': soil_name,
        'displayName': getattr(soil, 'display_name', '') or soil_name,
        'texture': getattr(soil, 'texture', ''),
        'porosity': round(porosity, 4) if porosity is not None
        else None,
        'plantAvailableWaterVol': round(available, 4)
        if available is not None else None,
        'drainableVol': round(sat - fc, 4)
        if sat is not None and fc is not None else None,
        'hydraulicConductivityMmHr':
            _f(soil, 'hydraulic_conductivity_mm_hr'),
        'cationExchangeCmolKg': _f(soil, 'cation_exchange_cmol_kg'),
        'scales': _parse(getattr(soil, 'scales_json', '[]'), '[]'),
        'findings': findings,
        'note': 'plant-available water = field capacity - wilting '
                'point; drainable = saturation - field capacity. The '
                'aqp-3 hydraulics reads these as the storage the '
                'reservoir fills and the soil holds.',
    }


def water_summary(manager, water_name):
    """The solution's state, source, and dissolved-gas standing."""
    waters = _by_name(manager, 'WaterDefinition')
    water = waters.get(water_name)
    if water is None:
        return {'ok': False,
                'error': f"no WaterDefinition named '{water_name}'",
                'knownWaters': sorted(waters)}
    do = _f(water, 'dissolved_oxygen_mg_l')
    findings = []
    # Root health rule of thumb: < 5 mg/L dissolved O2 stresses roots.
    if do is not None and do < 5.0:
        findings.append({
            'kind': 'low-dissolved-oxygen',
            'evidence': f'dissolved O2 {do} mg/L < 5 mg/L — roots '
                        'stress and pathogens favour low-O2 water',
            'suggestion': {'knob': 'dissolved_oxygen_mg_l',
                           'action': 'aerate the source (aquaponics: '
                                     'more circulation/air stones)'}})
    profile = getattr(water, 'nutrient_profile_name', '')
    nutrient = analyze_nutrient_profile(manager, profile) \
        if profile else {'ok': False,
                         'error': 'no nutrient_profile_name set'}
    return {
        'ok': True,
        'water': water_name,
        'displayName': getattr(water, 'display_name', '')
        or water_name,
        'sourceKind': getattr(water, 'source_kind', ''),
        'sourceParams': _parse(
            getattr(water, 'source_params_json', '{}'), '{}'),
        'temperatureC': _f(water, 'temperature_c'),
        'ph': _f(water, 'ph'),
        'dissolvedOxygenMgL': do,
        'dissolvedCo2MgL': _f(water, 'dissolved_co2_mg_l'),
        'flowRateLPerHr': _f(water, 'flow_rate_l_per_hr'),
        'scales': _parse(getattr(water, 'scales_json', '[]'), '[]'),
        'nutrientProfile': nutrient.get('profile')
        if nutrient.get('ok') else None,
        'nutrientBalanced': nutrient.get('balanced')
        if nutrient.get('ok') else None,
        'findings': findings,
        'note': 'the aquaponic/hydroponic source feeds the pot input '
                'holes at flowRateLPerHr; dissolved gases couple to '
                'the atmosphere and root demand in later phases',
    }
