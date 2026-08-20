"""
@module polariApiServer.module_pages_seed

No-code Display PAGES for the backend modules that had APIs but no
frontend surface (FRONTEND_WORK_MAP.md section B3, Dustin 2026-07-16:
"build out UIs for ones that do not have UIs yet, no-code based
primarily if at all possible"). Every page here is PURE DATA — rows of
the two generic registered components (class-rows-table /
api-json-panel, see polari-platform-angular
components/dashboard/generic/) — so future module pages need a seed
row, not Angular work.

Routes land at /display/<pageRoute> (the aquaponics pot-geometry
pattern). Detail panels point at the modules' seeded demo rows
(demo-household, basil-loop-direct, saltwater-food-forest, …); repoint
by editing the Display row — it's a knob, not code.
"""

import json


def _table(item_id, index, segments, title, class_name, columns='',
           max_rows=0):
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'class-rows-table',
            'inputs': {'className': class_name, 'columns': columns,
                       'maxRows': max_rows},
        },
        'item': None, 'nestedRows': [],
    }


def _api(item_id, index, segments, title, path):
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'api-json-panel',
            'inputs': {'path': path},
        },
        'item': None, 'nestedRows': [],
    }


def _row(index, items, min_height=320):
    return {
        'index': index, 'rowSegments': 12,
        'minRowHeight': min_height, 'maxRowHeight': 0,
        'autoHeight': True, 'cssClass': '', 'items': items,
    }


def _page(name, route, description, source_class, rows):
    return {
        'name': name,
        'description': description,
        'source_class': source_class,
        'isPage': True,
        'pageRoute': route,
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': rows}),
    }


