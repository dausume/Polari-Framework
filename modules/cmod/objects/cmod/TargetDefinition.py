"""
@module cmod.objects.cmod.TargetDefinition

TargetDefinition — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TargetDefinition(treeObject):
    """What it is: WHAT ONE PORT OF A GRAPH NODE (or one 'field' `CGraphEdge`) ACTUALLY CONTROLS on the device (demo-4,
    DEMONSTRABLES_PLAN.md §3 demo-4, his ruling: "we may say 'assign to 1 specific register this part of a struct, which
    we will use to track temperature from a sensor'"). `port_ref` names the atom instance and port inside the graph
    ('adc.channel') or, for a memory-field target, the writing port ('temp.return'). `kind` says what kind of thing the
    port is tied to (register | pin | peripheral | memory-field | bus | dynamic). `controls` is the physical quantity or
    actuator in plain words ("TMP36 temperature on A0"). `lives_on` REFERENCES a `BoardPin` row ('arduino-uno-r3:A0')
    when the port is bound to a specific board pin; 'unbound' when it is not yet tied to a board (still a real target —
    just not placed). `constraints` carries width/direction, derived from the atom's own `CPort`. `provenance` says how
    this row was produced: 'annotation' (an atom's POLARI_NODE-informed resource/declared-macro touch, matched against a
    board's BoardPin rows), 'derived' (a structural edge, e.g. a 'field' CGraphEdge, with no direct annotation), or
    'canvas' (typed in by a person on the canvas — none yet; the deriver never produces this kind).

    ucd-0b2a (§5h B1, widened per ROW, never one kind for a whole task): `requirement_kind` is the
    board.custom.target_compat.TASK_KINDS vocabulary (analog-in, pwm-out, uart-rx/tx, i2c-sda/scl, spi-mosi/miso/
    sck/ss, digital-in/out, interrupt-in, …) or 'undetermined' — '' for a memory-field row (not a hardware kind at
    all). Bound to a real BoardPin, it follows THAT PIN's own already-known signal when the atom-level heuristic
    alone cannot settle it (cmod.custom.targets._kind_for_pin — a usart_init atom touching neither UDR0-read nor
    UDR0-write settles uart-rx on its D0 row and uart-tx on its D1 row from the pins themselves, never one guess for
    both); unbound, from the atom's own resources/ports (the pre-existing per-task heuristic). `role` is input |
    output | receive | transmit | clock | select | data | address | '' (the physical role implied by
    `requirement_kind`). `required` is False only for a memory-field row (a struct field is not a hardware
    requirement at all) — True otherwise. `resource_kind` is pin | signal | peripheral | bus | undetermined ('' for
    a memory-field row) — every TASK_KINDS entry is inherently pin-level (board.custom.target_compat: "the pins are
    the targets"), so a resolved `requirement_kind` always carries `resource_kind='pin'` today.
    Related concepts: `CGraphNode`, `CGraphEdge`, `CPort`, `CFunctionAtom`, board's `BoardPin`, `CapabilityDefinition`.
    """

    plain_words = ('A target definition says what one input or output of a firmware drawing actually controls — a '
                   'register, a pin, a struct field — and whether it is tied to a real board pin yet.')

    @treeObjectInit
    def __init__(self, name: str = '', graph: str = '', node: str = '', port: str = '', port_ref: str = '',
                 kind: str = 'dynamic', controls: str = '', lives_on: str = '', board: str = '', direction: str = '',
                 ctype: str = '', width_bytes: int = 0, polari_type: str = '', unit: str = '', constraints: str = '',
                 provenance: str = 'derived', requirement_kind: str = 'undetermined', role: str = '',
                 required: bool = True, resource_kind: str = 'undetermined', peripheral: str = '', signal: str = '',
                 notes: str = '', manager=None):
        self.name = name                # '<graph>:<port_ref>'
        self.graph = graph
        self.node = node                # the CGraphNode instance this target is on
        self.port = port                # the port name on that node's atom ('' for a whole-node target)
        self.port_ref = port_ref        # '<node>.<port>' or '<node>'
        self.kind = kind                # register | pin | peripheral | memory-field | bus | dynamic
        self.controls = controls        # the physical quantity / actuator, in plain words
        self.lives_on = lives_on        # 'unbound' or a BoardPin row name ('<board>:<canonical>')
        self.board = board              # the board the graph targets (blank when unbound makes no sense to name one)
        self.direction = direction      # in | out | inout (from CPort), '' for a field target
        self.ctype = ctype
        self.width_bytes = width_bytes
        self.polari_type = polari_type
        self.unit = unit
        self.constraints = constraints  # 'in, width 2 B' — width/direction/rate, plain words
        self.provenance = provenance    # annotation | derived | canvas
        self.requirement_kind = requirement_kind  # board.custom.target_compat.TASK_KINDS vocabulary | undetermined | '' (memory-field)
        self.role = role                # input | output | receive | transmit | clock | select | data | address | ''
        self.required = required        # False only for a memory-field row
        self.resource_kind = resource_kind  # pin | signal | peripheral | bus | undetermined | '' (memory-field)
        # ucd-0b2d (§5h, the HardwareBinding fix): the SPECIFIC resource named, beside lives_on — a `board.Peripheral`
        # row name ('atmega328p:TIMER2') when resource_kind='peripheral', a `board.PeripheralSignal` row name
        # ('atmega328p:USART0:RXD') when resource_kind='signal'; '' otherwise (incl. every 'pin' row — the BOUND
        # PIN already names the resource via lives_on, never duplicated here).
        self.peripheral = peripheral
        self.signal = signal
        self.notes = notes
