"""
@module hwnocode.objects.hwnocode.SchematicComponentPart

SchematicComponentPart — one class per file (design §7). cb-1 (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §3), a PROTOTYPE.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SchematicComponentPart(treeObject):
    """What it is: ONE PART INSIDE A SCHEMATIC COMPONENT - its core part (the pushbutton, the LED) or a conditioning part placed so the
    component behaves on a real pin. One row = one part of one `SchematicComponent`. `role` core | pull | series | guard | filter |
    supply: pull = a pull-up or pull-down resistor, series = a current-limiting resistor, guard = a diode that stops current flowing
    back into a GPIO, filter = a capacitor that smooths an incoming signal as close to the pin as possible, supply = what powers it.
    `part_kind` pushbutton | led | resistor | capacitor | diode | battery. `value` '' when no value has been worked out (shown as
    unverified, never guessed). `port` the port the part sits on, between the core part and that port ('' = the core part itself).
    `placed_by` drawing | rule | person; `rule` says, in words, which rule placed it and the numbers it used.
    Related concepts: `SchematicComponent`, `SchematicComponentPort`, board `ProtectionPart`, electrodevice `CircuitComponentDefinition`.
    """

    plain_words = 'One part of a schematic component - the button or light itself, or a small part around it - and why it is there.'

    ROLES = ('core', 'pull', 'series', 'guard', 'filter', 'supply')

    @treeObjectInit
    def __init__(self, name: str = '', component: str = '', ref: str = '', role: str = 'core', part_kind: str = '', value: str = '',
                 port: str = '', placed_by: str = '', rule: str = '', order: int = 0, notes: str = '', manager=None):
        self.name = name                # '<component>/<ref>'
        self.component = component      # the SchematicComponent's name
        self.ref = ref                  # the reference on the drawing: SW1, LED1, C1, D1, BT1
        self.role = role                # core | pull | series | guard | filter | supply
        self.part_kind = part_kind      # pushbutton | led | resistor | capacitor | diode | battery
        self.value = value              # e.g. 100 nF ('' = not worked out yet)
        self.port = port                # the port the part sits on ('' = the core part)
        self.placed_by = placed_by      # drawing | rule | person
        self.rule = rule                # which rule placed it and with what numbers, in words
        self.order = order
        self.notes = notes
