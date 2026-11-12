"""
@module mech.mech_catalog_basis

mxc-1 (MECH_FREECAD_INTERCHANGE_PLAN §3.1, §3.2): THE STANDARD-PARTS
CATALOGUE AS DATA. A family is one standard or geometric archetype
(ISO 4762; a 20-series T-slot profile; a Gridfinity bin) with its
dimension table keyed by size, a length rule, and the FEATURE
TEMPLATES every variant exposes. A variant is one orderable size with
the table resolved to numbers. A feature is one place on a part where
something can land — a thread, a slot, a bore, a face, a grid cell —
with a compatibility KEY and a ROLE, so that assembly validity is a
lookup (key equal, roles pair) and never code per family.

Every family names the DimensionSource its numbers came from (upstream
file, commit, sha256, licence in the publisher's words) — D-mxc-10 makes
that row a sibling of meshassets' MeshAssetSource, same licence field
names. Geometry is regenerated from parameters (D-mxc-3): `generator`
is '' until mxc-3b writes the MathShape forms, and the catalogue says so.

Honesty pinned here so it travels on every payload:
- dimensions are TRANSCRIBED standard tables (cited), not measured;
- bracketed sizes "(M14)" are the standard's non-preferred sizes;
- the drawer-slide rated load is a KNOB until a datasheet is cited;
- hand-entered rows (rod, TR8x4, bore-8 pulleys, lid) say so in notes.

@consumers mech.custom.compatibility, mech.custom.catalog_import,
mech.mech_catalog_selftest, polariServer
"""
# INDEX (design §7): the classes live one-per-file under objects/catalog/;
# this file re-exports them (imports keep working) and holds what they share.

from objectTreeDecorators import treeObject, treeObjectInit  # noqa: F401

from mech.objects.catalog._shared import (  # noqa: F401
    BASES, CATEGORIES, DOF_AXES, FEATURE_KINDS, FEATURE_ROLES,
    LENGTH_RULE_KINDS, VARIANT_AXES,
)
from mech.objects.catalog.DimensionSource import DimensionSource  # noqa: F401
from mech.objects.catalog.MechPartFamily import MechPartFamily  # noqa: F401
from mech.objects.catalog.MechPartVariant import MechPartVariant  # noqa: F401
from mech.objects.catalog.MechFeature import MechFeature  # noqa: F401
