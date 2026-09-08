"""
@module agro_forestry.objects.gardenBoundaryPost.GardenBoundaryPost

Row class GardenBoundaryPost of the agro_forestry module — one class per file (design §7), split
from gardenBoundaryPost_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class GardenBoundaryPost(treeObject):
    """
    GardenBoundaryPost model class.

    Attributes:
        boundaryPost: map_coordinate
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 boundaryPost='[]'):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.boundaryPost = boundaryPost

    def __repr__(self):
        return f"GardenBoundaryPost(id='{self.id}')"
