"""
@module plant_morphology.objects.organ.OrganModel

Row class OrganModel of the plant_morphology module — one class per file (design §7), split
from organ_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class OrganModel(treeObject):
    """A parametric 3D stand-in for one organ type of a plant."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('sweet-basil-leaf-organ').
        name: str = '',
        # The aqp-4 PlantDefinition this belongs to (by name).
        plant_name: str = '',
        # ORGAN_TYPES entry.
        organ: str = 'leaf',
        display_name: str = '',
        # SHAPE_PRIMITIVES entry — how volume/bounds are computed.
        shape_primitive: str = 'ellipsoid',
        # Bounding dimensions of ONE organ (mm).
        length_mm: float = 40.0,
        width_mm: float = 20.0,
        thickness_mm: float = 3.0,
        # How many of this organ at maturity (drives total volume +
        # canopy fill).
        count: int = 20,
        # ARRANGEMENTS entry.
        arrangement: str = 'opposite',
        # Estimate vs measured.
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.plant_name = plant_name
        self.organ = organ
        self.display_name = display_name
        self.shape_primitive = shape_primitive
        self.length_mm = length_mm
        self.width_mm = width_mm
        self.thickness_mm = thickness_mm
        self.count = count
        self.arrangement = arrangement
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
