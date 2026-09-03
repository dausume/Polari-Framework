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
  - household.household_analysis
  - nutrition.logistics_basis (re-export), nutrition.workflow_basis
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

SKILL_LEVELS = ('novice', 'intermediate', 'experienced')
#: labeled convention priors — refined per person from observed
#: durations (the judicial-process refinement loop).
SKILL_FACTORS = {'novice': 1.3, 'intermediate': 1.0,
                 'experienced': 0.8}

_PROV = 'mlg-1'
SCHEDULE_KINDS = ('work', 'commute', 'school', 'sleep', 'care', 'other')
LOCATION_KINDS = ('home', 'workplace', 'away', 'transit')
#: Dustin 2026-09-02: "default to 2 hours" — the citation says ~3 h;
#: both are carried, the person's own number wins.
DINNER_TO_SLEEP_DEFAULT_MIN = 120
DINNER_TO_SLEEP_CITATION = ('ACG clinical guideline for GERD (Katz et al. 2022) / '
                            'NIDDK GERD lifestyle guidance: avoid lying down within '
                            '~3 h of a meal — comfort heuristic, general population, '
                            'not treatment')
WORKLOAD_TYPES = ('purchase-trip', 'put-away', 'pre-prep', 'meal-prep',
                  'packing', 'cleanup')
DISTRIBUTION_MODES = ('everyone', 'rotate', 'shares', 'assigned', 'delivery')
HAZARD_TAGS = ('knife', 'hot-oil', 'hot-surface', 'steam', 'pressure',
               'raw-meat', 'heavy')
#: a speed factor is never refined below this (D15: skill shortens a
#: step only to its safety floor; "observed faster" is a question).
SPEED_FACTOR_FLOOR = 0.7
LEVEL_ORDER = {'': 0, 'novice': 1, 'intermediate': 2, 'experienced': 3}

# ---------------------------------------------------------------
# schedules + sleep (mlg-1)
# ---------------------------------------------------------------

