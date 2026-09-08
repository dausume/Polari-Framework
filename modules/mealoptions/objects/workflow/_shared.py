"""@module mealoptions.objects.workflow._shared — what the workflow row classes share (constants, seeds, helpers); split from workflow_basis.py (sap-2c)."""

FIDELITY = ('estimate', 'observed')
PROVENANCES = ('seeded', 'mine')
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
