"""
@module cmod.objects.cmod.StructNodePath

StructNodePath - one class per file (design section 7); bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 2 "Path").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructNodePath(treeObject):
    """What it is: ONE WAY FROM THE ROOT TO A NODE - the ordered `StructEdge` names (comma-separated), its length, and whether it is the FASTEST
    (fewest edges; ties broken by name). Every test of a node replays a path from the root (the user: "we go from the beginning in terms of struct
    state"); the first test uses the fastest. Derived by cmod.custom.bench_topology.paths from the edges and written as rows so runs and confirmations
    (bss-3) can name them; re-derived when the edges change.
    Related concepts: `StructNode` (the parent), `StructEdge`.
    """

    plain_words = 'A path is one route from the moment the USB is plugged in to a given situation, counted in events; the shortest one is tested first.'

    @treeObjectInit
    def __init__(self, name: str = '', node: str = '', edges: str = '', length: int = 0, fastest: bool = False, notes: str = '', manager=None):
        self.name = name        # '<node>#<n>'
        self.node = node        # a StructNode name
        self.edges = edges      # comma-separated StructEdge names, root first
        self.length = length
        self.fastest = fastest
        self.notes = notes
