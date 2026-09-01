"""
@cross-cutting
@module nutrition.dri_seed
@tags @xc:bindings

nmp-0 — the DRI/UL transcription: NASEM Dietary Reference Intakes for
every nutrient in the nut-1 vocabulary, per life-stage band, with EAR
+ RDA/AI + UL per row. NASEM publishes NO machine-readable format —
this is the one-time transcription the plan calls for, versioned and
cited here, consumed as NutrientReference rows.

Coverage (deliberate): adults 19+ (the four DRI bands) + pregnancy +
lactation (19-50, sub-banded where NASEM sub-bands). CHILD BANDS
(0-18) ARE A NAMED GAP — not transcribed yet; the profiler falls back
to its nutrient-wide fallback for under-19 ages. Say so in any UI.

Band semantics: closed bands sharing integer edges (19-31, 31-51,
51-71, 71-120), seeded HIGHER-BAND-FIRST so the person_analysis
first-match rule resolves an exact boundary age (31, 51, 71) to the
band NASEM assigns it to (31 belongs to "31-50").

Supersedes the nut-1 adult-only reference table (single 19-120 band):
nutrient_seed re-exports THIS table as SEED_NUTRIENT_REFERENCES.
Fresh DBs only see these rows; a pre-nmp-0 DB would keep its old
wide-band rows by name — none exist (full purge 2026-08-17).

Every value transcribed VERBATIM from the NASEM DRI summary tables /
NIH ODS fact sheets. value_type says what the number IS:
  'rda'   firm Recommended Dietary Allowance
  'ai'    Adequate Intake (no EAR exists by definition)
  'prior' a literature convention with NO official DRI (flagged)
  'none'  marker row (computed elsewhere / AMDR-only)

is_prior keeps the nut-1 convention (False only for firm RDA rows —
person_analysis flags priors from it). Upsert caveat, stated
honestly: the seed-upsert path treats is_prior=False as
"human-customized, never touch", so firm-RDA rows are
insert-once-frozen — a future DRI edition bump converges every AI/
prior row automatically but firm rows only on a fresh DB (or a
deliberate migration). Acceptable now: DRI revisions are rare and
edition is carried per row.

@consumers
  - nutrition.nutrient_seed (re-export), polariServer seed pairs
  - nutrition.person_analysis (band matcher skips life_stage rows)
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-0
"""

JURISDICTION = 'US-NASEM'
EDITION = ('NASEM DRI summary tables; macronutrients 2005, '
           'vitamin D + calcium 2011, sodium + potassium 2019; '
           'transcribed 2026-08-20 from NASEM/NIH-ODS tables')

