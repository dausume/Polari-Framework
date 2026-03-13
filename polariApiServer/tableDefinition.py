from objectTreeDecorators import treeObject, treeObjectInit

class TableDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', description='', source_class='', definition='{}',
                 is_default_table=False, is_default_instance_display=False,
                 is_default_dataset_display=False, manager=None):
        self.name = name
        self.description = description
        self.source_class = source_class
        self.definition = definition
        self.is_default_table = is_default_table
        self.is_default_instance_display = is_default_instance_display
        self.is_default_dataset_display = is_default_dataset_display
