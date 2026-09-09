"""
@module suiteapps.suiteapps_seed

The suite apps we already had without the name (design §10, his go
2026-09-09): archipelago, engines, scorecard, business-ops, meetings,
wax-research, ai-assistant — written as SuiteAppDefinition / SuitePart /
SuiteContract rows so each gets a placement plan and a contract list.
Parts of kind isle-app that are compose roles / topology instances (not
store rows yet) name the role and say so in notes. The printing suite
lives in printing_suite; the isle itself is the platform, not a row.
"""


def _part(suite, key, app, kind, role, placement='any', required=True, order=0, notes='', same_as='', node=''):
    return {'name': '%s:%s' % (suite, key), 'suite': suite, 'app': app, 'kind': kind, 'role': role, 'placement': placement,
            'same_as': same_as, 'node': node, 'required': required, 'order': order, 'notes': notes}


def _contract(suite, key, cls, owner, producer, consumer, description):
    return {'name': '%s:%s' % (suite, key), 'suite': suite, 'object_class': cls, 'owner_module': owner,
            'producer': producer, 'consumer': consumer, 'description': description}


SEED_SUITES = [
    {'name': 'archipelago', 'title': 'Archipelago (mesh + relays)', 'purpose': 'isle-to-isle networking over Reticulum',
     'description': 'The Reticulum sidecar, the reticulum module (an extension of the relay guest), relay guests on hardware-tier devices, '
                    'the VPN mirror and the archipelago pages: .arch names, measured floors, relay policy.', 'front_page': 'reticulum'},
    {'name': 'engines', 'title': 'Science engines', 'purpose': 'compute workers the science modules call',
     'description': 'msci / cad / cnt engine containers + dask + the modules that resolve them through the *_remote ladders; '
                    'SPICE stays on isle-core.', 'front_page': 'engines'},
    {'name': 'scorecard', 'title': 'Democratic Scorecard', 'purpose': 'policy scoring as a client of Polari',
     'description': 'The political-scorecard project (Angular frontend, Java backend, its own DB/KeyDB/Keycloak/proxy) consuming '
                    'Polari scoring + dmvdata through the psc-a instance; the four policy/judicial apps sit on top.', 'front_page': 'scoring'},
    {'name': 'business-ops', 'title': 'Business operations', 'purpose': 'running a business on Odoo with Polari as the analysis layer',
     'description': 'Odoo + its Postgres on econ-core, the odooconnect bindings/sync, bizops stages and compliance, supplychain sourcing.', 'front_page': 'bizops'},
    {'name': 'meetings', 'title': 'Meetings', 'purpose': 'talking about the work, in Polari',
     'description': 'The LiveKit media server as a container + the collab module (sessions, meeting records, avatars).', 'front_page': 'collab'},
    {'name': 'wax-research', 'title': 'Wax printing research', 'purpose': 'the research stack behind wax printing and casting',
     'description': 'waxprint sims and lifecycle, waxsupply sourcing, supplychain, mathshapes, materials, casting molds, with the msci/cad engines — '
                    'the research sibling of the production printing suite.', 'front_page': 'waxprint'},
    {'name': 'ai-assistant', 'title': 'AI assistant', 'purpose': 'reasoning and voice over Polari objects',
     'description': 'The LocalAI fork as an engine container + the AI tools (ai-* rows in appstore) + the reasoning/voice pages; '
                    'the seeded ai-assistant-reasoning / ai-voice apps carry the pages.', 'front_page': 'ai-assistant'},
]

