"""
@module polariApiServer.mealplan_pages_seed

mpa-5 — the meal-planning APP's display pages, all PURE DATA, seeded
THE POLARI WAY (Dustin 2026-09-02: "there should not be any json
showing on the screens, everything should be configured tables,
graphs, or visualizations … embedded into displays that are put into
the app pages … look at how we do configuration of those already in
polari, do not create new custom code"):

  TableDefinition   one per meal-planning class — the class's OWN
                    display configuration (columns, instance cards),
                    visible on its class page and EMBEDDED here via
                    embeddedTable (scoped with filterField/filterValue)
  GraphDefinition   the trend charts, embedded via embeddedGraph BY NAME
  api-structured-panel
                    the derived verdicts (cost, coverage, budget,
                    acidity, state chain…) rendered through the generic
                    structured reading — chips / prose / real tables —
                    with `pick`/`hideKeys` tuned so NOTHING falls
                    through to the "unrendered fields" JSON expander
  DisplayDefinition the five pages the nutrition-planner nav ties
                    together; demo rows (demo-alex / demo-household /
                    demo-alex-week) are knobs — repoint by editing the
                    Display row (or route the pages by ?object= — the
                    display page substitutes `{object}`).

Seeded through composition.seed_upsert (CONVERGES on edit — no more
INSERT-BY-NAME backfills) and the embed ids are re-pointed at THIS
node's TableDefinition ids after the upsert — the motors_pages
pattern, verbatim. See seed_mealplan_pages().

Routes: /display/mealplan, /display/mealplan/planner,
/display/mealplan/pantry, /display/mealplan/market,
/display/mealplan/trends.

@consumers polariServer (seed pass — seed_mealplan_pages, gated on
  nutrition + DisplayDefinition scope)
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-5
"""

import json

from polariApiServer.module_pages_seed import _page, _row

#: Demo knobs — every embed below is scoped to these.
PERSON = 'demo-alex'
HOUSEHOLD = 'demo-household'
PLAN = 'demo-alex-week'
TEMPLATE = 'chicken-bowl-dinner'
DAY = '2026-09-01'


# --------------------------------------------------------------------
# TableDefinition rows — the classes' own display configuration.
# ⚠ COLUMN SHAPE is ColumnConfiguration {name, displayName, dataType,
# order, visible, …}; {id, fieldName, index} parses to ZERO columns
# (per-object-display-config memory / motors_pages header).
# --------------------------------------------------------------------

def _col(name, label, dtype, width, order):
    return {'name': name, 'displayName': label, 'dataType': dtype,
            'available': True, 'visible': True, 'order': order,
            'sortable': True, 'filterable': True, 'resizable': True,
            'width': width, 'minWidth': 60, 'alignment': 'left',
            'format': 'default', 'pinned': False, 'showTypeIcon': True,
            'userCanHide': True, 'userCanReorder': True}


def _card(name, label, dtype):
    return {'id': f'c-{name}', 'fieldName': name, 'label': label,
            'icon': 'label',
            'format': 'number' if dtype in ('int', 'float') else 'text'}


def _table_def(name, class_name, display_name, description, columns,
               defaults=True):
    """One class's standard table + instance display. `columns` =
    [(field, label, dtype, width), …]; the first six become the
    instance-display cards."""
    cols = [_col(f, label, dtype, width, i)
            for i, (f, label, dtype, width) in enumerate(columns)]
    definition = {
        'tableConfiguration': {
            'id': f'{class_name.lower()}-table',
            'className': class_name, 'displayName': display_name,
            'columns': cols, 'removedColumns': [], 'sortOrder': [],
            'sortDirection': 'asc', 'sortColumn': columns[0][0],
            'pagination': {'enabled': True, 'pageSize': 25,
                           'pageSizeOptions': [10, 25, 50]},
            'filter': {'globalFilterEnabled': True,
                       'columnFiltersEnabled': True,
                       'activeFilters': {}, 'caseSensitive': False},
            'sections': {'enabled': False, 'sections': []},
            'density': 'comfortable', 'selectionMode': 'none',
            'showRowNumbers': False, 'showHeaders': True,
            'stripedRows': True, 'showGridLines': True,
            'hoverHighlight': True, 'reorderableColumns': True,
            'fixedHeight': 0, 'cssClass': '',
            'lastModified': '2026-09-02T00:00:00.000Z', 'version': 1,
        },
        'rowWrapping': {'enabled': False, 'fieldsPerRow': 4,
                        'separatorStyle': 'thin'},
        'crudPermissions': {'allowCreate': True, 'allowEdit': True,
                            'allowDelete': False},
        'instanceActions': [], 'datasetActions': [],
        'detailDisplay': {'cards': [_card(f, label, dtype)
                                    for f, label, dtype, _w
                                    in columns[:6]]},
    }
    return {'name': name, 'description': description,
            'source_class': class_name,
            'definition': json.dumps(definition),
            'is_default_table': defaults,
            'is_default_dataset_display': defaults,
            'is_default_instance_display': defaults}


