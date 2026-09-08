"""
@module mathshapes.objects.shape.MathShapeDefinition

Row class MathShapeDefinition of the mathshapes module — one class per file (design §7), split
from shape_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MathShapeDefinition(treeObject):
    """A shape defined by mathematics — quadric matrix, analytic
    primitive, or boolean CSG of other shapes."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('unit-sphere', 'pot-with-holes').
        name: str = '',
        display_name: str = '',
        # SHAPE_FAMILIES entry.
        family: str = 'primitive',

        # --- family=quadric ---
        # 16 numbers, row-major, symmetric 4x4 Q. Surface: pᵀQp = 0
        # for p=[x y z 1]; solid interior: pᵀQp < 0.
        quadric_matrix_json: str = '',

        # --- family=primitive ---
        # PRIMITIVE_KINDS entry.
        primitive_kind: str = '',

        # --- family=csg ---
        # {"op": "difference", "shapes": ["frustum-pot", "hole-a", ...]}.
        # First shape is the base; the rest are subtracted/unioned/
        # intersected with it in order.
        csg_json: str = '',

        # The named tunable knobs (radius/height/count/center/axis/...).
        # For primitives this holds the geometry; for all families it is
        # the shape-2 modification seam (knobs-and-suggestions).
        parameters_json: str = '{}',

        # Axis-aligned bounding box used to grid-sample volume for
        # unbounded quadrics + CSG: [[xmin,xmax],[ymin,ymax],[zmin,zmax]]
        # (cm). Primitives derive their own bounds analytically.
        bounds_json: str = '',

        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.family = family
        self.quadric_matrix_json = quadric_matrix_json
        self.primitive_kind = primitive_kind
        self.csg_json = csg_json
        self.parameters_json = parameters_json
        self.bounds_json = bounds_json
        self.notes = notes
        self.provenance_id = provenance_id
