"""
@module techtree.objects.techtree.TechSegmentAssignment

Row class TechSegmentAssignment of the techtree module — one class per file (design §7), split
from techtree_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TechSegmentAssignment(treeObject):
    """The join that FILLS a segment (B2): one referenced item per
    row. What ref_name points at depends on segment_kind —
    theory: a Polari module id; real: a RealArtifact.name;
    business: a BusinessModelDefinition.name; politics: a
    PolicyDefinition.name. The done-criterion per kind lives in
    techtree_analysis (first-cut done-tests, evidence-bearing)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<tech_node>:<kind>:<ref_name>'.
        name: str = '',
        tech_node: str = '',
        tree_name: str = '',
        # SEGMENT_KINDS entry.
        segment_kind: str = 'theory',
        # The referenced module / artifact / business model / policy.
        ref_name: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.tech_node = tech_node
        self.tree_name = tree_name
        self.segment_kind = segment_kind
        self.ref_name = ref_name
        self.notes = notes
