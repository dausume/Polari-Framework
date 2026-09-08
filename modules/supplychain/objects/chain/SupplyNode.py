"""
@module supplychain.objects.chain.SupplyNode

Row class SupplyNode of the supplychain module — one class per file (design §7), split
from chain_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SupplyNode(treeObject):
    """One producer/processor in the chain + its declared throughput."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('nanno-reactor-node').
        name: str = '',
        display_name: str = '',
        # NODE_MODULES entry.
        module: str = 'aquaponics',
        # The system this node stands for (a name in that module).
        system_ref: str = '',
        # Resources OUT (JSON list of {resource, kind, ratePerYear,
        # unit}) — the node's production, a flagged prior until live-
        # resolved.
        outputs_json: str = '[]',
        # Resources IN the node needs (JSON list of {resource, kind,
        # ratePerYear, unit}) — for the dependency check.
        inputs_json: str = '[]',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.module = module
        self.system_ref = system_ref
        self.outputs_json = outputs_json
        self.inputs_json = inputs_json
        self.provenance_id = provenance_id
        self.notes = notes
