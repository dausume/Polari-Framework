"""
@module cmod.objects.cmod.CGraph

CGraph — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CGraph(treeObject):
    """What it is: A NO-CODE GRAPH over atoms (C_MODULARIZATION_PLAN.md §5, cmod-1): nodes are CFunctionAtoms, edges join an out
    port to an in port, and Polari GENERATES plain-C glue (polari_graph.c + Makefile) from it — always a real C project. What
    today's firmware "variant" is (an app wiring the HAL atoms). cmod-0 registers the ROW KIND only; no graph exists yet.
    Related concepts: `CFunctionAtom`, `CPort`, `CProject`, board's `FirmwareVariant`.
    """

    plain_words = 'A C graph will be a drawing of how firmware building blocks connect, from which Polari writes ordinary C code.'

    @treeObjectInit
    def __init__(self, name: str = '', project: str = '', title: str = '', purpose: str = '', nodes: str = '',
                     edges: str = '', status: str = 'row-kind-only', generated_project: str = '', notes: str = '',
                     manager=None):
        self.name = name
        self.project = project
        self.title = title
        self.purpose = purpose
        self.nodes = nodes
        self.edges = edges
        self.status = status
        self.generated_project = generated_project
        self.notes = notes