SEED_SUITE_PARTS = [
    # archipelago
    _part('archipelago', 'sidecar', 'pol-reticulum', 'isle-app', 'network', 'core', True, 0, 'compose role reticulum (docker-compose.reticulum.yml); engines/reticulum on the offline medium'),
    _part('archipelago', 'module', 'reticulum', 'hardware-extension-app', 'network', 'core', True, 1, 'rows, pages, the .arch namespace; extends isle-relay'),
    _part('archipelago', 'relay', 'isle-relay', 'hardware-app', 'network', 'hardware', False, 2, 'a relay guest per household/segment'),
    _part('archipelago', 'vpn', 'vpn', 'polari-app', 'network', 'core', False, 3, 'the isle-vpn mirror + proposals'),
    _part('archipelago', 'mesh', 'islemesh', 'polari-app', 'map', 'core', True, 4, 'the accepted copy of the isle inventory'),
    # engines
    _part('engines', 'msci', 'msci-engines', 'isle-app', 'support', 'node', True, 0, 'compose role msci-engines; SPICE on isle-core (his rule)', node='isle-core'),
    _part('engines', 'cad', 'cad-engines', 'isle-app', 'support', 'any', True, 1, 'compose role cad-engines (CAD import/export worker)'),
    _part('engines', 'cnt', 'cnt-engines', 'isle-app', 'support', 'node', False, 2, 'compose role cnt-engines', node='isle-core'),
    _part('engines', 'dask', 'dask', 'isle-app', 'support', 'any', False, 3, 'compose role dask (distributed compute)'),
    _part('engines', 'materials', 'materials_science', 'polari-app', 'material', 'core', True, 4, ''),
    _part('engines', 'shapes', 'mathshapes', 'polari-app', 'design', 'core', True, 5, ''),
    _part('engines', 'cntfet', 'cntfet', 'polari-app', 'design', 'core', False, 6, ''),
    _part('engines', 'sifet', 'sifet', 'polari-app', 'design', 'core', False, 7, ''),
    _part('engines', 'profiles', 'resources', 'polari-app', 'map', 'core', True, 8, 'ModuleResourceProfile + node resources'),
    # scorecard
    _part('scorecard', 'frontend', 'political-scorecard-frontend', 'isle-app', 'design', 'any', True, 0, 'political-scorecard-node compose service (Angular)'),
    _part('scorecard', 'backend', 'political-scorecard-backend', 'isle-app', 'control', 'same-as', True, 1, 'Java/Spring backend + its MariaDB/KeyDB/Keycloak/proxy', same_as='scorecard:frontend'),
    _part('scorecard', 'scoring', 'scoring', 'polari-app', 'measure', 'core', True, 2, 'the psc-a instance carries it'),
    _part('scorecard', 'sources', 'dmvdata', 'polari-app', 'material', 'core', True, 3, 'source retrievals and confirmations'),
    # business-ops
    _part('business-ops', 'odoo', 'pol-odoo', 'isle-app', 'control', 'node', True, 0, 'Odoo + pol-odoo-postgres on econ-core (his own system, keep it)', node='econ-core'),
    _part('business-ops', 'bindings', 'odooconnect', 'polari-app', 'support', 'core', True, 1, 'model bindings, sync receipts, scenarios'),
    _part('business-ops', 'bizops', 'bizops', 'polari-app', 'measure', 'core', True, 2, 'stages, compliance, milestones'),
    _part('business-ops', 'supply', 'supplychain', 'polari-app', 'material', 'core', False, 3, 'sourcing + price citations'),
    # meetings
    _part('meetings', 'livekit', 'pol-livekit', 'isle-app', 'control', 'any', True, 0, 'compose role livekit; lan_ip() for its address'),
    _part('meetings', 'collab', 'collab', 'polari-app', 'measure', 'core', True, 1, 'sessions, meeting records, avatars'),
    # wax-research
    _part('wax-research', 'waxprint', 'waxprint', 'polari-app', 'control', 'core', True, 0, 'print sims + mold lifecycle'),
    _part('wax-research', 'waxsupply', 'waxsupply', 'polari-app', 'material', 'core', True, 1, ''),
    _part('wax-research', 'supply', 'supplychain', 'polari-app', 'material', 'core', False, 2, ''),
    _part('wax-research', 'shapes', 'mathshapes', 'polari-app', 'design', 'core', True, 3, ''),
    _part('wax-research', 'materials', 'materials_science', 'polari-app', 'material', 'core', True, 4, ''),
    _part('wax-research', 'casting', 'casting', 'polari-app', 'mold', 'core', True, 5, 'mold nesting chains'),
    _part('wax-research', 'msci', 'msci-engines', 'isle-app', 'support', 'node', True, 6, 'the material sims', node='isle-core'),
    _part('wax-research', 'cad', 'cad-engines', 'isle-app', 'support', 'any', True, 7, 'CAD import/export'),
    # ai-assistant
    _part('ai-assistant', 'localai', 'localai', 'isle-app', 'control', 'any', True, 0, 'the dausume/LocalAI fork as an engine container (appstore ai tool row localai)'),
    _part('ai-assistant', 'tools', 'appstore', 'polari-app', 'support', 'core', True, 1, 'AiToolDefinition rows + the ai pages'),
    _part('ai-assistant', 'apps', 'polariapps', 'polari-app', 'design', 'core', True, 2, 'the ai-assistant-reasoning / ai-voice app rows'),
]

