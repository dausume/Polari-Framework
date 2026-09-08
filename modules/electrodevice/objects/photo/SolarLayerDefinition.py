"""
@module electrodevice.objects.photo.SolarLayerDefinition

Row class SolarLayerDefinition of the electrodevice module — one class per file (design §7), split
from photo_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SolarLayerDefinition(treeObject):
    """One layer of the thin-film stack — a knob row: role, material,
    thickness, and the property this layer is chosen FOR (structured
    record or an honest named gap)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        stack_name: str = '',
        position: int = 0,
        role: str = '',
        material: str = '',
        thickness_m: float = 0.0,
        # The property that justifies the layer (structured record) —
        # or {} with the gap named in notes.
        key_property_json: str = '{}',
        community_source: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.stack_name = stack_name
        self.position = position
        self.role = role
        self.material = material
        self.thickness_m = thickness_m
        self.key_property_json = key_property_json
        self.community_source = community_source
        self.notes = notes