SEED_MEALPLAN_TABLES = [
    _table_def('mealplan-plan-standard', 'MealPlanDefinition',
               'Meal plans', 'A household\'s meal plans.',
               [('name', 'Plan', 'str', 160),
                ('display_name', 'Title', 'str', 200),
                ('person_name', 'Person', 'str', 120),
                ('household_name', 'Household', 'str', 140),
                ('days', 'Days', 'int', 70),
                ('start_date', 'Starts', 'str', 110)]),
    _table_def('mealplan-entry-standard', 'MealEntry',
               'Plan entries', 'One meal slot of a plan.',
               [('plan_name', 'Plan', 'str', 150),
                ('day_index', 'Day', 'int', 60),
                ('slot', 'Slot', 'str', 90),
                ('template_name', 'Meal', 'str', 170),
                ('variation_name', 'Variation', 'str', 190),
                ('scale', 'Scale', 'float', 70),
                ('time_hhmm', 'Time', 'str', 70)]),
    _table_def('mealplan-pantry-standard', 'PantryItem',
               'Pantry lots', 'What the household has on hand.',
               [('food_name', 'Food', 'str', 160),
                ('quantity', 'Qty', 'float', 70),
                ('unit', 'Unit', 'str', 70),
                ('storage_state', 'Storage', 'str', 90),
                ('acquired_date', 'Acquired', 'str', 110),
                ('source_location_name', 'From', 'str', 150),
                ('price_paid', 'Paid', 'float', 80)]),
    _table_def('mealplan-unit-weight-standard', 'UnitWeightPrior',
               'Approximate unit weights',
               'Labeled weight priors a kitchen scale can override.',
               [('food_name', 'Food', 'str', 160),
                ('unit_label', 'Unit', 'str', 90),
                ('grams', 'Grams', 'float', 80),
                ('household_name', 'Household override', 'str', 150),
                ('citation', 'Citation', 'str', 320)]),
    _table_def('mealplan-location-standard', 'SourceLocation',
               'Source locations', 'Where food is bought.',
               [('name', 'Location', 'str', 150),
                ('display_name', 'Name', 'str', 170),
                ('kind', 'Kind', 'str', 110),
                # mo-2: who sets the price (chain vs independent).
                ('ownership_kind', 'Ownership', 'str', 120),
                ('chain_name', 'Chain', 'str', 120),
                ('region_label', 'Region', 'str', 170),
                ('latitude', 'Lat', 'float', 90),
                ('longitude', 'Lon', 'float', 90)]),
    _table_def('mealplan-price-standard', 'PriceObservation',
               'Price observations', 'User-entered prices, never scraped.',
               [('food_name', 'Food', 'str', 160),
                ('location_name', 'Location', 'str', 150),
                ('price', 'Price', 'float', 80),
                ('currency', 'Cur.', 'str', 60),
                ('package_quantity', 'Pkg qty', 'float', 80),
                ('package_unit', 'Pkg unit', 'str', 90),
                ('observed_date', 'Observed', 'str', 110)]),
    # mo-2: the published, person-free month references (mealoptions).
    _table_def('mealplan-price-reference-standard', 'PriceReference',
               'Price references',
               'Month-level $/kg by source type (chain named, independents '
               'typed only); purchaser, place and day stripped.',
               [('food_name', 'Food', 'str', 160),
                ('month', 'Month', 'str', 90),
                ('source_type', 'Source type', 'str', 120),
                ('chain_name', 'Chain', 'str', 120),
                ('region_label', 'Region', 'str', 150),
                ('price_per_kg_median', 'Median $/kg', 'float', 100),
                ('price_per_kg_min', 'Min', 'float', 80),
                ('price_per_kg_max', 'Max', 'float', 80),
                ('sample_count', 'Samples', 'int', 80),
                ('varies_by_vendor', 'Varies by vendor', 'bool', 120)]),
    _table_def('mealplan-intake-standard', 'IntakeRecord',
               'Intake records', 'What was actually eaten.',
               [('person_name', 'Person', 'str', 110),
                ('date', 'Date', 'str', 110),
                ('slot', 'Slot', 'str', 90),
                ('template_name', 'Meal', 'str', 170),
                ('variation_name', 'Variation', 'str', 190),
                ('scale', 'Scale', 'float', 70),
                ('source', 'Source', 'str', 90)]),
    _table_def('mealplan-account-link-standard', 'UserAccountLink',
               'Account links', 'Keycloak login → person (no silent '
               'provisioning).',
               [('keycloak_username', 'Keycloak user', 'str', 150),
                ('keycloak_email', 'Email', 'str', 200),
                ('person_name', 'Person', 'str', 120),
                ('household_name', 'Household', 'str', 140),
                ('linked_date', 'Linked', 'str', 110)]),
    _table_def('mealplan-weight-standard', 'WeightObservation',
               'Weight observations', 'Measured weights (facts).',
               [('person_name', 'Person', 'str', 110),
                ('date', 'Date', 'str', 110),
                ('weight_kg', 'Weight (kg)', 'float', 100),
                ('context', 'Context', 'str', 200)]),
    _table_def('mealplan-day-metric-standard', 'DailyIntakeMetric',
               'Day metrics', 'Derive-on-demand day rollups (gap days '
               'have no row).',
               [('date', 'Date', 'str', 110),
                ('meals_logged', 'Meals', 'int', 70),
                ('calories', 'kcal', 'float', 80),
                ('protein_g', 'Protein (g)', 'float', 90),
                ('fiber_g', 'Fiber (g)', 'float', 80),
                ('sodium_mg', 'Sodium (mg)', 'float', 100),
                ('max_meal_gl', 'Max meal GL', 'float', 100),
                ('max_meal_acid_share', 'Max acid share', 'float', 110),
                ('day_warning_count', 'Warnings', 'int', 80)]),
    _table_def('mealplan-exclusion-standard', 'PersonExclusion',
               'Declared exclusions', 'Allergies/exclusions in the '
               'person\'s own words — a hard safety filter.',
               [('person_name', 'Person', 'str', 110),
                ('allergen_class', 'Allergen class', 'str', 130),
                ('food_name', 'Food', 'str', 150),
                ('severity', 'Severity', 'str', 100),
                ('stated_reason', 'Stated reason', 'str', 260)]),
    _table_def('mealplan-condition-standard', 'StatedCondition',
               'Stated conditions', 'Conditions stated by the person '
               '("do not make it worse" — never diagnosis).',
               [('person_name', 'Person', 'str', 110),
                ('condition', 'Condition', 'str', 140),
                ('stated_reason', 'Stated reason', 'str', 260),
                ('declared_date', 'Declared', 'str', 110)]),
    _table_def('mealplan-steering-standard', 'ConditionSteering',
               'Condition steering', 'Cited do-not-worsen guidance per '
               'condition.',
               [('condition', 'Condition', 'str', 130),
                ('display_name', 'Guidance name', 'str', 180),
                ('guidance', 'Guidance', 'str', 320),
                ('confidence', 'Confidence', 'str', 100),
                ('citation', 'Citation', 'str', 260)]),
    _table_def('mealplan-budget-standard', 'PlanBudget',
               'Plan budgets', 'The weekly envelope a plan is held to.',
               [('plan_name', 'Plan', 'str', 150),
                ('household_name', 'Household', 'str', 140),
                ('weekly_amount', 'Weekly cap', 'float', 100),
                ('currency', 'Cur.', 'str', 60),
                ('scope_note', 'Scope', 'str', 300)]),
    _table_def('mealplan-waste-standard', 'WasteRecord',
               'Waste records', 'Food wasted — the honest budget leak.',
               [('food_name', 'Food', 'str', 160),
                ('quantity', 'Qty', 'float', 70),
                ('unit', 'Unit', 'str', 70),
                ('reason', 'Reason', 'str', 130),
                ('date', 'Date', 'str', 110),
                ('pantry_item_name', 'Pantry lot', 'str', 170)]),
    _table_def('mealplan-rating-standard', 'MealRating',
               'Meal ratings', 'How meals were rated after eating.',
               [('person_name', 'Person', 'str', 110),
                ('template_name', 'Meal', 'str', 170),
                ('variation_name', 'Variation', 'str', 190),
                ('rating', 'Rating', 'int', 70),
                ('date', 'Date', 'str', 110),
                ('note', 'Note', 'str', 260)]),
    # cal-4/5: the event layer's own tables — generated + personal
    # events, the no-code triggers and their firings, bulk staples.
    _table_def('mealplan-event-standard', 'CalendarEvent',
               'Calendar events', 'Purchase / bulk-purchase / pre-prep / '
               'meal-prep events the triggers generate, plus your own.',
               [('title', 'Event', 'str', 240),
                ('category', 'Category', 'str', 110),
                ('span', 'When (start/end)', 'str', 260),
                ('status', 'Status', 'str', 90),
                ('generated_by', 'Generated by', 'str', 170),
                ('linked_name', 'Linked to', 'str', 170),
                ('household_name', 'Household', 'str', 130)]),
    _table_def('mealplan-trigger-standard', 'EventTrigger',
               'Event triggers', 'The no-code event logic: when X happens, '
               'run solution Y (disable = the knob).',
               [('name', 'Trigger', 'str', 190),
                ('enabled', 'On', 'bool', 60),
                ('source_kind', 'Source', 'str', 90),
                ('solution_name', 'Solution', 'str', 220),
                ('cooldown_s', 'Cooldown (s)', 'float', 100),
                ('fire_count', 'Fired', 'int', 70),
                ('last_fired', 'Last fired', 'str', 150),
                ('description', 'What it does', 'str', 320)]),
    _table_def('mealplan-firing-standard', 'TriggerFiring',
               'Trigger firings', 'Every firing, audited: status, source, '
               'depth, the plain error when it failed.',
               [('fired_at', 'Fired at', 'str', 150),
                ('trigger_name', 'Trigger', 'str', 190),
                ('status', 'Status', 'str', 90),
                ('source_kind', 'Source', 'str', 90),
                ('source_ref', 'From', 'str', 240),
                ('depth', 'Depth', 'int', 60),
                ('error', 'Error', 'str', 300)]),
    _table_def('mealplan-bulk-staple-standard', 'BulkStaple',
               'Bulk staples', 'Long-shelf-life foods bought on a cadence: '
               'shelf life (cited prior), the bulk offer, the cadence knob.',
               [('food_name', 'Food', 'str', 160),
                ('cadence_months', 'Every (months)', 'int', 110),
                ('shelf_life_days', 'Shelf life (d)', 'int', 110),
                ('bulk_package_quantity', 'Pkg qty', 'float', 80),
                ('bulk_package_unit', 'Unit', 'str', 60),
                ('bulk_price', 'Bulk price', 'float', 90),
                ('bulk_location_name', 'Where', 'str', 140),
                ('confidence', 'Confidence', 'str', 110)]),
    # mlg-1..4: the household logistics tables (schedules, sleep,
    # members, policies, situations, skills, safety, dishes, ledger).
    _table_def('mealplan-member-standard', 'HouseholdMember', 'Household members',
               'Who is in the household and how they take part in purchases.',
               [('person_name', 'Person', 'str', 130), ('role', 'Role', 'str', 80),
                ('purchase_participation', 'Purchase trips', 'str', 120),
                ('can_drive', 'Drives', 'bool', 70),
                ('has_workplace_meals', 'Eats at work', 'bool', 100)]),
    _table_def('mealplan-schedule-standard', 'PersonSchedule', 'Schedules',
               'Recurring commitments — work, commute, sleep — with where.',
               [('person_name', 'Person', 'str', 120), ('kind', 'Kind', 'str', 90),
                ('display_name', 'Block', 'str', 220), ('location_kind', 'Where', 'str', 100),
                ('location_name', 'Location', 'str', 140),
                ('recurrence', 'Recurrence', 'str', 320),
                ('flexibility_min', 'Flex (min)', 'int', 90)]),
    _table_def('mealplan-sleep-standard', 'SleepPreference', 'Sleep preferences',
               'Bedtime, wake, and the dinner→sleep spacing (yours; default 2 h).',
               [('person_name', 'Person', 'str', 120), ('bedtime_hhmm', 'Bed', 'str', 70),
                ('wake_hhmm', 'Wake', 'str', 70),
                ('dinner_to_sleep_min', 'Dinner→sleep (min)', 'int', 140),
                ('late_snack_ok', 'Late snack ok', 'bool', 100),
                ('stated_reason', 'Stated reason', 'str', 200),
                ('citation', 'Citation', 'str', 320)]),
    _table_def('mealplan-workload-type-standard', 'WorkloadType', 'Workload types',
               'The distinct kinds of meal-prep work.',
               [('name', 'Type', 'str', 130), ('display_name', 'Name', 'str', 180),
                ('description', 'What it covers', 'str', 320),
                ('default_skills_json', 'Default skills', 'str', 200)]),
    _table_def('mealplan-work-policy-standard', 'WorkDistributionPolicy', 'Work distribution',
               'How each workload type is split: shares (%), rotation, assigned, delivery.',
               [('workload_type', 'Workload', 'str', 120), ('mode', 'Mode', 'str', 90),
                ('shares_json', 'Shares (%)', 'str', 200),
                ('share_tolerance_pct', 'Tolerance %', 'float', 90),
                ('delivery_fee', 'Delivery fee', 'float', 90),
                ('delivery_markup_pct', 'Markup %', 'float', 80),
                ('labor_value_per_hour', 'Labor $/h (yours)', 'str', 110),
                ('travel_min_per_trip', 'Trip (min)', 'float', 80)]),
    _table_def('mealplan-work-ledger-standard', 'WorkLedger', 'Work ledger',
               'Minutes of work actually done, by person and type.',
               [('date', 'Date', 'str', 110), ('person_name', 'Person', 'str', 120),
                ('workload_type', 'Workload', 'str', 120), ('minutes', 'Minutes', 'float', 80),
                ('event_name', 'Event', 'str', 220), ('source', 'Source', 'str', 100)]),
    _table_def('mealplan-situation-standard', 'MealSituation', 'Meal situations',
               'Where a meal is eaten and what that needs (container, cold packs).',
               [('name', 'Situation', 'str', 150), ('eaten_at', 'Eaten at', 'str', 90),
                ('reheat_available', 'Reheat', 'bool', 70),
                ('needs_container', 'Container', 'str', 140),
                ('cold_pack_count', 'Cold packs', 'int', 80),
                ('cold_hours_required', 'Cold hours', 'float', 90),
                ('pack_minutes', 'Pack (min)', 'float', 80), ('pack_when', 'Pack when', 'str', 100),
                ('citation', 'Citation', 'str', 260)]),
    _table_def('mealplan-logistics-standard', 'MealLogistics', 'Meal logistics',
               'Which planned meal is eaten where, by whom, packed how.',
               [('entry_name', 'Plan entry', 'str', 220), ('person_name', 'Person', 'str', 120),
                ('situation_name', 'Situation', 'str', 150),
                ('container_tool_name', 'Container', 'str', 140),
                ('cold_pack_count', 'Cold packs', 'int', 80), ('pack_when', 'Pack when', 'str', 100)]),
    _table_def('mealplan-skill-standard', 'SkillDefinition', 'Skills',
               'The skill vocabulary (safety skills bound speed).',
               [('name', 'Skill', 'str', 140), ('display_name', 'Name', 'str', 160),
                ('is_safety', 'Safety skill', 'bool', 90),
                ('description', 'Description', 'str', 360)]),
    _table_def('mealplan-person-skill-standard', 'PersonSkill', 'Skill profiles',
               'Each person\'s level + speed factor per skill (priors, refined).',
               [('person_name', 'Person', 'str', 120), ('skill_name', 'Skill', 'str', 140),
                ('level', 'Level', 'str', 110), ('speed_factor', 'Speed factor', 'float', 100),
                ('fidelity', 'Fidelity', 'str', 90),
                ('observation_count', 'Observations', 'int', 100)]),
    _table_def('mealplan-method-skill-standard', 'MethodSkillRequirement', 'Skills per step',
               'What a step method needs: skills, the safety floor, hazards.',
               [('method_name', 'Method', 'str', 160), ('task_kind', 'Task', 'str', 90),
                ('skills_json', 'Skills (floor)', 'str', 240),
                ('safety_floor_min', 'Safety floor (min)', 'float', 120),
                ('hazard_tags_json', 'Hazards', 'str', 180)]),
    _table_def('mealplan-safety-rule-standard', 'SafetyRule', 'Safety rules',
               'hazard → the safety level required, else supervised (cited).',
               [('hazard_tag', 'Hazard', 'str', 100), ('skill_name', 'Skill', 'str', 130),
                ('required_level', 'Required level', 'str', 120),
                ('below_floor', 'Below floor', 'str', 100), ('rule_text', 'Rule', 'str', 300),
                ('citation', 'Citation', 'str', 240), ('confidence', 'Confidence', 'str', 100)]),
    _table_def('mealplan-duration-obs-standard', 'DurationObservation', 'Duration observations',
               'How long steps and meals actually took — the refinement loop\'s facts.',
               [('date', 'Date', 'str', 110), ('person_name', 'Person', 'str', 120),
                ('kind', 'Kind', 'str', 100), ('method_name', 'Method', 'str', 150),
                ('skill_name', 'Skill', 'str', 130), ('observed_min', 'Observed (min)', 'float', 110),
                ('source', 'Source', 'str', 90)]),
    _table_def('mealplan-meal-time-standard', 'MealTimeProfile', 'Eating time',
               'Eating minutes per person × slot (household priors, refined).',
               [('person_name', 'Person', 'str', 120), ('slot', 'Slot', 'str', 100),
                ('eating_min', 'Eating (min)', 'float', 100), ('fidelity', 'Fidelity', 'str', 90)]),
    _table_def('mealplan-dish-strategy-standard', 'DishStrategy', 'Dish strategies',
               'Ways to do the dishes, their minutes per load and timing.',
               [('name', 'Strategy', 'str', 160), ('timing', 'Timing', 'str', 130),
                ('needs_tool', 'Needs', 'str', 110), ('min_per_load_unit', 'Min / load unit', 'float', 110),
                ('setup_min', 'Setup (min)', 'float', 90), ('cycle_min', 'Cycle (min)', 'float', 90),
                ('unload_min', 'Unload (min)', 'float', 90), ('description', 'Description', 'str', 300)]),
    _table_def('mealplan-dish-policy-standard', 'HouseholdDishPolicy', 'Dish policy',
               'Which strategy the household uses for sessions and meals.',
               [('household_name', 'Household', 'str', 140),
                ('preprep_strategy', 'After pre-prep', 'str', 160),
                ('meal_strategy', 'After meals', 'str', 160),
                ('cooldown_after_eating_min', 'Cooldown (min)', 'float', 110)]),
    # mpt: the week / month condensation rows.
    _table_def('mealplan-period-standard', 'PeriodIntakeMetric', 'Period means',
               'Week / month means per logged day (the cache the period charts read).',
               [('period_kind', 'Period', 'str', 80), ('period_start', 'Start', 'str', 110),
                ('period_end', 'End', 'str', 110), ('days_logged', 'Logged', 'int', 70),
                ('calories_mean', 'kcal', 'float', 80), ('protein_g_mean', 'Protein', 'float', 80),
                ('carbohydrate_g_mean', 'Carbs', 'float', 80), ('fiber_g_mean', 'Fiber', 'float', 70),
                ('sodium_mg_mean', 'Sodium', 'float', 80), ('max_meal_gl_mean', 'Max GL', 'float', 80),
                ('max_meal_acid_share_mean', 'Acid share', 'float', 90),
                ('weight_kg_mean', 'Weight', 'float', 80), ('low_confidence', 'Low conf.', 'bool', 80)]),
    # mpc: the meals vocabulary the meals page offers.
    _table_def('mealplan-template-standard', 'MealTemplate', 'Meals',
               'The meals (templates) a household can plan — recipes + the slots they suit.',
               [('name', 'Meal', 'str', 170), ('display_name', 'Name', 'str', 180),
                ('slots_json', 'Suits slots', 'str', 160), ('dish_base', 'Dish base', 'str', 120),
                ('description', 'Description', 'str', 320)]),
    _table_def('mealplan-variation-standard', 'VariationDefinition', 'Variations',
               'Swaps of a meal (tofu for chicken…) with the portion bounds a scale may use.',
               [('name', 'Variation', 'str', 200), ('template_name', 'Meal', 'str', 170),
                ('display_name', 'Name', 'str', 180), ('scale_min', 'Scale min', 'float', 90),
                ('scale_max', 'Scale max', 'float', 90), ('swaps_json', 'Swaps', 'str', 260)]),
    # Not this class's default (nutrition owns NutrientContent) — a
    # purchase-preview view only.
    _table_def('mealplan-nutrient-content-view', 'NutrientContent',
               'Nutrient content per 100 g', 'FDC-cited nutrient '
               'content of one food, per 100 g.',
               [('nutrient_name', 'Nutrient', 'str', 150),
                ('amount_per_100g', 'Per 100 g', 'float', 100),
                ('unit', 'Unit', 'str', 70),
                ('source', 'Source', 'str', 320)],
               defaults=False),
]


