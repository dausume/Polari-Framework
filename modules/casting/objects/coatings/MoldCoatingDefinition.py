"""
@module casting.objects.coatings.MoldCoatingDefinition

Row class MoldCoatingDefinition of the casting module — one class per file (design §7), split
from coatings_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from casting.objects.coatings._shared import COATING_PURPOSES

class MoldCoatingDefinition(treeObject):
    """A coat applied to a mold face — release or sealing — with its
    thermal ceiling and local-renewability carried as data."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 coating_material_ref: str = '',
                 purpose: str = 'release',
                 accessibility_tier: str = 'household',
                 renewable: bool = False,
                 max_service_temp_c: float = 0.0,
                 applies_to_mold_materials_json: str = '[]',
                 is_prior: bool = True, notes: str = '',
                 provenance_id: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.coating_material_ref = coating_material_ref
        self.purpose = (purpose if purpose in COATING_PURPOSES
                        else 'release')
        self.accessibility_tier = accessibility_tier
        self.renewable = renewable
        self.max_service_temp_c = max_service_temp_c
        self.applies_to_mold_materials_json = \
            applies_to_mold_materials_json
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
