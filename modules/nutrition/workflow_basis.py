"""
@cross-cutting
@module nutrition.workflow_basis
@tags @xc:bindings

nmp-10 — cooking as a task-oriented WORKFLOW (decisions 10/12/13):

  KitchenToolDefinition  the tool vocabulary (seeded, USER-EXTENDABLE
                         — decision 13: declare any tool the catalog
                         never heard of; same CRUDE surface).
  KitchenTool            one household's inventory row.
  CookingTaskDefinition  a task KIND naming WHAT (dice, batch-cook,
                         pan-fry…), honoring ONE uniform STEP
                         CONTRACT: inputs+state -> outputs+state,
                         duration (from the method), equipment slot.
  StepMethod             one WAY to do a task kind: tool x duration
                         model x skill floor x optional R6 retention
                         mapping (bake != fry nutritionally).
                         Provenance mine-vs-seeded; duration
                         fidelity estimate-vs-observed.
  StorageActionDefinition freeze/refrigerate/thaw/reheat as
                         first-class actions with the USDA FSIS
                         safety windows (public domain, cited).
  MethodPreference       a stated pin ("hand-dice") — beats
                         time-optimality; the delta is shown, never
                         judged.
  ToolAdvisorDismissal   a remembered "stop suggesting this tool".
  CookingWorkflow        a saved week DAG (graphs-as-data for the
                         EXISTING polariNoCode editor — a step-node
                         vocabulary, never a new editor).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.workflow_analysis
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-10
"""

from objectTreeDecorators import treeObject, treeObjectInit
# hh-1: the skill vocabulary + the labeled level priors (refined per
# person from observed durations) live in the household layer now;
# re-exported here so existing importers keep working.
from household.household_basis import SKILL_FACTORS, SKILL_LEVELS  # noqa: F401

FIDELITY = ('estimate', 'observed')
PROVENANCES = ('seeded', 'mine')


