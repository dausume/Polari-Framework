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
  - mathshapes.cad_import / mathshapes.cad_api
@see /MATH_SHAPES_PLAN.md (PHASE shape-3)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class ImportedCadObject(treeObject):
    """One imported CAD file: MinIO-backed source + pulled geometry."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('bracket-v2-import').
        name: str = '',
        display_name: str = '',
        # original filename + its format (stl/step/fcstd/...).
        source_filename: str = '',
        source_format: str = '',
        # MinIO object key of the stored original ('cad-imports/....').
        minio_key: str = '',
        # geometry the worker pulled.
        volume_cm3: float = 0.0,
        bbox_json: str = '',
        centroid_json: str = '',
        # parametric parameters FreeCAD exposed -> Polari knobs.
        parametric_params_json: str = '{}',
        # the render + math rows this import produced (by name).
        mesh3d_name: str = '',
        shape_name: str = '',
        # which importer answered (trimesh / freecad).
        importer: str = '',
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.source_filename = source_filename
        self.source_format = source_format
        self.minio_key = minio_key
        self.volume_cm3 = volume_cm3
        self.bbox_json = bbox_json
        self.centroid_json = centroid_json
        self.parametric_params_json = parametric_params_json
        self.mesh3d_name = mesh3d_name
        self.shape_name = shape_name
        self.importer = importer
        self.notes = notes
        self.provenance_id = provenance_id
