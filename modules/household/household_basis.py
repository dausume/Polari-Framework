"""
@module household.household_basis

hh-1 (HOUSEHOLD_APP_PLAN.md) — the household-generic object model the
meal-logistics round (mlg-1..4, MEAL_LOGISTICS_PLAN.md §2) built,
MOVED here with names unchanged; every row a knob, every number a
labeled prior:

  PersonSchedule / SleepPreference     where + when a person is; the
                                       dinner→sleep spacing (D1, D2)
  HouseholdMember / WorkloadType /     who does what share of which
  WorkDistributionPolicy / WorkLedger  work; delivery cost shift (D3-D6, D13)
  SkillDefinition / PersonSkill /      skill profiles, skills per step,
  MethodSkillRequirement / SafetyRule  safety bounding speed (D9, D14, D15)
  DurationObservation                  the refinement loop's facts (D10)
  DishStrategy / HouseholdDishPolicy   dishes as scheduled work (D16) —
                                       the first non-cooking chore

The meal-specific rows (MealSituation, MealLogistics, MealTimeProfile)
stay in nutrition.logistics_basis, which re-exports everything here.
Nothing here imports nutrition: SKILL_LEVELS / SKILL_FACTORS live
here now (nutrition.workflow_basis re-exports them).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence, gated on
    _feature_available('household'))
  - household.custom.household_analysis
  - nutrition.logistics_basis (re-export), nutrition.workflow_basis
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/household/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from household.objects.household._shared import DINNER_TO_SLEEP_CITATION, DINNER_TO_SLEEP_DEFAULT_MIN, DISTRIBUTION_MODES, HAZARD_TAGS, LEVEL_ORDER, LOCATION_KINDS, SCHEDULE_KINDS, SEED_DISH_POLICIES, SEED_DISH_STRATEGIES, SEED_DURATION_OBSERVATIONS, SEED_HOUSEHOLD_MEMBERS, SEED_METHOD_SKILL_REQUIREMENTS, SEED_PERSON_SCHEDULES, SEED_PERSON_SKILLS, SEED_SAFETY_RULES, SEED_SKILLS, SEED_SLEEP_PREFERENCES, SEED_WORKLOAD_TYPES, SEED_WORK_POLICIES, SKILL_FACTORS, SKILL_LEVELS, SPEED_FACTOR_FLOOR, WORKLOAD_TYPES, _PROV, _SAFETY_CIT, _d, _k, _policy, _pskill, _r, _req, _sched, _w  # noqa: F401
from household.objects.household.PersonSchedule import PersonSchedule  # noqa: F401
from household.objects.household.SleepPreference import SleepPreference  # noqa: F401
from household.objects.household.HouseholdMember import HouseholdMember  # noqa: F401
from household.objects.household.WorkloadType import WorkloadType  # noqa: F401
from household.objects.household.WorkDistributionPolicy import WorkDistributionPolicy  # noqa: F401
from household.objects.household.WorkLedger import WorkLedger  # noqa: F401
from household.objects.household.SkillDefinition import SkillDefinition  # noqa: F401
from household.objects.household.PersonSkill import PersonSkill  # noqa: F401
from household.objects.household.MethodSkillRequirement import MethodSkillRequirement  # noqa: F401
from household.objects.household.SafetyRule import SafetyRule  # noqa: F401
from household.objects.household.DurationObservation import DurationObservation  # noqa: F401
from household.objects.household.DishStrategy import DishStrategy  # noqa: F401
from household.objects.household.HouseholdDishPolicy import HouseholdDishPolicy  # noqa: F401


HOUSEHOLD_SEED_PAIRS = [
    ('PersonSchedule', PersonSchedule, SEED_PERSON_SCHEDULES),
    ('SleepPreference', SleepPreference, SEED_SLEEP_PREFERENCES),
    ('HouseholdMember', HouseholdMember, SEED_HOUSEHOLD_MEMBERS),
    ('WorkloadType', WorkloadType, SEED_WORKLOAD_TYPES),
    ('WorkDistributionPolicy', WorkDistributionPolicy, SEED_WORK_POLICIES),
    ('WorkLedger', WorkLedger, []),
    ('SkillDefinition', SkillDefinition, SEED_SKILLS),
    ('PersonSkill', PersonSkill, SEED_PERSON_SKILLS),
    ('MethodSkillRequirement', MethodSkillRequirement, SEED_METHOD_SKILL_REQUIREMENTS),
    ('SafetyRule', SafetyRule, SEED_SAFETY_RULES),
    ('DurationObservation', DurationObservation, SEED_DURATION_OBSERVATIONS),
    ('DishStrategy', DishStrategy, SEED_DISH_STRATEGIES),
    ('HouseholdDishPolicy', HouseholdDishPolicy, SEED_DISH_POLICIES),
]
HOUSEHOLD_CLASSES = [cls for _, cls, _ in HOUSEHOLD_SEED_PAIRS]
