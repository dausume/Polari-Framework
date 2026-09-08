"""
@cross-cutting
@module waxprint.custom.melt_analysis

Manager-facing layer over waxprint.custom.auger_melt — resolves an assembly +
feedstock + condition by NAME from the object tables, converts the mm /
Celsius row fields into the SI payload the pure physics wants (applying
the assembly `assembly_scale` and the condition's nozzle override), runs
the two-zone melt, and returns a result dict plus honest resolution
notes. No physics lives here (that is auger_melt); no HTTP lives here
(that is waxprint_api).

@consumers
  - waxprint.waxprint_api (/api/waxprint/melt)
  - waxprint.custom.print_optimizer (per-trial evaluation)
  - waxprint.auger_melt_selftest
"""

from waxprint.custom import auger_melt


def find_row(manager, class_name, name):
    """First row in manager.objectTables[class_name] whose .name == name,
    else None. Mirrors the aquaponics lookup idiom."""
    table = (getattr(manager, 'objectTables', {}) or {}).get(class_name, {}) or {}
    for obj in table.values():
        if getattr(obj, 'name', None) == name:
            return obj
    return None


def _f(obj, attr, default=0.0):
    try:
        return float(getattr(obj, attr, default))
    except (TypeError, ValueError):
        return default


def effective_nozzle_diameter_mm(assembly, condition):
    """Condition override wins when > 0, else the assembly's own nozzle."""
    override = _f(condition, 'nozzle_diameter_mm', 0.0)
    return override if override > 0 else _f(assembly, 'nozzle_diameter_mm', 0.4)


def build_melt_payload(assembly, feedstock, condition):
    """Assemble the SI kwargs for auger_melt.two_zone_melt from three
    rows. mm -> m and the assembly scale are applied here (pellets do NOT
    scale with the machine — they are the feedstock)."""
    scale = _f(assembly, 'assembly_scale', 1.0) or 1.0
    mm_to_m = 0.001

    nozzle_d_mm = effective_nozzle_diameter_mm(assembly, condition)

    return {
        # feedstock
        'pellet_diameter_m': _f(feedstock, 'pellet_diameter_mm', 3.0) * mm_to_m,
        'density': _f(feedstock, 'density_kg_m3', 950.0),
        'cp': _f(feedstock, 'specific_heat_j_kgk', 2100.0),
        'latent_heat_fusion': _f(feedstock, 'latent_heat_fusion_j_kg', 180000.0),
        'k_wax': _f(feedstock, 'thermal_conductivity_w_mk', 0.25),
        'melt_point_c': _f(feedstock, 'melt_point_c', 82.0),
        # geometry (scaled)
        'bore_m': _f(assembly, 'bore_diameter_mm', 12.0) * mm_to_m * scale,
        'core_m': _f(assembly, 'screw_core_diameter_mm', 6.0) * mm_to_m * scale,
        'pitch_m': _f(assembly, 'screw_pitch_mm', 8.0) * mm_to_m * scale,
        'barrel_length_m': _f(assembly, 'barrel_length_mm', 120.0) * mm_to_m * scale,
        'auger_zone_fraction': _f(assembly, 'auger_zone_fraction', 0.6),
        'nozzle_radius_m': (nozzle_d_mm / 2.0) * mm_to_m * scale,
        'nozzle_land_m': _f(assembly, 'nozzle_land_mm', 0.8) * mm_to_m * scale,
        # process
        'rpm': _f(condition, 'rpm', 30.0),
        'ambient_c': _f(condition, 'ambient_temp_c', 22.0),
        'auger_temp_c': _f(condition, 'auger_temp_c', 90.0),
        'hotend_temp_c': _f(condition, 'hotend_temp_c', 110.0),
        # coupling
        'h_wall': _f(assembly, 'wall_h_w_m2k', 250.0),
        'drag_efficiency': _f(assembly, 'drag_efficiency', 0.6),
        # viscosity
        'eta_ref_pa_s': _f(feedstock, 'viscosity_ref_pa_s', 5.0),
        'viscosity_ref_temp_c': _f(feedstock, 'viscosity_ref_temp_c', 100.0),
        'viscosity_activation_k': _f(feedstock, 'viscosity_activation_k', 6000.0),
        # safety
        'safe_melt_max_c': _f(feedstock, 'safe_melt_max_c', 150.0),
    }


