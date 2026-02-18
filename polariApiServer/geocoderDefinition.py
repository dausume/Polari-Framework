from objectTreeDecorators import treeObject, treeObjectInit

class GeocoderDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', type='self-hosted', provider='pelias', definition='{}', manager=None):
        self.name = name
        self.type = type  # 'self-hosted' or 'web-limited'
        self.provider = provider  # 'pelias', 'nominatim', or 'google-maps'
        self.definition = definition  # JSON blob of geocoder config
