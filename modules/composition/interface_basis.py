"""
@module composition.interface_basis

arch-2: the INTERFACE as a first-class row — the load-bearing idea
of the whole schema. mag-26 proved promotion attaches to a NAMED
INTERFACE SET, never to a whole assembly, so interfaces need
identity, ownership, and their own evidence level (practice: ICDs,
CAD mates, the FMEA boundary — PART_COMPOSITION_PRACTICE_MAP §2).

`designed_separable` is THE level-deciding bit: a node whose
interfaces are all non-separable is a part; all separable, an
assembly; mixed, a part with separable sub-parts (the layered
stator — one object, two separability regimes).

@consumers composition.node_basis, composition.routing_basis,
polariServer seed passes
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/interface/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from composition.objects.interface._shared import DOF_AXES, RETENTION_SCHEMES  # noqa: F401
from composition.objects.interface.InterfaceDefinition import InterfaceDefinition  # noqa: F401
