"""
@module techtree.objects.techtree.TechDependencyEdge

Row class TechDependencyEdge of the techtree module — one class per file (design §7), split
from techtree_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TechDependencyEdge(treeObject):
    """tech_node DEPENDS-ON depends_on_tech, derived from
    TechNode.depends_on_json by sync_edges. Carries the same
    transient/primary designation as ModuleDependencyEdge (tt-1):
    a technology needed by N>1 others is solid under one primary
    dependent and a dashed transient copy under the rest."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<tech_node>-><depends_on_tech>'.
        name: str = '',
        tree_name: str = '',
        tech_node: str = '',
        depends_on_tech: str = '',
        is_primary: bool = False,
        is_transient: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.tree_name = tree_name
        self.tech_node = tech_node
        self.depends_on_tech = depends_on_tech
        self.is_primary = is_primary
        self.is_transient = is_transient
        self.notes = notes