SEED_MODULE_PAGE_DISPLAYS = [
    _page(
        'nutrition-home', 'nutrition',
        'Household nutrition: foods + nutrient contents, person/'
        'household daily needs, and garden-plan coverage — the '
        'harvest-to-meal ledger.',
        'FoodItem',
        [
            _row(0, [
                _table('nutrition-foods', 0, 6, 'Foods', 'FoodItem'),
                _table('nutrition-nutrients', 1, 6, 'Dietary nutrients',
                       'DietaryNutrient'),
            ]),
            _row(1, [
                _api('nutrition-person-needs', 0, 6,
                     'Daily needs — demo-alex',
                     '/api/nutrition/persons/demo-alex/needs'),
                _api('nutrition-household-needs', 1, 6,
                     'Household needs — demo-household',
                     '/api/nutrition/households/demo-household/needs'),
            ]),
        ]),
    # ── nmp-8: the meal-planning pages (all pure data) ────────
    _page(
        'nutrition-profile', 'nutrition/profile',
        'nmp-8: one person, honestly — obesity screening (with its '
        'caveats), the healthy calorie envelope + per-slot bands, '
        'per-nutrient thresholds with derivations, and the Hall '
        'weight trajectory vs observations.',
        'PersonProfile',
        [
            _row(0, [
                _table('nmp-profiles', 0, 6, 'People', 'PersonProfile'),
                _api('nmp-obesity', 1, 6,
                     'Obesity screening — demo-alex',
                     '/api/nutrition/persons/demo-alex/obesity'),
            ]),
            _row(1, [
                _api('nmp-envelope', 0, 6,
                     'Calorie envelope + slot bands — demo-alex',
                     '/api/nutrition/persons/demo-alex/envelope'),
                _api('nmp-thresholds', 1, 6,
                     'Thresholds (day) — demo-alex',
                     '/api/nutrition/persons/demo-alex/thresholds'),
            ]),
            _row(2, [
                _api('nmp-trajectory', 0, 12,
                     'Weight trajectory (Hall model; own profile '
                     'only by default)',
                     '/api/nutrition/persons/demo-alex/trajectory'),
            ]),
        ]),
    _page(
        'nutrition-meals', 'nutrition/meals',
        'nmp-8: meal templates (gate-checked), variations, plans and '
        'their rollups vs thresholds — warnings name symptoms, '
        'suggestions never auto-edit.',
        'MealTemplate',
        [
            _row(0, [
                _table('nmp-templates', 0, 6, 'Meal templates',
                       'MealTemplate'),
                _table('nmp-variations', 1, 6, 'Variations',
                       'VariationDefinition'),
            ]),
            _row(1, [
                _api('nmp-template-gate', 0, 6,
                     'The authoring gate — chicken-bowl-dinner',
                     '/api/nutrition/templates/chicken-bowl-dinner'
                     '/validate'),
                _api('nmp-template-rollup', 1, 6,
                     'Per-meal rollup — chicken-bowl-dinner',
                     '/api/nutrition/templates/chicken-bowl-dinner'
                     '/rollup'),
            ]),
            _row(2, [
                _table('nmp-plans', 0, 6, 'Meal plans',
                       'MealPlanDefinition'),
                _table('nmp-entries', 1, 6, 'Plan entries',
                       'MealEntry'),
            ]),
        ]),
    _page(
        'nutrition-recipes', 'nutrition/recipes',
        'nmp-8: recipes with the retention/yield engine — '
        'per-serving nutrition labels with raw-vs-cooked provenance; '
        'the tolerance table with citations and confidence grades.',
        'Recipe',
        [
            _row(0, [
                _table('nmp-recipes', 0, 6, 'Recipes', 'Recipe'),
                _table('nmp-lines', 1, 6, 'Ingredient lines',
                       'IngredientLine'),
            ]),
            _row(1, [
                _api('nmp-recipe-nutrition', 0, 6,
                     'Per-serving label — chicken-rice-bowl',
                     '/api/nutrition/recipes/chicken-rice-bowl'
                     '/nutrition'),
                _api('nmp-tolerances', 1, 6,
                     'Tolerance table (cited, confidence-graded)',
                     '/api/nutrition/tolerances'),
            ]),
        ]),
    _page(
        'nutrition-activity', 'nutrition/activity',
        'nmp-8: activity (Compendium METs, verbatim + attributed), '
        'logged weeks, the day timeline with timing evaluations, and '
        'the honest fasted-exercise page.',
        'ActivityDefinition',
        [
            _row(0, [
                _table('nmp-activities', 0, 6, 'Activities '
                       '(2024 Adult Compendium, values unaltered)',
                       'ActivityDefinition'),
                _table('nmp-activity-logs', 1, 6, 'Activity logs',
                       'ActivityLog'),
            ]),
            _row(1, [
                _api('nmp-activity-week', 0, 6,
                     'Logged week — demo-alex',
                     '/api/nutrition/persons/demo-alex/activity-week'),
                _api('nmp-fasted', 1, 6,
                     'Fasted exercise — honestly',
                     '/api/nutrition/fasted-exercise'),
            ]),
        ]),
    _page(
        'nutrition-garden', 'nutrition/garden',
        'nmp-8: the garden loop — coverage of a meal plan or '
        'household from the hydroponic garden, gaps named, '
        'uncoverable nutrients pointed at their real source.',
        'GardenPlanDefinition',
        [
            _row(0, [
                _table('nmp-gardens', 0, 6, 'Garden plans',
                       'GardenPlanDefinition'),
                _api('nmp-coverage', 1, 6,
                     'Coverage — starter-garden (week)',
                     '/api/nutrition/garden-plans/starter-garden'
                     '/coverage'),
            ]),
            _row(1, [
                _api('nmp-garden-suggest', 0, 12,
                     'Planting suggestions (arithmetic shown)',
                     '/api/nutrition/garden-plans/starter-garden'
                     '/suggest'),
            ]),
        ]),
    _page(
        'vermicompost-home', 'vermicompost',
        'aqp-7 worm-compost enrichment loops: bins, profiles, loops, '
        'and the direct-vs-periodic mode comparison for the demo '
        'basil loop.',
        'CompostLoopDefinition',
        [
            _row(0, [
                _table('vc-loops', 0, 6, 'Compost loops',
                       'CompostLoopDefinition'),
                _table('vc-bins', 1, 6, 'Compost bins',
                       'CompostBinDefinition'),
            ]),
            _row(1, [
                _api('vc-compare', 0, 6,
                     'Mode comparison — basil-loop-direct',
                     '/api/aquaponics/compost-loops/basil-loop-direct/'
                     'compare-modes'),
                _api('vc-enriched', 1, 6,
                     'Enriched water — basil-loop-direct',
                     '/api/aquaponics/compost-loops/basil-loop-direct/'
                     'enriched-water'),
            ]),
        ]),
    _page(
        'tanks-home', 'tanks',
        'Freshwater/saltwater tank systems: substrates, species, '
        'systems, and the demo saltwater food forest balance + yield.',
        'TankSystemDefinition',
        [
            _row(0, [
                _table('tanks-systems', 0, 7, 'Tank systems',
                       'TankSystemDefinition'),
                _table('tanks-substrates', 1, 5, 'Substrates',
                       'TankSubstrateDefinition'),
            ]),
            _row(1, [
                _api('tanks-balance', 0, 6,
                     'Balance — saltwater-food-forest',
                     '/api/tanks/systems/saltwater-food-forest/balance'),
                _api('tanks-yield', 1, 6,
                     'Yield — saltwater-food-forest',
                     '/api/tanks/systems/saltwater-food-forest/yield'),
            ]),
        ]),
    _page(
        'biomining-home', 'biomining',
        'Biomining / bioextraction: bacteria+algae agents, mineral '
        'products, systems, and the demo iron-ferrite biomine yield.',
        'BiomineSystemDefinition',
        [
            _row(0, [
                _table('bm-agents', 0, 6, 'Bioextraction agents',
                       'BioextractionAgent'),
                _table('bm-products', 1, 6, 'Biomineral products',
                       'BiomineralProduct'),
            ]),
            _row(1, [
                _table('bm-systems', 0, 6, 'Biomine systems',
                       'BiomineSystemDefinition'),
                _api('bm-yield', 1, 6,
                     'Yield — iron-ferrite-biomine',
                     '/api/biomining/systems/iron-ferrite-biomine/yield'),
            ]),
        ]),
    _page(
        'microalgae-home', 'microalgae',
        'Microalgae photobioreactors: strains, reactors, integrated '
        'loops, and the demo chlorella reactor sustainability + '
        'decarbonization verdicts.',
        'AlgaeReactorDefinition',
        [
            _row(0, [
                _table('ma-strains', 0, 6, 'Algae strains',
                       'AlgaeStrain'),
                _table('ma-reactors', 1, 6, 'Reactors',
                       'AlgaeReactorDefinition'),
            ]),
            _row(1, [
                _api('ma-sustainability', 0, 6,
                     'Sustainability — chlorella-hydro-reactor',
                     '/api/microalgae/reactors/chlorella-hydro-reactor/'
                     'sustainability'),
                _api('ma-decarb', 1, 6,
                     'Decarbonization — chlorella-hydro-reactor',
                     '/api/microalgae/reactors/chlorella-hydro-reactor/'
                     'decarbonization'),
            ]),
        ]),
    _page(
        'waxsupply-home', 'wax-supply',
        'Bio wax sources: every registered source with hydroponic '
        'compatibility and the for-use suitability report.',
        'WaxSourceDefinition',
        [
            _row(0, [
                _table('wax-sources', 0, 7, 'Wax sources',
                       'WaxSourceDefinition'),
                _api('wax-for-use', 1, 5, 'Suitability by use',
                     '/api/wax/for-use'),
            ]),
        ]),
    _page(
        'supplychain-home', 'supply-chain',
        'Supply chains: nodes, flows, and the demo household bio-chain '
        'inventory, carbon ledger, and dependency report.',
        'SupplyChainDefinition',
        [
            _row(0, [
                _table('sc-nodes', 0, 6, 'Supply nodes', 'SupplyNode'),
                _table('sc-flows', 1, 6, 'Supply flows', 'SupplyFlow'),
            ]),
            _row(1, [
                _api('sc-inventory', 0, 4,
                     'Inventory — household-bio-chain',
                     '/api/supplychain/chains/household-bio-chain/'
                     'inventory'),
                _api('sc-carbon', 1, 4,
                     'Carbon — household-bio-chain',
                     '/api/supplychain/chains/household-bio-chain/carbon'),
                _api('sc-deps', 2, 4,
                     'Dependencies — household-bio-chain',
                     '/api/supplychain/chains/household-bio-chain/'
                     'dependencies'),
            ]),
        ]),
    _page(
        'morphology-home', 'plant-morphology',
        'Plant morphology: organ models, root systems, and the demo '
        'sweet-basil geometry + pot-confinement reports.',
        'OrganModel',
        [
            _row(0, [
                _table('morph-organs', 0, 6, 'Organ models',
                       'OrganModel'),
                _table('morph-roots', 1, 6, 'Root systems',
                       'RootSystemModel'),
            ]),
            _row(1, [
                _api('morph-geometry', 0, 6,
                     'Geometry — sweet-basil',
                     '/api/morphology/plants/sweet-basil/geometry'),
                _api('morph-confinement', 1, 6,
                     'Confinement — sweet-basil in demo-herb-pot',
                     '/api/morphology/plants/sweet-basil/confinement'
                     '?pot=demo-herb-pot'),
            ]),
        ]),
    _page(
        'zones-home', 'zones',
        'AR zone capture: sites, zones, placed points, and the demo '
        'zones\' live estimate + 0.25 m cube packing reports.',
        'ZoneDefinition',
        [
            _row(0, [{
                'id': 'zones-board-item', 'index': 0,
                'type': 'component', 'rowSegmentsUsed': 12,
                'gridColumnStart': None,
                'title': 'Rooms / zones board',
                'visible': True, 'collapsed': False, 'cssClass': '',
                'componentProps': {'componentName': 'zones-board',
                                   'inputs': {}},
                'item': None, 'nestedRows': [],
            }]),
            _row(1, [
                _table('zones-zones', 0, 7, 'Zones', 'ZoneDefinition',
                       'name,site_name,room_label,zone_role,'
                       'simulation_ref,capture_mode,status'),
                _table('zones-sites', 1, 5, 'Sites', 'SiteDefinition'),
            ]),
            _row(2, [
                _table('zones-points', 0, 6, 'Placed points',
                       'ZonePoint',
                       'zone_name,index,kind,x,y,z,confidence', 60),
                _api('zones-site-summary', 1, 6,
                     'House summary — demo-house (0.25 m cubes)',
                     '/api/sites/demo-house/summary?cube_size_m=0.25'),
            ]),
            _row(3, [
                _api('zones-room-summary', 0, 6,
                     'Room summary — demo-room-zone (room volume vs '
                     'selected volumes)',
                     '/api/zones/demo-room-zone/room-summary'
                     '?cube_size_m=0.25'),
                _api('zones-air-estimate', 1, 6,
                     'Estimate — demo-air-shape (direct-3D hull)',
                     '/api/zones/demo-air-shape/estimate'),
            ]),
        ]),
    _page(
        'authority-home', 'authority',
        'Group/instance authority: who holds primary/shared authority, '
        'which group↔instance bindings are active on both sides, and '
        'every term-availability signal with its admission verdict.',
        'GroupAuthorityGrant',
        [
            _row(0, [
                _table('auth-group-grants', 0, 6, 'Group authority',
                       'GroupAuthorityGrant',
                       'name,group_name,username,role,status'),
                _table('auth-instance-grants', 1, 6,
                       'Instance authority', 'InstanceAuthorityGrant',
                       'name,instance_name,username,role,status'),
            ]),
            _row(1, [
                _table('auth-bindings', 0, 6, 'Bindings',
                       'GroupInstanceBinding',
                       'name,group_name,instance_name,counterparty,'
                       'status'),
                _table('auth-signals', 1, 6,
                       'Term-availability signals',
                       'TermAvailabilitySignal',
                       'term_name,context_name,group_name,'
                       'instance_name,status'),
            ]),
        ]),
]
