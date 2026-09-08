"""
@module magnetics.field_view_basis

mag-fv (§A2, Dustin 2026-07-29): E/B FIELD VIEWS of devices for
SimSpaces — two display modes:
- vector-dispersion: vector glyphs SAMPLED through the volume,
  drawn ONLY where |field| falls inside the view's threshold bands
  (sparse dispersions, threshold-gated by construction);
- threshold-shapes: per-band USER-DEFINED math-shapes (sphere/box/
  cylinder specs) with color + alpha — translucent shells the
  designer draws; the system reports HOW WELL each shape matches
  its band (precision/recall fit metrics), never pretends the
  shape IS the field.

FieldViewGroup = the alternation ask: named ordered sets of views
so the UI cycles which field flow of a device is shown (B-flow vs
E-flow vs flux paths).

Source honesty (the watermark travels on every payload):
analytic closed forms (exact, available immediately) |
reluctance-solve (per-element flux tubes along the circuit/layout
paths — 1D-per-path, no off-path field claimed) | fem-2d (REFUSED
in v1: field-map export from the fem engine is the named
follow-up).

@consumers magnetics.custom.field_views, magnetics.magnet_api,
polariServer (registration + seed)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/field_view/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from magnetics.objects.field_view._shared import DISPLAY_MODES, FIELD_KINDS, SEED_FIELD_BANDS, SEED_FIELD_GROUPS, SEED_FIELD_VIEWS, SOURCE_KINDS  # noqa: F401
from magnetics.objects.field_view.FieldViewDefinition import FieldViewDefinition  # noqa: F401
from magnetics.objects.field_view.FieldThresholdBand import FieldThresholdBand  # noqa: F401
from magnetics.objects.field_view.FieldViewGroup import FieldViewGroup  # noqa: F401
