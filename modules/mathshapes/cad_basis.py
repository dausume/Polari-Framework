"""
@cross-cutting
@module mathshapes.cad_basis
@tags @xc:bindings

The persisted record of a CAD file imported through the cad-engines
worker: where the original bytes live in MinIO, the geometry the worker
pulled, and any parametric parameters FreeCAD exposed (which become
Polari knobs). Sits alongside the MathShapeDefinition(family=
'imported-mesh') + Mesh3DDefinition the import also creates.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - mathshapes.custom.cad_import / mathshapes.cad_api
@see /MATH_SHAPES_PLAN.md (PHASE shape-3)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cad/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from mathshapes.objects.cad.ImportedCadObject import ImportedCadObject  # noqa: F401
