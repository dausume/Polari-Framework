from objectTreeDecorators import treeObject, treeObjectInit

class DataSetDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', description='', source_class='', definition='{}', field_profile_id='', filter_chain_id='', manager=None):
        self.name = name
        self.description = description
        self.source_class = source_class
        self.definition = definition
        self.field_profile_id = field_profile_id
        self.filter_chain_id = filter_chain_id
