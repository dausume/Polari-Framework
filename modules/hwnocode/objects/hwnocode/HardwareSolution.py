"""
@module hwnocode.objects.hwnocode.HardwareSolution

HardwareSolution — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareSolution(treeObject):
    """What it is: ONE no-code solution that spans hardware, the bridge, the backend and the browser (HARDWARE_NOCODE_PLAN.md §2c,
    D-hn-1 ruled "subgraph"): `solution` names the SolutionDefinition drawn on the ONE canvas (its states include the node kinds
    `HardwareSubgraph` and `HardwareInterface`), `cgraph` names the cmod `CGraph` that IS the hardware subgraph (cmod's rows,
    checker and byte-identical proof stay as they are), `interface` the grpcbridge `HardwareInterfaceBinding` where the graph
    crosses device ⇄ backend, `displays` the configured DisplayDefinition rows. `firmware_runtime` is the KNOB (bare-c | freertos |
    esp-idf | zephyr — the person's pick, never pre-selected by Polari, D-hn-3; hn-0 renders bare-c only and refuses the others
    with the reason). The placement (every node → board | twin | bridge | backend | browser, plan §2b) and the split
    (`hn-split`: the board half through `cmod-glue`, the backend half as its own SolutionDefinition) are DERIVED, never typed in.
    Related concepts: `HardwareNodePlacement`, cmod `CGraph`, grpcbridge `HardwareInterfaceBinding`, `SolutionDefinition`.
    """

    plain_words = ('A hardware solution is one drawing that spans a board, the cable to Polari, the server and a screen; '
                   'Polari works out where each piece runs.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', purpose: str = '', variant_kind: str = '', solution: str = '',
                 backend_solution: str = '', cgraph: str = '', board_definition: str = '', board_instance: str = '',
                 interface: str = '', displays: str = '', firmware_runtime: str = 'bare-c', runtime_status: str = '',
                 placement_summary: str = '', node_count: int = 0, refused: str = '', split_sha256: str = '',
                 glue_files_sha256: str = '', glue_hex_sha256: str = '', status: str = '', proof: str = '', costs: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.title = title
        self.purpose = purpose
        self.variant_kind = variant_kind            # plan §4: a standalone · b peripheral · h split app · …
        self.solution = solution                    # the SolutionDefinition drawn on the canvas (all node kinds)
        self.backend_solution = backend_solution    # derived by hn-split: the backend half as its own SolutionDefinition
        self.cgraph = cgraph                        # D-hn-1: the cmod CGraph that IS the hardware subgraph
        self.board_definition = board_definition    # arduino-uno-r3
        self.board_instance = board_instance        # a BoardInstance name; twin:… = the simavr twin (no board attached)
        self.interface = interface                  # the HardwareInterfaceBinding name — the split point
        self.displays = displays                    # DisplayDefinition names (csv)
        self.firmware_runtime = firmware_runtime    # KNOB: bare-c | freertos | esp-idf | zephyr (the person's pick)
        self.runtime_status = runtime_status        # derived: supported | refused — the reason
        self.placement_summary = placement_summary  # derived: 'twin 18, bridge 1, backend 6, browser 1'
        self.node_count = node_count                # derived
        self.refused = refused                      # derived: the placement refusal ('' = none)
        self.split_sha256 = split_sha256            # derived: one sha over the placement + both halves
        self.glue_files_sha256 = glue_files_sha256  # derived: the board half's files (cmod-glue) — equal to cmod-1's record
        self.glue_hex_sha256 = glue_hex_sha256      # the .hex the board half builds to (make alone; measured)
        self.status = status                        # seeded | placed | rendered | built | proven
        self.proof = proof                          # the twin proof in words (hn-0)
        self.costs = costs                          # measured costs (the cost rule)
        self.notes = notes