# (nutrient, sex, age_min, age_max, life_stage, ear, value,
#  value_type, ul, note)
# Bands DESCENDING within a nutrient (boundary rule above). ul=0 means
# no UL established — never "unlimited", just honestly absent.
_ROWS = [
    # ── vitamins ─────────────────────────────────────────
    ('vitamin-a', 'male', 19, 120, '', 625, 900, 'rda', 3000,
     'ug RAE; UL is for preformed retinol'),
    ('vitamin-a', 'female', 19, 120, '', 500, 700, 'rda', 3000,
     'ug RAE; UL is for preformed retinol'),
    ('vitamin-a', 'female', 19, 50, 'pregnancy', 550, 770, 'rda', 3000, ''),
    ('vitamin-a', 'female', 19, 50, 'lactation', 900, 1300, 'rda', 3000, ''),

    ('vitamin-b1', 'male', 19, 120, '', 1.0, 1.2, 'rda', 0, ''),
    ('vitamin-b1', 'female', 19, 120, '', 0.9, 1.1, 'rda', 0, ''),
    ('vitamin-b1', 'female', 19, 50, 'pregnancy', 1.2, 1.4, 'rda', 0, ''),
    ('vitamin-b1', 'female', 19, 50, 'lactation', 1.2, 1.4, 'rda', 0, ''),

    ('vitamin-b2', 'male', 19, 120, '', 1.1, 1.3, 'rda', 0, ''),
    ('vitamin-b2', 'female', 19, 120, '', 0.9, 1.1, 'rda', 0, ''),
    ('vitamin-b2', 'female', 19, 50, 'pregnancy', 1.2, 1.4, 'rda', 0, ''),
    ('vitamin-b2', 'female', 19, 50, 'lactation', 1.3, 1.6, 'rda', 0, ''),

    ('vitamin-b3', 'male', 19, 120, '', 12, 16, 'rda', 35,
     'mg NE; UL is for supplemental nicotinic acid'),
    ('vitamin-b3', 'female', 19, 120, '', 11, 14, 'rda', 35,
     'mg NE; UL is for supplemental nicotinic acid'),
    ('vitamin-b3', 'female', 19, 50, 'pregnancy', 14, 18, 'rda', 35, ''),
    ('vitamin-b3', 'female', 19, 50, 'lactation', 13, 17, 'rda', 35, ''),

    ('vitamin-b5', 'any', 19, 120, '', 0, 5, 'ai', 0, ''),
    ('vitamin-b5', 'female', 19, 50, 'pregnancy', 0, 6, 'ai', 0, ''),
    ('vitamin-b5', 'female', 19, 50, 'lactation', 0, 7, 'ai', 0, ''),

    ('vitamin-b6', 'male', 51, 120, '', 1.4, 1.7, 'rda', 100, ''),
    ('vitamin-b6', 'male', 19, 51, '', 1.1, 1.3, 'rda', 100, ''),
    ('vitamin-b6', 'female', 51, 120, '', 1.3, 1.5, 'rda', 100, ''),
    ('vitamin-b6', 'female', 19, 51, '', 1.1, 1.3, 'rda', 100, ''),
    ('vitamin-b6', 'female', 19, 50, 'pregnancy', 1.6, 1.9, 'rda', 100, ''),
    ('vitamin-b6', 'female', 19, 50, 'lactation', 1.7, 2.0, 'rda', 100, ''),

    ('vitamin-b7', 'any', 19, 120, '', 0, 30, 'ai', 0, ''),
    ('vitamin-b7', 'female', 19, 50, 'pregnancy', 0, 30, 'ai', 0, ''),
    ('vitamin-b7', 'female', 19, 50, 'lactation', 0, 35, 'ai', 0, ''),

    ('vitamin-b9', 'any', 19, 120, '', 320, 400, 'rda', 1000,
     'ug DFE; UL is for synthetic folic acid'),
    ('vitamin-b9', 'female', 19, 50, 'pregnancy', 520, 600, 'rda', 1000, ''),
    ('vitamin-b9', 'female', 19, 50, 'lactation', 450, 500, 'rda', 1000, ''),

    ('vitamin-b12', 'any', 19, 120, '', 2.0, 2.4, 'rda', 0, ''),
    ('vitamin-b12', 'female', 19, 50, 'pregnancy', 2.2, 2.6, 'rda', 0, ''),
    ('vitamin-b12', 'female', 19, 50, 'lactation', 2.4, 2.8, 'rda', 0, ''),

    ('vitamin-c', 'male', 19, 120, '', 75, 90, 'rda', 2000,
     'smokers need +35 mg/day (ODS)'),
    ('vitamin-c', 'female', 19, 120, '', 60, 75, 'rda', 2000,
     'smokers need +35 mg/day (ODS)'),
    ('vitamin-c', 'female', 19, 50, 'pregnancy', 70, 85, 'rda', 2000, ''),
    ('vitamin-c', 'female', 19, 50, 'lactation', 100, 120, 'rda', 2000, ''),

    ('vitamin-d', 'any', 71, 120, '', 10, 20, 'rda', 100, 'NASEM 2011'),
    ('vitamin-d', 'any', 19, 71, '', 10, 15, 'rda', 100, 'NASEM 2011'),
    ('vitamin-d', 'female', 19, 50, 'pregnancy', 10, 15, 'rda', 100, ''),
    ('vitamin-d', 'female', 19, 50, 'lactation', 10, 15, 'rda', 100, ''),

    ('vitamin-e', 'any', 19, 120, '', 12, 15, 'rda', 1000,
     'alpha-tocopherol; UL is for supplemental forms'),
    ('vitamin-e', 'female', 19, 50, 'pregnancy', 12, 15, 'rda', 1000, ''),
    ('vitamin-e', 'female', 19, 50, 'lactation', 16, 19, 'rda', 1000, ''),

    ('vitamin-k', 'male', 19, 120, '', 0, 120, 'ai', 0, 'phylloquinone'),
    ('vitamin-k', 'female', 19, 120, '', 0, 90, 'ai', 0, 'phylloquinone'),
    ('vitamin-k', 'female', 19, 50, 'pregnancy', 0, 90, 'ai', 0, ''),
    ('vitamin-k', 'female', 19, 50, 'lactation', 0, 90, 'ai', 0, ''),

    # ── minerals / electrolytes / trace ──────────────────
    ('iron', 'male', 19, 120, '', 6, 8, 'rda', 45, ''),
    ('iron', 'female', 51, 120, '', 5, 8, 'rda', 45, 'post-menopause band'),
    ('iron', 'female', 19, 51, '', 8.1, 18, 'rda', 45, ''),
    ('iron', 'female', 19, 50, 'pregnancy', 22, 27, 'rda', 45, ''),
    ('iron', 'female', 19, 50, 'lactation', 6.5, 9, 'rda', 45, ''),

    ('calcium', 'any', 71, 120, '', 1000, 1200, 'rda', 2000, 'NASEM 2011'),
    ('calcium', 'female', 51, 71, '', 1000, 1200, 'rda', 2000,
     'NASEM 2011'),
    ('calcium', 'male', 51, 71, '', 800, 1000, 'rda', 2000, 'NASEM 2011'),
    ('calcium', 'any', 19, 51, '', 800, 1000, 'rda', 2500, 'NASEM 2011'),
    ('calcium', 'female', 19, 50, 'pregnancy', 800, 1000, 'rda', 2500, ''),
    ('calcium', 'female', 19, 50, 'lactation', 800, 1000, 'rda', 2500, ''),

    ('magnesium', 'male', 31, 120, '', 350, 420, 'rda', 350,
     'UL applies to SUPPLEMENTAL Mg only, not food'),
    ('magnesium', 'male', 19, 31, '', 330, 400, 'rda', 350,
     'UL applies to SUPPLEMENTAL Mg only, not food'),
    ('magnesium', 'female', 31, 120, '', 265, 320, 'rda', 350,
     'UL applies to SUPPLEMENTAL Mg only, not food'),
    ('magnesium', 'female', 19, 31, '', 255, 310, 'rda', 350,
     'UL applies to SUPPLEMENTAL Mg only, not food'),
    ('magnesium', 'female', 31, 50, 'pregnancy', 300, 360, 'rda', 350, ''),
    ('magnesium', 'female', 19, 31, 'pregnancy', 290, 350, 'rda', 350, ''),
    ('magnesium', 'female', 31, 50, 'lactation', 265, 320, 'rda', 350, ''),
    ('magnesium', 'female', 19, 31, 'lactation', 255, 310, 'rda', 350, ''),

    ('omega-3', 'male', 19, 120, '', 0, 1.6, 'ai', 0, 'ALA basis'),
    ('omega-3', 'female', 19, 120, '', 0, 1.1, 'ai', 0, 'ALA basis'),
    ('omega-3', 'female', 19, 50, 'pregnancy', 0, 1.4, 'ai', 0, ''),
    ('omega-3', 'female', 19, 50, 'lactation', 0, 1.3, 'ai', 0, ''),

    ('potassium', 'male', 19, 120, '', 0, 3400, 'ai', 0, 'NASEM 2019'),
    ('potassium', 'female', 19, 120, '', 0, 2600, 'ai', 0, 'NASEM 2019'),
    ('potassium', 'female', 19, 50, 'pregnancy', 0, 2900, 'ai', 0, ''),
    ('potassium', 'female', 19, 50, 'lactation', 0, 2800, 'ai', 0, ''),

    ('sodium', 'any', 19, 120, '', 0, 1500, 'ai', 2300,
     'the max is the 2019 CDRR (chronic disease risk reduction), '
     'not a classical UL'),
    ('sodium', 'female', 19, 50, 'pregnancy', 0, 1500, 'ai', 2300,
     'CDRR, not a classical UL'),
    ('sodium', 'female', 19, 50, 'lactation', 0, 1500, 'ai', 2300,
     'CDRR, not a classical UL'),

    ('chloride', 'any', 71, 120, '', 0, 1800, 'ai', 3600, ''),
    ('chloride', 'any', 51, 71, '', 0, 2000, 'ai', 3600, ''),
    ('chloride', 'any', 19, 51, '', 0, 2300, 'ai', 3600, ''),
    ('chloride', 'female', 19, 50, 'pregnancy', 0, 2300, 'ai', 3600, ''),
    ('chloride', 'female', 19, 50, 'lactation', 0, 2300, 'ai', 3600, ''),

    ('zinc', 'male', 19, 120, '', 9.4, 11, 'rda', 40, ''),
    ('zinc', 'female', 19, 120, '', 6.8, 8, 'rda', 40, ''),
    ('zinc', 'female', 19, 50, 'pregnancy', 9.5, 11, 'rda', 40, ''),
    ('zinc', 'female', 19, 50, 'lactation', 10.4, 12, 'rda', 40, ''),

    ('selenium', 'any', 19, 120, '', 45, 55, 'rda', 400, ''),
    ('selenium', 'female', 19, 50, 'pregnancy', 49, 60, 'rda', 400, ''),
    ('selenium', 'female', 19, 50, 'lactation', 59, 70, 'rda', 400, ''),

    ('copper', 'any', 19, 120, '', 700, 900, 'rda', 10000, 'ug'),
    ('copper', 'female', 19, 50, 'pregnancy', 800, 1000, 'rda', 10000, ''),
    ('copper', 'female', 19, 50, 'lactation', 1000, 1300, 'rda', 10000, ''),

    ('manganese', 'male', 19, 120, '', 0, 2.3, 'ai', 11, ''),
    ('manganese', 'female', 19, 120, '', 0, 1.8, 'ai', 11, ''),
    ('manganese', 'female', 19, 50, 'pregnancy', 0, 2.0, 'ai', 11, ''),
    ('manganese', 'female', 19, 50, 'lactation', 0, 2.6, 'ai', 11, ''),

    ('iodine', 'any', 19, 120, '', 95, 150, 'rda', 1100, ''),
    ('iodine', 'female', 19, 50, 'pregnancy', 160, 220, 'rda', 1100, ''),
    ('iodine', 'female', 19, 50, 'lactation', 209, 290, 'rda', 1100, ''),

    ('chromium', 'male', 51, 120, '', 0, 30, 'ai', 0, ''),
    ('chromium', 'male', 19, 51, '', 0, 35, 'ai', 0, ''),
    ('chromium', 'female', 51, 120, '', 0, 20, 'ai', 0, ''),
    ('chromium', 'female', 19, 51, '', 0, 25, 'ai', 0, ''),
    ('chromium', 'female', 19, 50, 'pregnancy', 0, 30, 'ai', 0, ''),
    ('chromium', 'female', 19, 50, 'lactation', 0, 45, 'ai', 0, ''),

    ('molybdenum', 'any', 19, 120, '', 34, 45, 'rda', 2000, ''),
    ('molybdenum', 'female', 19, 50, 'pregnancy', 40, 50, 'rda', 2000, ''),
    ('molybdenum', 'female', 19, 50, 'lactation', 40, 50, 'rda', 2000, ''),

    # no official RDA/AI exists — the UL is official; the daily value
    # is the nut-1 literature prior, kept and labeled.
    ('boron', 'any', 19, 120, '', 0, 1.0, 'prior', 20,
     'no NASEM RDA/AI; 1 mg/day is a literature prior; UL is official'),
    ('silicon', 'any', 19, 120, '', 0, 25, 'prior', 0,
     'no NASEM DRI and no UL determinable; 25 mg/day is a '
     'literature prior'),

    # ── macros ───────────────────────────────────────────
    ('carbohydrate', 'any', 19, 120, '', 100, 130, 'rda', 0,
     'brain glucose basis; AMDR 45-65% kcal is the real envelope '
     '(see dga_limits)'),
    ('carbohydrate', 'female', 19, 50, 'pregnancy', 135, 175, 'rda', 0, ''),
    ('carbohydrate', 'female', 19, 50, 'lactation', 160, 210, 'rda', 0, ''),

    ('healthy-fat', 'any', 19, 120, '', 0, 65, 'prior', 0,
     'no RDA/AI for total fat; 65 g is a convention prior (~30% of '
     '2000 kcal); AMDR 20-35% kcal is the real envelope'),

    ('calories', 'any', 19, 120, '', 0, 0, 'none', 0,
     'calorie target is computed per person from BMR/TDEE (nut-3)'),
]

