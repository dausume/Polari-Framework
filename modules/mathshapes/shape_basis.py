"""
@cross-cutting
@module mathshapes.shape_basis
@tags @xc:bindings, @xc:render-3d

Math-defined shapes — surfaces and volumes defined by MATHEMATICS
(matrix equations / analytic primitives / boolean CSG) rather than
hand-built meshes. This is the foundation that fixes "shapes look weird"
in 3D sims: a shape is an exact math definition the analysis can
evaluate (inside/outside), measure (volume/area/bbox/centroid),
classify, and sample into a clean render mesh.

One treeObject (auto-CRUDE + persisted — object-coherence):

  MathShapeDefinition   a shape from one of three FAMILIES:
      quadric    a surface/solid from a symmetric 4x4 matrix Q:
                 [x y z 1]·Q·[x y z 1]ᵀ = 0 is the surface, < 0 the
                 solid. Covers sphere/ellipsoid/cylinder/cone/
                 paraboloid/hyperboloid — every standard quadric, one
                 matrix. Stored as quadric_matrix_json (16 numbers,
                 row-major, symmetric).
      primitive  primitive_kind (box/sphere/cylinder/cone/frustum/
                 ellipsoid) + parameters_json — ANALYTIC volume + area
                 + inside-test.
      csg        csg_json {op: union|difference|intersection, shapes:
                 [names]} — a pot-with-holes = frustum DIFFERENCE
                 hole-cylinders.

The 4x4 quadric matrix is intended to round-trip as a MatrixDefinition
so a shape flows through the no-code matrix-equation editor
(object-coherence; see [[matrix-equation-operation-node]]).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - mathshapes.shape_analysis (evaluate/measure/classify/sample)
  - SimSpace3D / Mesh3DDefinition rendering (sample_surface output)
@see /MATH_SHAPES_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: The three shape families shape-1 defines.
SHAPE_FAMILIES = ('quadric', 'primitive', 'csg')

#: Analytic primitive kinds — each has a closed-form volume/area/inside.
PRIMITIVE_KINDS = ('box', 'sphere', 'cylinder', 'cone', 'frustum',
                   'ellipsoid', 'annular_sector', 'arc_faced_bar')

#: Boolean operations for a csg-family shape.
CSG_OPS = ('union', 'difference', 'intersection')


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
