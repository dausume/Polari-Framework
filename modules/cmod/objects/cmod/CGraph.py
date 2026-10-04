"""
@module cmod.objects.cmod.CGraph

CGraph — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CGraph(treeObject):
    """What it is: A NO-CODE GRAPH over atoms (C_MODULARIZATION_PLAN.md §5, cmod-1): `CGraphNode` rows are atom instances (plus the
    few glue-owned node kinds: the class state, the frame parser, the telemetry frame, a tick, a rule), `CGraphEdge` rows join an
    out port to an in port or schedule a node (tick / on-rx / on-command). Polari GENERATES plain-C glue from it
    (`polari_graph.c` + `polari_graph.h` + a Makefile, committed into `generated_project`) — always a real C project that
    `make` alone builds; no Python at run time. What today's firmware "variant" is (an app wiring the HAL atoms); `replaces`
    names the hand-written app it stands in for, whose twin frames it must reproduce (the `CGlueBuild` proof).
    Related concepts: `CGraphNode`, `CGraphEdge`, `CGlueBuild`, `CFunctionAtom`, `CPort`, board's `FirmwareVariant`.
    """

    plain_words = 'A C graph is a drawing of how firmware building blocks connect, from which Polari writes an ordinary C project.'

    @treeObjectInit
    def __init__(self, name: str = '', project: str = '', board: str = '', base_configuration: str = '', class_name: str = '',
                     replaces: str = '', generated_project: str = '', title: str = '', purpose: str = '', status: str = '',
                     graph_sha256: str = '', node_count: int = 0, edge_count: int = 0, atom_count: int = 0,
                     cost_estimate_bytes: int = 0, cost_estimate_why: str = '', glue_contains: str = '', notes: str = '',
                     manager=None):
        self.name = name
        self.project = project                      # the atoms' C project (uno)
        self.board = board
        self.base_configuration = base_configuration  # the configuration whose knobs (board_config.h) + compiled atoms it uses
        self.class_name = class_name                # the Polari class the frames carry (SimRigState)
        self.replaces = replaces                    # the hand-written app it stands in for
        self.generated_project = generated_project  # where the rendered project is committed (relative to modules/)
        self.title = title
        self.purpose = purpose
        self.status = status                        # seeded | rendered | built | proven
        self.graph_sha256 = graph_sha256
        self.node_count = node_count
        self.edge_count = edge_count
        self.atom_count = atom_count
        self.cost_estimate_bytes = cost_estimate_bytes
        self.cost_estimate_why = cost_estimate_why
        self.glue_contains = glue_contains
        self.notes = notes