def material_service_findings(manager, assembly, condition):
    """Resolve the assembly's part materials and check each against the
    zone temperature it must tolerate — a safety axis independent of the
    wax's own degradation ceiling (e.g. a PTFE-lined hotend fails long
    before the wax does). Returns a list of evidence-bearing findings and
    whether any is a hard block."""
    auger_t = _f(condition, 'auger_temp_c', 90.0)
    hotend_t = _f(condition, 'hotend_temp_c', 110.0)
    checks = [
        ('nozzle_material_ref', hotend_t, 'nozzle', 'hotend'),
        ('chamber_material_ref', hotend_t, 'chamber', 'hotend'),
        ('auger_material_ref', auger_t, 'auger', 'auger'),
    ]
    findings, blocked = [], False
    for ref_attr, zone_temp, part, zone in checks:
        name = getattr(assembly, ref_attr, '') or ''
        if not name:
            continue
        mat = find_row(manager, 'DeviceMaterialDefinition', name)
        if mat is None:
            continue
        limit = _f(mat, 'max_service_temp_c', 400.0)
        if zone_temp > limit:
            blocked = True
            findings.append({
                'code': 'material-over-service-temp', 'severity': 'block',
                'evidence': f'{part} material "{name}" max service temp '
                            f'{limit:.0f}C is below the {zone} set '
                            f'{zone_temp:.0f}C.',
                'knob': f'assembly.{ref_attr} / condition.{zone}_temp_c',
                'action': f'Pick a {part} material rated above '
                          f'{zone_temp:.0f}C, or lower the {zone} zone.'})
    return findings, blocked


def run_melt(manager, assembly_name, feedstock_name, condition_name):
    """Resolve the three rows and run the two-zone melt. Returns
    {'ok': True, 'result': {...}, 'inputs': {...}} or {'ok': False,
    'error', 'missing': [...]} naming exactly which row was not found."""
    assembly = find_row(manager, 'PrinterAssemblyDefinition', assembly_name)
    feedstock = find_row(manager, 'WaxFeedstockDefinition', feedstock_name)
    condition = find_row(manager, 'PrintConditionDefinition', condition_name)

    missing = []
    if assembly is None:
        missing.append(f'PrinterAssemblyDefinition:{assembly_name}')
    if feedstock is None:
        missing.append(f'WaxFeedstockDefinition:{feedstock_name}')
    if condition is None:
        missing.append(f'PrintConditionDefinition:{condition_name}')
    if missing:
        return {'ok': False, 'error': 'row(s) not found', 'missing': missing}

    result, payload = evaluate_melt(manager, assembly, feedstock, condition)
    return {
        'ok': True,
        'assembly': assembly_name,
        'feedstock': feedstock_name,
        'condition': condition_name,
        'result': result,
        'inputs': payload,
    }


def evaluate_melt(manager, assembly, feedstock, condition):
    """Rows-based melt core: the two-zone physics PLUS the part-material
    service-temperature safety axis (which needs the manager to resolve
    the material rows). Returns (result, payload). Used by run_melt and by
    the optimizer with ephemeral trial conditions."""
    payload = build_melt_payload(assembly, feedstock, condition)
    result = auger_melt.two_zone_melt(**payload)
    result['nozzle_diameter_mm'] = effective_nozzle_diameter_mm(
        assembly, condition)
    mat_findings, mat_blocked = material_service_findings(
        manager, assembly, condition)
    if mat_findings:
        result['findings'] = list(result.get('findings', [])) + mat_findings
    if mat_blocked:
        result['thermally_safe'] = False
        result['printable'] = False
    return result, payload


def run_melt_rows(assembly, feedstock, condition):
    """Same as run_melt but with already-resolved rows (used by the
    optimizer's inner loop to avoid repeated table scans)."""
    payload = build_melt_payload(assembly, feedstock, condition)
    result = auger_melt.two_zone_melt(**payload)
    result['nozzle_diameter_mm'] = effective_nozzle_diameter_mm(
        assembly, condition)
    return result, payload
