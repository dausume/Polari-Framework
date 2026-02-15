from objectTreeDecorators import treeObject, treeObjectInit

class DisplayDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', description='', source_class='', definition='{}', manager=None):
        self.name = name
        self.description = description
        self.source_class = source_class  # The class this display belongs to
        self.definition = definition  # JSON blob of the full Display structure
