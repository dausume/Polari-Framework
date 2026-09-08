"""
@cross-cutting
@module aquaponics.custom.hydraulics
@tags @xc:bindings

aqp-3 — pot hydraulics analysis: turns a PotDefinition + its PotHoles
+ a SoilDefinition into a Darcy payload, runs it at the requested
FIDELITY, and maps the result into evidence-bearing findings.

Two fidelities (knobs-and-suggestions — the knob is `fidelity`, every
result names which fidelity produced it):

  'reservoir'  reduced 1-D Darcy-lite model, pure python, ALWAYS
               answers in-backend (the default fallback): the soil
               column is one porous conductor between the water table
               and the lowest output hole,
                   Q = K · A_hole · Δh / L_path
               — an honest order-of-magnitude estimate.
  'fem'        the scikit-fem field solve
               (materialsScience/engines/darcy_engine.py), local when
               skfem imports, else the msci-engines worker via the
               topology-routed remote seam. Falls BACK to 'reservoir'
               (and says so) when no solver is reachable.

Duck-typed manager (anything with .objectTables) so selftests run
stdlib-only; the engine call is injectable for the same reason
(selftest mocks it).

Units: rows carry mm and mm/hr; this module converts ONCE to SI
(m, m/s) at the payload boundary and labels every output.

@consumers
  - aquaponics.hydraulics_api
  - aqp-7 vermicompost (loop flow rate) / aqp-8 growth (moisture supply)
@see /AQUAPONICS_PHASE2_PLAN.md
"""

MM_PER_M = 1000.0
SECONDS_PER_HOUR = 3600.0

FIDELITIES = ('reservoir', 'fem')


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


def soil_conductivity_m_per_s(soil):
    """SoilDefinition.hydraulic_conductivity_mm_hr -> K in m/s."""
    return _f(soil, 'hydraulic_conductivity_mm_hr', 20.0) \
        / MM_PER_M / SECONDS_PER_HOUR


def build_darcy_payload(manager, pot_name, soil_name,
                        water_level_mm=None, refine=6):
    """The engine payload (SI) from tree rows. Returns
    {'ok': True, 'payload': ...} or an honest refusal naming what is
    missing."""
    pot = _named(manager, 'PotDefinition', pot_name)
    if pot is None:
        return {'ok': False,
                'error': f"no PotDefinition named '{pot_name}'"}
    soil = _named(manager, 'SoilDefinition', soil_name) \
        if soil_name else None
    if soil_name and soil is None:
        return {'ok': False,
                'error': f"no SoilDefinition named '{soil_name}'"}
    holes = [h for h in _rows(manager, 'PotHole')
             if getattr(h, 'pot_name', '') == pot_name]
    outputs = [h for h in holes if getattr(h, 'kind', '') == 'output']
    inputs = [h for h in holes if getattr(h, 'kind', '') == 'input']
    if not outputs or not inputs:
        return {'ok': False,
                'error': f"pot '{pot_name}' needs at least one input "
                         f'and one output hole '
                         f'({len(inputs)} inputs / {len(outputs)} '
                         f'outputs found)',
                'suggestion': {
                    'knob': 'PotHole rows (kind, height_mm)',
                    'action': 'POST /api/aquaponics/pots/'
                              f'{pot_name}/generate-holes for a valid '
                              'preview, then create the rows via CRUDE',
                    'evidence': 'hydraulics needs a supply and a drain '
                                'to define the head difference'}}

    wall = _f(pot, 'wall_thickness_mm', 8.0)
    inner_width_m = (_f(pot, 'outer_base_diameter_mm', 200.0)
                     - 2.0 * wall) / MM_PER_M
    inner_height_m = (_f(pot, 'height_mm', 250.0)
                      - _f(pot, 'base_thickness_mm', 12.0)) / MM_PER_M
    if water_level_mm is None:
        # the maintained level of a flow-through pot: the lowest
        # output lip keeps the reservoir there; default to the highest
        # input center so the solve shows the full working head.
        water_level_mm = max(_f(h, 'height_mm', 0.0) for h in inputs)
    water_level_m = float(water_level_mm) / MM_PER_M

    conductivity = soil_conductivity_m_per_s(soil) if soil is not None \
        else 20.0 / MM_PER_M / SECONDS_PER_HOUR
    k_labeled = 'SoilDefinition.hydraulic_conductivity_mm_hr' \
        if soil is not None else 'DEFAULT 20 mm/hr (no soil named)'

    def _hole(hole, side):
        return {'kind': getattr(hole, 'kind', 'output'),
                'z_m': _f(hole, 'height_mm', 0.0) / MM_PER_M,
                'radius_m': 0.5 * _f(hole, 'diameter_mm', 10.0)
                / MM_PER_M,
                'side': side}

    # 2-D cross-section: inputs on the left wall, outputs on the right
    # (the seeds place them on opposite sides; azimuth collapses in 2-D).
    payload_holes = [_hole(h, 'left') for h in inputs] \
        + [_hole(h, 'right') for h in outputs]
    return {
        'ok': True,
        'payload': {
            'geometry': {'width_m': round(inner_width_m, 6),
                         'height_m': round(inner_height_m, 6)},
            'k_m_per_s': conductivity,
            'water_level_m': round(water_level_m, 6),
            'holes': payload_holes,
            'refine': int(refine),
        },
        'unitsNote': 'converted once from row mm / mm/hr to SI',
        'conductivitySource': k_labeled,
    }


