"""
@module composition.failure_modes_basis

arch-2: ONE failure-mode catalogue with TWO loci. Interface modes
live on InterfaceDefinition rows and are DELETED when a promotion
consumes the interface; bulk modes live on the part and are what
promotion buys them with (handover §1.1: promotion trades interface
failure modes for bulk ones, and spends repairability).

A mode without a governing equation names that gap loudly
(equation_ref='') — the Hertzian-contact discipline: a named gap,
never a silent skip.

@consumers composition.node_basis, composition.routing_basis,
polariServer seed passes
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/failure_modes/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit
from composition.custom.part_roles import DOMAINS  # noqa: F401 — same axis

from composition.objects.failure_modes._shared import LOCI, PROV, SEED_FAILURE_MODES  # noqa: F401
from composition.objects.failure_modes.FailureModeDefinition import FailureModeDefinition  # noqa: F401
