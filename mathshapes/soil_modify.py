"""
@cross-cutting
@module mathshapes.soil_modify
@tags @xc:bindings

aquaponics-pot-shape phase 4 — the soil fill, derived from the SAME
pot geometry pot_shape_from_definition already computes (Dustin's
plan-doc note: "shrinks the pot's interior by wall_thickness_mm/
base_thickness_mm and fills to some level"). Reuses
shape_modify._pot_core_dimensions + build_quadric_eq_row so the soil's
floor and radius profile can NEVER drift from the wall/bottom's own —
they are read from the identical derived numbers, not recomputed.

Soil is a SOLID fill (not hollow like the wall) — one capped frustum,
sitting on the interior floor (the wall's own bottom, i.e. the top of
the bottom slab), radius bounded by the wall's INNER surface at every
height so it can never poke through the wall. Fill height above that
floor is `PotDefinition.soil_fill_height_mm` — an explicit, editable
knob (never a hidden fraction of the pot's height), clamped to the
usable interior height when it would otherwise reach the rim.

@consumers
  - mathshapes.shape_api (called from on_post_from_pot as a side effect
    of POST /api/shapes/from-pot/{pot_name} — there is no separate
    from-soil route; soil always re-derives alongside the wall/bottom)
@see /AQUAPONICS_POT_SHAPE_PLAN.md (phase 4)
"""

import json

from mathshapes.shape_modify import (
    _ShapeRow, _f, _insert_rows, _pot_core_dimensions, _pot_named,
    build_quadric_eq_row,
)
from mathshapes.shape_geometry import radius_at_z


def soil_shape_from_definition(manager, pot_name, persist=True):
    """Build the soil fill for an aqp-1 pot FROM its already-derived
    wall/bottom geometry (`_pot_core_dimensions` — the exact same
    numbers `pot_shape_from_definition` uses, so soil's floor/radius
    can't drift from the wall it sits inside). Call
    `pot_shape_from_definition` first (or at least once) so the pot's
    own gravity validity has been checked — this function doesn't
    re-check it (soil doesn't affect drainage)."""
    pot = _pot_named(manager, pot_name)
    if pot is None:
        return {'ok': False,
                'error': f"no PotDefinition named '{pot_name}'"}
    dims = _pot_core_dimensions(pot)

    fill_height_mm_raw = _f(pot, 'soil_fill_height_mm', 180.0)
    usable_height_mm = dims['wall_height'] * 10.0   # cm -> mm
    fill_clamped = fill_height_mm_raw > usable_height_mm
    fill_height = min(max(0.0, fill_height_mm_raw), usable_height_mm) / 10.0

    if fill_height <= 0.01:
        return {'ok': False, 'pot': pot_name,
                'error': 'soil_fill_height_mm resolves to ~0cm — raise it '
                         'or check base_thickness_mm/height_mm',
                'suggestion': {'knob': 'PotDefinition.soil_fill_height_mm',
                               'action': 'set a positive fill height'}}

    floor_z = dims['wall_bottom_z']
    top_z = floor_z + fill_height
    soil_center = [0.0, 0.0, (floor_z + top_z) / 2.0]

    # The wall's OWN inner-radius taper, evaluated at the soil's z-range
    # (a SUBSET of the wall's full height) — not re-derived, read off
    # the same linear interpolation the wall itself uses.
    def inner_radius_at(z):
        frac = ((z - dims['wall_bottom_z']) / dims['wall_height']
                if dims['wall_height'] > 1e-9 else 0.0)
        return (dims['wall_bottom_inner_r']
                + (dims['wall_top_inner_r'] - dims['wall_bottom_inner_r']) * frac)

    base_r_soil = inner_radius_at(floor_z)
    top_r_soil = inner_radius_at(top_z)

    soil_eq_name = f'{pot_name}-soil-eq'
    soil_notes = f'soil fill, {fill_height_mm_raw:.1f}mm requested'
    if fill_clamped:
        soil_notes += (f' (clamped to {usable_height_mm:.1f}mm — the '
                       'usable interior height)')
    soil_eq_row, soil_Q = build_quadric_eq_row(
        soil_eq_name, f'{pot_name} soil (equation)',
        base_r_soil, top_r_soil, fill_height, 'z', soil_center,
        soil_notes, dims['xy_cap'])

    # Renderable number DERIVED from the equation (radius_at_z), never
    # independently specified — same principle as the wall/bottom.
    soil_base_r = radius_at_z(soil_Q, 'z', floor_z)
    soil_top_r = radius_at_z(soil_Q, 'z', top_z)

    soil_name = f'{pot_name}-soil'
    soil_row = _ShapeRow(
        name=soil_name, display_name=f'{pot_name} soil fill',
        family='primitive', primitive_kind='frustum',
        quadric_matrix_json='', csg_json='', bounds_json='',
        provenance_id='shape-4',
        notes=f'derived from {soil_eq_name}; sits on the bottom slab, '
              f'bounded by the wall inner surface',
        parameters_json=json.dumps({
            'base_radius': round(soil_base_r, 4),
            'top_radius': round(soil_top_r, 4),
            'height': round(fill_height, 4), 'axis': 'z',
            'center': [0.0, 0.0, round(soil_center[2], 4)],
            # A solid fill needs both caps to read as solid, same as
            # the bottom slab.
            'cap_base': True, 'cap_top': True}))

    if persist:
        _insert_rows(manager, [soil_eq_row, soil_row])

    return {
        'ok': True, 'pot': pot_name,
        'soilEquation': soil_eq_name, 'soilShape': soil_name,
        'fillHeightMm': round(fill_height * 10.0, 2),
        'fillHeightClamped': fill_clamped,
        'note': 'soil fill DEFINED by a quadric equation (source of '
                'truth, same as the wall/bottom) whose radius profile '
                'is read directly off the wall\'s own inner-surface '
                'taper — cannot poke through the wall. Fill height is '
                'the explicit soil_fill_height_mm knob, clamped to the '
                'usable interior height when it would otherwise reach '
                'the rim (fillHeightClamped says when that happened).'}
