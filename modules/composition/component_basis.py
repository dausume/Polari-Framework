"""
@module composition.component_basis

arch-2: the PART COMPONENT — a single-material element, the bottom
of the separability hierarchy (PART_COMPOSITION_HANDOVER §1: one
material row, no internal interfaces).

Two hard-won attribute splits are fields here, not notes:
- COATING is distinct from material, with its own thickness, because
  build adds to diameter and therefore costs window area as a SQUARE
  (handover §3.4 — cotton covering was ruled out by arithmetic).
- MATERIAL CONDITION (temper) is a key, not prose: drawn-then-
  annealed copper is a different property set from as-cast under the
  same base material (practice map §1.2 — C11000-H02 vs O60).
  '' means UNSTATED, which screens like any missing datum.

@consumers polariServer seed passes, composition.node_basis,
composition.composition_seed
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/component/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from composition.objects.component.PartComponentDefinition import PartComponentDefinition  # noqa: F401
