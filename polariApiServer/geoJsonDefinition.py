from objectTreeDecorators import treeObject, treeObjectInit

class GeoJsonDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', description='', source_class='', definition='{}', manager=None):
        self.name = name
        self.description = description
        self.source_class = source_class
        self.definition = definition
