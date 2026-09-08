"""
@module mathshapes.objects.cad.ImportedCadObject

Row class ImportedCadObject of the mathshapes module — one class per file (design §7), split
from cad_basis.py (sap-2c). The class docstring below is the explanation.
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
