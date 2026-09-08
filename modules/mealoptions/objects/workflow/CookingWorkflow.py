"""
@module mealoptions.objects.workflow.CookingWorkflow

Row class CookingWorkflow of the mealoptions module — one class per file (design §7), split
from workflow_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CookingWorkflow(treeObject):
    """A saved week DAG — pure graph data for the no-code editor."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 plan_name: str = '',
                 # {nodes: [{id, kind, task/action, grams, day,
                 #  session}], edges: [{from, to, state}]}
                 definition_json: str = '{}',
                 provenance: str = 'mine',
                 is_prior: bool = False, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.plan_name = plan_name
        self.definition_json = definition_json
        self.provenance = provenance
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
