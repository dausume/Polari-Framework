"""
@cross-cutting
@module aquaponics.plant_stress_basis
@tags @xc:bindings

Plant-growth-sim phase 7 (2026-07-15) — Dustin, verbatim: "these
equations can vary based on different kinds of stress conditions...
these should be interconnected matrix equations that define
multivariable spaces based on atmospheric and soil and water inputs."

Two tiers, so every species gets a real answer on day one without
anyone hand-authoring an equation, while still giving the genuine
multivariable matrix-equation power Dustin asked for wherever it's
worth the authoring effort:

  TIER A — a `StressResponseCurve` row's min/optimalLow/optimalHigh/
  max fields define a standard trapezoidal response over ONE real
  scalar field (a well-established crop-model pattern — DSSAT/APSIM
  use the same shape): 0 below min, ramps to 1 across [min,
  optimalLow], holds 1 across [optimalLow, optimalHigh], ramps back to
  0 across [optimalHigh, max]. This is the DEFAULT — always available,
  no equation authoring required.

  TIER B — a curve can instead set `equation_ref` (a
  matrices.MatrixEquationDefinition name) + `input_bindings_json`
  (symbol -> {source, field} — source is 'atmosphere'/'water'/'soil',
  field is a real attribute on that class, e.g. AtmosphereDefinition.
  co2_ppm). The REAL equation engine already built for the no-code
  matrix-equation editor (matrices/matrix_equation_executor.py)
  evaluates it — genuinely multivariable/interconnected, not
  reinvented here. Falls back to Tier A if unset.

Curves are keyed by (plant_name, part, stress_type) — Dustin's "vary
based on the plant part" applies here too: sweet-basil's ROOT curves
read water/soil fields (it touches the root zone), its LEAF/STEM
curves read atmosphere fields (it touches the air) — never the same
equation forced onto every part.

Combining stress types: Liebig's Law of the Minimum (a standard
plant-physiology principle, and how real crop models combine
co-limiting factors) — growth is limited by the SINGLE scarcest
factor, not the product of all of them. `combined_stress_factor()`
takes `min()` across whatever stress types have curves for that part,
never a product (a product punishes several mildly-suboptimal-but-
not-limiting factors far more harshly than reality does).

@consumers
  - aquaponics.plant_growth_normalized_basis.advance_growth (the per-part
    RATE multiplier, replacing the old manual water/soil factors when
    no explicit override is given)
  - aquaponics.plant_growth_normalized_api (the diagnostic sweep
    endpoint)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 7
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/plant_stress/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from aquaponics.objects.plant_stress._shared import SOURCE_TABLES, STRESS_TYPES, STRESS_TYPE_FIELDS, _named, _rows, combined_stress_factor, evaluate_curve, part_stress_factors, sweep_curve, trapezoid_factor  # noqa: F401
from aquaponics.objects.plant_stress.StressResponseCurve import StressResponseCurve  # noqa: F401
