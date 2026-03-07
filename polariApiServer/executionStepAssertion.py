from objectTreeDecorators import treeObject, treeObjectInit

class ExecutionStepAssertion(treeObject):
    @treeObjectInit
    def __init__(self, test_case_id='', step_index=0,
                 state_name='', assertion_type='context_value',
                 variable_name='', expected_value='',
                 comparison_operator='equals',
                 expected_branch_taken='', expected_branch_label='',
                 expected_status='completed',
                 description='', enabled=True, manager=None):
        self.test_case_id = test_case_id
        self.step_index = step_index
        self.state_name = state_name
        self.assertion_type = assertion_type        # context_value | branch_taken | status | return_value
        self.variable_name = variable_name
        self.expected_value = expected_value
        self.comparison_operator = comparison_operator
        self.expected_branch_taken = expected_branch_taken
        self.expected_branch_label = expected_branch_label
        self.expected_status = expected_status
        self.description = description
        self.enabled = enabled
