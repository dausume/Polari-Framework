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
  - supplychain.custom.chain_analysis
@see nutrition/ aquaponics/ tanks/ microalgae/ biomining/ waxsupply/
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/chain/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from supplychain.objects.chain._shared import NODE_MODULES, RESOURCE_KINDS  # noqa: F401
from supplychain.objects.chain.SupplyNode import SupplyNode  # noqa: F401
from supplychain.objects.chain.SupplyFlow import SupplyFlow  # noqa: F401
from supplychain.objects.chain.SupplyChainDefinition import SupplyChainDefinition  # noqa: F401
