from objectTreeDecorators import treeObject, treeObjectInit

class SolutionTestCase(treeObject):
    @treeObjectInit
    def __init__(self, solution_id='', name='', description='',
                 input_params='{}', instance_fields='{}',
                 target_runtime='python_backend',
                 expected_return_value='', expected_status='completed',
                 tags='', created_at='', created_by='',
                 last_run_at='', last_run_passed=False, manager=None):
        self.solution_id = solution_id
        self.name = name
        self.description = description
        self.input_params = input_params        # JSON string of input parameter values
        self.instance_fields = instance_fields  # JSON string of pre-initialized fields
        self.target_runtime = target_runtime
        self.expected_return_value = expected_return_value
        self.expected_status = expected_status
        self.tags = tags
        self.created_at = created_at
        self.created_by = created_by
        self.last_run_at = last_run_at
        self.last_run_passed = last_run_passed