# --------------------------------------------------------------------
# GraphDefinition rows — the trend charts (embedded BY NAME).
# --------------------------------------------------------------------

SEED_MEALPLAN_GRAPHS = [
    {'name': 'mealplan-weight-trend',
     'description': 'Measured weights over time for one person '
                    '(facts, never the Hall projection — drift '
                    'between the two lives on the profile page).',
     'source_class': 'WeightObservation',
     'definition': json.dumps({'graphConfig': {
         'renderStyle': 'dot',
         'xDimension': 'date',
         'yDimensions': ['weight_kg'],
         'seriesColors': ['#2e7d32'],
         'options': {
             'width': 800, 'height': 320,
             'marginTop': 20, 'marginRight': 30,
             'marginBottom': 40, 'marginLeft': 60,
             'showLegend': False, 'showGrid': True,
             'xLabel': 'date', 'yLabel': 'weight (kg)',
         },
         'aggregation': {'enabled': False, 'strategy': 'average'},
     }})},
]


def _metric_graph(name, description, y_dims, y_label, colors):
    """mpa-8: day-series charts over the DailyIntakeMetric cache
    rows (derive-on-demand: reading /series refreshes them)."""
    return {'name': name, 'description': description,
            'source_class': 'DailyIntakeMetric',
            'definition': json.dumps({'graphConfig': {
                'renderStyle': 'lineY',
                'xDimension': 'date',
                'yDimensions': list(y_dims),
                'seriesColors': list(colors),
                'options': {
                    'width': 800, 'height': 280,
                    'marginTop': 20, 'marginRight': 30,
                    'marginBottom': 40, 'marginLeft': 60,
                    'showLegend': len(y_dims) > 1,
                    'showGrid': True,
                    'xLabel': 'date', 'yLabel': y_label,
                },
                'aggregation': {'enabled': False,
                                'strategy': 'average'},
            }})}


SEED_MEALPLAN_GRAPHS += [
    _metric_graph('mealplan-calories-trend',
                  'Calories per day from logged intake (cache rows '
                  'refresh when the series is read; gap days have '
                  'no row — honest absence, not zeros).',
                  ['calories'], 'kcal/day', ['#1565c0']),
    _metric_graph('mealplan-gl-trend',
                  'The day\'s MAX per-meal glycemic load (spike '
                  'metric; GL>20 = the published high convention).',
                  ['max_meal_gl'], 'max per-meal GL', ['#ef6c00']),
    _metric_graph('mealplan-acid-trend',
                  'The day\'s MAX per-meal acid mass share '
                  '(fraction of meal mass at pH<=4.6; comfort '
                  'heuristic, not medical advice).',
                  ['max_meal_acid_share'], 'max acid share (0-1)',
                  ['#c62828']),
]


