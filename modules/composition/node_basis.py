"""
@module composition.node_basis

arch-2: the COMPOSITION TREE, with LEVEL DERIVED — never stamped.

The handover's distinguishing question at every boundary is
SEPARABILITY, and it is testable from structure alone:

  no members, one material            -> component
  interfaces all non-separable       -> part
  interfaces all separable           -> assembly
  mixed                              -> part-with-separable-sub-parts
                                        (mag-26 layered stator: one
                                        object, two regimes)

Ownership does the nesting work: a promoted part's internal
interfaces belong to IT, so a movement one level up sees only its
own separable boundaries and derives 'assembly' — no special case.

A node may DECLARE an intended level; declared != derived is a
REFUSAL naming the interface rows that decide it (same discipline as
viability: derived, and disagreement is information). Two or more
members with NO interface rows is 'I do not know' — stated, with the
member pairs that need rows.

@consumers polariServer seed passes, composition.composition_seed,
composition.composition_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/node/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from composition.custom.data_refs import resolve_named, rows

from composition.objects.node._shared import DECLARED_LEVELS, MEMBER_KINDS, _is_nested, _loads, composition_report, derive_level, owned_interfaces  # noqa: F401
from composition.objects.node.CompositionNode import CompositionNode  # noqa: F401
