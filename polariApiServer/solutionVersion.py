from objectTreeDecorators import treeObject, treeObjectInit

class SolutionVersion(treeObject):
    @treeObjectInit
    def __init__(self, solution_id='', version_number=1, label='',
                 description='', definition='{}', generated_code='{}',
                 created_at='', created_by='', parent_version_id='',
                 is_current=False, manager=None):
        self.solution_id = solution_id
        self.version_number = version_number
        self.label = label
        self.description = description
        self.definition = definition          # JSON snapshot of the solution
        self.generated_code = generated_code  # JSON: {"python": "...", "typescript": "..."}
        self.created_at = created_at
        self.created_by = created_by
        self.parent_version_id = parent_version_id
        self.is_current = is_current
