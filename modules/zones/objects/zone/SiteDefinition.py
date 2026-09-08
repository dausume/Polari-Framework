"""
@module zones.objects.zone.SiteDefinition

Row class SiteDefinition of the zones module — one class per file (design §7), split
from zone_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SiteDefinition(treeObject):
    """A named collection of zones (a house, a lot)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.notes = notes
