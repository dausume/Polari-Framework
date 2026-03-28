from objectTreeDecorators import treeObject, treeObjectInit

class MapPolygonDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', vertex_point_ids='[]', boundary_segment_ids='[]', composition_mode='points', style_name='default-polygon', icon_name='', icon_style_name='', center_lng=0.0, center_lat=0.0, center_offset_lng=0.0, center_offset_lat=0.0, area_sq_meters=0.0, manager=None):
        self.name = name
        self.vertex_point_ids = vertex_point_ids
        self.boundary_segment_ids = boundary_segment_ids
        self.composition_mode = composition_mode
        self.style_name = style_name
        self.icon_name = icon_name
        self.icon_style_name = icon_style_name
        self.center_lng = center_lng
        self.center_lat = center_lat
        self.center_offset_lng = center_offset_lng
        self.center_offset_lat = center_offset_lat
        self.area_sq_meters = area_sq_meters
