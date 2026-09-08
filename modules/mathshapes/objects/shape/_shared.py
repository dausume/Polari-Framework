"""@module mathshapes.objects.shape._shared — what the shape row classes share (constants, seeds, helpers); split from shape_basis.py (sap-2c)."""

SHAPE_FAMILIES = ('quadric', 'primitive', 'csg')
PRIMITIVE_KINDS = ('box', 'sphere', 'cylinder', 'cone', 'frustum',
                   'ellipsoid', 'annular_sector', 'arc_faced_bar')
CSG_OPS = ('union', 'difference', 'intersection')
