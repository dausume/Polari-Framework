from objectTreeDecorators import treeObject, treeObjectInit

class DisplayDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', description='', source_class='', definition='{}',
                 linkedSolutions='[]', isPage=False, pageRoute='', manager=None):
        self.name = name
        self.description = description
        self.source_class = source_class  # The class this display belongs to
        self.definition = definition  # JSON blob of the full Display structure
        self.linkedSolutions = linkedSolutions  # JSON array of solution names linked to this display
        self.isPage = isPage  # Whether this display is published as a standalone page
        self.pageRoute = pageRoute  # Custom route path when published as a page
