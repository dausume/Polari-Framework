"""
@module mathshapes.spool_geometry

ws-4 (Dustin 2026-07-31): "define a spool geometry math object for
the stator that corresponds DIRECTLY with values defined for the
wire wound around it. Then the bobbin as a math object should just
follow what the spool geometry is in terms of size, and the gear as
well. We are generally going to be modulating the size of the
engine to the amount of force we want to generate."

THE COUPLING IS BY REFERENCE, so a modulation CASCADES:

  winding (r0, L, d, N)  →  spool barrel = the winding's bore,
                            window = the winding's window,
                            flanges = winding OUTER radius + a
                            declared clearance
                         →  derived-cylinder followers (the gear/
                            pinion) size themselves from a NAMED
                            derived value of the object they follow
                            by a declared ratio.

Tune the winding (turns, fineness) and the spool flanges grow with
the wound outer radius; the followers scale with the spool. Nothing
is copied — every size is resolved LIVE from the referenced row, so
the engine-scale modulation Dustin describes is one edit that flows
through the whole family. Incoherence REFUSES: a winding that
overflows its flanges, a wall thicker than the barrel, a follower
referencing a value that does not exist.

@consumers mathshapes.shape_analysis (families 'spool',
'derived-cylinder'), motors.motor_shapes seeds,
mathshapes.selftest_winding
"""

import math

from mathshapes.winding_geometry import winding_coherence

AXIS_OF = {(1.0, 0.0, 0.0): 'x', (0.0, 1.0, 0.0): 'y',
           (0.0, 0.0, 1.0): 'z'}


def _axis_letter(axis_vec):
    key = tuple(abs(round(float(c), 9)) for c in axis_vec)
    return AXIS_OF.get(key)


