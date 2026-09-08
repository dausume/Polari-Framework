"""
@module hwdigital.objects.logic.LogicBlockNode

Row class LogicBlockNode of the hwdigital module — one class per file (design §7), split
from logic_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LogicBlockNode(treeObject):
    """One logic block on a design's diagram — a row, configurable
    at the row."""

    @treeObjectInit
    def __init__(self, name: str = '', design_name: str = '',
                 kind: str = 'and',
                 # JSON dict: width (default 1), value (const),
                 # init (dff/counter reset value).
                 params_json: str = '{}',
                 # JSON list of source node names, in port order.
                 inputs_json: str = '[]',
                 description: str = '', manager=None):
        self.name = name
        self.design_name = design_name
        self.kind = kind
        self.params_json = params_json
        self.inputs_json = inputs_json
        self.description = description
