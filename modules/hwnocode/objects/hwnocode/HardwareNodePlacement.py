"""
@module hwnocode.objects.hwnocode.HardwareNodePlacement

HardwareNodePlacement — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareNodePlacement(treeObject):
    """What it is: WHERE one node of a `HardwareSolution` runs and WHY (HARDWARE_NOCODE_PLAN.md §2b — the placement is DERIVED,
    never typed in): c-atom / glue kinds → `board` (`twin` while no BoardInstance is attached: the same .hex in simavr); the
    hw-interface → `bridge` (the split point: the generated Java bridge on the host carries the binding's frames both ways);
    engine state classes → `backend` (the Python engine); displays → `browser`. A Python node found on the device side is
    REFUSED with the reason (RULE 2: C, Verilog or SystemVerilog only on a device) — `refused` names it and `why` says how to
    move it across the hw-interface. Rows are written by `pol hwnocode place` / the seed, one per node.
    Related concepts: `HardwareSolution`, cmod `CGraphNode`, grpcbridge `HardwareInterfaceBinding`.
    """

    plain_words = 'A node placement says where one block of a hardware solution runs — on the board, in the bridge, on the server or on screen — and why.'

    @treeObjectInit
    def __init__(self, name: str = '', solution: str = '', node: str = '', layer: str = '', kind: str = '', placement: str = '',
                 language: str = '', why: str = '', refused: bool = False, order: int = 0, runtime: str = '', purpose: str = '',
                 notes: str = '', manager=None):
        self.name = name            # <solution>:<layer>:<node>
        self.solution = solution
        self.node = node            # the state name (solution canvas) or the CGraphNode instance (subgraph)
        self.layer = layer          # solution | subgraph | display
        self.kind = kind            # c-atom | class | parser | frame | tick | rule | hardware-subgraph | hw-interface | <engine class> | display
        self.placement = placement  # board | twin | bridge | backend | browser | host-engine
        self.language = language    # C | Java (generated bridge) | Python (engine) | TypeScript (Angular)
        self.why = why
        self.refused = refused
        self.order = order
        self.runtime = runtime      # demo-4b: one Runtime row name, derived from kind/placement (hwnocode.custom.runtimes)
        self.purpose = purpose      # one plain-words sentence, layer=='solution' nodes only (hwnocode.custom.solutions.STATE_PURPOSES)
        self.notes = notes
