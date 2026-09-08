"""
@cross-cutting
@module polariapps.apps_seed

The first three Polari-Apps (tt-12, Dustin's examples verbatim):
a local wax 3D-printing company, a lean judicial app, and a DMV
policy-analysis build. Each is just a module configuration — the
capability comes from modules that already exist; the app names
the use-case and its front doors.

nav-1 (NAVIGATION_REVAMP_PLAN §5): eight DISCIPLINE apps join the
three use-case apps. A discipline app carries its own navigation
menu as data (nav_json): groups of items whose `kind`
(page | simspace | view | tech-node) is what makes studies navigate
INTO visuals instead of dumping payloads. `requires_module` is never
used to HIDE an item — availability is derived live (nav-2) and an
absent module renders as a bring-online affordance. Every route here
exists in the Angular router today; catalog links ride the generic
/class-main-page/:class CRUDE surface; tech-node items carry a `ref`
into the seeded tech trees instead of a route.

@consumers
  - polariServer seed loop (legacy insert pass + the arch-1 upsert
    path, so changed seed fields REACH live prior rows)
  - polariapps.apps_selftest
"""

import json as _json


def _app(name, title, use_case, description, modules, pages,
         nav=(), personas=(), discipline='', engine_page=''):
    return {'name': name, 'title': title, 'use_case': use_case,
            'description': description,
            'modules_json': _json.dumps(list(modules)),
            'pages_json': _json.dumps(list(pages)),
            'nav_json': _json.dumps(list(nav)),
            'personas_json': _json.dumps(list(personas)),
            'discipline': discipline, 'engine_page': engine_page,
            'notes': ''}


def _grp(group, *items, top=False):
    """A nav group. The side menu always renders every group (the
    complete map); top=True ADDITIONALLY promotes the group to the
    shell's top bar as a dropdown — apps leverage BOTH menus, they
    replace neither (Dustin 2026-07-31)."""
    grp = {'group': group, 'items': list(items)}
    if top:
        grp['top_menu'] = True
    return grp


def _tgrp(group, *items):
    """A group promoted to the top bar (and still in the side map)."""
    return _grp(group, *items, top=True)


def _it(label, kind, route='', requires_module='', ref=''):
    item = {'label': label, 'kind': kind}
    if route:
        item['route'] = route
    if requires_module:
        item['requires_module'] = requires_module
    if ref:
        item['ref'] = ref
    return item


