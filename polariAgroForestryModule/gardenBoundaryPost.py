from objectTreeDecorators import treeObject, treeObjectInit


class GardenBoundaryPost(treeObject):
    """
    GardenBoundaryPost model class.

    Attributes:
        boundaryPost: str
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 boundaryPost=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.boundaryPost = boundaryPost

    def __repr__(self):
        return f"GardenBoundaryPost(id='{self.id}')"
