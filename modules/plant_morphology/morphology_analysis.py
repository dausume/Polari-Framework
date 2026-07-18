"""
@cross-cutting
@module plant_morphology.morphology_analysis
@tags @xc:bindings, @xc:render-3d

Mock/estimate 3D geometry from the organ + root stand-in models. Duck-
typed manager (stdlib-only selftests). All outputs are ESTIMATES that
carry how they were derived (labels travel with numbers).

- organ_geometry: per-organ bounding box + volume from the shape
  primitive, plus the whole-plant canopy envelope.
- root_spread: the unconfined root envelope (spread radius, depth,
  root-ball volume) from RootSystemModel.
- confinement_assessment: THE headline — given a pot (aqp-1
  PotDefinition inner volume) or an explicit container, does the root
  ball fit? what dwarf factor results? CAN IT BE KEPT INDEFINITELY, and
  with what root-prune cadence? The limiting factor is named
  (honest-absence).

@consumers
  - plant_morphology.morphology_api
@see /AQUAPONICS_MODULE_PLAN.md (aqp-1 pot geometry)
"""

import math

MM3_PER_L = 1_000_000.0   # 1 L = 1e6 mm^3


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


def _organs_of(manager, plant_name):
    return [o for o in _rows(manager, 'OrganModel')
            if getattr(o, 'plant_name', '') == plant_name]


def primitive_volume_mm3(shape, length, width, thickness):
    """Volume of ONE organ from its shape primitive (mm^3)."""
    a, b, c = length / 2.0, width / 2.0, thickness / 2.0
    if shape == 'ellipsoid':
        return (4.0 / 3.0) * math.pi * a * b * c
    if shape == 'cylinder':
        return math.pi * b * b * length     # axis = length, radius=w/2
    if shape == 'cone':
        return (1.0 / 3.0) * math.pi * b * b * length
    if shape == 'sphere':
        r = width / 2.0
        return (4.0 / 3.0) * math.pi * r ** 3
    if shape == 'lamina':                    # flat blade ≈ a thin box
        return length * width * thickness
    return length * width * thickness         # fallback: bounding box


def organ_geometry(manager, plant_name):
    """Per-organ 3D bounds + volume, and the canopy envelope."""
    organs = _organs_of(manager, plant_name)
    if not organs:
        return {'ok': False,
                'error': f"no OrganModel rows for plant '{plant_name}'",
                'suggestion': {'knob': 'OrganModel rows (plant_name)',
                               'action': 'seed organ stand-ins for the '
                                         'plant',
                               'evidence': 'geometry needs organ models'}}
    per_organ = []
    total_volume = 0.0
    max_span = 0.0
    max_height = 0.0
    for o in organs:
        shape = getattr(o, 'shape_primitive', 'ellipsoid')
        length = _f(o, 'length_mm', 40.0)
        width = _f(o, 'width_mm', 20.0)
        thickness = _f(o, 'thickness_mm', 3.0)
        count = int(_f(o, 'count', 1))
        one = primitive_volume_mm3(shape, length, width, thickness)
        organ_total = one * count
        total_volume += organ_total
        # crude envelope contribution: leaves/branches spread, stems rise
        span = max(length, width)
        max_span = max(max_span, span)
        if getattr(o, 'organ', '') in ('stem', 'branch'):
            max_height = max(max_height, length)
        per_organ.append({
            'organ': getattr(o, 'organ', ''),
            'shape': shape, 'count': count,
            'boundingBoxMm': [round(length, 1), round(width, 1),
                              round(thickness, 1)],
            'oneVolumeMm3': round(one, 1),
            'totalVolumeMm3': round(organ_total, 1),
            'isPrior': bool(getattr(o, 'is_prior', True))})
    # Canopy envelope ≈ an ellipsoid of the widest span × height.
    height = max_height or max_span
    envelope = (4.0 / 3.0) * math.pi * (max_span / 2.0) ** 2 \
        * (height / 2.0)
    return {'ok': True, 'plant': plant_name,
            'perOrgan': per_organ,
            'totalOrganVolumeCm3': round(total_volume / 1000.0, 2),
            'canopyEnvelope': {
                'spanMm': round(max_span, 1),
                'heightMm': round(height, 1),
                'volumeCm3': round(envelope / 1000.0, 2)},
            'note': 'mock stand-in geometry from shape primitives — '
                    'estimates, not measured meshes.'}


def _root_ball_volume_mm3(root):
    """Dense root-ball volume ≈ a hemisphere of the spread radius scaled
    by root_ball_fraction, clamped by depth (a half-ellipsoid)."""
    radius = _f(root, 'natural_spread_radius_mm', 120.0)
    depth = _f(root, 'natural_depth_mm', 200.0)
    frac = _f(root, 'root_ball_fraction', 0.5)
    # half-ellipsoid: (2/3)π r^2 depth, times the dense fraction.
    full = (2.0 / 3.0) * math.pi * radius * radius * depth
    return full * frac, full


