"""
@module hwnocode.objects.hwnocode.SchematicComponentPort

SchematicComponentPort — one class per file (design §7). cb-1 (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §3), a PROTOTYPE.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SchematicComponentPort(treeObject):
    """What it is: ONE CONNECTION OF A SCHEMATIC COMPONENT TO THE OUTSIDE - a chip pin it meets, or the supply or ground it draws on.
    One row = one port of one `SchematicComponent` (`component` names it). `kind` signal | supply | ground. `chip` and `pin` say where a
    signal port lands (e.g. chip1 GPIO3); either may be '' - left open for the pin solver to suggest. `net` the circuit net it is on (a derived
    port; two ports on one net are one line, the second a tap); `pin_source` chosen (a person
    picked it and it is held) | suggested (a solver filled it and may change it) | '' (open). `order` draws the ports top to bottom.
    Related concepts: `SchematicComponent`, `SchematicComponentPart` (a part sits on a port), `HardwareFeature`.
    """

    plain_words = 'Where a schematic component connects: a chip pin, the supply or ground, and whether that pin was picked or suggested.'

    KINDS = ('signal', 'supply', 'ground')

    @treeObjectInit
    def __init__(self, name: str = '', component: str = '', port: str = '', kind: str = 'signal', chip: str = '', pin: str = '',
                 pin_source: str = '', order: int = 0, net: str = '', notes: str = '', manager=None):
        self.name = name                # '<component>/<port>'
        self.component = component      # the SchematicComponent's name
        self.port = port                # the port's own name within the component, e.g. a | b | supply
        self.kind = kind                # signal | supply | ground
        self.chip = chip                # which chip a signal port lands on ('' = open)
        self.pin = pin                  # the chip pin, e.g. GPIO3 ('' = open)
        self.pin_source = pin_source    # chosen | suggested | '' (open)
        self.order = order
        self.net = net                  # the circuit net it is on ('' = not from a circuit); ports on one net are one line
        self.notes = notes
