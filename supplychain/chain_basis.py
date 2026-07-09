"""
@cross-cutting
@module supplychain.chain_basis
@tags @xc:bindings

Bio supply-chain accounting (chain-1) — one ledger that CHAINS every
system we've built and accounts for its outputs: bio-derivable
MATERIALS, FOOD, and CARBON (sinks). Own module + own data
(framework-core only). Nodes declare their throughput (soft-linked to the
producing system by name; live yield resolution is a later step), flows
connect producers to consumers/harvest, and the analysis rolls it up.

Three treeObjects (auto-CRUDE + persisted — object-coherence):

  SupplyNode        one producer/processor — its module + system, and
                    the resources it OUTPUTS (and consumes) per period.
  SupplyFlow        a directed resource flow: from a node to another
                    node or to 'harvest' (leaves the system).
  SupplyChainDefinition  binds nodes + flows into one accountable chain.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - supplychain.chain_analysis
@see nutrition/ aquaponics/ tanks/ microalgae/ biomining/ waxsupply/
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: What a resource IS, for the ledger's three-way rollup.
RESOURCE_KINDS = ('material', 'food', 'carbon', 'nutrient', 'energy')

#: Which module/system family a node represents.
NODE_MODULES = ('aquaponics', 'tanks', 'microalgae', 'biomining',
                'nutrition', 'waxsupply', 'garden', 'external-feedstock')


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