def spool_from_winding(winding_params, spool_params):
    """The spool math object DERIVED from its winding: nothing about
    the barrel or flanges is stated twice. Returns
    {'ok', 'object': {...}, 'derived': {...}} or a refusal."""
    coherent = winding_coherence(winding_params)
    if not coherent['ok']:
        return {'ok': False,
                'refusals': ['winding it wraps is incoherent: '
                             + '; '.join(coherent['refusals'])]}
    w = coherent['object']
    wd = coherent['derived']
    refusals = []
    wall = float(spool_params.get('barrel_wall', 0) or 0)
    flange_t = float(spool_params.get('flange_thickness', 0) or 0)
    clearance = float(spool_params.get('flange_clearance', 0) or 0)
    if wall <= 0 or wall >= w['r0']:
        refusals.append(f'barrel_wall must be in (0, bore radius '
                        f'{w["r0"]}) — got {wall}')
    if flange_t <= 0:
        refusals.append(f'flange_thickness must be > 0 '
                        f'(got {flange_t})')
    if clearance < 0:
        refusals.append(f'flange_clearance must be >= 0 '
                        f'(got {clearance})')
    axis_letter = _axis_letter(w['M'][2])
    if axis_letter is None:
        refusals.append('spool meshes are axis-aligned in v1 — the '
                        'winding axis must be a coordinate axis '
                        '(the winding itself stays general)')
    if refusals:
        return {'ok': False, 'refusals': refusals}
    # Two coupling modes, both real:
    #  - FOLLOW (default): flange = wound outer + clearance — the
    #    design-modulation mode, overflow impossible by
    #    construction (the flange grows with the winding).
    #  - FIXED: an explicit flange_radius (a physical spool you
    #    already have) — here the winding CAN overflow, and does so
    #    as a refusal naming the capacity.
    explicit_flange = params_flange = spool_params.get(
        'flange_radius')
    if explicit_flange is not None:
        flange_r = float(params_flange)
        if flange_r <= w['r0']:
            return {'ok': False, 'refusals': [
                f'flange_radius {flange_r} does not clear the '
                f'barrel (bore radius {w["r0"]})']}
    else:
        flange_r = wd['outerRadius'] + clearance
    shaft_r = w['r0'] - wall
    obj = {
        'C': w['C'], 'axisLetter': axis_letter,
        'barrelOuterR': w['r0'], 'shaftBoreR': shaft_r,
        'windowLength': w['L'], 'flangeThickness': flange_t,
        'flangeR': flange_r,
        'flangeCenters': [
            [w['C'][i] - (w['L'] / 2 + flange_t / 2) * w['M'][2][i]
             for i in range(3)],
            [w['C'][i] + (w['L'] / 2 + flange_t / 2) * w['M'][2][i]
             for i in range(3)]],
    }
    # capacity: how many turns fit before the wound coil overflows
    # the flange — the mag-9 fill check appearing as GEOMETRY.
    cap_layers = int((flange_r - w['r0']) // w['d'])
    capacity = cap_layers * w['tpl']
    if capacity < w['N']:
        return {'ok': False, 'refusals': [
            f'the winding OVERFLOWS this spool: {w["N"]} turns '
            f'need more radial room than the flange allows '
            f'(capacity {capacity} at flange radius '
            f'{round(flange_r, 4)}) — raise flange_clearance, '
            f'coarsen the window, or refine the wire']}
    return {
        'ok': True, 'object': obj,
        'windingDerived': wd,
        'derived': {
            'flangeRadius': round(flange_r, 6),
            'shaftBoreRadius': round(shaft_r, 6),
            'overallLength': round(w['L'] + 2 * flange_t, 6),
            'turnCapacity': capacity,
            'utilization': round(w['N'] / capacity, 4)
            if capacity else None,
        },
        'note': 'every spool size derives from the winding it '
                'wraps; turnCapacity is the geometric fill limit '
                '(wound outer radius reaching the flange)',
    }


def spool_mesh(spool, n_lon=32):
    """Barrel tube + two flange discs, one vertex set."""
    from mathshapes.shape_geometry import tube_mesh
    o = spool['object']
    pts, tris = [], []

    def add(p2, t2):
        base = len(pts)
        pts.extend(p2)
        tris.extend([[a + base, b + base, c + base]
                     for a, b, c in t2])

    add(*tube_mesh(o['C'], o['axisLetter'], o['barrelOuterR'],
                   o['shaftBoreR'],
                   o['windowLength'] + 2 * o['flangeThickness'],
                   n_lon=n_lon))
    for fc in o['flangeCenters']:
        add(*tube_mesh(fc, o['axisLetter'], o['flangeR'],
                       o['shaftBoreR'], o['flangeThickness'],
                       n_lon=n_lon))
    return pts, tris


def derived_cylinder(manager, params, resolve_properties):
    """A follower (gear, pinion, wheel...) whose radius derives
    from a NAMED derived value of the shape it follows, by a
    declared ratio — the third link of the cascade. Height may be
    absolute or its own ratio of the same value."""
    ref = params.get('ref', '')
    key = params.get('radius_from', 'flangeRadius')
    ratio = float(params.get('radius_ratio', 0) or 0)
    if not ref or ratio <= 0:
        return {'ok': False,
                'refusals': ['derived-cylinder needs {ref, '
                             'radius_ratio > 0}']}
    props = resolve_properties(manager, ref)
    if not props.get('ok'):
        return {'ok': False,
                'refusals': [f'follows "{ref}" which refuses: '
                             f'{props.get("error")}']}
    source = props.get('derived') or {}
    value = source.get(key)
    if not isinstance(value, (int, float)):
        return {'ok': False,
                'refusals': [f'"{ref}" derives no "{key}" — '
                             f'available: {sorted(source)}']}
    radius = value * ratio
    h_ratio = params.get('height_ratio')
    height = (value * float(h_ratio) if h_ratio
              else float(params.get('height', 1.0)))
    return {'ok': True,
            'object': {'center': params.get('center', [0, 0, 0]),
                       'axis': params.get('axis', 'z'),
                       'radius': round(radius, 6),
                       'height': round(height, 6)},
            'derived': {'radius': round(radius, 6),
                        'height': round(height, 6),
                        'followed': ref, 'radiusFrom': key,
                        'sourceValue': value, 'ratio': ratio},
            'note': f'radius = {key}({ref}) x {ratio} — modulate '
                    f'the source and this follower rescales'}