SEED_POLARI_APPS = [
    _app('wax-print-shop', 'Wax 3D Printing Company',
         'A local wax 3D-printing company trying different wax '
         'simulations and different auger shapes for the different '
         'models they can offer.',
         'Wax print simulation + recipe optimizer (waxprint), the '
         'materials basis for wax formulations (materialsScience), '
         'auger/part shape variants (mathshapes), simulation '
         'composition (simulations), and the wax sourcing + supply '
         'ledger (waxsupply, supplychain).',
         ('waxprint', 'materialsScience', 'mathshapes',
          'simulations', 'waxsupply', 'supplychain'),
         ('/wax-print-sim', '/display/wax-supply',
          '/display/supply-chain')),
    _app('judicial-lean', 'Lean Judicial App',
         'A lean judicial deployment: court cases as no-code rows, '
         'democratic proofs, term competition and credibility '
         'tracking — nothing else.',
         'The no-code engine with the judicial CourtCase compiler '
         '(polariNoCode) plus the scoring/epistemics stack '
         '(scoring).',
         ('polariNoCode', 'scoring'),
         ('/custom-no-code', '/scoring')),
    _app('dmv-policy-analysis', 'DMV Policy Analysis',
         'A DMV-area policy-analysis build: cost-of-living '
         'evidence, source trust, legislation tracking, and the '
         'accountability scorecards over them.',
         'DMV cost-of-living catalog + trust stack (dmvdata) and '
         'the scoring engine that reads it (scoring).',
         ('dmvdata', 'scoring'),
         ('/scoring/survival', '/scoring/accountability')),
    # nmp-0 (Dustin 2026-08-20): nutrition IS a polari app — meal
    # planning ships as its own configurable, deb-buildable shell
    # (`pol apps shell nutrition-planner`) like every other app;
    # every capability underneath is treeObject rows + displays, so
    # the app is extendable through the same CRUDE/no-code surfaces.
    # Pages grow with the nmp phases (nmp-8 adds the real pages).
    _app('nutrition-planner', 'Nutrition & Meal Planning',
         'A household planning meals: profiles with thresholds, '
         'meal plans checked against healthy bands, cooking '
         'workflows, activity, the garden loop — and the mpa app '
         'layer: pantry, prices by geolocation, per-login tracking '
         'of nutrition/acidity/weight over time, PSPP food states.',
         'Person/household profiles + DRI thresholds, the FDC '
         'starter pantry, foods and nutrient contents, and the '
         'harvest loop (nutrition + aquaponics); meal/recipe/'
         'activity layers (nmp arc); market/pantry/accounts/'
         'tracking + the foodstate PSPP substrate (mpa arc).',
         ('nutrition', 'aquaponics', 'foodstate', 'pspp'),
         ('/display/mealplan', '/display/mealplan/planner',
          '/display/mealplan/pantry', '/display/mealplan/market',
          '/display/mealplan/trends', '/display/mealplan/household',
          '/display/mealplan/meals', '/display/mealplan/week',
          '/display/mealplan/me', '/display/mealplan/supply',
          '/display/nutrition-home', '/display/nutrition/profile',
          '/display/nutrition/meals', '/display/nutrition/recipes',
          '/display/nutrition/activity', '/display/nutrition/garden'),
         nav=(
             _tgrp('Meal Planning',
                   _it('Home', 'page', '/display/mealplan',
                       'nutrition'),
                   _it('Plan the week', 'page', '/display/mealplan/week',
                       'nutrition'),
                   _it('Meals for me', 'page',
                       '/display/mealplan/meals?object=demo-alex',
                       'nutrition'),
                   _it('My tracking', 'page',
                       '/display/mealplan/me?object=demo-alex',
                       'nutrition'),
                   _it('Today', 'page',
                       '/display/mealplan/today?object=demo-alex',
                       'nutrition'),
                   _it('Cook now', 'page',
                       '/display/mealplan/cooknow?object=demo-alex',
                       'nutrition'),
                   _it('Shopping trip', 'page',
                       '/display/mealplan/shoptrip', 'nutrition'),
                   _it('Weekly review', 'page',
                       '/display/mealplan/review', 'nutrition'),
                   _it('Planner', 'page', '/display/mealplan/planner',
                       'nutrition'),
                   _it('Pantry', 'page', '/display/mealplan/pantry',
                       'nutrition'),
                   _it('Food Supply (map)', 'page',
                       '/display/mealplan/supply', 'nutrition'),
                   _it('Market & Prices', 'page',
                       '/display/mealplan/market', 'nutrition'),
                   _it('Trends', 'page', '/display/mealplan/trends',
                       'nutrition'),
                   _it('Household & Work', 'page',
                       '/display/mealplan/household', 'nutrition')),
             _tgrp('Kitchen',
                   _it('Meals & Templates', 'page',
                       '/display/nutrition/meals', 'nutrition'),
                   _it('Recipes', 'page',
                       '/display/nutrition/recipes', 'nutrition'),
                   _it('Garden Loop', 'page',
                       '/display/nutrition/garden', 'nutrition')),
             _grp('Profile & Tracking',
                  _it('My Profile', 'page',
                      '/display/nutrition/profile', 'nutrition'),
                  _it('Activity', 'page',
                      '/display/nutrition/activity', 'nutrition'),
                  _it('Trends', 'page', '/display/mealplan/trends',
                      'nutrition')),
             _grp('Foundations',
                  _it('Nutrition Home', 'page',
                      '/display/nutrition-home', 'nutrition'),
                  _it('Food States (PSPP)', 'page',
                      '/display/mealplan/trends', 'foodstate')),
         ),
         personas=('household-cook', 'meal-planner')),

    # ------------------------------------------------------------------
    # Discipline apps (nav-1). Personas per NAVIGATION_REVAMP_PLAN §4.4
    # plus software-engineer and network/cloud (Dustin 2026-07-31).
    # ------------------------------------------------------------------
    _app('app-magnetics', 'Magnetics & Motors',
         'Electrical engineers studying magnetic circuits, the Lavet '
         'clock motors, and the goal-driven scale studies over them.',
         'The magnetics field views and motor studies (magnetics, '
         'motors), the composition-backed clock views (composition), '
         'and the gear trains the motors drive (gears).',
         ('magnetics', 'motors', 'composition', 'gears'),
         ('/magnetics/motor', '/magnetics/clock-views'),
         nav=(
             _tgrp('Studies',
                  _it('M0 clock motor — running', 'page',
                      route='/magnetics/motor', requires_module='motors'),
                  _it('Motor scene (3D)', 'simspace',
                      route='/sim-spaces/motor-m0-viz',
                      requires_module='motors'),
                  _it('Goals & scales (clock views)', 'view',
                      route='/magnetics/clock-views',
                      requires_module='composition'),
                  _it('M1 reluctance — sequencing & drive', 'view',
                      route='/magnetics/clock-views'
                            '?view=view-m1-sequencing',
                      requires_module='composition'),
                  _it('M1 motor scene (3D)', 'simspace',
                      route='/sim-spaces/motor-m1-viz',
                      requires_module='motors'),
                  _it('M2 PM rotor — rotation & lift', 'view',
                      route='/magnetics/clock-views'
                            '?view=view-m2-rotation',
                      requires_module='composition'),
                  _it('M2 motor scene (3D)', 'simspace',
                      route='/sim-spaces/motor-m2-viz',
                      requires_module='motors'),
                  _it('Field views', 'page', route='/magnetics/fields',
                      requires_module='magnetics'),
                  _it('Clock motor — parts & materials', 'page',
                      route='/magnetics/clock-motor',
                      requires_module='motors')),
             _grp('Tree',
                  _it('Electromagnetic systems', 'tech-node',
                      ref='electronics/electromagnetic-systems'))),
         personas=('electrical-engineer',), discipline='magnetics'),
    _app('app-mechanical', 'Mechanical Engineering',
         'Mechanical engineers working gear trains, part composition '
         '(components, interfaces, promotion), and the stress/fatigue '
         'studies on moving parts.',
         'Gear trains as graphs (gears), part composition with its '
         'mechanical clock views (composition), and the motor scenes '
         'the mechanisms ride in (motors, mathshapes).',
         ('gears', 'composition', 'motors', 'mathshapes'),
         ('/magnetics/clock-views',),
         nav=(
             _tgrp('Studies',
                  _it('Clock views — mechanical sections', 'view',
                      route='/magnetics/clock-views',
                      requires_module='composition'),
                  _it('M1 — mechanical & interfaces', 'view',
                      route='/magnetics/clock-views'
                            '?view=view-m1-mechanical',
                      requires_module='composition'),
                  _it('M1 — positioning proof', 'view',
                      route='/magnetics/clock-views'
                            '?view=view-m1-positioning',
                      requires_module='composition'),
                  _it('M2 — lifting (the hoist proof)', 'view',
                      route='/magnetics/clock-views'
                            '?view=view-m2-lift',
                      requires_module='composition'),
                  _it('Motor scene (3D)', 'simspace',
                      route='/sim-spaces/motor-m0-viz',
                      requires_module='motors')),
             _grp('Catalogs',
                  _it('Gear trains', 'page',
                      route='/class-main-page/GearTrainDefinition',
                      requires_module='gears'),
                  _it('Gear types', 'page',
                      route='/class-main-page/GearTypeDefinition',
                      requires_module='gears'),
                  _it('Part archetypes', 'page',
                      route='/class-main-page/PartArchetypeDefinition',
                      requires_module='composition'),
                  _it('Failure modes', 'page',
                      route='/class-main-page/FailureModeDefinition',
                      requires_module='composition'))),
         personas=('mechanical-engineer',), discipline='mechanical'),
    _app('app-materials-science', 'Materials Science',
         'Materials scientists searching and simulating materials — '
         'FEM/DFT engines, the PSPP statistical stack, and the '
         'multi-scale simulations over material bodies.',
         'The materials catalog + engines (materialsScience), the '
         'PSPP process-structure-property-performance stack (pspp), '
         'and the multi-scale/sim-space composition surfaces.',
         ('materialsScience', 'pspp', 'mathshapes'),
         ('/pspp', '/multi-scale-sims'),
         nav=(
             _tgrp('Materials',
                  _it('Materials catalog', 'page',
                      route='/class-main-page/Material',
                      requires_module='materialsScience'),
                  _it('Equations', 'page', route='/equations')),
             _tgrp('Simulations',
                  _it('Multi-scale sims', 'page',
                      route='/multi-scale-sims'),
                  _it('Sim spaces', 'simspace', route='/sim-spaces')),
             _grp('PSPP',
                  _it('PSPP home', 'page', route='/pspp',
                      requires_module='pspp'),
                  _it('Proofing', 'page', route='/pspp/proofing',
                      requires_module='pspp'),
                  _it('Network', 'page', route='/pspp/network',
                      requires_module='pspp'),
                  _it('Grader', 'page', route='/pspp/grader',
                      requires_module='pspp'),
                  _it('Progress', 'page', route='/pspp/progress',
                      requires_module='pspp'),
                  _it('Guide', 'page', route='/pspp/guide',
                      requires_module='pspp'),
                  _it('Benchmarks', 'page', route='/pspp/benchmarks',
                      requires_module='pspp'),
                  _it('State DAG', 'page', route='/pspp/states',
                      requires_module='pspp'),
                  _it('Structure', 'page', route='/pspp/structure',
                      requires_module='pspp'),
                  _it('Ceramics', 'page', route='/pspp/ceramics',
                      requires_module='pspp'),
                  _it('Research', 'page', route='/pspp/research',
                      requires_module='pspp'))),
         personas=('materials-scientist',),
         discipline='materials-science'),
    _app('app-business', 'Business Operations',
         'Business operators running the make-vs-buy stack: flows, '
         'planning, readiness, quotes, and the Odoo splice.',
         'Business operations + deal pricing (bizops) and the Odoo '
         'connector/sync surfaces (odooconnect), with the supply '
         'ledger underneath (supplychain).',
         ('bizops', 'odooconnect', 'supplychain'),
         ('/business/start', '/business/odoo'),
         engine_page='/engines/business-ops',
         nav=(
             _tgrp('Operations',
                  _it('Business start', 'page', route='/business/start',
                      requires_module='bizops'),
                  _it('Odoo business', 'page', route='/business/odoo',
                      requires_module='odooconnect')),),
         personas=('business-operator',), discipline='business'),
    _app('app-policy', 'Policy Analysis',
         'Policy analysts working evidence: cost-of-living data, '
         'source trust, government/legal catalogs, and maps. The '
         'political-scorecard splice is this app\'s future group.',
         'DMV-area sources + cost-of-living evidence (dmvdata) and '
         'the scoring epistemics that read it (scoring).',
         ('dmvdata', 'scoring'),
         ('/scoring/survival', '/maps'),
         nav=(
             _tgrp('Evidence',
                  _it('Cost of living — survival costs', 'page',
                      route='/scoring/survival',
                      requires_module='scoring'),
                  _it('Scoring & epistemics', 'page', route='/scoring',
                      requires_module='scoring'),
                  _it('Maps', 'page', route='/maps')),
             _grp('Sources & catalogs',
                  _it('Government sources', 'page',
                      route='/class-main-page/GovSource',
                      requires_module='dmvdata'),
                  _it('Legislation records', 'page',
                      route='/class-main-page/LegislationRecord',
                      requires_module='dmvdata'),
                  _it('Company sources', 'page',
                      route='/class-main-page/CompanySource',
                      requires_module='dmvdata'))),
         personas=('policy-analyst',), discipline='policy'),
    _app('app-scorecards-data-analysis', 'Scorecards & Data Analysis',
         'Analysts building scorecards over evidence — accountability '
         'and survival scoring — with the no-code data workbench '
         '(datasets, graphs, tables) alongside.',
         'The scoring engine + scorecards (scoring) over the dmvdata '
         'evidence base, and the core no-code analysis pages as the '
         'workbench.',
         ('scoring', 'dmvdata'),
         ('/scoring', '/datasets'),
         nav=(
             _tgrp('Scorecards',
                  _it('Scoring home', 'page', route='/scoring',
                      requires_module='scoring'),
                  _it('Accountability', 'page',
                      route='/scoring/accountability',
                      requires_module='scoring'),
                  _it('Survival costs', 'page',
                      route='/scoring/survival',
                      requires_module='scoring')),
             _grp('Workbench',
                  _it('Datasets', 'page', route='/datasets'),
                  _it('Graphs', 'page', route='/graphs'),
                  _it('Tables', 'page', route='/tables'))),
         personas=('policy-analyst', 'business-operator'),
         discipline='data-analysis'),
    _app('app-software-engineering', 'Software Engineering',
         'Software engineers customizing the instance itself: '
         'classes, displays, no-code logic, equations — and the '
         'inspection surfaces underneath.',
         'The no-code build surfaces (create-class, custom no-code, '
         'displays, equations, matrices — all core) plus the API/'
         'typing/diagnostics inspection pages; the testing module '
         'gates the test surface on test builds.',
         ('polariNoCode',),
         ('/displays', '/custom-no-code'),
         nav=(
             _tgrp('Build',
                  _it('Create class', 'page', route='/create-class'),
                  _it('Custom no-code', 'page',
                      route='/custom-no-code'),
                  _it('Displays', 'page', route='/displays'),
                  _it('Equations', 'page', route='/equations'),
                  _it('Matrices', 'page', route='/matrices')),
             _grp('Inspect',
                  _it('Typing info', 'page', route='/typing-info'),
                  _it('Manager info', 'page', route='/manager-info'),
                  _it('API config', 'page', route='/api-config'),
                  _it('API profiler', 'page', route='/api-profiler'),
                  _it('System diagnostics', 'page',
                      route='/system-diagnostics'),
                  _it('Testing', 'page', route='/testing',
                      requires_module='testing'))),
         personas=('software-engineer',), discipline='software'),
    _app('app-topology-network', 'Topology, Network & Cloud',
         'Network and cloud engineers running the instance mesh: '
         'topology, module placement, bringup, and deployment plans.',
         'The topology surfaces (core), module management + lazy '
         'bringup (moduleService, core), app deployment planning '
         '(polariapps), and the tech trees the placements answer to '
         '(techtree).',
         ('polariapps', 'techtree'),
         ('/topology', '/module-management'),
         nav=(
             _tgrp('Topology',
                  _it('Topology home', 'page', route='/topology'),
                  _it('Polari config', 'page', route='/polari-config')),
             _tgrp('Modules & deployment',
                  _it('Module management', 'page',
                      route='/module-management'),
                  _it('Module bringup', 'page',
                      route='/modules/bringup'),
                  _it('Apps & deployment plans', 'page',
                      route='/apps')),
             _grp('Tree',
                  _it('Tech trees', 'page', route='/tech-tree',
                      requires_module='techtree'))),
         personas=('network-engineer', 'cloud-engineer'),
         discipline='network-cloud'),
    # mtg-3: collaboration is CROSS-DISCIPLINE — every persona meets.
    # Its own app rather than a group bolted onto one discipline, so
    # an instance can carry meetings without carrying that discipline
    # (and can drop them just as cleanly — the modularization rule).
    _app('app-collaboration', 'Meetings & Collaboration',
         'Anyone meeting about the work: group audio/video/screen '
         'share on the LAN, around the same Polari objects.',
         'Collaboration sessions + KC-gated LiveKit tokens (collab); '
         'the media server itself is the separate pol-livekit '
         'service, and an absent one refuses honestly rather than '
         'hiding the page.',
         ('collab',),
         ('/meetings',),
         nav=(
             _tgrp('Meetings',
                  _it('Meetings', 'page', route='/meetings',
                      requires_module='collab')),),
         personas=('researcher', 'business-operator'),
         discipline='collaboration',
         engine_page='/engines/livekit'),
    # ret-1b: the mesh archipelago — isles as blocks, radios and apps
    # inside, measured latency between, demand vs capacity honestly
    # verdicted. Off-grid transport is its own app: an instance can
    # carry the mesh without carrying any one discipline.
    _app('app-archipelago', 'Mesh Archipelago',
         'The .arch mesh at a glance: which isles are actually '
         'reachable right now, what radios they carry, what the apps '
         'are asking for and what the links can bear.',
         'Reticulum transport rows (reticulum module); the RNS stack '
         'itself is the separate pol-reticulum sidecar, and an '
         'absent one refuses honestly rather than hiding the page.',
         ('reticulum',),
         ('/arch',),
         nav=(
             _tgrp('Archipelago',
                  _it('Arch topology', 'page', route='/arch',
                      requires_module='reticulum')),),
         personas=('network-engineer', 'researcher'),
         discipline='network-cloud',
         engine_page='/engines/reticulum'),

    # ------------------------------------------------------------------
    # sep-4 (decision 9): engine-only tiles — "just so we can see
    # where they are". One page each: the engine DATA PAGE
    # (placement, reachability ladder, usage windows). Dual-natured
    # engines (odoo/livekit/reticulum) keep their own UI and carry
    # engine_page on their EXISTING rows instead — one tile, two
    # natures, never two tiles.
    # ------------------------------------------------------------------
    _app('engine-msci', 'Materials-Science Engines',
         'Anyone asking where the DFT/FEM compute lives, whether it '
         'is reachable, and what flows through it.',
         'The compiled-extension science worker (pyscf, pymatgen, '
         'sfepy) as a tile: placement across the topology, the '
         'resolution ladder rendered honestly, usage over time.',
         ('materialsScience',),
         ('/engines/msci',),
         nav=(
             _tgrp('Engine',
                  _it('Engine data page', 'page',
                      route='/engines/msci',
                      requires_module='materialsScience')),),
         personas=('researcher',),
         engine_page='/engines/msci'),
    _app('engine-cad', 'CAD Engines',
         'Anyone asking where the mesh/CAD compute lives, whether '
         'it is reachable, and what flows through it.',
         'The trimesh + optional FreeCAD/OpenCASCADE worker as a '
         'tile: placement across the topology, the resolution '
         'ladder rendered honestly, usage over time.',
         ('mathshapes',),
         ('/engines/cad',),
         nav=(
             _tgrp('Engine',
                  _it('Engine data page', 'page',
                      route='/engines/cad',
                      requires_module='mathshapes')),),
         personas=('researcher',),
         engine_page='/engines/cad'),
    # ------------------------------------------------------------------
    # ai-4 (AI_TOOL_LINKAGES decision 5): the linkages that matter
    # as visitable, configurable APPS. The seam is CORE
    # (polariApiServer), so no module requirement; sep-3 launchers
    # come free. meetings-stt waits for the collab transcription
    # seam — seeding a tile onto an unbuilt page would be dishonest.
    # ------------------------------------------------------------------
    _app('ai-assistant-reasoning', 'Assistant Reasoning',
         'Anyone asking WHICH AI backs the assistant on this '
         'instance, whether it is ready, and what flows through it.',
         'The assistant\'s reasoning binding as a tile: the active '
         'provider, its readiness ladder, and usage over time '
         '(counts/bytes/latency — never conversation content). '
         'Tool choice + credentials live in the store\'s AI '
         'section and /ai/providers.',
         (),
         ('/engines/reasoning', '/isle-store', '/ai-hosting'),
         nav=(
             _tgrp('AI',
                  _it('Reasoning engine page', 'page',
                      route='/engines/reasoning'),
                  _it('AI tools (store section)', 'page',
                      route='/isle-store'),
                  _it('Remote hosting (dated prices)', 'page',
                      route='/ai-hosting')),),
         personas=('business-operator', 'researcher'),
         engine_page='/engines/reasoning'),
    _app('ai-voice', 'Assistant Voice',
         'Anyone asking where the assistant\'s EARS and MOUTH run — '
         'on the isle (sovereign) or in a cloud.',
         'Both voice directions as one tile: speech-to-text '
         '(/ai/voice/transcribe) and text-to-speech '
         '(/ai/voice/speak) ride the active OpenAI-compatible '
         'provider — fully on-isle when that provider is a local '
         'server (LocalAI). Browser Web Speech is the STATED '
         'fallback (Chrome STT is cloud-backed). Status: GET '
         '/ai/voice.',
         (),
         ('/engines/reasoning', '/isle-store', '/ai-hosting'),
         nav=(
             _tgrp('AI',
                  _it('Reasoning engine page', 'page',
                      route='/engines/reasoning'),
                  _it('AI tools (store section)', 'page',
                      route='/isle-store'),
                  _it('Remote hosting (dated prices)', 'page',
                      route='/ai-hosting')),),
         personas=('business-operator',),
         engine_page='/engines/reasoning'),
]
