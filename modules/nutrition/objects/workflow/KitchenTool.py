"""
@module nutrition.objects.workflow.KitchenTool

Row class KitchenTool of the nutrition module — one class per file (design §7), split
from workflow_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class KitchenTool(treeObject):
    """One inventory row: does THIS household own the tool?"""

    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '',
                 tool_name: str = '', owned: bool = True,
                 is_prior: bool = False, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.household_name = household_name
        self.tool_name = tool_name
        self.owned = owned
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
