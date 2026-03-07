from objectTreeDecorators import treeObject, treeObjectInit

class SolutionProcessLink(treeObject):
    @treeObjectInit
    def __init__(self, solution_id='', state_name='',
                 manual_process_step='', manual_process_description='',
                 manual_process_order=0,
                 code_snippet='', code_line_start=0, code_line_end=0,
                 code_runtime='python_backend',
                 notes='', tags='', manager=None):
        self.solution_id = solution_id
        self.state_name = state_name
        self.manual_process_step = manual_process_step
        self.manual_process_description = manual_process_description
        self.manual_process_order = manual_process_order
        self.code_snippet = code_snippet
        self.code_line_start = code_line_start
        self.code_line_end = code_line_end
        self.code_runtime = code_runtime
        self.notes = notes
        self.tags = tags
