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
    Related concepts: `CGraphNode`, `CGraphEdge`, `CPort`, `CFunctionAtom`, board's `BoardPin`, `CapabilityDefinition`.
    """

    plain_words = ('A target definition says what one input or output of a firmware drawing actually controls — a '
                   'register, a pin, a struct field — and whether it is tied to a real board pin yet.')

    @treeObjectInit
    def __init__(self, name: str = '', graph: str = '', node: str = '', port: str = '', port_ref: str = '',
                 kind: str = 'dynamic', controls: str = '', lives_on: str = '', board: str = '', direction: str = '',
                 ctype: str = '', width_bytes: int = 0, polari_type: str = '', unit: str = '', constraints: str = '',
                 provenance: str = 'derived', notes: str = '', manager=None):
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
        self.notes = notes