class KitchenToolDefinition(treeObject):
    """One tool the vocabulary knows (seeded or user-declared)."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 category: str = 'hand-tool',
                 provenance: str = 'seeded',
                 is_prior: bool = True, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.category = category
        self.provenance = provenance
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class KitchenTool(treeObject):
    """One inventory row: does THIS household own the tool?"""

    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '',
                 tool_name: str = '', owned: bool = True,
                 is_prior: bool = False, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.household_name = household_name
        self.tool_name = tool_name
        self.owned = owned
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class CookingTaskDefinition(treeObject):
    """A task KIND — WHAT, not HOW (the step contract)."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 # the uniform contract: what comes in / goes out
                 # (state words: raw, prepped, cooked, cooled,
                 # portioned, frozen, thawed, reheated).
                 input_state: str = 'raw',
                 output_state: str = 'prepped',
                 # equipment slot the task occupies while running
                 # ('' = hands only) — the overlap constraint.
                 equipment_slot: str = '',
                 provenance: str = 'seeded',
                 is_prior: bool = True, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.input_state = input_state
        self.output_state = output_state
        self.equipment_slot = equipment_slot
        self.provenance = provenance
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class StepMethod(treeObject):
    """One WAY to do a task kind (decision 12): tool x duration
    model x skill; picks its own R6 retention row when it cooks."""

    @treeObjectInit
    def __init__(self, name: str = '', task_kind: str = '',
                 display_name: str = '', tool_name: str = '',
                 # duration model: base + per-100g, scaled by the
                 # cook's SKILL_FACTORS (labeled priors).
                 base_min: float = 0.0,
                 per_100g_min: float = 0.0,
                 # minimum skill to use safely ('' = anyone).
                 skill_floor: str = '',
                 # whether the cook attends it the whole time (active
                 # minutes are THE optimizer score) or it runs itself
                 # (oven/rice-cooker — only base_min is active).
                 attended: bool = True,
                 # R6 retention code this method maps to ('' = honest
                 # none — decision 13: none-if-unknown).
                 retention_code: str = '',
                 provenance: str = 'seeded',
                 duration_fidelity: str = 'estimate',
                 is_prior: bool = True, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.task_kind = task_kind
        self.display_name = display_name
        self.tool_name = tool_name
        self.base_min = base_min
        self.per_100g_min = per_100g_min
        self.skill_floor = skill_floor
        self.attended = attended
        self.retention_code = retention_code
        self.provenance = provenance
        self.duration_fidelity = duration_fidelity
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class StorageActionDefinition(treeObject):
    """freeze/refrigerate/thaw/reheat with FSIS safety windows."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 # state transition per the step contract.
                 input_state: str = 'cooked',
                 output_state: str = 'refrigerated',
                 # the FSIS window this action must respect (days the
                 # resulting state stays SAFE; 0 = not a hold state).
                 safety_window_days: float = 0.0,
                 # quality window (freezer months etc.) — noted, not
                 # a safety bound.
                 quality_window_days: float = 0.0,
                 duration_min: float = 0.0,
                 citation: str = 'USDA FSIS cold storage charts '
                                 '(public domain)',
                 is_prior: bool = True, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.input_state = input_state
        self.output_state = output_state
        self.safety_window_days = safety_window_days
        self.quality_window_days = quality_window_days
        self.duration_min = duration_min
        self.citation = citation
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class MethodPreference(treeObject):
    """A stated pin — preference beats time-optimality."""

    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '',
                 household_name: str = '', task_kind: str = '',
                 method_name: str = '',
                 is_prior: bool = False, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.person_name = person_name
        self.household_name = household_name
        self.task_kind = task_kind
        self.method_name = method_name
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class ToolAdvisorDismissal(treeObject):
    """A remembered 'stop suggesting this tool' (never a nag)."""

    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '',
                 tool_name: str = '',
                 is_prior: bool = False, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.household_name = household_name
        self.tool_name = tool_name
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class CookingWorkflow(treeObject):
    """A saved week DAG — pure graph data for the no-code editor."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 plan_name: str = '',
                 # {nodes: [{id, kind, task/action, grams, day,
                 #  session}], edges: [{from, to, state}]}
                 definition_json: str = '{}',
                 provenance: str = 'mine',
                 is_prior: bool = False, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.plan_name = plan_name
        self.definition_json = definition_json
        self.provenance = provenance
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


# ── seeds ─────────────────────────────────────────────────
def _tool(name, display, category):
    return {'name': name, 'display_name': display,
            'category': category, 'provenance': 'seeded',
            'is_prior': True, 'provenance_id': 'nmp-10'}


SEED_KITCHEN_TOOLS = [
    _tool('chef-knife', 'Chef knife', 'hand-tool'),
    _tool('food-processor', 'Food processor', 'appliance'),
    _tool('mandoline', 'Mandoline slicer', 'hand-tool'),
    _tool('stove-burner', 'Stove burner', 'fixed'),
    _tool('oven', 'Oven', 'fixed'),
    _tool('sheet-pan', 'Sheet pan', 'cookware'),
    _tool('pot', 'Pot', 'cookware'),
    _tool('pan', 'Frying pan', 'cookware'),
    _tool('rice-cooker', 'Rice cooker', 'appliance'),
    _tool('microwave', 'Microwave', 'appliance'),
    _tool('fridge', 'Refrigerator', 'fixed'),
    _tool('freezer', 'Freezer', 'fixed'),
    # mlg-3: portability + dishes vocabulary (a household marks what it owns).
    _tool('insulated-lunchbox', 'Insulated lunchbox', 'container'),
    _tool('cold-pack', 'Cold pack (frozen gel)', 'container'),
    _tool('dishwasher', 'Dishwasher', 'appliance'),
]


def _task(name, display, in_state, out_state, slot=''):
    return {'name': name, 'display_name': display,
            'input_state': in_state, 'output_state': out_state,
            'equipment_slot': slot, 'provenance': 'seeded',
            'is_prior': True, 'provenance_id': 'nmp-10'}


SEED_TASK_KINDS = [
    _task('dice', 'Dice / chop', 'raw', 'prepped'),
    _task('marinate', 'Marinate', 'prepped', 'prepped'),
    _task('boil', 'Boil / simmer', 'prepped', 'cooked', 'stove'),
    _task('steam', 'Steam', 'prepped', 'cooked', 'stove'),
    _task('pan-fry', 'Pan-fry / saute', 'prepped', 'cooked', 'stove'),
    _task('grill', 'Grill / broil', 'prepped', 'cooked', 'oven'),
    _task('bake', 'Bake / roast', 'prepped', 'cooked', 'oven'),
    _task('cool', 'Cool before storing', 'cooked', 'cooled'),
    _task('portion', 'Portion & pack', 'cooled', 'portioned'),
    _task('assemble', 'Assemble / plate', 'portioned', 'served'),
]


def _method(name, task, display, tool, base, per100, attended=True,
            retention='', floor='', notes=''):
    return {'name': name, 'task_kind': task, 'display_name': display,
            'tool_name': tool, 'base_min': base,
            'per_100g_min': per100, 'skill_floor': floor,
            'attended': attended, 'retention_code': retention,
            'provenance': 'seeded', 'duration_fidelity': 'estimate',
            'is_prior': True, 'provenance_id': 'nmp-10',
            'notes': notes}


SEED_STEP_METHODS = [
    # dicing: three ways (decision 12's canonical example)
    _method('dice-knife', 'dice', 'Hand-dice with a chef knife',
            'chef-knife', 2.0, 1.5),
    _method('dice-processor', 'dice', 'Pulse in the food processor',
            'food-processor', 3.0, 0.3,
            notes='setup+cleanup dominates small batches — the '
                  'model says so via base_min'),
    _method('dice-mandoline', 'dice', 'Mandoline slices',
            'mandoline', 2.0, 0.8, floor='intermediate',
            notes='skill floor: guard use'),
    # boiling grain: pot vs rice cooker (attended vs not)
    _method('boil-pot', 'boil', 'Boil in a pot', 'pot', 5.0, 0.5,
            retention='0432'),
    _method('boil-rice-cooker', 'boil', 'Rice cooker',
            'rice-cooker', 3.0, 0.0, attended=False,
            retention='0432',
            notes='unattended after the pour — 3 active minutes'),
    _method('steam-pot', 'steam', 'Steam over a pot', 'pot',
            4.0, 0.4, retention='3784'),
    _method('pan-fry-pan', 'pan-fry', 'Pan-fry', 'pan', 4.0, 1.2,
            retention='0103'),
    _method('grill-broiler', 'grill', 'Broil in the oven', 'oven',
            5.0, 0.8, retention='0801'),
    _method('bake-oven', 'bake', 'Bake on a sheet pan', 'oven',
            6.0, 0.2, attended=False, retention='0805',
            notes='unattended once in — 6 active minutes'),
    _method('cool-counter', 'cool', 'Cool on the counter', '',
            5.0, 0.0, attended=False,
            notes='FSIS: into the fridge within 2 h of cooking'),
    _method('portion-containers', 'portion', 'Portion into '
            'containers', '', 2.0, 0.5),
    _method('assemble-plate', 'assemble', 'Plate & serve', '',
            3.0, 0.0),
]

# FSIS cold-storage windows (public domain), the safety data the
# scheduler must respect. Days are the FSIS chart values for cooked
# leftovers / frozen storage; cool-before-store is the 2-hour rule.
SEED_STORAGE_ACTIONS = [
    {'name': 'refrigerate', 'display_name': 'Refrigerate',
     'input_state': 'cooled', 'output_state': 'refrigerated',
     'safety_window_days': 4.0, 'quality_window_days': 4.0,
     'duration_min': 2.0,
     'citation': 'USDA FSIS cold storage chart: cooked leftovers '
                 '3-4 days refrigerated',
     'is_prior': True, 'provenance_id': 'nmp-10'},
    {'name': 'freeze', 'display_name': 'Freeze',
     'input_state': 'cooled', 'output_state': 'frozen',
     'safety_window_days': 3650.0, 'quality_window_days': 90.0,
     'duration_min': 3.0,
     'citation': 'USDA FSIS: frozen food is safe indefinitely; '
                 'quality window ~2-6 months for cooked dishes',
     'is_prior': True, 'provenance_id': 'nmp-10',
     'notes': 'safety indefinite; the QUALITY window drives '
              'suggestions'},
    {'name': 'thaw-fridge', 'display_name': 'Thaw in the fridge',
     'input_state': 'frozen', 'output_state': 'refrigerated',
     'safety_window_days': 4.0, 'quality_window_days': 2.0,
     'duration_min': 2.0,
     'citation': 'USDA FSIS: fridge thawing is the safe default; '
                 'thawed food keeps 3-4 days refrigerated',
     'is_prior': True, 'provenance_id': 'nmp-10',
     'notes': 'started the evening BEFORE the meal day'},
    {'name': 'reheat', 'display_name': 'Reheat to 165F/74C',
     'input_state': 'refrigerated', 'output_state': 'served',
     'safety_window_days': 0.0, 'quality_window_days': 0.0,
     'duration_min': 5.0,
     'citation': 'USDA FSIS: reheat leftovers to 165 F (74 C)',
     'is_prior': True, 'provenance_id': 'nmp-10'},
]
