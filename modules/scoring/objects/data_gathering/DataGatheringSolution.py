"""
@module scoring.objects.data_gathering.DataGatheringSolution

Row class DataGatheringSolution of the scoring module — one class per file (design §7), split
from data_gathering_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DataGatheringSolution(treeObject):
    """One organization's data-gathering procedure for one term —
    a row, editable at the row."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 # The ScoreGroup that owns/practices the procedure.
                 organization_group: str = '',
                 # The ScoreTerm this procedure gathers data FOR.
                 term_name: str = '',
                 # GovSource / legal-source names drawn from (JSON
                 # list).
                 source_names_json: str = '[]',
                 # The ORDERED procedure: [{stepId, kind, description,
                 # method, toolOrSource}] — kinds in STEP_KINDS.
                 steps_json: str = '[]',
                 # Set when compiled through the seam.
                 compiled_solution_name: str = '',
                 version: int = 1,
                 status: str = 'draft',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.organization_group = organization_group
        self.term_name = term_name
        self.source_names_json = source_names_json
        self.steps_json = steps_json
        self.compiled_solution_name = compiled_solution_name
        self.version = version
        self.status = status
        self.notes = notes
