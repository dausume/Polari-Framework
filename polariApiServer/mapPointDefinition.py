from objectTreeDecorators import treeObject, treeObjectInit

class MapPointDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', lat=0.0, lng=0.0, source_class='', source_instance_id='', manager=None):
        self.name = name
        self.lat = lat
        self.lng = lng
        self.source_class = source_class
        self.source_instance_id = source_instance_id