def reservoir_model(payload):
    """The reduced 1-D fallback — pure python, always answers.

    One porous conductor from the water table to the LOWEST output:
    Q = K · A_hole · Δh / L_path, with L_path the straight-line
    distance across the soil from the input side to the output hole.
    Returns the same shape as darcy_engine.drains_by_gravity."""
    error_keys = [k for k in ('geometry', 'k_m_per_s', 'holes')
                  if not payload.get(k)]
    if error_keys:
        return {'ok': False,
                'error': f'payload missing {error_keys}'}
    outputs = [h for h in payload['holes'] if h.get('kind') == 'output']
    if not outputs:
        return {'ok': False, 'error': 'no output hole in payload'}
    lowest = min(outputs, key=lambda h: float(h['z_m']))
    z_out = float(lowest['z_m'])
    radius = float(lowest.get('radius_m', 0.005) or 0.005)
    water_level = float(payload.get('water_level_m', 0) or 0)
    head = water_level - z_out
    if head <= 0:
        return {'ok': True, 'drains': False, 'fidelity': 'reservoir',
                'outflowRateMlS': 0.0,
                'limitingFactor': 'water table at/below the lowest '
                                  'output hole',
                'evidence': f'water level {water_level:.4g} m <= output '
                            f'lip {z_out:.4g} m'}
    width = float(payload['geometry']['width_m'])
    path = (width ** 2 + head ** 2) ** 0.5
    area = 3.141592653589793 * radius ** 2
    conductivity = float(payload['k_m_per_s'])
    outflow_m3s = conductivity * area * head / path
    return {
        'ok': True, 'drains': outflow_m3s > 1e-15,
        'fidelity': 'reservoir',
        'outflowRateMlS': outflow_m3s * 1e6,
        'limitingFactor': None,
        'evidence': f'reduced reservoir model: Q = K·A·Δh/L with '
                    f'K={conductivity:.3g} m/s, A={area:.3g} m² '
                    f'(lowest output bore), Δh={head:.4g} m, '
                    f'L={path:.4g} m — an order-of-magnitude estimate; '
                    f"set fidelity='fem' for the field solve",
    }


def _default_engine(payload, want_field):
    from materialsScience.engines import darcy_engine
    if want_field:
        return darcy_engine.solve_head_field(payload)
    return darcy_engine.drains_by_gravity(payload)


def run_hydraulics(manager, pot_name, soil_name, water_level_mm=None,
                   fidelity='fem', want_field=False, refine=6,
                   engine=None):
    """The module entry point: build payload, run at fidelity, map to
    findings. `engine(payload, want_field)` is injectable for tests.

    fidelity='fem' falls back to the reservoir model (and SAYS so in
    `fidelityNote`) when no solver answers; fidelity='reservoir' never
    leaves the backend."""
    if fidelity not in FIDELITIES:
        return {'ok': False,
                'error': f"fidelity must be one of {FIDELITIES}, got "
                         f"'{fidelity}'"}
    built = build_darcy_payload(manager, pot_name, soil_name,
                                water_level_mm=water_level_mm,
                                refine=refine)
    if not built.get('ok'):
        return built
    payload = built['payload']

    fidelity_note = None
    if fidelity == 'reservoir':
        result = reservoir_model(payload)
    else:
        result = (engine or _default_engine)(payload, want_field)
        if not result.get('ok'):
            fallback = reservoir_model(payload)
            fidelity_note = {
                'requested': 'fem', 'used': 'reservoir',
                'why': result.get('error', 'engine unavailable'),
                'suggestion': result.get('suggestion'),
            }
            result = fallback
    if not result.get('ok'):
        return result

    result = dict(result)
    result['pot'] = pot_name
    result['soil'] = soil_name or ''
    result['conductivitySource'] = built['conductivitySource']
    result['waterLevelMm'] = float(payload['water_level_m']) * MM_PER_M
    if fidelity_note:
        result['fidelityNote'] = fidelity_note
    if 'drains' in result:
        result['findings'] = _findings(result, payload)
    return result