SEED_SUITE_CONTRACTS = [
    _contract('archipelago', 'node', 'ArchipelagoNode', 'reticulum', 'module', 'relay', 'the named, graded, measured nodes of the archipelago'),
    _contract('archipelago', 'link', 'LinkMeasurement', 'reticulum', 'sidecar', 'module', 'RTT / throughput / reliability per route (the floors)'),
    _contract('archipelago', 'device', 'DeviceLink', 'reticulum', 'mesh', 'relay', 'the radio / adapter a guest owns (exclusive)'),
    _contract('archipelago', 'exposure', 'AppVpnExposure', 'vpn', 'vpn', 'module', 'the .vpn rung of an app exposure'),
    _contract('archipelago', 'isle', 'IsleDevice', 'islemesh', 'mesh', 'module', 'the devices and their agent modes'),
    _contract('engines', 'profile', 'ModuleResourceProfile', 'resources', 'profiles', 'msci', 'what an engine needs (declared → measured)'),
    _contract('engines', 'material', 'Material', 'materials_science', 'materials', 'msci', 'the material rows the sims start from'),
    _contract('engines', 'shape', 'MathShapeDefinition', 'mathshapes', 'shapes', 'cad', 'shapes exported/imported through the CAD worker'),
    _contract('engines', 'cnt', 'CNTFETSimResult', 'cntfet', 'cnt', 'cntfet', 'a CNT engine run\'s result'),
    _contract('scorecard', 'claim', 'CredibilityClaim', 'scoring', 'scoring', 'frontend', 'what the scorecard shows'),
    _contract('scorecard', 'vote', 'AssertionCredibilityVote', 'scoring', 'frontend', 'scoring', 'a user\'s vote on an assertion (through the backend)'),
    _contract('scorecard', 'source', 'SourceRetrieval', 'dmvdata', 'sources', 'scoring', 'a retrieved source with its confirmation'),
    _contract('scorecard', 'case', 'CourtCase', 'scoring', 'scoring', 'frontend', 'judicial records the lean app shows'),
    _contract('business-ops', 'binding', 'OdooModelBinding', 'odooconnect', 'bindings', 'odoo', 'which Odoo model maps to which Polari class'),
    _contract('business-ops', 'receipt', 'OdooSyncReceipt', 'odooconnect', 'odoo', 'bizops', 'what a sync brought over, when'),
    _contract('business-ops', 'stage', 'BusinessStageDefinition', 'bizops', 'bizops', 'bindings', 'the business stage the ops run in'),
    _contract('business-ops', 'sourcing', 'SupplySourceProfile', 'supplychain', 'supply', 'bizops', 'where inputs come from, priced by citation'),
    _contract('meetings', 'session', 'CollaborationSession', 'collab', 'collab', 'livekit', 'a session the media server hosts'),
    _contract('meetings', 'record', 'MeetingRecord', 'collab', 'livekit', 'collab', 'what happened, recorded as a row'),
    _contract('wax-research', 'sim', 'WaxPrintSimState', 'waxprint', 'waxprint', 'casting', 'the print sim state a mold derives from'),
    _contract('wax-research', 'lifecycle', 'MoldLifecycleRecord', 'waxprint', 'casting', 'waxprint', 'a mold\'s life: fills, reclaims, retirement'),
    _contract('wax-research', 'feedstock', 'WaxFeedstockDefinition', 'waxprint', 'waxsupply', 'waxprint', 'the wax that gets printed'),
    _contract('wax-research', 'source', 'WaxSourceDefinition', 'waxsupply', 'supply', 'waxsupply', 'where the wax comes from'),
    _contract('wax-research', 'mold', 'MoldDefinition', 'casting', 'casting', 'waxprint', 'the mold the chain nests'),
    _contract('wax-research', 'shape', 'MathShapeDefinition', 'mathshapes', 'shapes', 'casting', 'the part shape'),
    _contract('ai-assistant', 'tool', 'AiToolDefinition', 'appstore', 'tools', 'localai', 'which tool a model may call, with its knob'),
    _contract('ai-assistant', 'app', 'PolariAppDefinition', 'polariapps', 'apps', 'tools', 'the assistant\'s app rows (pages, nav)'),
]


