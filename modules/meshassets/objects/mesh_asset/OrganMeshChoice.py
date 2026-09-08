"""
@module meshassets.objects.mesh_asset.OrganMeshChoice

Row class OrganMeshChoice of the meshassets module — one class per file (design §7), split
from mesh_asset_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class OrganMeshChoice(treeObject):
    """THE PICK: this OrganModel is approximated by that asset, at
    these per-axis scales. Created by a human choosing from the
    fit report — never auto-assigned, because "close enough" is a
    judgement and the number only informs it."""

    @treeObjectInit
    def __init__(self, name='', organ_model_ref='', asset_ref='',
                 scale_length=1.0, scale_width=1.0,
                 scale_thickness=1.0, rotation_deg_json='[0,0,0]',
                 accepted_by='', accepted_note='', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.organ_model_ref = organ_model_ref
        self.asset_ref = asset_ref
        #: Per-axis scale applied to the asset to reach the organ's
        #: vector dimensions. Equal scales = the proportions already
        #: matched; wildly unequal = the mesh is being squashed into
        #: a shape it is not, and fidelity reports how much.
        self.scale_length = scale_length
        self.scale_width = scale_width
        self.scale_thickness = scale_thickness
        self.rotation_deg_json = rotation_deg_json
        #: Who accepted this approximation, and why they judged it
        #: close enough. Blank = proposed, not accepted.
        self.accepted_by = accepted_by
        self.accepted_note = accepted_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
