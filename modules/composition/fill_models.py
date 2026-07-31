"""
@module composition.fill_models

arch-3: FILL FACTOR IS A PROPERTY OF THE CONSTRUCTION, not of the
wire (mag-26, requirement 2) — scramble, ordered-on-rigid-floor and
ordered-nested are three different numbers from the same components.
So the packing geometry lives in composition, keyed by the
construction's fill class; motors re-imports it (extracted from
motors.stator_construction, arch-3, same move as part_roles).

The physics is pure geometry and it is where two of the arc's
sharpest findings live:
- grooving beats scramble only while the wall stays under ~14% of
  the WOUND wire diameter (the mag-24 square-law again);
- a layer that SNAPS ON is a rigid floor, and rigid floors forbid
  nesting: ceiling 0.785 vs 0.907 before any wall is charged.

@consumers motors.stator_construction (shim),
composition.functional_basis, composition.selftest_composition
"""

import math

SCRAMBLE_FILL = 0.60
CLOSE_PACKED_CEILING = math.pi / (2.0 * math.sqrt(3.0))

#: The construction-side fill classes a ConstructionVariantDefinition
#: declares. 'n/a' = the variant does not wind anything.
FILL_CLASSES = ('scramble', 'ordered-rigid-floor', 'ordered-nested',
                'n/a')


def groove_viability(wound_diameter_mm, wall_mm, floor_mm=None,
                     nested=False):
    """Does grooving actually beat scramble winding at this size?

        fill = (pi/4)*d^2 / ((d + wall) * (radial_pitch + floor))

    Grooves buy ordered packing and spend window on walls, and the
    balance is pure geometry.

    NESTING IS THE HALF THAT MATTERS AND THE SNAP-ON CONSTRUCTION
    FORFEITS IT. Where each layer settles into the valleys of the
    one below, the radial pitch is d*sqrt(3)/2 = 0.866d and packing
    approaches the hexagonal ceiling of 0.907. Where layers sit
    squarely on a rigid floor — which is exactly what a separate
    grooved layer that SNAPS ON imposes — the radial pitch is a full
    d and the ceiling drops to pi/4 = 0.785 before any wall is
    charged. Most of the ordered-winding advantage lives in the
    nesting, not in the ordering.
    """
    d = float(wound_diameter_mm)
    w = float(wall_mm)
    f = float(floor_mm if floor_mm is not None else wall_mm)
    if d <= 0:
        return {'ok': False,
                'refusal': 'a wire of zero diameter has no packing'}
    radial_pitch = (math.sqrt(3.0) / 2.0) * d if nested else d
    fill = (math.pi / 4.0) * d * d / ((d + w) * (radial_pitch + f))
    # Break-even against scramble, solved for equal wall and floor.
    if nested:
        # (pi/4)d^2 = F*(d+x)*(0.866d+x) -> solve the quadratic in x
        k = (math.pi / 4.0) * d * d / SCRAMBLE_FILL
        b = d * (1.0 + math.sqrt(3.0) / 2.0)
        c = (math.sqrt(3.0) / 2.0) * d * d - k
        max_wall = (-b + math.sqrt(b * b - 4.0 * c)) / 2.0
    else:
        max_wall = d * (math.sqrt((math.pi / 4.0) / SCRAMBLE_FILL)
                        - 1.0)
    return {
        'ok': True, 'nested': bool(nested),
        'radialPitchMm': round(radial_pitch, 5),
        'packingCeilingNoWalls': round(
            CLOSE_PACKED_CEILING if nested else math.pi / 4.0, 4),
        'woundDiameterMm': d, 'wallMm': w, 'floorMm': f,
        'orderedFill': round(fill, 4),
        'scrambleFill': SCRAMBLE_FILL,
        'closePackedCeiling': round(CLOSE_PACKED_CEILING, 4),
        'beatsScramble': fill > SCRAMBLE_FILL,
        'gainVsScramble': round(fill / SCRAMBLE_FILL, 3),
        'maxWallForBreakEvenMm': round(max_wall, 4),
        'maxWallAsFractionOfWire': round(max_wall / d, 4),
        'rule': (
            f'grooving beats scramble winding only while the wall '
            f'stays under {max_wall / d * 100:.1f}% of the WOUND '
            f'wire diameter — here {max_wall * 1000:.0f} um. Thicker '
            f'than that and the ordered packing loses more window to '
            f'walls than it gains in order.'),
        'nestingNote': (
            'NESTED layers reach a ceiling of 0.907; layers sitting '
            'squarely on a rigid floor reach only 0.785 before any '
            'wall is charged. A grooved layer that SNAPS ON is a '
            'rigid floor by construction, so that variant forfeits '
            'most of the ordered-winding gain in exchange for its '
            'separability and per-layer inspectability. That is a '
            'real trade, not an oversight — but it should be made '
            'knowingly.'),
        'sameShapeAs': (
            'this is the mag-24 insulation result again: a thickness '
            'that adds to a diameter costs area as a SQUARE. Cotton '
            'covering was ruled out the same way.'),
    }


def fill_for_class(fill_class, wound_diameter_mm=None, wall_mm=None):
    """The fill a construction reaches, given its class — and an
    honest refusal when the class needs geometry it was not given."""
    if fill_class == 'scramble':
        return {'ok': True, 'fillClass': fill_class,
                'fill': SCRAMBLE_FILL,
                'note': 'literature scramble-winding figure'}
    if fill_class == 'n/a':
        return {'ok': True, 'fillClass': fill_class, 'fill': None,
                'note': 'this construction winds nothing'}
    if fill_class not in FILL_CLASSES:
        return {'ok': False,
                'refusal': f'unknown fill class "{fill_class}" — '
                           f'one of {FILL_CLASSES}'}
    if wound_diameter_mm is None or wall_mm is None:
        return {'ok': False, 'fillClass': fill_class,
                'refusal': 'ordered fill depends on wound wire '
                           'diameter and groove wall — geometry '
                           'unstated, so the fill is unknown, not '
                           'assumed',
                'suggestion': {'knob': 'wound_diameter_mm, wall_mm',
                               'action': 'state the geometry'}}
    g = groove_viability(wound_diameter_mm, wall_mm,
                         nested=(fill_class == 'ordered-nested'))
    if not g.get('ok'):
        return g
    return {'ok': True, 'fillClass': fill_class,
            'fill': g['orderedFill'], 'detail': g}
