"""
@cross-cutting
@module aquaponics.pot_basis
@tags @xc:bindings

Self-watering pot GEOMETRY as first-class objects (aqp-1). Dustin
2026-07-08: a self-watering pot, ceramic or geopolymer (waterproof
variant), with at least two side holes — higher = water INPUT, lower =
water OUTPUT, on opposite sides; pot size + slot diameter/height/number
tunable, slot angles tunable but LIMITED so water still flows through
by GRAVITY.

Two classes, both auto-CRUDE + persisted (object-coherence — every
tunable is a knob on a row, no hidden geometry):

  PotDefinition — the parametric vessel: size, wall/base thickness,
                  shape, and the material it is made of (a
                  MaterialsScienceMaterial, ceramic/geopolymer).
  PotHole       — one bored slot, a child row keyed to its pot: kind
                  (input/output), diameter, height up the wall,
                  azimuth (which side), and bore angle (clamped so
                  outputs stay gravity-fed).

The geometry MATH (validation, the gravity constraint, hole
generation) lives in pot_geometry.py; materials in
pot_materials_seed.py.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - aquaponics.custom.pot_geometry / aquaponics.pot_api
@see /AQUAPONICS_MODULE_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/pot/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from aquaponics.objects.pot._shared import HOLE_KINDS, IDEAL_SIDE_SEPARATION_DEG, MAX_ABS_ANGLE_DEG, MAX_WALL_THICKNESS_FRACTION, MIN_BASE_THICKNESS_MM, MIN_HOLE_DIAMETER_MM, MIN_OUTPUT_DOWNHILL_DEG, MIN_SIDE_SEPARATION_DEG, MIN_WALL_THICKNESS_MM, POT_SHAPES, RECOMMENDED_OUTPUT_DOWNHILL_DEG  # noqa: F401
from aquaponics.objects.pot.PotDefinition import PotDefinition  # noqa: F401
from aquaponics.objects.pot.PotHole import PotHole  # noqa: F401
