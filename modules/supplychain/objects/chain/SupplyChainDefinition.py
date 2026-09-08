"""
@module supplychain.objects.chain.SupplyChainDefinition

Row class SupplyChainDefinition of the supplychain module — one class per file (design §7), split
from chain_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SupplyChainDefinition(treeObject):
    """A named set of nodes + flows accounted as one chain."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # JSON list of SupplyNode names in this chain.
        node_names_json: str = '[]',
        # JSON list of SupplyFlow names in this chain.
        flow_names_json: str = '[]',
        # Persisted rollup snapshot (JSON) for scoring.
        ledger_result_json: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.node_names_json = node_names_json
        self.flow_names_json = flow_names_json
        self.ledger_result_json = ledger_result_json
        self.provenance_id = provenance_id
        self.notes = notes
