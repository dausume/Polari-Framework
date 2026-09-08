from objectTreeDecorators import treeObject, treeObjectInit


class GardenBoundary(treeObject):
    """
    GardenBoundary model class.

    Attributes:
        bounds: map_polygon
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 bounds='{}'):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.bounds = bounds

    def __repr__(self):
        return f"GardenBoundary(id='{self.id}')"
