"""
@module magnetics.objects.magnet_circuit.MagneticCircuitDefinition

Row class MagneticCircuitDefinition of the magnetics module — one class per file (design §7), split
from magnet_circuit_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MagneticCircuitDefinition(treeObject):
    """One magnetic circuit — the unit that renders to a reluctance
    network and solves."""

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '',
                 # JSON list of analyses, run in order. Shapes:
                 #   {'type': 'op'}
                 #   {'type': 'sweep', 'element': '<element name>',
                 #    'param': '<params_json key>',
                 #    'values': [..]}
                 analyses_json: str = '[{"type": "op"}]',
                 notes: str = '', manager=None):
        self.name = name
        self.description = description
        self.analyses_json = analyses_json
        self.notes = notes
