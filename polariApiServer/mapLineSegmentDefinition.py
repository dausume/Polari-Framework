from objectTreeDecorators import treeObject, treeObjectInit

class MapLineSegmentDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', start_point_id='', end_point_id='', style_name='default-line', manager=None):
        self.name = name
        self.start_point_id = start_point_id
        self.end_point_id = end_point_id
        self.style_name = style_name
