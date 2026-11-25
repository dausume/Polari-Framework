"""
@module hwnocode.objects.hwnocode.HardwareFeature

HardwareFeature — one class per file (design §7). cb-2 (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §4), a ROUGH MODEL: the name is the
user's (2026-11-24); the columns are provisional until the user confirms them (plan §9).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareFeature(treeObject):
    """What it is: ONE BEHAVIOUR OF A DEVICE BROUGHT TOGETHER ACROSS EVERY LAYER - "the button", "the light": the struct field that
    carries it, the UI control that drives or shows it, the no-code piece and HAL role that run it on the chip, the protocol it
    follows, the `SchematicComponent` that makes it real, and the chip pins it lands on. Every column may be left open and filled in
    any order; each choice narrows what the other columns can be (hwnocode.custom.feature_columns says how each column plugs in).
    `chosen` csv of the columns a person picked and holds; every other filled column was suggested by a solver and may change.
    The design is solved for the REAL device and built first on its simulator pair (the user, 2026-11-24): `hardware_solution` names the
    board HardwareSolution the feature belongs to, `device` the real board it is solved for, `simulator` the engine that stands in for that
    board (board.custom.twin_kinds), `firmware_variant` the firmware it runs. A feature derived by hwnocode.custom.feature_derive has every
    column filled from existing rows; the drawing's prototype rows have no solution and so are never complete.
    Related concepts: `SchematicComponent`, `SchematicComponentPort`, grpcbridge `StructObjectMap`, cmod `HalVariableState`.
    """

    plain_words = ('One thing a device does - a button, a light - tied together from the data that carries it, the screen control, '
                   'the firmware that runs it, the circuit that makes it real, and the pins it uses.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', struct_instance: str = '', struct_field: str = '', ui_control: str = '',
                 ui_direction: str = '', nocode_variable: str = '', hal_role: str = '', protocol: str = '', schematic_component: str = '',
                 chip: str = '', pins: str = '', hardware_solution: str = '', firmware_variant: str = '', device: str = '', simulator: str = '',
                 chosen: str = '', notes: str = '', manager=None):
        self.name = name                        # e.g. button-on
        self.title = title
        self.struct_instance = struct_instance  # the struct instance carrying it, e.g. struct-instance-1
        self.struct_field = struct_field        # its field, e.g. ButtonOn
        self.ui_control = ui_control            # the screen control, e.g. btnToggle
        self.ui_direction = ui_direction        # bridge input | bridge output
        self.nocode_variable = nocode_variable  # the no-code / HAL variable, e.g. BUTTON_PIN
        self.hal_role = hal_role                # the HAL role, e.g. button
        self.protocol = protocol                # how the signal behaves, in words
        self.schematic_component = schematic_component  # the SchematicComponent's name
        self.chip = chip                        # '' = open
        self.pins = pins                        # csv, '' = open (the pin solver suggests)
        self.hardware_solution = hardware_solution  # the board HardwareSolution, e.g. uno-light-system
        self.firmware_variant = firmware_variant    # the FirmwareVariant it runs, e.g. uno-light
        self.device = device                    # the real board it is solved for, e.g. arduino-uno-r3
        self.simulator = simulator              # its simulator pair: the twin engine standing in for that board
        self.chosen = chosen                    # csv of the columns a person picked and holds
        self.notes = notes
