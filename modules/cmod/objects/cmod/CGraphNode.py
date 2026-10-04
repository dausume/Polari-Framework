"""
@module cmod.objects.cmod.CGraphNode

CGraphNode — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CGraphNode(treeObject):
    """What it is: One NODE of a `CGraph` (C_MODULARIZATION_PLAN.md §5, §7). Kind `c-atom` = an instance of a `CFunctionAtom`
    (the no-code node kind the canvas will draw in cmod-3; its sockets ARE the atom's `CPort` rows) with its parameter
    BINDINGS (`channel=ADC_CHANNEL`: a C literal or a knob of board_config.h, never free C). The other kinds are what the
    generated glue owns: `class` (the Polari class instance the frames carry), `parser` (the generated header's receiver),
    `frame` (telemetry encode + frame), `tick` (a period on the ms clock), `rule` (a status rule). `stage` says where a
    c-atom runs: init (before sei()), loop (the main loop) or called (inside another atom, bound by its caller).
    Related concepts: `CGraph`, `CGraphEdge`, `CFunctionAtom`, `CPort`.
    """

    plain_words = 'A graph node is one building block placed in a firmware drawing, with the values its inputs are given.'

    @treeObjectInit
    def __init__(self, name: str = '', graph: str = '', instance: str = '', kind: str = 'c-atom', atom: str = '', stage: str = '',
                     order: int = 0, bindings: str = '', params: str = '', ports_summary: str = '', role: str = '',
                     cost_bytes: int = 0, isr_safe: str = '', pure: bool = False, notes: str = '', manager=None):
        self.name = name                # <graph>:<instance>
        self.graph = graph
        self.instance = instance        # the C-identifier-safe instance name (locals in the glue are <instance>_<port>)
        self.kind = kind                # c-atom | class | parser | frame | tick | rule
        self.atom = atom                # c-atom only: the CFunctionAtom row name (uno:hal.hal_adc_read)
        self.stage = stage              # c-atom: init | loop | called
        self.order = order              # the statement order inside its scope (data edges must agree)
        self.bindings = bindings        # 'port=VALUE; …' — a C literal or a board_config.h / class-header macro
        self.params = params            # kind-specific 'key=value; …' (tick period_ms, frame fields, rule from/to/after_ms)
        self.ports_summary = ports_summary   # derived from the atom's ports
        self.role = role                # derived from the atom's annotation
        self.cost_bytes = cost_bytes    # derived: the atom's text bytes as a node (-fno-inline)
        self.isr_safe = isr_safe        # derived
        self.pure = pure                # derived
        self.notes = notes
