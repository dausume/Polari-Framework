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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/logistics/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit
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
from mealoptions.situation_basis import (  # noqa: F401
    COLD_CHAIN_CITATION, MealSituation, SEED_MEAL_SITUATIONS,
)

from nutrition.objects.logistics._shared import EATING_PRIORS, SEED_MEAL_LOGISTICS, SEED_MEAL_TIME_PROFILES, _PROV  # noqa: F401
from nutrition.objects.logistics.MealLogistics import MealLogistics  # noqa: F401
from nutrition.objects.logistics.MealTimeProfile import MealTimeProfile  # noqa: F401


LOGISTICS_SEED_PAIRS = [
    ('MealLogistics', MealLogistics, SEED_MEAL_LOGISTICS),
    ('MealTimeProfile', MealTimeProfile, SEED_MEAL_TIME_PROFILES),
]
LOGISTICS_CLASSES = [cls for _, cls, _ in LOGISTICS_SEED_PAIRS]
