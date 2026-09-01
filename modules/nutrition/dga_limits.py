"""
@cross-cutting
@module nutrition.dga_limits
@tags @xc:bindings

nmp-0 — Dietary Guidelines for Americans limits + the NASEM AMDR
macro envelopes, as plain cited data (no treeObject yet: nmp-1's
PersonThresholds engine consumes these to derive per-person
min/target/max rows; keeping them as data until then avoids a class
nothing reads).

EDITION-TAGGED (the plan's rule): these are the 2020-2025 values.
The 2025-2030 edition exists (released Dec 2025) — when its numeric
limits are transcribed, they join as a second edition, they do not
overwrite this one.

@consumers
  - nmp-1 PersonThresholds derivation (planned)
  - nutrition.selftest_data (structure + spot values)
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-0/§nmp-1
"""

DGA_EDITION = '2020-2025'
DGA_SOURCE = ('Dietary Guidelines for Americans 2020-2025, '
              'dietaryguidelines.gov (public domain); '
              'transcribed 2026-08-20')

# Population-level intake LIMITS (the "less of" rules). basis:
#   'fraction_of_kcal' — share of the day's calories
#   'mg_per_day'       — absolute daily amount
DGA_LIMITS = [
    {'name': 'added-sugar-share', 'nutrient': 'added-sugar',
     'limit': 0.10, 'basis': 'fraction_of_kcal', 'applies': 'ages 2+',
     'direction': 'max',
     'note': 'less than 10% of calories from ADDED sugars '
             '(not naturally occurring ones)'},
    {'name': 'saturated-fat-share', 'nutrient': 'saturated-fat',
     'limit': 0.10, 'basis': 'fraction_of_kcal', 'applies': 'ages 2+',
     'direction': 'max',
     'note': 'less than 10% of calories from saturated fat'},
    {'name': 'sodium-cdrr', 'nutrient': 'sodium',
     'limit': 2300.0, 'basis': 'mg_per_day', 'applies': 'ages 14+',
     'direction': 'max',
     'note': 'the NASEM 2019 CDRR the DGA adopts; younger-age '
             'values not transcribed (child bands are a named gap)'},
]

# NASEM Acceptable Macronutrient Distribution Ranges (adults 19+),
# fractions of daily kcal. Children's AMDRs differ — named gap.
AMDR = [
    {'nutrient': 'carbohydrate', 'min_fraction': 0.45,
     'max_fraction': 0.65},
    {'nutrient': 'healthy-fat', 'min_fraction': 0.20,
     'max_fraction': 0.35},
    {'nutrient': 'protein', 'min_fraction': 0.10,
     'max_fraction': 0.35},
]
AMDR_SOURCE = ('NASEM Dietary Reference Intakes: Energy, '
               'Carbohydrate, Fiber, Fat, Fatty Acids (2005); '
               'adults 19+')

# Fiber has NO UL and no RDA — the DGA/NASEM daily value is an AI of
# 14 g per 1000 kcal. nut-1 does not carry fiber as a nutrient yet;
# nmp-2's tolerance table is where fiber thresholds land. Recorded
# here so the number and its shape are not lost.
FIBER_AI_G_PER_1000_KCAL = 14.0