def _store(name, title, image, port, domain, description, category, provides_engine='', service='', published=True, notes='', kind='mesh-app'):
    return {'name': name, 'title': title, 'kind': kind, 'category': category, 'description': description,
            'source_ref': image, 'service': service or name, 'port': port, 'domain': domain, 'provides_engine': provides_engine,
            'published': published, 'notes': notes}


#: store rows for the container parts of the prior suites (his go 2026-09-09) — images/ports from the compose roles they came from;
#: `isle app deploy <name> --image <ref> --service <svc> --port <p> --domain <d> [--engine <kind>]` is the plan for each
SEED_SUITE_CATALOG = [
    _store('pol-reticulum', 'Reticulum sidecar', 'pol-reticulum:staging', 4285, 'reticulum.isle',
           'The pinned MIT Reticulum stack (dausume forks) as a sidecar: TCP bearer 4242, /status 4285, LXMF messaging. The archipelago suite\'s transport.',
           'network', provides_engine='reticulum.mesh', notes='compose role reticulum (docker-compose.reticulum.yml); bearer port 4242 must also be published'),
    _store('msci-engines', 'Materials-science engines', 'prf-msci-engines:staging', 9500, 'msci.isle',
           'The materials-science compute worker (DFT/percolation/SPICE ladder) the materials modules resolve through their *_remote ladders.',
           'engines', provides_engine='msci', notes='compose role msci-engines; SPICE stays on isle-core (his rule 2026-08-31)'),
    _store('cad-engines', 'CAD engines', 'prf-cad-engines:staging', 9600, 'cad.isle',
           'The CAD import/export worker (STEP/STL) mathshapes resolves through cad_remote.', 'engines', provides_engine='cad', notes='compose role cad-engines'),
    _store('cnt-engines', 'CNT FET engines', 'prf-cnt-engines:staging', 9700, 'cnt.isle',
           'The CNT/FET simulation worker the cntfet + sifet modules call.', 'engines', provides_engine='cnt', notes='compose role cnt-engines'),
    _store('dask', 'Dask distributed compute', 'prf-backend:staging', 8786, 'dask.isle',
           'A dask scheduler + workers on the backend image (twins, cross-instance sims).', 'engines', provides_engine='dask', service='dask-scheduler',
           notes='compose role dask (scheduler + two workers) — a multi-service compose, deploy with --compose polari-rf-node/docker-compose.dask.yml'),
    _store('pol-livekit', 'LiveKit media server', 'livekit/livekit-server:v1.9.12', 7880, 'meet.isle',
           'The meetings media server (signalling 7880, ICE-TCP 7881); TLS at the proxy; the collab module\'s engine.', 'collaboration', provides_engine='livekit',
           notes='compose role livekit; lan_ip() for its advertised address (hostname -I lists docker bridges first)'),
    _store('pol-odoo', 'Odoo (business ops)', 'pol-odoo:staging', 8069, 'odoo.isle',
           'Odoo + its Postgres (pol-odoo-postgres) — the business backbone on econ-core; odooconnect binds it into Polari.', 'business', provides_engine='business-ops',
           notes='compose profile odoo in the suite compose (pol odoo up); two services — deploy with --compose'),
    _store('localai', 'LocalAI (self-hosted models)', 'ghcr.io/dausume/localai:<PIN ME>', 8080, 'ai.isle',
           'The MIT LocalAI fork as an OpenAI-compatible engine for the assistant (reasoning/voice/embeddings), offline once models are cached.', 'ai',
           provides_engine='reasoning', published=False, notes='unpublished until the dausume/LocalAI image is pinned (LocalAI gate: MIT)'),
    _store('political-scorecard-frontend', 'Democratic Scorecard (web)', 'psc-frontend:latest', 4200, 'scorecard.isle',
           'The scorecard\'s Angular frontend (political-scorecard-node).', 'policy', notes='built by political-scorecard-node/docker-compose.yml; multi-service — deploy with --compose'),
    _store('political-scorecard-backend', 'Democratic Scorecard (API)', 'psc-backend:latest', 8080, 'api.scorecard.isle',
           'The scorecard\'s Java/Spring backend with its MariaDB, KeyDB, Keycloak and proxy; a client of Polari scoring via the psc-a instance.', 'policy',
           notes='published on the host as 8580:8080 in the project compose; deploy with --compose'),
]
