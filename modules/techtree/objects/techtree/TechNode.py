"""
@module techtree.objects.techtree.TechNode

Row class TechNode of the techtree module — one class per file (design §7), split
from techtree_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TechNode(treeObject):
    """One TECHNOLOGY in a tree — the rectangular container of the
    tech-tree render mode. segments_present + completion_level are
    DERIVED by techtree_analysis (never stored here)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<tree>/<technology>'.
        name: str = '',
        tree_name: str = '',
        # Display title ('' = derive from name).
        title: str = '',
        description: str = '',
        # JSON list of TechNode names this technology depends on —
        # the durable dependency statement; TechDependencyEdge rows
        # are derived from it (sync_edges) so designation has rows
        # to stamp, mirroring ModuleDependencyEdge.
        depends_on_json: str = '[]',
        # JSON layout hints for the renderer ({} = auto-placed).
        layout_hints_json: str = '{}',
        # tt-9: CROSS-TREE relationships — never edges (edges are
        # tree-scoped); a JSON list of {tree, node, relation} the
        # renderer shows as zoom-to chips naming the home tree
        # ('produces' / 'supplied-by' / ...).
        cross_refs_json: str = '[]',
        # mtt-2: DigitizedDataset names this technology needs to be
        # QUANTITATIVELY complete. A referenced dataset that is
        # missing, provisional, or points-empty surfaces as a DERIVED
        # data gap (digitize it -> the gap auto-clears). Structural
        # (theory) completion and data completeness are separate axes:
        # a node can be 'built' yet still carry open data asks.
        data_dependencies_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.tree_name = tree_name
        self.title = title
        self.description = description
        self.depends_on_json = depends_on_json
        self.layout_hints_json = layout_hints_json
        self.cross_refs_json = cross_refs_json
        self.data_dependencies_json = data_dependencies_json
        self.notes = notes
