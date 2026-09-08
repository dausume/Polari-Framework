"""
@module meshassets.objects.mesh_asset.MeshAssetReference

Row class MeshAssetReference of the meshassets module — one class per file (design §7), split
from mesh_asset_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from meshassets.objects.mesh_asset._shared import ASSET_SUBJECTS

class MeshAssetReference(treeObject):
    """ONE catalogued asset. Rows carry a POINTER and a measured
    bounding box — never the mesh bytes: we do not vendor third-
    party geometry into this repo, we record where it is, what it
    is, and how well it fits."""

    @treeObjectInit
    def __init__(self, name='', display_name='', source_ref='',
                 subject='leaf', asset_url='',
                 bbox_mm_json='[]', poly_count=0,
                 morphology_note='', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.source_ref = source_ref
        self.subject = (subject if subject in ASSET_SUBJECTS
                        else 'other')
        self.asset_url = asset_url
        #: [length, width, thickness] in mm AS PUBLISHED/measured —
        #: the three numbers mesh_fit compares against an
        #: OrganModel's own vector dimensions. Empty = unmeasured,
        #: and fitting REFUSES rather than guessing a size.
        self.bbox_mm_json = bbox_mm_json
        self.poly_count = poly_count
        #: What morphology this shape actually reads as, honestly
        #: (a game-asset leaf is a stylized blade, not a species).
        self.morphology_note = morphology_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