def _period_graph(name, description, y_dim, y_label, color, style='lineY'):
    """mpt: charts over the PeriodIntakeMetric cache — the SAME
    definition serves weeks and months; the embed's filter
    series_key '<person>:week' | '<person>:month' picks the view."""
    return {'name': name, 'description': description,
            'source_class': 'PeriodIntakeMetric',
            'definition': json.dumps({'graphConfig': {
                'renderStyle': style, 'xDimension': 'period_start',
                'yDimensions': [y_dim], 'seriesColors': [color],
                'options': {'width': 800, 'height': 260, 'marginTop': 20,
                            'marginRight': 30, 'marginBottom': 40, 'marginLeft': 60,
                            'showLegend': False, 'showGrid': True,
                            'xLabel': 'period start', 'yLabel': y_label},
                'aggregation': {'enabled': False, 'strategy': 'average'},
            }})}


SEED_MEALPLAN_GRAPHS += [
    _period_graph('mealplan-period-calories', 'Mean kcal per logged day, per period.',
                  'calories_mean', 'kcal/day (mean)', '#1565c0'),
    _period_graph('mealplan-period-carbs', 'Mean carbohydrate per logged day ("sweets" '
                  'proxy with GL — no sugars column in the FDC set).',
                  'carbohydrate_g_mean', 'carbohydrate g/day (mean)', '#ef6c00'),
    _period_graph('mealplan-period-sodium', 'Mean sodium per logged day vs the CDRR.',
                  'sodium_mg_mean', 'sodium mg/day (mean)', '#6a1b9a'),
    _period_graph('mealplan-period-gl', 'Mean of the day\'s highest-GL meal (GL>20 = high).',
                  'max_meal_gl_mean', 'max meal GL (mean)', '#c62828'),
    _period_graph('mealplan-period-acid', 'Mean of the day\'s most acidic meal (share).',
                  'max_meal_acid_share_mean', 'max acid share (mean)', '#ad1457'),
    _period_graph('mealplan-period-protein', 'Mean protein per logged day vs the target.',
                  'protein_g_mean', 'protein g/day (mean)', '#2e7d32'),
    _period_graph('mealplan-period-weight', 'Mean measured weight per period.',
                  'weight_kg_mean', 'weight kg (mean)', '#455a64', style='dot'),
]


# --------------------------------------------------------------------
# Page items — three registered components, nothing bespoke.
# --------------------------------------------------------------------

#: Which seeded TableDefinition each embeddedTable item points at, BY
#: NAME — filled by _etable(); _repoint_display_refs resolves the ids
#: on this node after the upsert (motors_pages pattern).
EMBED_TARGETS = {}


def _item(item_id, index, segments, title, component, inputs):
    return {'id': item_id, 'index': index, 'type': 'component',
            'rowSegmentsUsed': segments, 'gridColumnStart': None,
            'title': title, 'visible': True, 'collapsed': False,
            'cssClass': '', 'item': None, 'nestedRows': [],
            'componentProps': {'componentName': component,
                               'inputs': inputs}}


def _etable(item_id, index, segments, title, table_name, class_name,
            filter_field='', filter_value=''):
    """A configured TableDefinition, embedded and scoped."""
    EMBED_TARGETS[item_id] = ('TableDefinition', table_name)
    return _item(item_id, index, segments, title, 'embeddedTable',
                 {'tableConfigId': '', 'className': class_name,
                  'filterField': filter_field,
                  'filterValue': filter_value})


def _egraph(item_id, index, segments, title, graph_name, class_name,
            filter_field='', filter_value=''):
    """A configured GraphDefinition, embedded BY NAME and scoped."""
    return _item(item_id, index, segments, title, 'embeddedGraph',
                 {'graphName': graph_name, 'className': class_name,
                  'filterField': filter_field,
                  'filterValue': filter_value})


def _ecal(item_id, index, segments, title, calendar_name, person='',
          household='', view='', editable=False):
    """A configured CalendarDefinition, embedded BY NAME (cal-3)."""
    return _item(item_id, index, segments, title, 'embeddedCalendar',
                 {'calendarName': calendar_name, 'person': person,
                  'household': household, 'view': view,
                  'editable': editable})


def _form(item_id, index, segments, title, solution_name, variables,
          submit_label='Apply'):
    """A no-code FORM item (P4 real forms): its fields become the
    linked solution's input context. `variables` = [(name, label,
    dataType, default, placeholder, required)]. '{object}' in a
    default is substituted by the display page (per-object pages)."""
    return {'id': item_id, 'index': index, 'type': 'form',
            'rowSegmentsUsed': segments, 'gridColumnStart': None,
            'title': title, 'visible': True, 'collapsed': False,
            'cssClass': '', 'componentProps': {}, 'nestedRows': [],
            'item': {'boundClassName': '', 'formFields': [],
                     'linkedSolutionName': solution_name,
                     'formLayout': 'grid', 'submissionMode': 'button',
                     'submitLabel': submit_label, 'debounceDelayMs': 1500,
                     'extraVariables': [
                         {'variableName': n, 'displayName': label,
                          'dataType': dtype, 'defaultValue': default,
                          'placeholder': ph, 'required': req}
                         for n, label, dtype, default, ph, req in variables]}}


#: the "use this meal for the week" form — the same on the meals page
#: (person pre-filled from ?object=) and the week page.
def _apply_meal_form(item_id, index, segments, person_default):
    return _form(
        item_id, index, segments,
        'Use this meal for the week — any slots × any days; portions fit '
        'each person (compromise stated)',
        'mealplan-apply-meal-to-week', [
            ('plan', 'Plan', 'string', PLAN, 'MealPlanDefinition name', True),
            ('template', 'Meal', 'string', '', 'a MealTemplate name (see the meals table)', True),
            ('variation', 'Variation', 'string', '', 'blank = the base variation', False),
            ('slots', 'Slots', 'string', 'all', 'e.g. breakfast,dinner — or all', False),
            ('days', 'Days', 'string', 'all', 'e.g. 1,3,5 — or all', False),
            ('person', 'Person', 'string', person_default,
             'blank = the whole household (one portion each)', False),
            ('scale', 'Fixed scale (0 = fit portions)', 'number', 0,
             '0 fits each portion to the person; >0 forces one scale', False),
        ], submit_label='Add to the week')


def _emap(item_id, index, segments, title, geojson_name, class_name,
          filter_field='', filter_value='', height='520px'):
    """A configured GeoJsonDefinition, embedded BY NAME (mps)."""
    return _item(item_id, index, segments, title, 'embeddedMap',
                 {'geoJsonName': geojson_name, 'className': class_name,
                  'filterField': filter_field, 'filterValue': filter_value,
                  'height': height})


#: mps: the Food Supply map — SourceLocation pins (grocery, farmers
#: market, warehouse club, workplace) by their lat/lon fields.
SEED_MEALPLAN_GEOJSON = [
    {'name': 'mealplan-food-sources',
     'description': 'Where the household buys food (and where it works): '
                    'SourceLocation rows by latitude/longitude.',
     'source_class': 'SourceLocation',
     'definition': json.dumps({'geoJsonConfig': {
         'coordinateMode': 'separate', 'latitudeVariable': 'latitude',
         'longitudeVariable': 'longitude', 'defaultMarkerName': 'default-pin',
         'mapOptions': {'center': [-77.05, 38.9], 'zoom': 10}}})},
]


def _sapi(item_id, index, segments, title, path, pick='', hide=''):
    """A derived verdict through the generic STRUCTURED reading
    (chips / prose / tables). `pick` = dot-path to render; `hide` =
    csv of keys to drop — used so no key is left for the JSON
    expander (dict-of-dicts and empty dicts would land there)."""
    return _item(item_id, index, segments, title, 'api-structured-panel',
                 {'path': path, 'pick': pick, 'hideKeys': hide,
                  'title': ''})


_MP = '/api/mealplanning'

