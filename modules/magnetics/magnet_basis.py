"""
@module magnetics.magnet_basis

Section A of MAGNETIC_MATERIALS_PLAN: the material option catalog
(§1c) with its REALIZATION LADDER, the functional role taxonomy
(mag-2r) whose viability is DERIVED from property rows via predicate
knobs, and the theoretical-powder designer rows (mag-2t).

Honesty spine:
- realization_level is EARNED, never declared: 'theoretical' ->
  'literature-demonstrated' -> 'recipe-seeded' -> 'made-and-measured';
  buyable_cited is the ORTHOGONAL flag derived live from supplychain
  PriceCitation rows, never stored here.
- Gates (magnet_analysis.gates_for): SIMULATION open at every level
  (watermark travels), COSTING needs buyable-cited OR recipe-seeded,
  BUSINESS/planner use needs made-and-measured.
- Role viability is derived (predicates over property values); missing
  data = 'unassessed' with the measurement ask, never assumed viable.
  Overrides are rows-with-reasons, not silent stamps.
- Property VALUES carry per-value provenance
  ('measured'|'vendor'|'literature-est'|'theoretical').

@consumers polariServer seed_pairs, magnetics.custom.magnet_analysis,
magnetics.magnet_api
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/magnet/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from magnetics.objects.magnet._shared import MATERIAL_FORMS, OPTION_FAMILIES, REALIZATION_LEVELS  # noqa: F401
from magnetics.objects.magnet.MaterialUseRole import MaterialUseRole  # noqa: F401
from magnetics.objects.magnet.MagneticMaterialOption import MagneticMaterialOption  # noqa: F401
from magnetics.objects.magnet.MagneticPowderDefinition import MagneticPowderDefinition  # noqa: F401
