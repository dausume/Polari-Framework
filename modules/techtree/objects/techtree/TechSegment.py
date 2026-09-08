"""
@module techtree.objects.techtree.TechSegment

Row class TechSegment of the techtree module — one class per file (design §7), split
from techtree_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TechSegment(treeObject):
    """Per-node, per-kind segment KNOB row: the weight a present
    segment contributes to node completion. Optional — an absent row
    means weight 1.0; presence/completion always derive from the
    assignments, never from this row."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<tech_node>:<kind>'.
        name: str = '',
        tech_node: str = '',
        tree_name: str = '',
        # SEGMENT_KINDS entry.
        kind: str = 'theory',
        weight: float = 1.0,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.tech_node = tech_node
        self.tree_name = tree_name
        self.kind = kind
        self.weight = weight
        self.notes = notes