SEED_MEALPLAN_PAGE_DISPLAYS = [
    _page(
        'mealplan-home', 'mealplan',
        'cal-5: the meal-planning front door IS the calendar — the '
        'week\'s planned meals, the purchase / bulk-purchase / '
        'pre-prep / meal-prep events the no-code triggers generate, '
        'what was eaten, activity and weight, one calendar with '
        'layer toggles; drag to move (confirm), click to open the '
        'row. Below it: today, your events, log what you ate, and '
        'the bulk-staple knobs.',
        'MealPlanDefinition',
        [
            _row(0, [
                _ecal('mp-week', 0, 12,
                      f'This week — {HOUSEHOLD} (meals · purchases · '
                      'prep · eaten · activity · weight)',
                      'mealplan-week', household=HOUSEHOLD,
                      editable=True),
            ], min_height=680),
            _row(1, [
                _sapi('mp-me', 0, 3, 'Me (this login)', f'{_MP}/me'),
                _sapi('mp-week-planned', 1, 3,
                      f'Is the week planned? — {PLAN}',
                      f'{_MP}/plans/{PLAN}/week-coverage',
                      hide='grid,perPerson,perDay,missing'),
                _sapi('mp-today', 2, 3,
                      f'Today — coverage steering ({PERSON})',
                      f'{_MP}/users/{PERSON}/coverage'),
                _sapi('mp-dashboard', 3, 3, f'Dashboard — {PERSON}',
                      f'{_MP}/users/{PERSON}/dashboard',
                      hide='latestDay,links'),
            ]),
            _row(2, [
                _etable('mp-upcoming', 0, 6,
                        f'Events — {HOUSEHOLD} (generated + yours; '
                        'Create New adds one)',
                        'mealplan-event-standard', 'CalendarEvent',
                        'household_name', HOUSEHOLD),
                _etable('mp-log-intake', 1, 6,
                        f'Log what you ate — {PERSON} (Create New)',
                        'mealplan-intake-standard', 'IntakeRecord',
                        'person_name', PERSON),
            ]),
            _row(3, [
                _etable('mp-bulk', 0, 6,
                        f'Bulk staples — {HOUSEHOLD} (cadence, shelf '
                        'life, bulk offer: your knobs)',
                        'mealplan-bulk-staple-standard', 'BulkStaple',
                        'household_name', HOUSEHOLD),
                _sapi('mp-bulk-yearly', 1, 6,
                      'Bulk buy proposal — yearly cadence (rice, '
                      'pasta, sugar): demand vs stock, bulk vs '
                      'retail $/kg, savings',
                      f'{_MP}/bulk-proposal?household={HOUSEHOLD}'
                      '&cadence=12', hide='proposals'),
            ]),
        ]),
    _page(
        'mealplan-meals', 'mealplan/meals',
        'mpc: meals for ONE person — open with ?object=<person>. The '
        'meals ranked for them, their slots, the variations, and the '
        'form that turns a meal into the week\'s entries (any slots × '
        'any days) with per-person portions fitted to each member\'s '
        'targets — the compromise stated, never hidden. Pre-prep, '
        'packing, dishes and the allocation follow through the triggers.',
        'MealTemplate',
        [
            _row(0, [
                _sapi('mp-ranked', 0, 6, 'Meals ranked for {object} (ratings, exclusions)',
                      f'{_MP}/users/{{object}}/templates-ranked', pick='ranked'),
                _sapi('mp-slots', 1, 6, 'Slots {object} eats (their eating pattern)',
                      f'{_MP}/users/{{object}}/expected-slots', pick='slots'),
            ]),
            _row(1, [
                _etable('mp-templates', 0, 6, 'Meals (templates)',
                        'mealplan-template-standard', 'MealTemplate'),
                _etable('mp-variations', 1, 6, 'Variations (swaps + portion bounds)',
                        'mealplan-variation-standard', 'VariationDefinition'),
            ]),
            _row(2, [
                _apply_meal_form('mp-apply-meal', 0, 12, '{object}'),
            ]),
            _row(3, [
                _sapi('mp-portions-dinner', 0, 6,
                      'Portions — chicken-bowl-dinner at dinner, per person (fit vs target)',
                      f'{_MP}/templates/chicken-bowl-dinner/portion-fit?slot=dinner'
                      f'&household={HOUSEHOLD}', hide='fits'),
                _sapi('mp-portions-dinner-fits', 1, 6, 'Per-person fit',
                      f'{_MP}/templates/chicken-bowl-dinner/portion-fit?slot=dinner'
                      f'&household={HOUSEHOLD}', pick='fits'),
            ]),
            _row(4, [
                _etable('mp-entries-meals', 0, 12, f'The week so far — {PLAN}',
                        'mealplan-entry-standard', 'MealEntry', 'plan_name', PLAN),
            ]),
        ]),
    _page(
        'mealplan-week', 'mealplan/week',
        'mpc: plan the week — is every meal planned? The person × day × '
        'slot grid names each missing meal; add a meal to any slots × '
        'days from here; the entries table is the plan.',
        'MealPlanDefinition',
        [
            _row(0, [
                _sapi('mp-coverage-head', 0, 6, f'Is the week planned? — {PLAN}',
                      f'{_MP}/plans/{PLAN}/week-coverage',
                      hide='grid,perPerson,perDay,missing'),
                _sapi('mp-coverage-missing', 1, 6, 'Missing meals (person × day × slot)',
                      f'{_MP}/plans/{PLAN}/week-coverage', pick='missing'),
            ]),
            _row(1, [
                _sapi('mp-coverage-person', 0, 4, 'Per person',
                      f'{_MP}/plans/{PLAN}/week-coverage', pick='perPerson'),
                _sapi('mp-coverage-day', 1, 4, 'Per day',
                      f'{_MP}/plans/{PLAN}/week-coverage', pick='perDay'),
                _etable('mp-plans-week', 2, 4, 'Plans',
                        'mealplan-plan-standard', 'MealPlanDefinition'),
            ]),
            _row(2, [
                _apply_meal_form('mp-apply-meal-week', 0, 12, ''),
            ]),
            _row(3, [
                _sapi('mp-coverage-grid', 0, 12, 'The grid — every expected meal, planned or missing',
                      f'{_MP}/plans/{PLAN}/week-coverage', pick='grid'),
            ]),
            _row(4, [
                _etable('mp-entries-week', 0, 12, f'Entries — {PLAN} (edit / delete here)',
                        'mealplan-entry-standard', 'MealEntry', 'plan_name', PLAN),
            ]),
        ]),
    _page(
        'mealplan-me', 'mealplan/me',
        'mpt: ONE person over time — open with ?object=<person>. Log '
        'what you ate and your weight here; the day series, then the '
        'same metrics condensed to WEEK and MONTH means per logged day '
        'against your own lines (calorie envelope, targets, the sodium '
        'CDRR, GL>20, the acid-share row) — so a consistent "too much" '
        '(salty, sweets/refined carbs, acid-inducing, calories) or '
        '"too little" (calories, protein, fiber, carbs) shows itself. '
        'Comfort readings over your own targets, never diagnosis.',
        'IntakeRecord',
        [
            _row(0, [
                _sapi('mp-me-week', 0, 6, 'By WEEK — {object} (means per logged day)',
                      f'{_MP}/users/{{object}}/periods?kind=week',
                      hide='periods,lines,consistency'),
                _sapi('mp-me-month', 1, 6, 'By MONTH — {object}',
                      f'{_MP}/users/{{object}}/periods?kind=month',
                      hide='periods,lines,consistency'),
            ]),
            _row(1, [
                _sapi('mp-me-consist-w', 0, 6, 'Consistently too much / too little — weeks',
                      f'{_MP}/users/{{object}}/periods?kind=week', pick='consistency'),
                _sapi('mp-me-consist-m', 1, 6, 'Consistently too much / too little — months',
                      f'{_MP}/users/{{object}}/periods?kind=month', pick='consistency'),
            ]),
            # ENTER DATA
            _row(2, [
                _form('mp-me-log-intake', 0, 6, 'Log what I ate', 'mealplan-log-intake', [
                    ('person', 'Person', 'string', '{object}', '', True),
                    ('date', 'Date (YYYY-MM-DD, blank = today)', 'string', '', 'YYYY-MM-DD (blank = today)', False),
                    ('slot', 'Slot', 'string', 'dinner', 'breakfast / lunch / dinner / snack …', True),
                    ('template', 'Meal', 'string', '', 'a MealTemplate name', True),
                    ('variation', 'Variation', 'string', '', 'blank = base', False),
                    ('scale', 'Portion (× serving)', 'number', 1, '', False),
                    ('time', 'Time (HH:MM)', 'string', '', '18:30', False),
                ], submit_label='Log it'),
                _form('mp-me-log-weight', 1, 6, 'Log my weight', 'mealplan-log-weight', [
                    ('person', 'Person', 'string', '{object}', '', True),
                    ('date', 'Date (YYYY-MM-DD, blank = today)', 'string', '', 'YYYY-MM-DD (blank = today)', False),
                    ('weight_kg', 'Weight (kg)', 'number', '', '80.1', True),
                    ('context', 'Context', 'string', 'morning', 'morning / evening / after workout', False),
                ], submit_label='Log it'),
            ]),
            # DAY series (the existing charts, this person)
            _row(3, [
                _egraph('mp-me-cal-day', 0, 6, 'Calories per day — {object}',
                        'mealplan-calories-trend', 'DailyIntakeMetric', 'person_name', '{object}'),
                _egraph('mp-me-weight-day', 1, 6, 'Weight — {object} (measured)',
                        'mealplan-weight-trend', 'WeightObservation', 'person_name', '{object}'),
            ], min_height=300),
            _row(4, [
                _egraph('mp-me-gl-day', 0, 6, 'Max per-meal GL per day — {object}',
                        'mealplan-gl-trend', 'DailyIntakeMetric', 'person_name', '{object}'),
                _egraph('mp-me-acid-day', 1, 6, 'Max per-meal acid share per day — {object}',
                        'mealplan-acid-trend', 'DailyIntakeMetric', 'person_name', '{object}'),
            ], min_height=300),
            # WEEK means
            _row(5, [
                _egraph('mp-me-cal-week', 0, 4, 'WEEKLY mean kcal/day', 'mealplan-period-calories',
                        'PeriodIntakeMetric', 'series_key', '{object}:week'),
                _egraph('mp-me-carbs-week', 1, 4, 'WEEKLY mean carbohydrate/day', 'mealplan-period-carbs',
                        'PeriodIntakeMetric', 'series_key', '{object}:week'),
                _egraph('mp-me-sodium-week', 2, 4, 'WEEKLY mean sodium/day (salty foods)',
                        'mealplan-period-sodium', 'PeriodIntakeMetric', 'series_key', '{object}:week'),
            ], min_height=290),
            _row(6, [
                _egraph('mp-me-gl-week', 0, 4, 'WEEKLY mean max-meal GL (sweets / refined carbs)',
                        'mealplan-period-gl', 'PeriodIntakeMetric', 'series_key', '{object}:week'),
                _egraph('mp-me-acid-week', 1, 4, 'WEEKLY mean acid share (acid-inducing foods)',
                        'mealplan-period-acid', 'PeriodIntakeMetric', 'series_key', '{object}:week'),
                _egraph('mp-me-protein-week', 2, 4, 'WEEKLY mean protein/day', 'mealplan-period-protein',
                        'PeriodIntakeMetric', 'series_key', '{object}:week'),
            ], min_height=290),
            # MONTH means
            _row(7, [
                _egraph('mp-me-cal-month', 0, 4, 'MONTHLY mean kcal/day', 'mealplan-period-calories',
                        'PeriodIntakeMetric', 'series_key', '{object}:month'),
                _egraph('mp-me-sodium-month', 1, 4, 'MONTHLY mean sodium/day', 'mealplan-period-sodium',
                        'PeriodIntakeMetric', 'series_key', '{object}:month'),
                _egraph('mp-me-weight-month', 2, 4, 'MONTHLY mean weight', 'mealplan-period-weight',
                        'PeriodIntakeMetric', 'series_key', '{object}:month'),
            ], min_height=290),
            # the rows behind it (Create New works here too)
            _row(8, [
                _etable('mp-me-intake', 0, 6, 'What {object} ate (Create New logs a meal)',
                        'mealplan-intake-standard', 'IntakeRecord', 'person_name', '{object}'),
                _etable('mp-me-weights', 1, 6, 'Weights — {object} (Create New logs one)',
                        'mealplan-weight-standard', 'WeightObservation', 'person_name', '{object}'),
            ]),
            _row(9, [
                _etable('mp-me-periods', 0, 12, 'Period means — {object} (weeks and months)',
                        'mealplan-period-standard', 'PeriodIntakeMetric', 'person_name', '{object}'),
            ]),
            _row(10, [
                _sapi('mp-me-periods-week', 0, 6, 'Weeks — every bucket, its means and verdicts',
                      f'{_MP}/users/{{object}}/periods?kind=week', pick='periods'),
                _sapi('mp-me-lines', 1, 6, 'Your lines (the numbers the verdicts compare to)',
                      f'{_MP}/users/{{object}}/periods?kind=week', pick='lines'),
            ]),
        ]),
    _page(
        'mealplan-planner', 'mealplan/planner',
        'mpa-5: the week being planned — entries, rollup vs '
        'thresholds, what it costs, and whether the pantry covers '
        'it (adjust-by-availability suggestions never auto-edit).',
        'MealEntry',
        [
            _row(0, [
                _etable('mp-entries', 0, 6, f'Plan entries — {PLAN}',
                        'mealplan-entry-standard', 'MealEntry',
                        'plan_name', PLAN),
                _sapi('mp-plan-rollup', 1, 6,
                      f'Rollup per entry — {PLAN}',
                      f'/api/nutrition/plans/{PLAN}/rollup',
                      pick='entries'),
            ]),
            _row(1, [
                _sapi(f'mp-under-{d}', d - 1, 4,
                      f'Under target — day {d}',
                      f'/api/nutrition/plans/{PLAN}/rollup',
                      pick=f'days.{d}.underTarget')
                for d in (1, 2, 3)
            ]),
            _row(2, [
                _sapi('mp-plan-cost', 0, 6, f'Estimated cost — {PLAN}',
                      f'{_MP}/plans/{PLAN}/cost'),
                _sapi('mp-plan-avail', 1, 6, f'Pantry coverage — {PLAN}',
                      f'{_MP}/plans/{PLAN}/availability'),
            ]),
            _row(3, [
                _sapi('mp-plan-suggest', 0, 6,
                      'Stock-aware suggestions (yours to apply)',
                      f'{_MP}/plans/{PLAN}/suggestions'),
                _sapi('mp-prep', 1, 6,
                      'Prep schedule (total active minutes minimized)',
                      f'/api/nutrition/plans/{PLAN}/prep-schedule',
                      hide='dailyActions,workflowDag'),
            ]),
            _row(4, [
                _sapi('mp-prep-tasks', 0, 6, 'Prep tasks — the workflow',
                      f'/api/nutrition/plans/{PLAN}/prep-schedule',
                      pick='workflowDag.nodes'),
                _sapi('mp-protein-value', 1, 6,
                      'Protein per dollar (observed prices)',
                      f'{_MP}/nutrient-value?nutrient=protein',
                      hide='unpricedFoods,foodsWithoutNutrient'),
            ]),
            # mpb: safety + steering + budget on the same planner.
            _row(5, [
                _sapi('mp-exclusion-screen', 0, 6,
                      'Exclusion screen (declared allergies — hard '
                      'safety filter)',
                      f'{_MP}/plans/{PLAN}/exclusion-screen',
                      hide='declaredExclusions'),
                _etable('mp-exclusions-declared', 1, 6,
                        f'Declared exclusions — {PERSON}',
                        'mealplan-exclusion-standard',
                        'PersonExclusion', 'person_name', PERSON),
            ]),
            _row(6, [
                _sapi('mp-conditions', 0, 6,
                      'Stated-condition flags ("do not make it '
                      'worse" — never diagnosis)',
                      f'{_MP}/plans/{PLAN}/conditions'),
                _etable('mp-conditions-stated', 1, 6,
                        f'Stated conditions — {PERSON}',
                        'mealplan-condition-standard',
                        'StatedCondition', 'person_name', PERSON),
            ]),
            _row(7, [
                _etable('mp-steering', 0, 12,
                        'Condition steering (cited guidance rows)',
                        'mealplan-steering-standard',
                        'ConditionSteering'),
            ]),
            _row(8, [
                _sapi('mp-budget', 0, 6,
                      'Budget envelope — spend vs cap, drivers named',
                      f'{_MP}/plans/{PLAN}/budget'),
                _etable('mp-budget-rows', 1, 6, f'Plan budget — {PLAN}',
                        'mealplan-budget-standard', 'PlanBudget',
                        'plan_name', PLAN),
            ]),
            # cal-4/5: the week coordinated + the no-code event logic.
            _row(9, [
                _sapi('mp-coordination', 0, 12,
                      f'This week coordinated — purchase → pre-prep → '
                      f'meals → meal-prep ({PLAN}; rules named; the '
                      'triggers generate exactly these)',
                      f'{_MP}/plans/{PLAN}/coordination',
                      hide='proposals'),
            ]),
            _row(10, [
                _etable('mp-triggers', 0, 6,
                        'Event triggers — the no-code event logic '
                        '(disable = the knob)',
                        'mealplan-trigger-standard', 'EventTrigger'),
                _etable('mp-firings', 1, 6,
                        'Trigger firings — every run audited',
                        'mealplan-firing-standard', 'TriggerFiring'),
            ]),
            _row(11, [
                _etable('mp-plans', 0, 6, 'Meal plans',
                        'mealplan-plan-standard', 'MealPlanDefinition'),
                _etable('mp-links', 1, 6,
                        'Account links (Keycloak → person)',
                        'mealplan-account-link-standard',
                        'UserAccountLink'),
            ]),
        ]),
    _page(
        'mealplan-pantry', 'mealplan/pantry',
        'mpa-5: what the household actually has — lots with storage '
        'states and approximate weights (labeled priors), and the '
        'weight-prior vocabulary a kitchen scale can override.',
        'PantryItem',
        [
            _row(0, [
                _etable('mp-pantry-items', 0, 6,
                        f'Pantry lots — {HOUSEHOLD}',
                        'mealplan-pantry-standard', 'PantryItem',
                        'household_name', HOUSEHOLD),
                _sapi('mp-pantry-stock', 1, 6,
                      f'Resolved stock — {HOUSEHOLD}',
                      f'{_MP}/pantry/{HOUSEHOLD}', hide='lots'),
            ]),
            _row(1, [
                _etable('mp-unit-weights', 0, 6,
                        'Approximate unit weights (tunable priors)',
                        'mealplan-unit-weight-standard',
                        'UnitWeightPrior'),
                _sapi('mp-shopping', 1, 6, f'Shopping list — {PLAN}',
                      f'{_MP}/plans/{PLAN}/shopping-list',
                      hide='oneStoreTotals'),
            ]),
            # mpb-4/9: the waste leak + the quick-add grammar.
            _row(2, [
                _sapi('mp-waste', 0, 6,
                      'Waste ledger — the honest budget leak',
                      f'{_MP}/waste/{HOUSEHOLD}'),
                _etable('mp-waste-rows', 1, 6,
                        f'Waste records — {HOUSEHOLD}',
                        'mealplan-waste-standard', 'WasteRecord',
                        'household_name', HOUSEHOLD),
            ]),
            _row(3, [
                _sapi('mp-quickadd', 0, 12,
                      'Quick-add preview (edit ?q= — proposals only, '
                      'you apply them)',
                      f'{_MP}/quick-add?q=2+lb+chicken+breast+11.98'
                      '+%40+demo-grocery'),
            ]),
        ]),
    _page(
        'mealplan-supply', 'mealplan/supply',
        'mps: the Food Supply — a map of where we buy food (and where we '
        'work), with addresses, what we buy there and at what prices; the '
        'best $/kg per food across places; the next purchase and bulk '
        'proposals. Add a place with its address and coordinates; log a '
        'price where you saw it.',
        'SourceLocation',
        [
            _row(0, [
                _emap('mp-supply-map', 0, 12,
                      'Where we buy food — grocery, farmers market, warehouse '
                      'club, workplace (click a pin)',
                      'mealplan-food-sources', 'SourceLocation'),
            ], min_height=560),
            _row(1, [
                _etable('mp-supply-places', 0, 6,
                        'Places (Create New: name, kind, address, latitude, longitude)',
                        'mealplan-location-standard', 'SourceLocation'),
                _etable('mp-supply-prices', 1, 6,
                        'Prices seen (Create New: food, place, price, package)',
                        'mealplan-price-standard', 'PriceObservation'),
            ]),
            _row(2, [
                _sapi('mp-supply-compare', 0, 6,
                      'Best place per food ($/kg, how old the price is)',
                      f'{_MP}/prices', pick='foods'),
                _sapi('mp-supply-purchase', 1, 6,
                      f'Next weekly purchase — {PLAN} (what, how much, where)',
                      f'{_MP}/plans/{PLAN}/purchase-proposal', hide='proposals'),
            ]),
            _row(3, [
                _sapi('mp-supply-bulk-3', 0, 6, 'Bulk buy — 3-month cadence (warehouse club)',
                      f'{_MP}/bulk-proposal?household={HOUSEHOLD}&cadence=3', hide='proposals'),
                _sapi('mp-supply-bulk-12', 1, 6, 'Bulk buy — yearly cadence',
                      f'{_MP}/bulk-proposal?household={HOUSEHOLD}&cadence=12', hide='proposals'),
            ]),
            _row(4, [
                # mo-1: the shipped staples are mealoptions data with a
                # BLANK household_name (= any household), so the table
                # is unfiltered — a household's own rows list beside them.
                _etable('mp-supply-staples', 0, 6, 'Bulk staples (cadence, shelf life, bulk offer)',
                        'mealplan-bulk-staple-standard', 'BulkStaple'),
                _etable('mp-supply-events', 1, 6, 'Purchase events on the calendar',
                        'mealplan-event-standard', 'CalendarEvent', 'category', 'purchase'),
            ]),
            # mo-2: local-first price advice over the month references
            # (chain vs farmers market vs X; the 10 % knob labelled) +
            # the published reference rows. Publishing a month =
            # `POST /api/mealplanning/prices/publish` (or, from mo-3,
            # `pol modules export mealoptions`) — no form: the export
            # is not a no-code solution.
            _row(5, [
                _sapi('mp-supply-advice', 0, 8,
                      'Price advice — local first (chicken breast: chain vs '
                      'farmers market, $/kg, which rule decided)',
                      f'{_MP}/prices/advice?food=chicken-breast-raw',
                      pick='ranking'),
                _sapi('mp-supply-advice-pick', 1, 4,
                      'Recommended source + the local-preference knob',
                      f'{_MP}/prices/advice?food=chicken-breast-raw',
                      hide='ranking,recommended,knob,honesty,whyLocalFirst'),
            ]),
            _row(6, [
                _etable('mp-supply-references', 0, 12,
                        'Price references — food × month × source type '
                        '(chain named; independents typed only; no place, '
                        'no day). Publish: POST /api/mealplanning/prices/publish',
                        'mealplan-price-reference-standard', 'PriceReference'),
            ]),
        ]),
    _page(
        'mealplan-market', 'mealplan/market',
        'mpa-5: buying — locations with geolocations, observed '
        'prices normalized to $/kg, the per-food price compare, and '
        'the purchase preview that assigns approximate weight + '
        'nutrition + cost to a would-be purchase.',
        'PriceObservation',
        [
            _row(0, [
                _etable('mp-locations', 0, 6, 'Source locations',
                        'mealplan-location-standard', 'SourceLocation'),
                _etable('mp-prices-raw', 1, 6, 'Price observations',
                        'mealplan-price-standard', 'PriceObservation'),
            ]),
            _row(1, [
                _sapi('mp-price-compare', 0, 6,
                      'Price compare (best store named, $/kg)',
                      f'{_MP}/prices'),
                _sapi('mp-purchase-preview', 1, 6,
                      'Purchase preview — a dozen eggs',
                      f'{_MP}/purchase-preview?food=egg-whole-raw'
                      '&quantity=1&unit=dozen', hide='nutrients'),
            ]),
            _row(2, [
                _etable('mp-purchase-nutrients', 0, 12,
                        'Nutrient content per 100 g — egg-whole-raw '
                        '(FDC-cited; × approx grams = the preview)',
                        'mealplan-nutrient-content-view',
                        'NutrientContent', 'food_name', 'egg-whole-raw'),
            ]),
        ]),
    _page(
        'mealplan-household', 'mealplan/household',
        'mlg-1..4: the household behind the calendar — who is where '
        'and when (schedules, sleep spacing), how the work is split '
        '(percent shares per workload type, delivery cost shift), '
        'where meals are eaten (lunchbox, cold packs), skill profiles '
        'with safety floors, eating-time priors, dish strategies — '
        'every row a knob; the allocation and its fairness readout.',
        'HouseholdMember',
        [
            _row(0, [
                _etable('mp-members', 0, 6, f'Members — {HOUSEHOLD}',
                        'mealplan-member-standard', 'HouseholdMember',
                        'household_name', HOUSEHOLD),
                _etable('mp-sleep', 1, 6, 'Sleep preferences (dinner→sleep '
                        'spacing: yours; default 2 h; the citation says ~3 h)',
                        'mealplan-sleep-standard', 'SleepPreference'),
            ]),
            _row(1, [
                _etable('mp-schedules', 0, 12,
                        'Schedules — work, commute, sleep (drawn as the '
                        'calendar\'s background)',
                        'mealplan-schedule-standard', 'PersonSchedule'),
            ]),
            _row(2, [
                _sapi('mp-avail-alex', 0, 6, f'Availability — {PERSON} (this plan week)',
                      f'{_MP}/users/{PERSON}/availability?from=2026-08-31&to=2026-09-06',
                      pick='busy'),
                _sapi('mp-timing', 1, 6,
                      f'Meal timing check — {PLAN} (dinner→sleep, meals away from home)',
                      f'{_MP}/plans/{PLAN}/timing-check', hide='verdicts'),
            ]),
            _row(3, [
                _sapi('mp-timing-verdicts', 0, 12, 'Timing verdicts per entry × person',
                      f'{_MP}/plans/{PLAN}/timing-check', pick='verdicts'),
            ]),
            _row(4, [
                _etable('mp-workload-types', 0, 6, 'Workload types',
                        'mealplan-workload-type-standard', 'WorkloadType'),
                _etable('mp-work-policies', 1, 6,
                        f'Work distribution — {HOUSEHOLD} (shares %, delivery knobs)',
                        'mealplan-work-policy-standard', 'WorkDistributionPolicy',
                        'household_name', HOUSEHOLD),
            ]),
            _row(5, [
                _sapi('mp-allocation', 0, 6,
                      f'This week\'s allocation — {PLAN} (minimum person-minutes '
                      'within the shares; both allocations shown)',
                      f'{_MP}/plans/{PLAN}/work-allocation',
                      hide='allocation,readout,purchaseVsDelivery'),
                _sapi('mp-allocation-readout', 1, 6, 'Shares: target vs actual, per workload',
                      f'{_MP}/plans/{PLAN}/work-allocation', pick='readout'),
            ]),
            _row(6, [
                _sapi('mp-allocation-steps', 0, 8, 'Every step, who, minutes, supervised?',
                      f'{_MP}/plans/{PLAN}/work-allocation', pick='allocation'),
                _sapi('mp-purchase-vs-delivery', 1, 4, 'Purchase trip vs delivery (a comparison)',
                      f'{_MP}/plans/{PLAN}/work-allocation', pick='purchaseVsDelivery'),
            ]),
            _row(7, [
                _sapi('mp-fairness', 0, 6, f'Fairness — {HOUSEHOLD} (ledger vs targets)',
                      f'{_MP}/households/{HOUSEHOLD}/fairness'),
                _etable('mp-ledger', 1, 6, 'Work ledger (done events, logs)',
                        'mealplan-work-ledger-standard', 'WorkLedger',
                        'household_name', HOUSEHOLD),
            ]),
            _row(8, [
                _etable('mp-situations', 0, 6, 'Meal situations (lunchbox, cold packs — FSIS-cited)',
                        'mealplan-situation-standard', 'MealSituation'),
                _etable('mp-logistics', 1, 6, f'Meal logistics — {PLAN} (who eats what where)',
                        'mealplan-logistics-standard', 'MealLogistics'),
            ]),
            _row(9, [
                _sapi('mp-portability', 0, 12, f'Packing plan — {PLAN} (pack + freeze-packs events; missing tools named)',
                      f'{_MP}/plans/{PLAN}/portability', hide='proposals'),
            ]),
            _row(10, [
                _etable('mp-skills', 0, 4, 'Skills (safety skills bound speed)',
                        'mealplan-skill-standard', 'SkillDefinition'),
                _etable('mp-person-skills', 1, 8, 'Skill profiles — level + speed factor per skill',
                        'mealplan-person-skill-standard', 'PersonSkill'),
            ]),
            _row(11, [
                _etable('mp-method-skills', 0, 6, 'Skills + safety floor per step method',
                        'mealplan-method-skill-standard', 'MethodSkillRequirement'),
                _etable('mp-safety-rules', 1, 6, 'Safety rules (hazard → level; cited)',
                        'mealplan-safety-rule-standard', 'SafetyRule'),
            ]),
            _row(12, [
                _sapi('mp-prep-profile', 0, 6,
                      'Prep-time profile — day-1 dinner for demo-alex (final prep vs eating)',
                      f'{_MP}/entries/{PLAN}-d1-dinner/prep-profile?person={PERSON}',
                      hide='steps'),
                _sapi('mp-prep-profile-sam', 1, 6,
                      'Prep-time profile — day-1 dinner for demo-sam',
                      f'{_MP}/entries/{PLAN}-d1-dinner/prep-profile?person=demo-sam',
                      hide='steps'),
            ]),
            _row(13, [
                _sapi('mp-speed-refinement', 0, 6, 'Speed refinement from observations (never below the floor)',
                      f'{_MP}/speed-refinement'),
                _etable('mp-duration-obs', 1, 6, 'Duration observations',
                        'mealplan-duration-obs-standard', 'DurationObservation'),
            ]),
            _row(14, [
                _etable('mp-meal-times', 0, 4, 'Eating time per slot',
                        'mealplan-meal-time-standard', 'MealTimeProfile'),
                _etable('mp-dish-strategies', 1, 4, 'Dish strategies',
                        'mealplan-dish-strategy-standard', 'DishStrategy'),
                _etable('mp-dish-policy', 2, 4, 'Dish policy',
                        'mealplan-dish-policy-standard', 'HouseholdDishPolicy',
                        'household_name', HOUSEHOLD),
            ]),
            _row(15, [
                _sapi('mp-dish-plan', 0, 12, f'Dish plan — {PLAN} (unattended windows first, then after eating)',
                      f'{_MP}/plans/{PLAN}/dish-plan', pick='proposals'),
            ]),
        ]),
    _page(
        'mealplan-trends', 'mealplan/trends',
        'mpa-5: the person over time — day metrics (calories, '
        'protein, fiber, sodium, per-meal GL and acid-share peaks) '
        'with gap days NAMED, weight observations, meal acidity, '
        'and the PSPP state chain behind a meal.',
        'IntakeRecord',
        [
            _row(0, [
                # Reading /series is what refreshes the metric cache
                # the charts + day-metric table read — keep it first.
                _sapi('mp-series', 0, 6, f'Tracking series — {PERSON}',
                      f'{_MP}/users/{PERSON}/series',
                      hide='days,weightObservations'),
                _sapi('mp-day', 1, 6, f'One day — {DAY}',
                      f'{_MP}/users/{PERSON}/day/{DAY}'),
            ]),
            _row(1, [
                _etable('mp-day-metrics', 0, 6,
                        f'Day metrics — {PERSON}',
                        'mealplan-day-metric-standard',
                        'DailyIntakeMetric', 'person_name', PERSON),
                _etable('mp-weights', 1, 6,
                        f'Weight observations — {PERSON}',
                        'mealplan-weight-standard', 'WeightObservation',
                        'person_name', PERSON),
            ]),
            _row(2, [
                _egraph('mp-calories-chart', 0, 6,
                        f'Calories/day — {PERSON}',
                        'mealplan-calories-trend', 'DailyIntakeMetric',
                        'person_name', PERSON),
                _egraph('mp-weight-chart', 1, 6,
                        f'Weight over time — {PERSON} (measured '
                        'observations)',
                        'mealplan-weight-trend', 'WeightObservation',
                        'person_name', PERSON),
            ], min_height=300),
            _row(3, [
                _egraph('mp-gl-chart', 0, 6, f'Max per-meal GL — {PERSON}',
                        'mealplan-gl-trend', 'DailyIntakeMetric',
                        'person_name', PERSON),
                _egraph('mp-acid-chart', 1, 6,
                        f'Max per-meal acid share — {PERSON}',
                        'mealplan-acid-trend', 'DailyIntakeMetric',
                        'person_name', PERSON),
            ], min_height=300),
            _row(4, [
                _etable('mp-intake', 0, 6, f'Intake records — {PERSON}',
                        'mealplan-intake-standard', 'IntakeRecord',
                        'person_name', PERSON),
                _etable('mp-ratings', 1, 6, f'Meal ratings — {PERSON}',
                        'mealplan-rating-standard', 'MealRating',
                        'person_name', PERSON),
            ]),
            _row(5, [
                _sapi('mp-acidity', 0, 6, f'Meal acidity — {TEMPLATE}',
                      f'{_MP}/templates/{TEMPLATE}/acidity'),
                _sapi('mp-coverage', 1, 6,
                      'Coverage steering — 7-day under-targets + '
                      'cheapest exclusion-safe closers',
                      f'{_MP}/users/{PERSON}/coverage'),
            ]),
            _row(6, [
                _etable('mp-exclusions', 0, 12,
                        f'Declared exclusions — {PERSON} (yours, in '
                        'your words)',
                        'mealplan-exclusion-standard', 'PersonExclusion',
                        'person_name', PERSON),
            ]),
            _row(7, [
                _sapi('mp-state-chain', 0, 6,
                      'The PSPP state chain behind the meal '
                      '(mass-balance + retention claims; model rungs '
                      'refused by name)',
                      f'{_MP}/templates/{TEMPLATE}/state-chain',
                      hide='terminalState'),
                _sapi('mp-terminal-state', 1, 6,
                      'Terminal food state (the prepared meal)',
                      f'{_MP}/templates/{TEMPLATE}/state-chain',
                      pick='terminalState',
                      hide='composition_snapshot_json,'
                           'environmental_snapshot_json,'
                           'thermodynamic_phase_json'),
            ]),
        ]),
]


