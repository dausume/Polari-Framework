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