# protein rides per-kg body mass, so it gets explicit dict rows
# (the tuple table is flat-per-day only).
_PROTEIN_ROWS = [
    {'name': 'protein-any-19-120', 'nutrient_name': 'protein',
     'sex': 'any', 'age_min': 19.0, 'age_max': 120.0,
     'rda_per_day': 0.0, 'per_kg_body_mass': 0.8,
     'ear_per_day': 0.0, 'value_type': 'rda',
     'upper_limit_per_day': 0.0, 'life_stage': '',
     'jurisdiction': JURISDICTION, 'edition': EDITION,
     'is_prior': False, 'source': 'NASEM DRI (0.8 g/kg/day)',
     'notes': 'EAR is 0.66 g/kg/day (per-kg, not flat)',
     'provenance_id': 'nmp-0'},
    {'name': 'protein-female-pregnancy-19-50', 'nutrient_name': 'protein',
     'sex': 'female', 'age_min': 19.0, 'age_max': 50.0,
     'rda_per_day': 0.0, 'per_kg_body_mass': 1.1,
     'ear_per_day': 0.0, 'value_type': 'rda',
     'upper_limit_per_day': 0.0, 'life_stage': 'pregnancy',
     'jurisdiction': JURISDICTION, 'edition': EDITION,
     'is_prior': False, 'source': 'NASEM DRI (1.1 g/kg/day)',
     'notes': 'flat RDA equivalent 71 g/day; EAR 0.88 g/kg/day',
     'provenance_id': 'nmp-0'},
    {'name': 'protein-female-lactation-19-50', 'nutrient_name': 'protein',
     'sex': 'female', 'age_min': 19.0, 'age_max': 50.0,
     'rda_per_day': 0.0, 'per_kg_body_mass': 1.1,
     'ear_per_day': 0.0, 'value_type': 'rda',
     'upper_limit_per_day': 0.0, 'life_stage': 'lactation',
     'jurisdiction': JURISDICTION, 'edition': EDITION,
     'is_prior': False, 'source': 'NASEM DRI (1.1 g/kg/day)',
     'notes': 'flat RDA equivalent 71 g/day; EAR 1.05 g/kg/day',
     'provenance_id': 'nmp-0'},
]


def _name(nut, sex, lo, hi, stage):
    mid = f'{sex}-{stage}' if stage else sex
    return f'{nut}-{mid}-{lo:g}-{hi:g}'


def _row(nut, sex, lo, hi, stage, ear, value, vtype, ul, note):
    return {
        'name': _name(nut, sex, lo, hi, stage),
        'nutrient_name': nut, 'sex': sex,
        'age_min': float(lo), 'age_max': float(hi),
        'rda_per_day': float(value),
        'upper_limit_per_day': float(ul),
        'ear_per_day': float(ear),
        'value_type': vtype, 'life_stage': stage,
        'jurisdiction': JURISDICTION, 'edition': EDITION,
        'source': ('NASEM DRI (AI)' if vtype == 'ai'
                   else 'NASEM DRI' if vtype == 'rda'
                   else 'literature prior' if vtype == 'prior'
                   else 'computed (nut-3)'),
        # 'prior'/'ai' rows are estimates; markers too. Only firm RDA
        # rows are non-prior — same convention nut-1 used.
        'is_prior': vtype != 'rda',
        'notes': note, 'provenance_id': 'nmp-0',
    }


SEED_DRI_REFERENCES = (
    [_row(*t) for t in _ROWS] + _PROTEIN_ROWS
)