# --------------------------------------------------------------------
# The seed pass — upsert + repoint (motors_pages pattern).
# --------------------------------------------------------------------

def _by_name(manager, class_name, name):
    """The live row of `class_name` called `name`, or None."""
    table = (getattr(manager, 'objectTables', {}) or {}).get(class_name, {})
    for inst in (table or {}).values():
        if getattr(inst, 'name', '') == name:
            return inst
    return None


def _repoint_display_refs(manager):
    """Re-point every embeddedTable at THIS node's TableDefinition
    ids (ids are assigned at insert, so a seeded page cannot carry a
    working reference). Returns how many items were repointed."""
    wanted = {d['name'] for d in SEED_MEALPLAN_PAGE_DISPLAYS}
    wanted |= {d['name'] for d in _view_page_seeds()['displays']}
    repointed = 0
    for row in list((getattr(manager, 'objectTables', {}) or {})
                    .get('DisplayDefinition', {}).values()):
        if getattr(row, 'name', '') not in wanted:
            continue
        try:
            definition = json.loads(getattr(row, 'definition', '') or '{}')
        except ValueError:
            continue
        changed = False
        for display_row in (definition.get('rows') or []):
            for item in (display_row.get('items') or []):
                target = EMBED_TARGETS.get(item.get('id', ''))
                if not target:
                    continue
                class_name, def_name = target
                found = _by_name(manager, class_name, def_name)
                if found is None:
                    print(f'[MealplanPagesSeed] {def_name} not found — '
                          f'"{row.name}" keeps its stored id and that '
                          f'panel will render empty', flush=True)
                    continue
                inputs = (item.get('componentProps') or {}).get('inputs')
                if inputs is None:
                    continue
                if inputs.get('tableConfigId') != found.id:
                    inputs['tableConfigId'] = found.id
                    changed = True
                    repointed += 1
        if changed:
            row.definition = json.dumps(definition)
            try:
                manager.db.saveInstanceInDB(row)
            except Exception as save_error:
                print(f'[MealplanPagesSeed] could not persist repointed '
                      f'"{row.name}": {save_error}', flush=True)
    return repointed


