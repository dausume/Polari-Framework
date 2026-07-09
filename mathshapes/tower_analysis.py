"""
@cross-cutting
@module mathshapes.tower_analysis
@tags @xc:bindings, @xc:render-3d

Geometry of an aquaponic tower (shape-2). Duck-typed manager, stdlib.
Every number carries how it was derived (labels travel).

  tower_geometry   per-tier grow volume (from the pot shape's
                   shape_properties × grow_fraction), the total grow
                   volume, the tower footprint + overall height, and the
                   top→bottom water path (each tier's centre height, the
                   order water flows). shape-4 uses the per-tier grow
                   volume as each tier's carrying capacity.

@consumers
  - mathshapes.tower_api / mathshapes.growth_prediction (shape-4)
@see /MATH_SHAPES_PLAN.md (PHASE shape-2)
"""

from mathshapes.shape_analysis import _named, shape_properties

_TIER_RES = 26           # grid resolution for a per-tier CSG pot


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _tower(manager, name):
    for t in _rows(manager, 'AquaponicTowerDefinition'):
        if getattr(t, 'name', '') == name:
            return t
    return None


def _f(row, attr, default=0.0):
    try:
        v = getattr(row, attr, default)
        return float(default if v is None else v)
    except (TypeError, ValueError):
        return float(default)


def _footprint_cm2(bbox):
    """x-y footprint of a pot's axis-aligned bounding box (cm²)."""
    (x0, x1), (y0, y1), _ = bbox
    return (x1 - x0) * (y1 - y0)


def tower_geometry(manager, tower_name):
    tower = _tower(manager, tower_name)
    if tower is None:
        return {'ok': False,
                'error': f"no AquaponicTowerDefinition named "
                         f"'{tower_name}'"}
    pot_shape = getattr(tower, 'pot_shape_name', '')
    if _named(manager, pot_shape) is None:
        return {'ok': False,
                'error': f"tower references pot shape '{pot_shape}' which "
                         f"has no MathShapeDefinition",
                'suggestion': {'knob': 'AquaponicTowerDefinition.'
                               'pot_shape_name',
                               'action': 'point it at a math-defined pot '
                                         '(e.g. pot_shape_from_definition)'}}

    n_tiers = max(1, int(_f(tower, 'n_tiers', 1)))
    spacing = _f(tower, 'tier_spacing_cm', 25.0)
    grow_fraction = _f(tower, 'grow_fraction', 0.6)

    props = shape_properties(manager, pot_shape, resolution=_TIER_RES)
    if not props.get('ok'):
        return {'ok': False, 'error': 'could not measure the pot shape',
                'detail': props}
    pot_solid = props.get('volumeCm3', 0.0)
    bbox = props.get('boundingBox') or [[0, 0], [0, 0], [0, 0]]
    # grow volume ≈ the pot's bounding volume that is NOT solid wall,
    # scaled by the grow_fraction (soil/root void estimate).
    (x0, x1), (y0, y1), (z0, z1) = bbox
    bbox_vol = (x1 - x0) * (y1 - y0) * (z1 - z0)
    void_vol = max(0.0, bbox_vol - pot_solid)
    grow_per_tier = void_vol * grow_fraction

    footprint = _footprint_cm2(bbox)
    tiers = []
    for i in range(n_tiers):
        # tier 0 at the TOP; water falls to tier n-1 at the base
        centre_h = (n_tiers - 1 - i) * spacing
        tiers.append({
            'tier': i,
            'centreHeightCm': round(centre_h, 2),
            'potSolidVolumeCm3': round(pot_solid, 2),
            'growVolumeCm3': round(grow_per_tier, 2),
            'growVolumeL': round(grow_per_tier / 1000.0, 3)})

    total_grow = grow_per_tier * n_tiers
    tower_height = (n_tiers - 1) * spacing + (z1 - z0)
    water_path = [f'tier {i}' for i in range(n_tiers)]

    return {
        'ok': True, 'tower': tower_name,
        'potShape': pot_shape, 'nTiers': n_tiers,
        'tierSpacingCm': round(spacing, 2),
        'footprintCm2': round(footprint, 2),
        'towerHeightCm': round(tower_height, 2),
        'perTier': tiers,
        'growVolumePerTierCm3': round(grow_per_tier, 2),
        'totalGrowVolumeCm3': round(total_grow, 2),
        'totalGrowVolumeL': round(total_grow / 1000.0, 3),
        'sharedReservoir': bool(getattr(tower, 'shared_reservoir', True)),
        'reservoirVolumeL': _f(tower, 'reservoir_volume_l', 0.0),
        'waterPathTopToBottom': water_path,
        'note': 'per-tier grow volume ≈ (pot bounding volume − solid) × '
                'grow_fraction; a packing estimate. Water flows top → '
                'bottom through the shared reservoir (labels travel).'}