def root_spread(manager, plant_name):
    """The unconfined mature root envelope."""
    root = _named(manager, 'RootSystemModel', None) if False else None
    for r in _rows(manager, 'RootSystemModel'):
        if getattr(r, 'plant_name', '') == plant_name:
            root = r
            break
    if root is None:
        return {'ok': False,
                'error': f"no RootSystemModel for plant '{plant_name}'"}
    ball, full = _root_ball_volume_mm3(root)
    return {'ok': True, 'plant': plant_name,
            'pattern': getattr(root, 'pattern', ''),
            'spreadRadiusMm': _f(root, 'natural_spread_radius_mm', 0),
            'depthMm': _f(root, 'natural_depth_mm', 0),
            'fullEnvelopeVolumeCm3': round(full / 1000.0, 2),
            'denseRootBallVolumeCm3': round(ball / 1000.0, 2),
            'confinementTolerance': _f(root, 'confinement_tolerance', 0),
            'dwarfable': bool(getattr(root, 'dwarfable', True)),
            'note': 'root envelope estimated as a half-ellipsoid of the '
                    'natural spread × depth; dense ball = × root_ball_'
                    'fraction.'}


def _pot_inner_volume_l(pot):
    """aqp-1 PotDefinition inner soil volume (L) — same convention as
    aquaponics/hydraulics.build_darcy_payload."""
    wall = _f(pot, 'wall_thickness_mm', 8.0)
    base = _f(pot, 'base_thickness_mm', 12.0)
    inner_r = (_f(pot, 'outer_base_diameter_mm', 200.0)
               - 2.0 * wall) / 2.0
    inner_h = _f(pot, 'height_mm', 250.0) - base
    reservoir = _f(pot, 'reservoir_height_mm', 0.0)
    soil_h = max(0.0, inner_h - reservoir)
    return math.pi * inner_r * inner_r * soil_h / MM3_PER_L


def confinement_assessment(manager, plant_name, pot_name=None,
                           container_volume_l=None):
    """Can this plant be dwarfed + kept in the container indefinitely?

    Returns the confinement ratio (container vs dense root ball), the
    resulting dwarf factor (realized size fraction), whether it can live
    there indefinitely + the required root-prune cadence, and the
    limiting factor named."""
    spread = root_spread(manager, plant_name)
    if not spread.get('ok'):
        return spread
    for r in _rows(manager, 'RootSystemModel'):
        if getattr(r, 'plant_name', '') == plant_name:
            root = r
            break
    else:
        return {'ok': False, 'error': 'root model vanished'}

    if container_volume_l is None:
        if pot_name is None:
            return {'ok': False,
                    'error': 'provide pot_name or container_volume_l'}
        pot = _named(manager, 'PotDefinition', pot_name)
        if pot is None:
            return {'ok': False,
                    'error': f"no PotDefinition named '{pot_name}'"}
        container_volume_l = _pot_inner_volume_l(pot)
        container_source = f'aqp-1 pot inner volume ({pot_name})'
    else:
        container_volume_l = float(container_volume_l)
        container_source = 'explicit container_volume_l'

    ball_l = spread['denseRootBallVolumeCm3'] / 1000.0
    ratio = container_volume_l / ball_l if ball_l > 0 else 999.0
    tolerance = _f(root, 'confinement_tolerance', 0.6)
    dwarfable = bool(getattr(root, 'dwarfable', True))
    cadence = _f(root, 'root_prune_cadence_days', 0.0)

    # Dwarf factor: when confined (ratio < 1) a dwarfable plant shrinks
    # its realized size ~ ratio^(1/3) (volume→linear), floored by the
    # confinement tolerance (a tolerant plant holds more size). A
    # non-dwarfable plant does NOT shrink gracefully → it declines.
    if ratio >= 1.0:
        dwarf_factor = 1.0
        confined = False
    else:
        geometric = ratio ** (1.0 / 3.0)
        dwarf_factor = geometric + (1.0 - geometric) * tolerance \
            if dwarfable else geometric
        confined = True

    # Indefinite? dwarfable + (tolerant enough OR a prune cadence set).
    if not dwarfable:
        indefinite = ratio >= 1.0
        limiting = None if indefinite else (
            'not dwarfable — a root ball larger than the container will '
            'become root-bound and decline (knob: RootSystemModel.'
            'dwarfable / choose a larger container or a dwarf variety)')
    elif ratio >= 1.0:
        indefinite = True
        limiting = None
    elif tolerance >= 0.5 or cadence > 0:
        indefinite = True
        limiting = None if cadence <= 0 else (
            f'root-bound but maintainable — root-prune every '
            f'{cadence:.0f} days to hold it indefinitely (knob: '
            f'RootSystemModel.root_prune_cadence_days)')
    else:
        indefinite = False
        limiting = ('low confinement tolerance + no prune cadence — set '
                    'root_prune_cadence_days or enlarge the container')

    return {
        'ok': True, 'plant': plant_name,
        'containerVolumeL': round(container_volume_l, 3),
        'containerSource': container_source,
        'denseRootBallVolumeL': round(ball_l, 3),
        'confinementRatio': round(ratio, 3),
        'confined': confined,
        'dwarfFactor': round(dwarf_factor, 3),
        'realizedSizeNote': f'realized size ~{dwarf_factor * 100:.0f}% '
                            f'of unconfined (dwarf factor)',
        'dwarfable': dwarfable,
        'confinementTolerance': tolerance,
        'canKeepIndefinitely': indefinite,
        'rootPruneCadenceDays': cadence,
        'limitingFactor': limiting,
        'evidence': f'container {container_volume_l:.2f} L vs dense root '
                    f'ball {ball_l:.2f} L (ratio {ratio:.2f}); '
                    f'{"dwarfable" if dwarfable else "not dwarfable"}, '
                    f'tolerance {tolerance:.2f}',
        'note': 'estimate from the root stand-in model; dwarf factor '
                'from confinement ratio + tolerance.'}
