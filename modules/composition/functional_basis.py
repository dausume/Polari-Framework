"""
@module composition.functional_basis

arch-3: the EBOM/MBOM split (PART_COMPOSITION_PRACTICE_MAP §1.1).
Industry keeps two linked views and so do we:

- FunctionalPartDefinition — what the design NEEDS (one functional
  stator), carrying purpose, allocated roles and tunability. This is
  the engineering-BOM side.
- ConstructionVariantDefinition — one way of BUILDING it (simple /
  bound / layered-bound are three variants of ONE functional part,
  mag-26 requirement 1). Fill class, routing and rationale live
  here: they are manufacturing-BOM facts.

"Tunable toward a purpose" is ALLOCATION-side (handover §5.4): it is
a property of the functional slot in a design, not of the casting —
so it lives on the functional row, never on the node.

@consumers polariServer seed passes, composition.composition_seed,
composition.composition_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/functional/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from composition.custom.data_refs import resolve_named, rows
from composition.custom.fill_models import FILL_CLASSES, fill_for_class
from composition.node_basis import derive_level

from composition.objects.functional._shared import variant_report, variants_of  # noqa: F401
from composition.objects.functional.FunctionalPartDefinition import FunctionalPartDefinition  # noqa: F401
from composition.objects.functional.ConstructionVariantDefinition import ConstructionVariantDefinition  # noqa: F401
