"""
@module computers.objects.computers.ComputerAssemblyDefinition

Row class ComputerAssemblyDefinition of the computers module — one class per file (design §7), split
from computers_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ComputerAssemblyDefinition(treeObject):
    """A named computer assembly over one build's parts list."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('assembly-xeon-6338n').
        name: str = '',
        display_name: str = '',
        # The ComputerBuildDefinition this assembly realizes.
        build_ref: str = '',
        # Optional composition splice points (empty until the
        # materialization phase lands).
        archetype_ref: str = '',
        node_ref: str = '',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.build_ref = build_ref
        self.archetype_ref = archetype_ref
        self.node_ref = node_ref
        self.published = published
        self.is_prior = is_prior
        self.notes = notes