SEED_MEALPLAN_GEOCODERS = [
    {'name': 'osm-nominatim-public', 'type': 'web-limited',
     'provider': 'nominatim',
     'definition': json.dumps({
         'baseUrl': 'https://nominatim.openstreetmap.org',
         'note': ('OSM Nominatim public instance — a labelled convenience '
                  'prior for the Places table (usage policy: at most 1 '
                  'request/s, attribution required, no bulk). Replace with '
                  'a self-hosted Pelias/Nominatim row for volume.')})},
]


def _view_page_seeds():
    """Night run 2026-09-03: the view pages (Today / Shopping trip /
    Cook now / Weekly review) keep their seeds in their own modules,
    which import this module's helpers — so they are pulled in lazily
    here (a top-level import would be circular). A missing one is
    reported, never fatal."""
    out = {'tables': [], 'graphs': [], 'displays': []}
    for mod, pre in (('nutrition.today_seed', 'TODAY'),
                     ('nutrition.shoptrip_seed', 'SHOPTRIP'),
                     ('nutrition.cooknow_seed', 'COOKNOW'),
                     ('nutrition.weekreview_seed', 'WEEKREVIEW')):
        try:
            m = __import__(mod, fromlist=['x'])
        except Exception as e:  # noqa: BLE001
            print(f'[MealplanPagesSeed] {mod} skipped: {e}', flush=True)
            continue
        out['tables'] += list(getattr(m, f'SEED_{pre}_TABLES', []))
        out['graphs'] += list(getattr(m, f'SEED_{pre}_GRAPHS', []))
        out['displays'] += list(getattr(m, f'SEED_{pre}_PAGE_DISPLAYS', []))
    return out


