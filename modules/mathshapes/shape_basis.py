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
  - mathshapes.custom.shape_analysis (evaluate/measure/classify/sample)
  - SimSpace3D / Mesh3DDefinition rendering (sample_surface output)
@see /MATH_SHAPES_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/shape/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from mathshapes.objects.shape._shared import CSG_OPS, PRIMITIVE_KINDS, SHAPE_FAMILIES  # noqa: F401
from mathshapes.objects.shape.MathShapeDefinition import MathShapeDefinition  # noqa: F401
