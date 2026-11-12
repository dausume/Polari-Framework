"""@module mathshapes.objects.shape._shared — what the shape row classes share (constants, seeds, helpers); split from shape_basis.py (sap-2c)."""

SHAPE_FAMILIES = ('quadric', 'primitive', 'csg')
PRIMITIVE_KINDS = ('box', 'sphere', 'cylinder', 'cone', 'frustum',
                   'ellipsoid', 'annular_sector', 'arc_faced_bar',
                   # tt-11: a planar polygon (vertices in the xy plane, optional thickness) — FEM elements, plates
                   'polygon')
CSG_OPS = ('union', 'difference', 'intersection')

# ms-anchor (MECH_FREECAD_INTERCHANGE_PLAN §8.5): the anchored-offset
# tool's enums. A ShapeAnchor's reference axis is one of FOUR
# directions built from the viewer's ray d and the outward normal n at
# the picked point (the toggle); an AnchoredOffset is one of four
# profile MODES expressed in that anchor's frame.
REFERENCE_MODES = ('toward', 'away', 'tangent_toward', 'tangent_away')
OFFSET_MODES = ('planar_square', 'planar_disk', 'conform', 'custom')
OFFSET_OPS = ('add', 'subtract', 'intersect')
ANCHOR_BASES = ('exact', 'sampled')
