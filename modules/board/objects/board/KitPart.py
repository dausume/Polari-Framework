"""
@module board.objects.board.KitPart

KitPart — one class per file (design §7); fs-2d (his addition, verbatim: "there are still some unvalidated cases,
and the power pins have no definitions at all" + his follow-up: "these are all the parts in our kit, we will be
wanting to use these as reference for how we make our sample firmwares").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class KitPart(treeObject):
    """What it is: ONE ROW of THE KIT PARTS REGISTER — a physical part from a named kit (today: `arduino-starter-kit`,
    the Arduino Starter Kit), cited to the kit's own book ("Parts in your kit", pp. 6-9, + "The Arduino Board" p.11
    for the board itself) and to the Arduino UNO R3 docs / ATmega328P datasheet where a number crosses into one of
    those (board.custom.uno_facts / board.custom.soc_atmega328p — the same citations the rest of THE BOARD OBJECT
    uses; never a new, uncited number). His ruling (2026-10-07): these rows are not decoration — they are what a
    sample FirmwareSolution / Capability is BUILT FROM, so every row carries what a sample firmware actually needs:
    `interface_kind` (the kind of board pin it wants: analog-in | digital-in | digital-out | pwm-out | uart | i2c |
    spi | servo-pwm | via-driver | '' for a part with no pin interface of its own — a breadboard, a jumper wire, the
    board itself), `driver_needed` (a part that can never wire straight to a pin — a DC motor needs an H-bridge or
    transistor; an LED needs a series resistor; a pushbutton needs a pull resistor), `pin_count` + `pin_roles` (which
    physical pin of the PART does what, as the book shows it — TMP36: left=power, centre=signal, right=ground),
    `electrical_notes` (voltage/current where the kit book or the UNO docs state it; `undetermined: <what's missing>`
    otherwise — derive-or-cite, no guessed numbers), `polarity` (an LED's long leg = anode; a diode's banded end =
    cathode; an electrolytic capacitor's marked leg), `kit_quantity` (from the book when it states a count; almost
    never does — marked undetermined rather than guessed), `source` (the citation string).
    `connects_to_kinds` is the MACHINE half of `connects_to` (a comma list drawn from the same vocabulary as
    board.custom.target_compat.TASK_KINDS, plus 'power'/'ground'/'reference') — board.custom.kit_parts.parts_for_pin()
    walks it to answer "which kit parts connect HERE" for any pin, the Target-details panel's "Parts that connect
    here" (fs-2d, replacing the empty Registered-Tasks list on a power/reference pin). `sample_capabilities` is
    DERIVED (board.custom.kit_parts._sample_capabilities), never hand-set: the names of today's CapabilityDefinition
    rows (cmod.custom.capabilities) whose own purpose/goal text names this part — e.g. 'temp-sensor-to-os' names the
    TMP36, 'blink-on-command' names D13/the LED. A row with none is "a part without a sample yet" — the backlog the
    kit-parts table itself names (board.board_page).
    Related concepts: board.custom.board_uno (the board side of a wiring), board.custom.target_compat.TASK_KINDS
    (the interface-kind vocabulary this reuses), cmod.custom.capabilities.SEED_CAPABILITIES (what sample_capabilities
    is derived from).
    """

    plain_words = ('A kit part is one physical component from a named kit (what it is, how it wires to a board pin, '
                   'and which sample firmware — if any — already uses it).')

    @treeObjectInit
    def __init__(self, name: str = '', kit: str = '', title: str = '', what_it_is: str = '', interface_kind: str = '',
                 driver_needed: str = '', pin_count: int = 0, pin_roles: str = '', connects_to: str = '',
                 connects_to_kinds: str = '', electrical_notes: str = '', polarity: str = '', kit_quantity: str = '',
                 source: str = '', sample_capabilities: str = '', notes: str = '', manager=None):
        self.name = name                          # '<kit>:<part>' e.g. 'arduino-starter-kit:tmp36'
        self.kit = kit                             # 'arduino-starter-kit' (other kits can follow, same class)
        self.title = title                         # e.g. 'Temperature sensor (TMP36)'
        self.what_it_is = what_it_is               # one sentence, from the kit book
        self.interface_kind = interface_kind       # analog-in | digital-in | digital-out | pwm-out | uart | i2c |
                                                    # spi | servo-pwm | via-driver | '' (no pin interface of its own)
        self.driver_needed = driver_needed         # '' when it wires straight to a pin
        self.pin_count = pin_count
        self.pin_roles = pin_roles                 # which physical pin of the PART does what, plain words
        self.connects_to = connects_to             # plain-words: target kinds + typical pins
        self.connects_to_kinds = connects_to_kinds  # machine form of connects_to (comma list, TASK_KINDS + power/ground/reference)
        self.electrical_notes = electrical_notes   # cited number, or 'undetermined: <missing fact>'
        self.polarity = polarity                   # '' when the part has none
        self.kit_quantity = kit_quantity           # from the book, or 'undetermined (...)'
        self.source = source                       # the citation string
        self.sample_capabilities = sample_capabilities  # comma list of CapabilityDefinition names (derived)
        self.notes = notes
