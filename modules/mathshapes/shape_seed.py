"""
@cross-cutting
@module mathshapes.shape_seed
@tags @xc:bindings

Seed math shapes covering all three families: quadric matrix surfaces
(unit-sphere, demo-ellipsoid), analytic primitives (demo-cylinder,
frustum-pot, two radial hole-cylinders), and a CSG difference
(pot-with-holes = frustum − holes) — the shape shape-2 modifies.
Idempotent-by-name. Lengths in cm.

@consumers
  - polariServer seed_pairs
@see /MATH_SHAPES_PLAN.md
"""

import json

# Quadric Q stored as 16 numbers, row-major, symmetric.
# Interior is pᵀQp < 0.
_UNIT_SPHERE_Q = [1, 0, 0, 0,
                  0, 1, 0, 0,
                  0, 0, 1, 0,
                  0, 0, 0, -1]           # x²+y²+z²-1 = 0

_ELLIPSOID_Q = [0.25, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                0, 0, 0, -1]            # x²/4 + y² + z² - 1 = 0  (a=2,b=c=1)


SEED_MATH_SHAPES = [
    # --- quadric family ---
    {'name': 'unit-sphere', 'display_name': 'Unit sphere',
     'family': 'quadric',
     'quadric_matrix_json': json.dumps(_UNIT_SPHERE_Q),
     'bounds_json': json.dumps([[-1, 1], [-1, 1], [-1, 1]]),
     'notes': 'Q = diag(1,1,1,-1); the canonical quadric.',
     'provenance_id': 'shape-1'},
    {'name': 'demo-ellipsoid', 'display_name': 'Demo ellipsoid (2×1×1)',
     'family': 'quadric',
     'quadric_matrix_json': json.dumps(_ELLIPSOID_Q),
     'bounds_json': json.dumps([[-2, 2], [-1, 1], [-1, 1]]),
     'notes': 'a=2, b=c=1 ellipsoid as a diagonal quadric.',
     'provenance_id': 'shape-1'},

    # --- primitive family ---
    {'name': 'demo-cylinder', 'display_name': 'Demo cylinder (r1 h4)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 1.0, 'height': 4.0, 'axis': 'z',
          'center': [0.0, 0.0, 0.0]}),
     'provenance_id': 'shape-1'},
    {'name': 'frustum-pot', 'display_name': 'Frustum pot body',
     'family': 'primitive', 'primitive_kind': 'frustum',
     'parameters_json': json.dumps(
         {'base_radius': 6.0, 'top_radius': 9.0, 'height': 20.0,
          'axis': 'z', 'center': [0.0, 0.0, 0.0]}),
     'notes': 'a widening plant pot; the base solid for pot-with-holes.',
     'provenance_id': 'shape-1'},
    {'name': 'hole-cylinder-a', 'display_name': 'Drainage hole (x)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 1.2, 'height': 24.0, 'axis': 'x',
          'center': [0.0, 0.0, 6.0]}),
     'notes': 'a radial hole punched through the pot wall near the top.',
     'provenance_id': 'shape-1'},
    {'name': 'hole-cylinder-b', 'display_name': 'Drainage hole (y)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 1.2, 'height': 24.0, 'axis': 'y',
          'center': [0.0, 0.0, 6.0]}),
     'notes': 'the second radial hole (perpendicular to the first).',
     'provenance_id': 'shape-1'},

    # --- csg family ---
    {'name': 'pot-with-holes', 'display_name': 'Pot with drainage holes',
     'family': 'csg',
     'csg_json': json.dumps(
         {'op': 'difference',
          'shapes': ['frustum-pot', 'hole-cylinder-a', 'hole-cylinder-b']}),
     'notes': 'frustum-pot DIFFERENCE two hole-cylinders; the shape-2 '
              'modification seam.',
     'provenance_id': 'shape-1'},
]