def seed_mealplan_pages(manager):
    """Upsert the meal-planning classes' display configuration —
    converges on edit (no INSERT-BY-NAME backfill), then re-points
    the embeds at this node's ids."""
    from composition.seed_upsert import upsert_seed_pairs
    from polariApiServer.tableDefinition import TableDefinition
    from polariApiServer.graphDefinition import GraphDefinition
    from polariApiServer.displayDefinition import DisplayDefinition

    from polariApiServer.geoJsonDefinition import GeoJsonDefinition
    from polariApiServer.geocoderDefinition import GeocoderDefinition

    views = _view_page_seeds()
    reports = upsert_seed_pairs(manager, [
        ('TableDefinition', TableDefinition,
         list(SEED_MEALPLAN_TABLES) + views['tables']),
        ('GraphDefinition', GraphDefinition,
         list(SEED_MEALPLAN_GRAPHS) + views['graphs']),
        ('GeoJsonDefinition', GeoJsonDefinition, SEED_MEALPLAN_GEOJSON),
        # Night run 2026-09-03: the CRUD dialog's "Find coordinates from
        # address" needs a GeocoderDefinition; staging had none (real-
        # browser pass). One labelled convenience prior — delete or
        # replace with a self-hosted Pelias/Nominatim for volume.
        ('GeocoderDefinition', GeocoderDefinition, SEED_MEALPLAN_GEOCODERS),
        ('DisplayDefinition', DisplayDefinition,
         list(SEED_MEALPLAN_PAGE_DISPLAYS) + views['displays']),
    ], tag='MealplanPagesSeed')

    repointed = _repoint_display_refs(manager)
    if repointed:
        print(f'[MealplanPagesSeed] repointed {repointed} embed '
              f'reference(s) at this node\'s definition ids', flush=True)
    # cal-4: the event layer (definitions, calendar, analyses, the
    # no-code solutions, triggers) rides the same upsert pass.
    try:
        from nutrition.calendar_seed import seed_mealplan_calendar
        reports.extend(seed_mealplan_calendar(manager))
    except Exception as e:
        print(f'[MealplanCalendarSeed] failed: {e}', flush=True)
    return reports
