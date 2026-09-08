"""
@module hwdigital.objects.logic.LogicBlockDesign

Row class LogicBlockDesign of the hwdigital module — one class per file (design §7), split
from logic_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LogicBlockDesign(treeObject):
    """One digital design — the unit that compiles to a Verilog
    module, simulates behind Renode, and synthesizes for iCE40."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 description: str = '',
                 # 'ice40' is the synthesis target family (Dustin
                 # 2026-07-16); 'sim' designs skip the synth leg.
                 target: str = 'ice40',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.target = target
        self.notes = notes
