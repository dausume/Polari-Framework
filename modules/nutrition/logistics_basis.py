"""
@module nutrition.logistics_basis

mlg-1..4 — the meal-LOGISTICS object model (MEAL_LOGISTICS_PLAN.md
§2). hh-1 (HOUSEHOLD_APP_PLAN.md) MOVED the household-generic half
to household.household_basis with names unchanged; this module keeps
the meal-specific rows and RE-EXPORTS the moved names so every
`from nutrition.logistics_basis import X` keeps working:

  MealLogistics                        a MealEntry's situation (lunchbox,
                                       cold packs) for one person (D7, D8)
  MealTimeProfile                      eating time per person × slot (D10, D11)
  (moved → mealoptions, mo-1)          MealSituation (the portability
                                       vocabulary) + SEED_MEAL_SITUATIONS,
                                       COLD_CHAIN_CITATION
  (moved → household)                  PersonSchedule, SleepPreference,
                                       HouseholdMember, WorkloadType,
                                       WorkDistributionPolicy, WorkLedger,
                                       SkillDefinition, PersonSkill,
                                       MethodSkillRequirement, SafetyRule,
                                       DurationObservation, DishStrategy,
                                       HouseholdDishPolicy + their seeds

Nothing here changes an existing class's schema: a meal's situation
is a MealLogistics row beside MealEntry. LOGISTICS_SEED_PAIRS /
LOGISTICS_CLASSES now hold ONLY the person-side meal classes (the
server registers HOUSEHOLD_SEED_PAIRS under the household gate and
MEALOPTIONS_SEED_PAIRS under the mealoptions gate).
"""

from objectTreeDecorators import treeObject, treeObjectInit
# hh-1: the household layer — re-exported (names unchanged).
from household.household_basis import (  # noqa: F401
    DINNER_TO_SLEEP_CITATION, DINNER_TO_SLEEP_DEFAULT_MIN, DISTRIBUTION_MODES,
    HAZARD_TAGS, LEVEL_ORDER, LOCATION_KINDS, SCHEDULE_KINDS, SKILL_FACTORS,
    SKILL_LEVELS, SPEED_FACTOR_FLOOR, WORKLOAD_TYPES,
    PersonSchedule, SleepPreference, HouseholdMember, WorkloadType,
    WorkDistributionPolicy, WorkLedger, SkillDefinition, PersonSkill,
    MethodSkillRequirement, SafetyRule, DurationObservation, DishStrategy,
    HouseholdDishPolicy,
    SEED_PERSON_SCHEDULES, SEED_SLEEP_PREFERENCES, SEED_HOUSEHOLD_MEMBERS,
    SEED_WORKLOAD_TYPES, SEED_WORK_POLICIES, SEED_SKILLS, SEED_PERSON_SKILLS,
    SEED_METHOD_SKILL_REQUIREMENTS, SEED_SAFETY_RULES, SEED_DURATION_OBSERVATIONS,
    SEED_DISH_STRATEGIES, SEED_DISH_POLICIES,
    HOUSEHOLD_SEED_PAIRS, HOUSEHOLD_CLASSES,
)
# mo-1: the situation vocabulary — re-exported (names unchanged).
from mealoptions.situation_basis import (  # noqa: F401
    COLD_CHAIN_CITATION, MealSituation, SEED_MEAL_SITUATIONS,
)

_PROV = 'mlg-1'


# ---------------------------------------------------------------
# per-entry logistics (mlg-3)
# ---------------------------------------------------------------

class MealLogistics(treeObject):
    """A MealEntry's situation (no MealEntry schema change)."""

    @treeObjectInit
    def __init__(self, name: str = '', entry_name: str = '', person_name: str = '',
                 situation_name: str = 'at-home', container_tool_name: str = '',
                 cold_pack_count: int = 0, pack_when: str = '',
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.entry_name = entry_name
        self.person_name = person_name
        self.situation_name = situation_name
        self.container_tool_name = container_tool_name
        self.cold_pack_count = cold_pack_count
        self.pack_when = pack_when
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes



# ---------------------------------------------------------------
# eating time (mlg-2)
# ---------------------------------------------------------------

class MealTimeProfile(treeObject):
    """Eating time per person × slot (household priors, refined)."""

    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '', slot: str = 'dinner',
                 eating_min: float = 30.0, fidelity: str = 'estimate',
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.person_name = person_name
        self.slot = slot
        self.eating_min = eating_min
        self.fidelity = fidelity
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes



# ---------------------------------------------------------------
# seeds — the demo household (Alex + Sam), every row a knob
# ---------------------------------------------------------------

#: Sam works Tue–Sat 12:00–20:00 → her day-2 dinner is eaten at work, cold.
SEED_MEAL_LOGISTICS = [
    {'name': 'demo-alex-week-d2-dinner-demo-sam', 'entry_name': 'demo-alex-week-d2-dinner',
     'person_name': 'demo-sam', 'situation_name': 'at-workplace-cold',
     'container_tool_name': 'insulated-lunchbox', 'cold_pack_count': 2, 'pack_when': 'morning',
     'is_prior': True, 'provenance_id': _PROV, 'notes': 'demo: Sam eats day-2 dinner on shift'},
]

EATING_PRIORS = {'breakfast': 15.0, 'brunch': 30.0, 'lunch': 30.0, 'linner': 35.0,
                 'dinner': 40.0, 'snack': 10.0}
SEED_MEAL_TIME_PROFILES = [
    {'name': f'{p}-{slot}', 'person_name': p, 'slot': slot, 'eating_min': m,
     'fidelity': 'estimate', 'is_prior': True, 'provenance_id': _PROV,
     'notes': 'household prior — no literature worth citing; refined from observations'}
    for p in ('demo-alex', 'demo-sam') for slot, m in EATING_PRIORS.items()
]

#: (class name, class, seeds) — the registration list the server
#: consumes: the person-side meal classes only (hh-1, mo-1); the
#: household layer registers via household.household_basis.
#: HOUSEHOLD_SEED_PAIRS, the situation vocabulary via
#: mealoptions.MEALOPTIONS_SEED_PAIRS.
LOGISTICS_SEED_PAIRS = [
    ('MealLogistics', MealLogistics, SEED_MEAL_LOGISTICS),
    ('MealTimeProfile', MealTimeProfile, SEED_MEAL_TIME_PROFILES),
]
LOGISTICS_CLASSES = [cls for _, cls, _ in LOGISTICS_SEED_PAIRS]
