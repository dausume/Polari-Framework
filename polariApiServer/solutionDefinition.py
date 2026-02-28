from objectTreeDecorators import treeObject, treeObjectInit

class SolutionDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', function_name='', target_runtime='python_backend', definition='{}', manager=None):
        self.name = name
        self.function_name = function_name
        self.target_runtime = target_runtime  # 'python_backend' or 'typescript_frontend'
        self.definition = definition  # JSON blob of the full solution data
