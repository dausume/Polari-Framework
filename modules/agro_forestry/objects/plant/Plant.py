"""
@module agro_forestry.objects.plant.Plant

Row class Plant of the agro_forestry module — one class per file (design §7), split
from plant_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class Plant(treeObject):
    """
    Plant model class.

    Attributes:
        maxHeight: float
        maxRootDepth: float
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 maxHeight=0.0,
                 maxRootDepth=0.0):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.maxHeight = maxHeight
        self.maxRootDepth = maxRootDepth

    def __repr__(self):
        return f"Plant(id='{self.id}')"
