"""
@module pcb.objects.pcb.PcbDesignRule

PcbDesignRule — one class per file (design §7); kxc-4, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PcbDesignRule(treeObject):
    """What it is: ONE CUSTOM DESIGN RULE of an ingested project (its .kicad_dru) - the rule's name, the condition it applies under, the layer, and its
    constraints (kind + arguments, e.g. clearance (min 0.2mm)).
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', rule: str = '', condition: str = '', layer: str = '', constraints_json: str = '[]', notes: str = '',
                 manager=None):
        self.name = name
        self.board = board
        self.rule = rule
        self.condition = condition
        self.layer = layer
        self.constraints_json = constraints_json
        self.notes = notes
