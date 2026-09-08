"""
@module reticulum.meshsim_basis

MESH SIMULATION (ret-1e, plan §5p, Dustin 2026-08-13): plan an
isle-mesh with KNOWN devices across a map before anyone buys
hardware or walks a field.

⚠ THE STANDING DISCLAIMER, carried on every result:
TERRAIN IS NOT ACCOUNTED FOR YET. v1 predicts on ASSUMED FLAT
TERRAIN (or anchors on measured rows); elevation/terrain modes exist
in the vocabulary and REFUSE — deliberately deferred, and we say so
rather than pretend.

What it computes, all assumptions listed in the result:
  - node SPACING for max spread with the smallest node count (hex
    packing at a safety-margined range),
  - per-node RELAY ALLOWANCE for a target per-peer bandwidth across
    the whole mesh at a given size,
  - per-scenario BEARER budgets (lora-only / halow-only / combos /
    +HAM broadcast / CONFINED variants like wifi-only-mesh-app-
    broadcasting so lighthouse traffic never crowds LoRa transport),
  - per-app SPREAD allowances: max hops, max distance, or a boundary
    SHAPE that derives max hops per direction,
  - INTERFERENCE suspicions from irregular reach (sectors whose
    measured reach falls far short of prediction while others don't).

Pure functions over plain dicts + three rows (scenario / node /
result snapshot). Coordinates are LOCAL METERS (x east, y north) in
v1 — geodesy is part of the terrain feature we are not pretending
to have.

@consumers reticulum.reticulum_api (/api/reticulum/meshsim)
@see modules/reticulum/device_catalog_basis.py (the known devices),
     reticulum_basis.py (measured rows), plan §5p
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/meshsim/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import math
from objectTreeDecorators import treeObject, treeObjectInit

from reticulum.objects.meshsim._shared import PROPAGATION_MODE_VALUES, SCENARIO_BEARER_SETS, TERRAIN_DISCLAIMER, _IMPLEMENTED_MODES, _distance_to_boundary, _point_in_ring, _ring_of, flat_range_m, hops_toward, interference_suspicions, mode_supported, relay_allowance, spacing_plan, spread_allows  # noqa: F401
from reticulum.objects.meshsim.MeshSimScenario import MeshSimScenario  # noqa: F401
from reticulum.objects.meshsim.MeshSimNode import MeshSimNode  # noqa: F401
from reticulum.objects.meshsim.MeshSimResult import MeshSimResult  # noqa: F401
