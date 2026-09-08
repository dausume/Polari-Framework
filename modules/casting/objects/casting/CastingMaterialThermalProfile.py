"""
@module casting.objects.casting.CastingMaterialThermalProfile

Row class CastingMaterialThermalProfile of the casting module — one class per file (design §7), split
from casting_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CastingMaterialThermalProfile(treeObject):
    """cast-3b: the thermal data NO other table carries — melt/pour
    temperatures for castable metals (the survey found none anywhere
    in the framework). Literature-approximate with claim status, the
    CeramicSample pattern; a measured row replaces a prior."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # the MaterialsScienceMaterial (or common name) this covers.
        material_ref: str = '',
        solidus_c: float = 0.0,
        liquidus_c: float = 0.0,
        recommended_pour_c: float = 0.0,
        solidification_shrink_pct: float = 0.0,
        claim_status: str = 'literature-approximate',
        source_note: str = '',
        is_prior: bool = True,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.material_ref = material_ref
        self.solidus_c = solidus_c
        self.liquidus_c = liquidus_c
        self.recommended_pour_c = recommended_pour_c
        self.solidification_shrink_pct = solidification_shrink_pct
        self.claim_status = claim_status
        self.source_note = source_note
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
