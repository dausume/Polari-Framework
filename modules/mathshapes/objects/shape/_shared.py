"""@module mathshapes.objects.shape._shared — what the shape row classes share (constants, seeds, helpers); split from shape_basis.py (sap-2c)."""

SHAPE_FAMILIES = ('quadric', 'primitive', 'csg')
PRIMITIVE_KINDS = ('box', 'sphere', 'cylinder', 'cone', 'frustum',
                   'ellipsoid', 'annular_sector', 'arc_faced_bar',
                   # tt-11: a planar polygon (vertices in the xy plane, optional thickness) — FEM elements, plates
                   'polygon')
CSG_OPS = ('union', 'difference', 'intersection')
