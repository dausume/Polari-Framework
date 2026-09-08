"""
@module cntfet.cnt_characteristics_basis

fv-3 (FET_VIEWS_PLAN §1): the FET-CHARACTERISTIC registry — "select
FET characteristics and get appropriate views and description of them
and what they mean for the performance of a FET" (Dustin 2026-08-27).

Each characteristic is a ROW (FETCharacteristic): the physics
description, the performance meaning, the governing equation, the
regimes / states / transport nodes it touches, the ScoreTerms it
feeds, and an ORDERED list of VIEWS — each view names a seeded
GraphDefinition (or an API panel, or a sim-space scene) and a
device-relative dataPath template, plus WHY that view is the one to
look at. Nothing here renders: the explorer (fv-5) and the per-device
detail page resolve `{device}` and hand the paths to the existing
named-graph-panel / api-structured-panel / sim-space components
(report views carry `pick` / `hideKeys` so no JSON reaches the
screen).

Honesty: a view whose graph is not (yet) seeded on this node is
reported `status: 'unbuilt'` with the phase that owns it — a
characteristic never silently loses a view.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/device/{name}/characteristics,
    …/characteristic/{key})
  - cntfet.custom.cnt_compare (detail page seeds, fv-5)
  - polariServer (FETCharacteristic registration + seeds)
  - cntfet.cntfet_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_characteristics/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.objects.cnt_characteristics._shared import CATEGORY, CATEGORY_MEANING, EXPLAIN, SEED_FET_CHARACTERISTICS, _api, _apply_fp6, _c, _device_provenance, _graph, _rows, _scene, _seeded_graph_names, characteristic_detail, characteristics_index, resolve_views  # noqa: F401
from cntfet.objects.cnt_characteristics.FETCharacteristic import FETCharacteristic  # noqa: F401
