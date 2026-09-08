"""
@module electrodevice.objects.circuit.CircuitDefinition

Row class CircuitDefinition of the electrodevice module — one class per file (design §7), split
from circuit_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CircuitDefinition(treeObject):
    """One circuit — the unit that renders to a netlist and runs."""

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '',
                 # JSON list of analyses, run in order. Shapes:
                 #   {'type': 'op'}
                 #   {'type': 'tran', 'args': '<step> <stop>',
                 #    'meas': '<full ngspice meas expression>'}
                 analyses_json: str = '[{"type": "op"}]',
                 # JSON list of 'print' probes for op analyses
                 # (one per line — table output defeats the parser).
                 probes_json: str = '[]',
                 notes: str = '', manager=None):
        self.name = name
        self.description = description
        self.analyses_json = analyses_json
        self.probes_json = probes_json
        self.notes = notes
