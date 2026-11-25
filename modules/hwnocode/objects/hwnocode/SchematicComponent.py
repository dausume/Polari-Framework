"""
@module hwnocode.objects.hwnocode.SchematicComponent

SchematicComponent — one class per file (design §7). cb-1 (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §3), a PROTOTYPE: the user's
drawing of 2026-11-24 ("LightComp", "BtnSchematicComponent", each marked Solved or Unsolved).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SchematicComponent(treeObject):
    """What it is: ONE COMPONENT OF A SCHEMATIC AS A PERSON THINKS OF IT - "a button", "a light" - with the parts that make it behave
    on a real pin: the core part plus its conditioning parts (a pull resistor, a series resistor, a guard diode against current
    flowing back into a GPIO, a filter capacitor as close to the pin as possible). Its ports are `SchematicComponentPort` rows, its
    parts `SchematicComponentPart` rows. A `HardwareFeature` binds it to a struct field, a no-code piece and the pins.
    `intent` what it is for (button | light | ...); `core_part` the part kind at its centre; `protocol` how the signal behaves
    (active-low, debounced, interrupt or polled, ...), the protocol it was solved for.
    `solve_state` unsolved | solved | blocked | stale. unsolved = no solver ever ran on it (its paths are drawn red); solved = the
    schematic solver (hwnocode.custom.schematic_solve) ran on its circuit and every conditioning rule is placed or not needed and no
    electrical rule refuses; blocked = the solver ran and a part is needed that it cannot place itself, or a rule refuses (red, named in
    its `SchematicComponentCheck` rows); stale = its inputs changed since it was solved (`inputs_sha256` no longer matches).
    `solved_by` says who or what placed the conditioning parts: the solver and its version, or the user's drawing (the prototype rows).
    `hardware_solution`, `circuit` and `board` name what it was derived from ('' for the drawing's rows); `findings` the solver's verdict
    in words.
    Related concepts: `SchematicComponentPort`, `SchematicComponentPart`, `HardwareFeature`, electrodevice `CircuitDefinition`.
    """

    plain_words = ('One piece of a schematic as you would name it - a button or a light - with the small parts around it that make it '
                   'safe and reliable on a chip pin, and whether those parts have been worked out yet.')

    SOLVE_STATES = ('unsolved', 'solved', 'blocked', 'stale')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', intent: str = '', core_part: str = '', protocol: str = '',
                 solve_state: str = 'unsolved', solved_by: str = '', hardware_solution: str = '', circuit: str = '', board: str = '',
                 inputs_sha256: str = '', findings: str = '', description: str = '', notes: str = '', manager=None):
        self.name = name                # e.g. btn-comp
        self.title = title              # the person's own name for it, e.g. BtnSchematicComponent
        self.intent = intent            # button | light | ...
        self.core_part = core_part      # the part kind at its centre: pushbutton | led | ...
        self.protocol = protocol        # how its signal behaves, in words ('' = not chosen yet)
        self.solve_state = solve_state  # unsolved | solved | blocked | stale
        self.solved_by = solved_by      # a solver and its version, or where the parts came from; '' when unsolved
        self.hardware_solution = hardware_solution  # the board HardwareSolution it was derived from ('' = not derived)
        self.circuit = circuit          # the electrodevice CircuitDefinition its parts are on
        self.board = board              # the board whose pins its ports land on
        self.inputs_sha256 = inputs_sha256  # one sha over the rows the solver read; a different sha now = stale
        self.findings = findings        # the solver's verdict in words
        self.description = description
        self.notes = notes