class PersonSchedule(treeObject):
    """A recurring commitment: when and WHERE a person is."""

    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '', kind: str = 'work',
                 display_name: str = '',
                 # `schedule` (semantic type applied at registration).
                 recurrence: str = '{}',
                 location_kind: str = 'workplace', location_name: str = '',
                 # minutes the block may move (0 = fixed).
                 flexibility_min: int = 0,
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.person_name = person_name
        self.kind = kind
        self.display_name = display_name
        self.recurrence = recurrence
        self.location_kind = location_kind
        self.location_name = location_name
        self.flexibility_min = flexibility_min
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class SleepPreference(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '',
                 bedtime_hhmm: str = '23:00', wake_hhmm: str = '07:00',
                 # DEFAULT 120 (his call); the citation says ~3 h.
                 dinner_to_sleep_min: int = DINNER_TO_SLEEP_DEFAULT_MIN,
                 late_snack_ok: bool = False, stated_reason: str = '',
                 citation: str = DINNER_TO_SLEEP_CITATION,
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.person_name = person_name
        self.bedtime_hhmm = bedtime_hhmm
        self.wake_hhmm = wake_hhmm
        self.dinner_to_sleep_min = dinner_to_sleep_min
        self.late_snack_ok = late_snack_ok
        self.stated_reason = stated_reason
        self.citation = citation
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


# ---------------------------------------------------------------
# household work (mlg-4)
# ---------------------------------------------------------------

class HouseholdMember(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '', person_name: str = '',
                 role: str = 'adult',
                 purchase_participation: str = 'always',   # always|rotate|never|driver-only
                 can_drive: bool = True, has_workplace_meals: bool = False,
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.household_name = household_name
        self.person_name = person_name
        self.role = role
        self.purchase_participation = purchase_participation
        self.can_drive = can_drive
        self.has_workplace_meals = has_workplace_meals
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class WorkloadType(treeObject):
    """The distinct kinds of meal-prep work (authorable)."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '', description: str = '',
                 default_skills_json: str = '[]', is_prior: bool = True,
                 provenance_id: str = '', notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.default_skills_json = default_skills_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class WorkDistributionPolicy(treeObject):
    """One per workload type: how the household splits it."""

    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '',
                 workload_type: str = 'pre-prep', mode: str = 'shares',
                 # {person_name: percent} — must sum to 100 for 'shares'.
                 shares_json: str = '{}',
                 # how far the optimiser may drift from the shares to save work.
                 share_tolerance_pct: float = 10.0,
                 assigned_person: str = '', rotation_order_json: str = '[]',
                 # delivery cost shift (mode='delivery').
                 delivery_fee: float = 0.0, delivery_markup_pct: float = 0.0,
                 delivery_min_order: float = 0.0, delivery_lead_days: int = 1,
                 # the household's OWN number ('' = compare minutes only).
                 labor_value_per_hour: str = '',
                 travel_min_per_trip: float = 0.0, travel_cost_per_trip: float = 0.0,
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.household_name = household_name
        self.workload_type = workload_type
        self.mode = mode
        self.shares_json = shares_json
        self.share_tolerance_pct = share_tolerance_pct
        self.assigned_person = assigned_person
        self.rotation_order_json = rotation_order_json
        self.delivery_fee = delivery_fee
        self.delivery_markup_pct = delivery_markup_pct
        self.delivery_min_order = delivery_min_order
        self.delivery_lead_days = delivery_lead_days
        self.labor_value_per_hour = labor_value_per_hour
        self.travel_min_per_trip = travel_min_per_trip
        self.travel_cost_per_trip = travel_cost_per_trip
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class WorkLedger(treeObject):
    """What actually happened — minutes of work by person and type."""

    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '', person_name: str = '',
                 workload_type: str = '', minutes: float = 0.0, event_name: str = '',
                 date: str = '', source: str = 'event-done',
                 is_prior: bool = False, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.household_name = household_name
        self.person_name = person_name
        self.workload_type = workload_type
        self.minutes = minutes
        self.event_name = event_name
        self.date = date
        self.source = source
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


# ---------------------------------------------------------------
# skills + safety (mlg-2)
# ---------------------------------------------------------------

class SkillDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '', description: str = '',
                 is_safety: bool = False, is_prior: bool = True,
                 provenance_id: str = '', notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.is_safety = is_safety
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class PersonSkill(treeObject):
    """A person's level + speed factor for ONE skill (refined)."""

    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '', skill_name: str = '',
                 level: str = 'novice',
                 # PRIOR from SKILL_FACTORS by level; refined from observations.
                 speed_factor: float = 1.3, fidelity: str = 'estimate',
                 observation_count: int = 0,
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.person_name = person_name
        self.skill_name = skill_name
        self.level = level
        self.speed_factor = speed_factor
        self.fidelity = fidelity
        self.observation_count = observation_count
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class MethodSkillRequirement(treeObject):
    """Skills + safety a StepMethod needs — a row beside the method,
    so "adding skills needed for particular steps" is a row edit."""

    @treeObjectInit
    def __init__(self, name: str = '', method_name: str = '', task_kind: str = '',
                 # [{"skill": "knife-work", "floor": "intermediate"}]
                 skills_json: str = '[]',
                 # minutes the step needs to be done SAFELY at any skill.
                 safety_floor_min: float = 0.0,
                 hazard_tags_json: str = '[]',
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.method_name = method_name
        self.task_kind = task_kind
        self.skills_json = skills_json
        self.safety_floor_min = safety_floor_min
        self.hazard_tags_json = hazard_tags_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class SafetyRule(treeObject):
    """hazard tag → the safety level required, else supervised."""

    @treeObjectInit
    def __init__(self, name: str = '', hazard_tag: str = '', skill_name: str = 'kitchen-safety',
                 required_level: str = 'intermediate',
                 below_floor: str = 'supervised',   # supervised | unassigned
                 rule_text: str = '', citation: str = '', confidence: str = 'transcribed',
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.hazard_tag = hazard_tag
        self.skill_name = skill_name
        self.required_level = required_level
        self.below_floor = below_floor
        self.rule_text = rule_text
        self.citation = citation
        self.confidence = confidence
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class DurationObservation(treeObject):
    """The refinement loop's facts: how long a step / a meal took."""

    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '',
                 kind: str = 'prep-step',   # prep-step | final-prep | eating | packing | cleanup
                 method_name: str = '', skill_name: str = '', entry_name: str = '',
                 slot: str = '', observed_min: float = 0.0, date: str = '',
                 source: str = 'logged', is_prior: bool = False,
                 provenance_id: str = '', notes: str = '', manager=None):
        self.name = name
        self.person_name = person_name
        self.kind = kind
        self.method_name = method_name
        self.skill_name = skill_name
        self.entry_name = entry_name
        self.slot = slot
        self.observed_min = observed_min
        self.date = date
        self.source = source
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


# ---------------------------------------------------------------
# dishes (mlg-2b)
# ---------------------------------------------------------------

class DishStrategy(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '', description: str = '',
                 needs_tool: str = '', min_per_load_unit: float = 1.5,
                 setup_min: float = 2.0, cycle_min: float = 0.0, unload_min: float = 0.0,
                 timing: str = 'unattended-first',   # unattended-first | after-meal | when-full
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.needs_tool = needs_tool
        self.min_per_load_unit = min_per_load_unit
        self.setup_min = setup_min
        self.cycle_min = cycle_min
        self.unload_min = unload_min
        self.timing = timing
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class HouseholdDishPolicy(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '',
                 preprep_strategy: str = 'wash-as-you-go',
                 meal_strategy: str = 'batch-after-meal',
                 cooldown_after_eating_min: float = 10.0,
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.household_name = household_name
        self.preprep_strategy = preprep_strategy
        self.meal_strategy = meal_strategy
        self.cooldown_after_eating_min = cooldown_after_eating_min
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


# ---------------------------------------------------------------
# seeds — the demo household (Alex + Sam), every row a knob
# ---------------------------------------------------------------

def _sched(person, kind, days, start, end, loc_kind, loc='', rng='2026-08-31'):
    return {'name': f'{person}-{kind}', 'person_name': person, 'kind': kind,
            'display_name': f'{person}: {kind} {start}–{end}',
            'recurrence': json.dumps({'eventType': 'datetime_duration', 'frequency': 'weekly',
                                      'byDay': days, 'startTime': start, 'endTime': end,
                                      'rangeStart': rng}),
            'location_kind': loc_kind, 'location_name': loc, 'flexibility_min': 0,
            'is_prior': True, 'provenance_id': _PROV,
            'notes': 'demo schedule — replace with the real one'}


SEED_PERSON_SCHEDULES = [
    _sched('demo-alex', 'work', ['MO', 'TU', 'WE', 'TH', 'FR'], '09:00', '17:00',
           'workplace', 'demo-workplace'),
    _sched('demo-alex', 'commute', ['MO', 'TU', 'WE', 'TH', 'FR'], '08:15', '09:00', 'transit'),
    _sched('demo-alex', 'sleep', ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU'], '23:00', '07:00', 'home'),
    _sched('demo-sam', 'work', ['TU', 'WE', 'TH', 'FR', 'SA'], '12:00', '20:00',
           'workplace', 'demo-workplace'),
    _sched('demo-sam', 'sleep', ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU'], '00:30', '08:30', 'home'),
]

SEED_SLEEP_PREFERENCES = [
    {'name': 'demo-alex-sleep', 'person_name': 'demo-alex', 'bedtime_hhmm': '23:00',
     'wake_hhmm': '07:00', 'dinner_to_sleep_min': DINNER_TO_SLEEP_DEFAULT_MIN,
     'late_snack_ok': False, 'stated_reason': 'default (2 h)', 'citation': DINNER_TO_SLEEP_CITATION,
     'is_prior': True, 'provenance_id': _PROV, 'notes': ''},
    {'name': 'demo-sam-sleep', 'person_name': 'demo-sam', 'bedtime_hhmm': '00:30',
     'wake_hhmm': '08:30', 'dinner_to_sleep_min': 150, 'late_snack_ok': True,
     'stated_reason': 'stated: evening shifts, prefers 2.5 h', 'citation': DINNER_TO_SLEEP_CITATION,
     'is_prior': True, 'provenance_id': _PROV, 'notes': ''},
]

SEED_HOUSEHOLD_MEMBERS = [
    {'name': 'demo-household-demo-alex', 'household_name': 'demo-household',
     'person_name': 'demo-alex', 'role': 'adult', 'purchase_participation': 'always',
     'can_drive': True, 'has_workplace_meals': True, 'is_prior': True,
     'provenance_id': _PROV, 'notes': ''},
    {'name': 'demo-household-demo-sam', 'household_name': 'demo-household',
     'person_name': 'demo-sam', 'role': 'adult', 'purchase_participation': 'always',
     'can_drive': True, 'has_workplace_meals': True, 'is_prior': True,
     'provenance_id': _PROV, 'notes': ''},
]

SEED_WORKLOAD_TYPES = [
    {'name': 'purchase-trip', 'display_name': 'Purchase trip', 'description':
        'Going to buy the food (or receiving a delivery).', 'default_skills_json': '[]'},
    {'name': 'put-away', 'display_name': 'Put away', 'description':
        'Unpacking and storing what was bought.', 'default_skills_json': '["food-safety"]'},
    {'name': 'pre-prep', 'display_name': 'Pre-prep (batch cooking)', 'description':
        'The batched sessions the scheduler minimizes.', 'default_skills_json': '["knife-work", "heat-control"]'},
    {'name': 'meal-prep', 'display_name': 'Meal prep (final)', 'description':
        'Reheat / assemble / plate right before eating.', 'default_skills_json': '["heat-control"]'},
    {'name': 'packing', 'display_name': 'Packing', 'description':
        'Packing portable meals, freezing cold packs.', 'default_skills_json': '["packing", "food-safety"]'},
    {'name': 'cleanup', 'display_name': 'Dishes & cleanup', 'description':
        'Dishes, wiping down, dishwasher runs.', 'default_skills_json': '[]'},
]
for _w in SEED_WORKLOAD_TYPES:
    _w.update({'is_prior': True, 'provenance_id': _PROV, 'notes': ''})


def _policy(wtype, mode, shares=None, **extra):
    row = {'name': f'demo-household-{wtype}', 'household_name': 'demo-household',
           'workload_type': wtype, 'mode': mode,
           'shares_json': json.dumps(shares or {}), 'share_tolerance_pct': 10.0,
           'assigned_person': '', 'rotation_order_json': '[]',
           'delivery_fee': 0.0, 'delivery_markup_pct': 0.0, 'delivery_min_order': 0.0,
           'delivery_lead_days': 1, 'labor_value_per_hour': '',
           'travel_min_per_trip': 0.0, 'travel_cost_per_trip': 0.0,
           'is_prior': True, 'provenance_id': _PROV,
           'notes': 'demo policy — the household edits its own split'}
    row.update(extra)
    return row


SEED_WORK_POLICIES = [
    _policy('purchase-trip', 'everyone', travel_min_per_trip=40.0, travel_cost_per_trip=3.50,
            delivery_fee=7.99, delivery_markup_pct=12.0, delivery_min_order=35.0,
            notes='both adults always shop (his 2-adult example); the delivery knobs '
                  'let the comparison show the cost shift'),
    _policy('put-away', 'shares', {'demo-alex': 50, 'demo-sam': 50}),
    _policy('pre-prep', 'shares', {'demo-alex': 70, 'demo-sam': 30}),
    _policy('meal-prep', 'shares', {'demo-alex': 50, 'demo-sam': 50}),
    _policy('packing', 'assigned', assigned_person='',
            notes='assigned = the eater packs their own (empty assigned_person)'),
    _policy('cleanup', 'shares', {'demo-alex': 40, 'demo-sam': 60}),
]

SEED_SKILLS = [
    {'name': 'knife-work', 'display_name': 'Knife work', 'description': 'Dicing, slicing, mandoline.', 'is_safety': False},
    {'name': 'heat-control', 'display_name': 'Heat control', 'description': 'Pan, pot, broiler timing.', 'is_safety': False},
    {'name': 'baking', 'display_name': 'Baking / roasting', 'description': 'Oven work.', 'is_safety': False},
    {'name': 'pressure-cooking', 'display_name': 'Pressure cooking', 'description': 'Pressure release, sealing.', 'is_safety': False},
    {'name': 'packing', 'display_name': 'Packing', 'description': 'Portable meals, cold chain.', 'is_safety': False},
    {'name': 'kitchen-safety', 'display_name': 'Kitchen safety', 'description':
        'Knives, hot surfaces / oil / steam, pressure, lifting — BOUNDS speed; default novice is an '
        'honest default, not a judgement.', 'is_safety': True},
    {'name': 'food-safety', 'display_name': 'Food safety', 'description':
        'FSIS clean / separate / cook / chill; temperatures and windows.', 'is_safety': True},
]
for _k in SEED_SKILLS:
    _k.update({'is_prior': True, 'provenance_id': _PROV, 'notes': ''})


def _pskill(person, skill, level):
    return {'name': f'{person}-{skill}', 'person_name': person, 'skill_name': skill,
            'level': level, 'speed_factor': SKILL_FACTORS.get(level, 1.0),
            'fidelity': 'estimate', 'observation_count': 0, 'is_prior': True,
            'provenance_id': _PROV, 'notes': 'level prior — refined from observations'}


SEED_PERSON_SKILLS = [
    _pskill('demo-alex', 'knife-work', 'experienced'),
    _pskill('demo-alex', 'heat-control', 'intermediate'),
    _pskill('demo-alex', 'baking', 'novice'),
    _pskill('demo-alex', 'packing', 'intermediate'),
    _pskill('demo-alex', 'kitchen-safety', 'intermediate'),
    _pskill('demo-alex', 'food-safety', 'intermediate'),
    _pskill('demo-sam', 'knife-work', 'novice'),
    _pskill('demo-sam', 'heat-control', 'experienced'),
    _pskill('demo-sam', 'baking', 'experienced'),
    _pskill('demo-sam', 'packing', 'experienced'),
    _pskill('demo-sam', 'kitchen-safety', 'experienced'),
    _pskill('demo-sam', 'food-safety', 'experienced'),
]


def _req(method, task, skills, floor_min, hazards):
    return {'name': f'req-{method}', 'method_name': method, 'task_kind': task,
            'skills_json': json.dumps(skills), 'safety_floor_min': floor_min,
            'hazard_tags_json': json.dumps(hazards), 'is_prior': True,
            'provenance_id': _PROV, 'notes': 'seeded requirement — add/edit rows to change'}


SEED_METHOD_SKILL_REQUIREMENTS = [
    _req('dice-knife', 'dice', [{'skill': 'knife-work', 'floor': ''}], 1.5, ['knife']),
    _req('dice-processor', 'dice', [{'skill': 'knife-work', 'floor': ''}], 1.0, ['knife']),
    _req('dice-mandoline', 'dice', [{'skill': 'knife-work', 'floor': 'intermediate'}], 2.0, ['knife']),
    _req('boil-pot', 'boil', [{'skill': 'heat-control', 'floor': ''}], 2.0, ['steam', 'hot-surface']),
    _req('boil-rice-cooker', 'boil', [{'skill': 'heat-control', 'floor': ''}], 1.0, ['steam']),
    _req('steam-pot', 'steam', [{'skill': 'heat-control', 'floor': ''}], 2.0, ['steam']),
    _req('pan-fry-pan', 'pan-fry', [{'skill': 'heat-control', 'floor': ''}], 3.0, ['hot-oil', 'hot-surface']),
    _req('grill-broiler', 'grill', [{'skill': 'heat-control', 'floor': ''}], 3.0, ['hot-surface']),
    _req('bake-oven', 'bake', [{'skill': 'baking', 'floor': ''}], 2.0, ['hot-surface']),
    _req('cool-counter', 'cool', [{'skill': 'food-safety', 'floor': ''}], 0.0, []),
    _req('portion-containers', 'portion', [{'skill': 'food-safety', 'floor': ''}], 1.0, ['raw-meat']),
    _req('assemble-plate', 'assemble', [{'skill': 'food-safety', 'floor': ''}], 1.0, []),
]

_SAFETY_CIT = ('USDA FSIS Kitchen Companion / "Clean, Separate, Cook, Chill"; burn and '
               'cut prevention per general home-kitchen safety guidance — transcribed priors')
SEED_SAFETY_RULES = [
    {'name': 'rule-knife', 'hazard_tag': 'knife', 'skill_name': 'kitchen-safety',
     'required_level': 'intermediate', 'below_floor': 'supervised',
     'rule_text': 'sharp knives, claw grip, stable board; never rushed', 'citation': _SAFETY_CIT},
    {'name': 'rule-hot-oil', 'hazard_tag': 'hot-oil', 'skill_name': 'kitchen-safety',
     'required_level': 'intermediate', 'below_floor': 'supervised',
     'rule_text': 'dry food into hot oil, pan handles in; never water on an oil fire', 'citation': _SAFETY_CIT},
    {'name': 'rule-hot-surface', 'hazard_tag': 'hot-surface', 'skill_name': 'kitchen-safety',
     'required_level': 'novice', 'below_floor': 'supervised',
     'rule_text': 'oven mitts, announce hot pans', 'citation': _SAFETY_CIT},
    {'name': 'rule-steam', 'hazard_tag': 'steam', 'skill_name': 'kitchen-safety',
     'required_level': 'novice', 'below_floor': 'supervised',
     'rule_text': 'lids away from the face; drain away from the body', 'citation': _SAFETY_CIT},
    {'name': 'rule-pressure', 'hazard_tag': 'pressure', 'skill_name': 'kitchen-safety',
     'required_level': 'experienced', 'below_floor': 'unassigned',
     'rule_text': 'natural release unless the recipe says quick; never force a lid', 'citation': _SAFETY_CIT},
    {'name': 'rule-raw-meat', 'hazard_tag': 'raw-meat', 'skill_name': 'food-safety',
     'required_level': 'intermediate', 'below_floor': 'supervised',
     'rule_text': 'separate boards, wash hands, cook to FSIS temperatures', 'citation': _SAFETY_CIT},
    {'name': 'rule-heavy', 'hazard_tag': 'heavy', 'skill_name': 'kitchen-safety',
     'required_level': 'novice', 'below_floor': 'supervised',
     'rule_text': 'two hands for full pots; never carry boiling water across the kitchen', 'citation': _SAFETY_CIT},
]
for _r in SEED_SAFETY_RULES:
    _r.update({'confidence': 'transcribed', 'is_prior': True, 'provenance_id': _PROV, 'notes': ''})

#: three observations of Alex dicing → the refinement loop has data
#: on the demo (median rule); Sam has none → priors stand, labeled.
SEED_DURATION_OBSERVATIONS = [
    {'name': f'obs-demo-alex-dice-{i}', 'person_name': 'demo-alex', 'kind': 'prep-step',
     'method_name': 'dice-knife', 'skill_name': 'knife-work', 'entry_name': '', 'slot': '',
     'observed_min': m, 'date': d, 'source': 'logged', 'is_prior': True,
     'provenance_id': _PROV, 'notes': 'demo observation'}
    for i, (m, d) in enumerate([(4.5, '2026-08-24'), (5.0, '2026-08-26'), (4.0, '2026-08-28')], 1)
]

SEED_DISH_STRATEGIES = [
    {'name': 'wash-as-you-go', 'display_name': 'Wash as you go', 'description':
        'Dishes in the unattended windows of a session (a simmer is a dish window).',
     'needs_tool': '', 'min_per_load_unit': 1.5, 'setup_min': 2.0, 'cycle_min': 0.0,
     'unload_min': 0.0, 'timing': 'unattended-first'},
    {'name': 'batch-after-meal', 'display_name': 'Batch after the meal', 'description':
        'Everything after eating, once.', 'needs_tool': '', 'min_per_load_unit': 1.5,
     'setup_min': 3.0, 'cycle_min': 0.0, 'unload_min': 0.0, 'timing': 'after-meal'},
    {'name': 'soak-then-wash', 'display_name': 'Soak, then wash', 'description':
        'Soak during the meal, wash after (less scrubbing).', 'needs_tool': '',
     'min_per_load_unit': 1.2, 'setup_min': 2.0, 'cycle_min': 0.0, 'unload_min': 0.0,
     'timing': 'after-meal'},
    {'name': 'dishwasher-when-full', 'display_name': 'Dishwasher when full', 'description':
        'Load as you go; run when full; unload later.', 'needs_tool': 'dishwasher',
     'min_per_load_unit': 0.5, 'setup_min': 1.0, 'cycle_min': 90.0, 'unload_min': 6.0,
     'timing': 'when-full'},
    {'name': 'rinse-and-stack', 'display_name': 'Rinse and stack for later', 'description':
        'Rinse now, wash in the next free window.', 'needs_tool': '', 'min_per_load_unit': 1.6,
     'setup_min': 1.0, 'cycle_min': 0.0, 'unload_min': 0.0, 'timing': 'unattended-first'},
]
for _d in SEED_DISH_STRATEGIES:
    _d.update({'is_prior': True, 'provenance_id': _PROV, 'notes': 'minutes are priors'})

SEED_DISH_POLICIES = [
    {'name': 'demo-household-dishes', 'household_name': 'demo-household',
     'preprep_strategy': 'wash-as-you-go', 'meal_strategy': 'batch-after-meal',
     'cooldown_after_eating_min': 10.0, 'is_prior': True, 'provenance_id': _PROV,
     'notes': 'demo: no dishwasher in the inventory'},
]

#: (class name, class, seeds) — the registration list the server consumes.
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
