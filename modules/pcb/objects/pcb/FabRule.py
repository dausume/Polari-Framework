"""
@module pcb.objects.pcb.FabRule

FabRule — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FabRule(treeObject):
    """What it is: One FAB CONSTRAINT (plan §2 `FabRule`), cited: key, operator (min | max | in | eq), value + unit + the mm
    value, the page text it came from, and the KiCad rule it becomes (a .kicad_dru constraint) or the Polari check that
    reads it.
    """

    @treeObjectInit
    def __init__(self, name: str = '', rule_set: str = '', key: str = '', op: str = '', value: str = '', unit: str = '',
                 value_mm: float = 0.0, source_text: str = '', url: str = '', retrieved: str = '', kicad_rule: str = '',
                 polari_check: str = '', notes: str = '', manager=None):
        self.name = name  # <set>:<key>
        self.rule_set = rule_set
        self.key = key
        self.op = op  # min | max | in | eq | info
        self.value = value  # as the page states it
        self.unit = unit
        self.value_mm = value_mm  # 0 = not a length
        self.source_text = source_text
        self.url = url
        self.retrieved = retrieved
        self.kicad_rule = kicad_rule  # the .kicad_dru constraint, or —
        self.polari_check = polari_check  # the row check, or —
        self.notes = notes