def water_slice_mesh(manager, pot_name, soil_name, water_level_mm=None,
                     refine=6, engine=None):
    """A 3-D-positioned triangulated slice of the steady Darcy head
    field (aquaponics-pot-shape phase 3) — the SAME (cm, z-vertical-
    through-the-pot's-own-center) coordinate frame
    mathshapes.custom.shape_modify.pot_shape_from_definition's own wall/soil/
    hole meshes already render in, so this drops into the existing
    renderer with no extra transform.

    VISUAL APPROXIMATION, stated plainly (matching the Darcy engine's
    own documented fidelity ceiling): the field solve is a flat 2-D
    vertical cross-section, not a full 3-D volume — this renders that
    cross-section as ONE flat plane through the pot's input->output
    azimuth line (a real chord through the pot, not an arbitrary
    slice), rather than claiming a revolved/3-D result the underlying
    physics doesn't support. 'Time-stepping' an animation is the
    CALLER's job: call this repeatedly at a rising water_level_mm
    across ticks (repeated independent steady-state solves, NOT a true
    transient formulation — the simpler of the two options the plan
    doc left open, picked because it reuses the existing solver
    unchanged; see AQUAPONICS_POT_SHAPE_PLAN.md phase 3)."""
    result = run_hydraulics(manager, pot_name, soil_name,
                            water_level_mm=water_level_mm, fidelity='fem',
                            want_field=True, refine=refine, engine=engine)
    if not result.get('ok'):
        return result
    if 'headField' not in result or 'headFieldTriangles' not in result:
        return {'ok': False,
                'error': 'no field solver reachable for this pot — '
                         'water-slice needs the fem field solve',
                'fidelityNote': result.get('fidelityNote')}

    pot = _named(manager, 'PotDefinition', pot_name)
    from mathshapes.custom.shape_modify import _pot_core_dimensions
    floor_z_cm = -_pot_core_dimensions(pot)['H'] / 2.0

    import math
    from aquaponics.custom.pot_geometry import _circular_mean_deg
    outputs = [h for h in _rows(manager, 'PotHole')
              if getattr(h, 'pot_name', '') == pot_name
              and getattr(h, 'kind', '') == 'output']
    output_az_deg = _circular_mean_deg(
        [_f(h, 'azimuth_deg') for h in outputs]) or 0.0
    az_rad = math.radians(output_az_deg)
    dir_x, dir_y = math.cos(az_rad), math.sin(az_rad)

    width_m = float(result.get('meshMeta', {}).get('widthM', 0.0))
    points_cm, head_values_m = [], []
    for x_m, z_m, head_m in result['headField']:
        t_cm = (x_m - width_m / 2.0) * 100.0
        points_cm.append([round(t_cm * dir_x, 4), round(t_cm * dir_y, 4),
                          round(floor_z_cm + z_m * 100.0, 4)])
        head_values_m.append(head_m)

    return {
        'ok': True,
        'pot': pot_name,
        'soil': soil_name or '',
        'points': points_cm,
        'triangles': result['headFieldTriangles'],
        'headValuesM': head_values_m,
        'waterLevelMm': result.get('waterLevelMm'),
        'outflowRateMlS': result.get('outflowRateMlS'),
        'fluxStats': result.get('fluxStats'),
        'meshMeta': result.get('meshMeta'),
        'note': 'VISUAL APPROXIMATION: a flat 2-D Darcy cross-section '
                "rendered as one plane through the pot's input->output "
                'azimuth line, not a full 3-D volume. Sequential calls '
                'at a rising water_level_mm approximate a fill '
                'transient as repeated independent steady-state solves '
                '— not a true transient formulation (see '
                'AQUAPONICS_POT_SHAPE_PLAN.md phase 3).',
    }


def _findings(result, payload):
    """Evidence-bearing findings, knobs named (knobs-and-suggestions)."""
    findings = []
    outputs = [h for h in payload['holes'] if h.get('kind') == 'output']
    lowest_mm = min(float(h['z_m']) for h in outputs) * MM_PER_M
    rate = float(result.get('outflowRateMlS', 0.0))
    if result.get('drains'):
        findings.append({
            'kind': 'drains-by-gravity',
            'evidence': f'output hole at height {lowest_mm:.0f} mm '
                        f'drains at {rate:.4g} mL/s '
                        f"({result.get('fidelity')} fidelity)",
            'knob': None, 'action': None})
    else:
        water_mm = float(payload.get('water_level_m', 0)) * MM_PER_M
        findings.append({
            'kind': 'does-not-drain',
            'evidence': f'water table {water_mm:.0f} mm vs lowest '
                        f'output {lowest_mm:.0f} mm — '
                        + (result.get('limitingFactor') or 'no flow'),
            'knob': 'PotHole.height_mm (output) / water_level_mm',
            'action': 'lower the output hole below the intended water '
                      'table, or raise the supply level'})
    return findings
