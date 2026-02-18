from objectTreeDecorators import treeObject, treeObjectInit

class TileSourceDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', type='tileserver', definition='{}', manager=None):
        self.name = name
        self.type = type  # 'tileserver' or 's3-bucket'
        self.definition = definition  # JSON blob of tile source config
