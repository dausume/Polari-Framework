"""
@module hwnocode.objects.hwnocode.SchematicComponentCheck

SchematicComponentCheck — one class per file (design §7). cb-3 (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §5): what the schematic solver
decided for one component, one rule at a time.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SchematicComponentCheck(treeObject):
    """What it is: ONE DECISION THE SCHEMATIC SOLVER MADE ABOUT ONE COMPONENT - a conditioning rule (does it need a pull, a series resistor,
    a guard diode, a filter capacitor?) or one finding of the board's electrical rules (board.custom.electrical_check (a)-(j)) that is about
    this component. One row = one rule on one `SchematicComponent`; a finding about the whole solution (the supply total, the serial pins) has
    `component` '' and names the solution in `hardware_solution`.
    `status`: placed (the part is there: named in `part`) | not-needed (the rule says why not) | needed (a part is missing; the fix in words)
    | ok | warn | refuse (an electrical finding) | undetermined (a number is not cited - never a guess; `detail` names it).
    `cite` the source of the numbers, as the electrical rule gave it.
    Related concepts: `SchematicComponent`, `SchematicComponentPart`, board electrical_check / electrical_hw.
    """

    plain_words = ('One thing the solver checked about a schematic component - does it need a resistor, a diode, a capacitor - and what it '
                   'decided, in words, with where the numbers came from.')

    STATUSES = ('placed', 'not-needed', 'needed', 'ok', 'warn', 'refuse', 'undetermined')

    @treeObjectInit
    def __init__(self, name: str = '', component: str = '', hardware_solution: str = '', rule: str = '', status: str = '',
                 subject: str = '', detail: str = '', part: str = '', cite: str = '', order: int = 0, notes: str = '', manager=None):
        self.name = name                    # '<component>/<rule>[/<subject>]'
        self.component = component          # the SchematicComponent's name ('' = about the whole solution)
        self.hardware_solution = hardware_solution  # the board HardwareSolution solved ('' when solved from a circuit alone)
        self.rule = rule                    # pull | series | guard | filter | an electrical_check rule name
        self.status = status                # placed | not-needed | needed | ok | warn | refuse | undetermined
        self.subject = subject              # what it is about: a pin, a net, a part
        self.detail = detail                # the decision in words, with its numbers
        self.part = part                    # the SchematicComponentPart it placed or found ('' = none)
        self.cite = cite                    # where the numbers come from
        self.order = order
        self.notes = notes
