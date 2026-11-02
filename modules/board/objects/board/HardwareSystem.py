"""
HardwareSystem - one class per file (design section 7); bss-0 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5, "template"; D-bss-1).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareSystem(treeObject):
    """What it is: THE HARDWARE TEMPLATE of a bench concept - which boards MAY be used (a family: the BoardDefinition names that fit) and which bench
    circuit it carries, with the part choices still open (the exact resistor, the exact LED, which module board). A `HardwareSolution` (renamed from
    HardwareSystem on 2026-11-02, D-bss-1) is this with every choice made: the specific boards, parts and nets. The user's rule (2026-11-01): a System
    is the baseline template; a Solution is the finalized specific result.
    Related concepts: `HardwareSolution` (names this as its `system`), `BoardDefinition`, electrodevice `CircuitDefinition`, `BenchSystem` (composes it).
    """

    plain_words = ('A hardware system is the template for the physical side of a bench: which kinds of board fit and what circuit goes on it, '
                   'before the exact parts are picked.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', boards: str = '', circuit: str = '', notes: str = '', manager=None):
        self.name = name
        self.title = title
        self.boards = boards      # comma-separated BoardDefinition names that fit this template (the family)
        self.circuit = circuit    # an electrodevice CircuitDefinition name, or '' when the template is a bare board
        self.notes = notes
