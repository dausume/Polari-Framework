"""
@cross-cutting
@module nutrition.threshold_basis
@tags @xc:bindings

nmp-1 — the threshold layer's objects:

  EatingPatternDefinition  one eating pattern (decision 4) with its
                           per-slot calorie FRACTIONS (decision 7 /
                           Q5) — labeled convention priors: the
                           meal-distribution literature is thin, and
                           these rows say so. Tunable per household.
  PersonThreshold          ONE overridden threshold knob. Derived
                           thresholds are computed on demand from the
                           DRI/UL + DGA seeds (threshold_analysis) —
                           only a HUMAN override materializes a row
                           (knobs-and-suggestions: the derivation is
                           the suggestion, this row is the knob).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.threshold_analysis
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-1
"""

from objectTreeDecorators import treeObject, treeObjectInit

THRESHOLD_PERIODS = ('meal', 'day', 'week', 'month')


class EatingPatternDefinition(treeObject):
    """One eating pattern and its per-slot calorie fractions."""

    @treeObjectInit
    def __init__(
        self,
        # matches PersonProfile.eating_pattern ('3-meal').
        name: str = '',
        display_name: str = '',
        # JSON list of {"slot": name, "fraction": 0-1} — fractions
        # sum to 1; slots come from the decision-5 vocabulary
        # (breakfast/lunch/dinner/brunch/linner/snack).
        slot_fractions_json: str = '[]',
        # convention priors, not literature findings — say so.
        is_prior: bool = True,
        source: str = 'convention prior (Q5, Dustin-proposed splits)',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.slot_fractions_json = slot_fractions_json
        self.is_prior = is_prior
        self.source = source
        self.provenance_id = provenance_id
        self.notes = notes


class PersonThreshold(treeObject):
    """One human-overridden threshold for (person, nutrient, period).

    Absent row = the derived value applies (threshold_analysis shows
    its derivation). A row here WINS over the derivation and is never
    touched by seeds (is_prior=False by construction — it exists
    because a human set it)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('alex-fiber-day').
        name: str = '',
        person_name: str = '',
        nutrient_name: str = '',
        # THRESHOLD_PERIODS entry.
        period: str = 'day',
        # the override values; 0 = keep the derived value for that
        # side (min/target/max are independently overridable).
        min_amount: float = 0.0,
        target_amount: float = 0.0,
        max_amount: float = 0.0,
        unit: str = '',
        # why the human set it — their words, kept with the number.
        reason: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.nutrient_name = nutrient_name
        self.period = period
        self.min_amount = min_amount
        self.target_amount = target_amount
        self.max_amount = max_amount
        self.unit = unit
        self.reason = reason
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


# ── seeds ─────────────────────────────────────────────────
# Q5's proposed splits, seeded as tunable convention priors.
SEED_EATING_PATTERNS = [
    {'name': '2-meal', 'display_name': '2 meals a day',
     'slot_fractions_json':
         '[{"slot": "brunch", "fraction": 0.45},'
         ' {"slot": "dinner", "fraction": 0.55}]',
     'is_prior': True, 'provenance_id': 'nmp-1',
     'notes': 'convention prior — meal-distribution literature is '
              'thin; tune freely'},
    {'name': '3-meal', 'display_name': '3 meals a day',
     'slot_fractions_json':
         '[{"slot": "breakfast", "fraction": 0.25},'
         ' {"slot": "lunch", "fraction": 0.35},'
         ' {"slot": "dinner", "fraction": 0.40}]',
     'is_prior': True, 'provenance_id': 'nmp-1',
     'notes': 'convention prior — meal-distribution literature is '
              'thin; tune freely'},
    {'name': '3-small-2-snacks',
     'display_name': '3 small meals + 2 snacks',
     'slot_fractions_json':
         '[{"slot": "breakfast", "fraction": 0.25},'
         ' {"slot": "lunch", "fraction": 0.25},'
         ' {"slot": "dinner", "fraction": 0.30},'
         ' {"slot": "snack", "fraction": 0.10},'
         ' {"slot": "snack-2", "fraction": 0.10}]',
     'is_prior': True, 'provenance_id': 'nmp-1',
     'notes': 'convention prior — meal-distribution literature is '
              'thin; tune freely'},
]
