"""@module aquaponics.objects.plant_stress._shared — what the plant_stress row classes share (constants, seeds, helpers); split from plant_stress_basis.py (sap-2c)."""
import json

STRESS_TYPES = ('temperature', 'co2', 'light', 'humidity', 'oxygen',
                'salinity', 'water-ph')
STRESS_TYPE_FIELDS = {
    'temperature': ('atmosphere', 'temperature_c'),
    'co2':         ('atmosphere', 'co2_ppm'),
    'light':       ('atmosphere', 'light_ppfd_umol_m2_s'),
    'humidity':    ('atmosphere', 'relative_humidity_pct'),
    'oxygen':      ('water', 'dissolved_oxygen_mg_l'),
    'salinity':    ('water', 'electrical_conductivity_ds_m'),
    'water-ph':    ('water', 'ph'),
}
SOURCE_TABLES = {
    'atmosphere': 'AtmosphereDefinition',
    'water': 'WaterDefinition',
    'soil': 'SoilDefinition',
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
def trapezoid_factor(value, min_value, optimal_low, optimal_high,
                     max_value):
    """The Tier-A default response shape — 0 outside [min, max], 1
    across [optimal_low, optimal_high], linear ramps between. Pure
    function, no manager — reused by both live evaluation and the
    diagnostic sweep."""
    if value <= min_value or value >= max_value:
        return 0.0
    if optimal_low <= value <= optimal_high:
        return 1.0
    if value < optimal_low:
        span = optimal_low - min_value
        return (value - min_value) / span if span > 1e-9 else 1.0
    span = max_value - optimal_high
    return (max_value - value) / span if span > 1e-9 else 1.0
def evaluate_curve(manager, curve, atmosphere_name, water_name, soil_name,
                   light_value_override=None):
    """One curve's factor in [0, 1] against the real bound rows —
    Tier B (equation_ref) if set, else Tier A (trapezoid). Always
    returns a result dict (never raises) — an unresolvable input is an
    honest 'ok: False' with the missing knob named, not a silent 1.0.

    light_value_override (plant-growth-sim phase 8, 2026-07-15): when
    given AND curve.stress_type == 'light', the curve's Tier-A
    trapezoid is evaluated against THIS value (a real computed per-
    part light-field absorption, aquaponics.custom.light_field.
    per_part_absorption) instead of the static AtmosphereDefinition.
    light_ppfd_umol_m2_s scalar — an explicit override, never applied
    silently to any OTHER stress type. Ignored for curves with an
    equation_ref (Tier B custom spectra are future work, see
    light_basis.py's module docstring)."""
    names = {'atmosphere': atmosphere_name, 'water': water_name,
            'soil': soil_name}

    if light_value_override is not None and curve.stress_type == 'light' \
            and not curve.equation_ref:
        factor = trapezoid_factor(float(light_value_override),
                                  curve.min_value, curve.optimal_low,
                                  curve.optimal_high, curve.max_value)
        return {'ok': True, 'factor': factor, 'tier': 'light-field',
                'inputField': 'aquaponics.custom.light_field.per_part_absorption',
                'inputValue': light_value_override,
                'bounds': {'min': curve.min_value,
                          'optimalLow': curve.optimal_low,
                          'optimalHigh': curve.optimal_high,
                          'max': curve.max_value}}

    if curve.equation_ref:
        from matrices.matrix_equation_executor import (
            evaluate_equation, MatrixEvalError,
        )
        eq_def = _named(manager, 'MatrixEquationDefinition',
                        curve.equation_ref)
        if eq_def is None:
            return {'ok': False,
                    'error': f"equation_ref '{curve.equation_ref}' "
                             "not found",
                    'suggestion': {
                        'knob': 'MatrixEquationDefinition',
                        'action': f"seed a MatrixEquationDefinition "
                                  f"named '{curve.equation_ref}', or "
                                  "clear equation_ref to use the Tier-A "
                                  "trapezoid"}}
        try:
            bindings_spec = json.loads(
                curve.input_bindings_json or '{}')
        except Exception:
            bindings_spec = {}
        binding_values, evidence_inputs = {}, {}
        for symbol, spec in bindings_spec.items():
            source = spec.get('source')
            field = spec.get('field')
            class_name = SOURCE_TABLES.get(source)
            row_name = names.get(source)
            if class_name is None or not row_name:
                return {'ok': False,
                        'error': f"binding '{symbol}' names an unknown "
                                 f"source '{source}'"}
            row = _named(manager, class_name, row_name)
            if row is None:
                return {'ok': False,
                        'error': f"no {class_name} named '{row_name}' "
                                 f"(needed for binding '{symbol}')"}
            value = getattr(row, field, None)
            if value is None:
                return {'ok': False,
                        'error': f"{class_name} '{row_name}' has no "
                                 f"field '{field}' (binding '{symbol}')"}
            binding_values[symbol] = float(value)
            evidence_inputs[symbol] = float(value)
        try:
            result = evaluate_equation(eq_def, binding_values, manager)
        except MatrixEvalError as e:
            return {'ok': False, 'error': f'equation evaluation failed: '
                                          f'{e}'}
        import numpy as np
        raw = float(np.asarray(result).reshape(-1)[0])
        clamped = max(0.0, min(1.0, raw))
        return {'ok': True, 'factor': clamped, 'tier': 'equation',
                'equationRef': curve.equation_ref,
                'rawValue': raw, 'inputs': evidence_inputs,
                'clamped': clamped != raw}

    source, field = STRESS_TYPE_FIELDS.get(
        curve.stress_type, (None, None))
    class_name = SOURCE_TABLES.get(source)
    row_name = names.get(source)
    if class_name is None or not row_name:
        return {'ok': False,
                'error': f"stress type '{curve.stress_type}' has no "
                         'bound source row to read (no system linkage)'}
    row = _named(manager, class_name, row_name)
    if row is None:
        return {'ok': False,
                'error': f"no {class_name} named '{row_name}'"}
    value = getattr(row, field, None)
    if value is None:
        return {'ok': False,
                'error': f"{class_name} '{row_name}' has no field "
                         f"'{field}'"}
    factor = trapezoid_factor(float(value), curve.min_value,
                              curve.optimal_low, curve.optimal_high,
                              curve.max_value)
    return {'ok': True, 'factor': factor, 'tier': 'trapezoid',
            'inputField': f'{class_name}.{field}', 'inputValue': value,
            'bounds': {'min': curve.min_value,
                      'optimalLow': curve.optimal_low,
                      'optimalHigh': curve.optimal_high,
                      'max': curve.max_value}}
def part_stress_factors(manager, plant_name, part, atmosphere_name,
                        water_name, soil_name, light_value_override=None):
    """Every curve for (plant_name, part), each evaluated — the
    per-stress-type breakdown a diagnostic view needs, before
    Liebig's-Law combination. light_value_override (phase 8) is
    forwarded to evaluate_curve — see its own docstring."""
    curves = [c for c in _rows(manager, 'StressResponseCurve')
             if getattr(c, 'plant_name', '') == plant_name
             and getattr(c, 'part', '') == part]
    by_type = {}
    for curve in curves:
        by_type[curve.stress_type] = evaluate_curve(
            manager, curve, atmosphere_name, water_name, soil_name,
            light_value_override=light_value_override)
    return by_type
def combined_stress_factor(by_type):
    """Liebig's Law of the Minimum across whatever stress types
    resolved OK for this part. No curves (or none resolvable) -> 1.0,
    an honest 'no data configured, no penalty applied' default, never
    a guessed penalty."""
    ok_factors = {stress_type: result['factor']
                 for stress_type, result in by_type.items()
                 if result.get('ok')}
    if not ok_factors:
        return 1.0, None, {}
    limiting_type = min(ok_factors, key=ok_factors.get)
    return ok_factors[limiting_type], limiting_type, ok_factors
def sweep_curve(curve, sample_count=20):
    """Diagnostic — Tier-A curves only (Tier-B equations can be swept
    the same way the no-code editor's own run-overlay already
    evaluates a single binding set; sweeping THOSE reuses that
    existing UI pattern rather than this function, see the API
    docstring). Samples the trapezoid across [min, max] so a caller can
    plot factor-vs-input without touching any live data row."""
    if curve.equation_ref:
        return {'ok': False,
                'error': 'sweep_curve only sweeps Tier-A trapezoid '
                         "curves (equation_ref is set) — use the "
                         'no-code matrix-equation run-overlay to '
                         'evaluate a Tier-B equation directly'}
    lo, hi = curve.min_value, curve.max_value
    if hi <= lo:
        return {'ok': False,
                'error': f'max_value ({hi}) must be > min_value ({lo})'}
    span = hi - lo
    pad = span * 0.15
    samples = []
    n = max(2, int(sample_count))
    for i in range(n):
        x = (lo - pad) + (span + 2 * pad) * i / (n - 1)
        samples.append({'input': round(x, 4),
                        'factor': round(trapezoid_factor(
                            x, curve.min_value, curve.optimal_low,
                            curve.optimal_high, curve.max_value), 5)})
    return {'ok': True, 'curve': curve.name, 'stressType': curve.stress_type,
            'part': curve.part, 'samples': samples,
            'bounds': {'min': lo, 'optimalLow': curve.optimal_low,
                      'optimalHigh': curve.optimal_high, 'max': hi}}
