"""
@module supplychain.objects.chain.SupplyFlow

Row class SupplyFlow of the supplychain module — one class per file (design §7), split
from chain_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SupplyFlow(treeObject):
    """A directed resource flow between nodes (or to harvest)."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key.
        name: str = '',
        # Producing SupplyNode name.
        from_node: str = '',
        # Consuming SupplyNode name, or 'harvest' (leaves the system).
        to_node: str = 'harvest',
        resource: str = '',
        kind: str = 'material',
        rate_per_year: float = 0.0,
        unit: str = 'g',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.from_node = from_node
        self.to_node = to_node
        self.resource = resource
        self.kind = kind
        self.rate_per_year = rate_per_year
        self.unit = unit
        self.provenance_id = provenance_id
        self.notes = notes
