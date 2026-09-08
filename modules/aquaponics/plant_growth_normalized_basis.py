"""
@cross-cutting
@module aquaponics.plant_growth_normalized_basis
@tags @xc:bindings

Plant-growth-sim phase 1 (2026-07-15) — Dustin's model, built up across
several rounds of direction in the same session, verbatim intent kept
here since it's load-bearing for every function below:

  1. Branching geometry needs SPECIES-LEVEL reference context: max root
     depth "in free soil", "usual root density... in free soil", "how
     root thickness changes with distance from plant core as a
     function of growth", max root volume/density at full growth, max
     stem/canopy volume at full growth "in free soil with infinite
     soil (no boundaries)".
  2. "Instead of age we have normalized growth as the measure of
     'age'" — conditions (water/soil) control how FAST real time
     reaches full growth; a safety ceiling ("height and width of the
     tallest tree doubled or something") keeps a genuinely-unbounded
     species from breaking computation.
  3. Two explicit named stages: "Free Soil Constants" first,
     "Constrained Limits" second — and whether the plant SURVIVES
     stabilizing growth when it hits those limits (not just a cosmetic
     dwarf estimate).
  4. Geometry should be an "animation bones" style graph — interconnected
     VECTORS, not a flat scalar profile — so the plant/root/organ
     definitions WRAP the vectors (a math foundation real enough to
     support reverse-mapping from real plant scans back into
     simulation parameters later). Built in plant_skeleton.py, on TOP
     of this file's state.
  5. "Defining vector generation and vector growth per unit time based
     on the plant part the vector defines... equations that define the
     SHAPE of the plant... and equations that GENERATE AND GROW those
     vectors over time" — two distinct equation families, both
     PART-SPECIFIC (a root vector's shape/growth equations are not a
     stem vector's). This is why growth here tracks PER PART (reusing
     PlantGrowthModel's already-per-part growth_rate, aqp-8's own
     field, rather than inventing a second whole-plant rate) instead
     of one global scalar.

Two explicit stages (point 3 above):

  free_soil_constants()   STAGE 1 — the species' UNCONFINED reference
                          maximums, PER PART where the data is
                          per-part (root envelope + taper + density,
                          per-part growth rates + max volumes) and
                          whole-plant where it genuinely is
                          (mature_height_mm/mature_canopy_mm) — read
                          straight off EXISTING rows (RootSystemModel,
                          OrganModel, PlantPart, PlantGrowthModel,
                          PlantDefinition), not a new source of truth,
                          plus the honesty safety ceiling
                          (SANE_MAX_LINEAR_MM).
  constrained_limits()    STAGE 2 — free_soil_constants() run through
                          THIS pot's actual geometry, reusing
                          plant_morphology.custom.morphology_analysis.
                          confinement_assessment() unchanged (it
                          already computes the dwarf factor + the
                          survives/doesn't-survive verdict — this
                          module reframes it as each part's
                          normalized-growth ceiling, it does not
                          reinvent the survival math).

`PotPlanting` is the missing INSTANCE state: everything above this
file was species-level catalog or a one-shot calculation; nothing
tracked "this specific plant, in this pot, currently this far along,
PER PART." `partGrowth = {partName: normalizedGrowth}` is that state,
advanced by advance_growth() — each part's own logistic climb, RATE
set by real conditions × that part's OWN PlantGrowthModel.growth_rate
each tick, CEILING set by constrained_limits() — conditions control
speed, confinement controls how far any part can ever get. These are
deliberately different knobs, never collapsed into one number.

@consumers
  - aquaponics.custom.plant_skeleton (the bone/vector graph generator — the
    actual geometry layer; this file is its state + constraint input)
  - aquaponics.plant_growth_normalized_api (not yet built)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 6
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/plant_growth_normalized/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import math
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit

from aquaponics.objects.plant_growth_normalized._shared import GROWTH_SEED_EPSILON, ORGAN_TO_PART, REFERENCE_SATURATING_PPFD, SANE_MAX_LINEAR_MM, SEED_RESERVE_FLOOR, _clamp_linear_mm, _f, _named, _part_growth, _rows, _size_fraction, advance_growth, closed_form_logistic, constrained_limits, current_canopy_profile, current_root_profile, free_soil_constants, organ_part_name, overall_normalized_growth, part_normalized_growth, transport_factor  # noqa: F401
from aquaponics.objects.plant_growth_normalized.PotPlanting import PotPlanting  # noqa: F401
