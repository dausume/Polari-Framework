"""
@cross-cutting
@module topology.topology_seed

Seeds mirroring CURRENT REALITY (2026-07-09) so the first Topology
page shows TRUTH, not placeholders: the combined compose suite +
twin/dask on staging A, the polari-engines swarm stack (single-node
swarm, :9500), and the ssh deploy targets from
pol-build/manifests/nodes.yml.

TopologyObservation is deliberately NOT seeded — observed state is
reported by `pol topology report`, never guessed.

@consumers
  - polariServer._seedSimSpace3D seed_pairs (idempotent-by-name)
  - topology.selftest_topology (fake-manager fixtures)
"""

import json

SEED_NODE_MACHINES = [
    {
        'name': 'staging-a',
        'ssh_alias': '',
        'arch': 'x86_64',
        'mem_gb': 0.0,
        'roles_json': json.dumps(['core', 'suite', 'swarm-manager']),
        'swarm_role': 'manager',
        'repo_dir': '~/Desktop/polari-suite',
        'source': 'manual',
        'notes': 'Local staging host (192.168.0.210) — combined '
                 'compose suite + single-node swarm (polari-engines '
                 'stack) + twin/dask compose projects.',
    },
    {
        'name': 'isle-core',
        'ssh_alias': 'isle-core',
        'arch': 'x86_64',
        'mem_gb': 7.6,
        'roles_json': json.dumps(['engines', 'remote-worker', 'node']),
        'swarm_role': 'none',
        'repo_dir': '~/polari-suite',
        'source': 'nodes.yml',
        # res-1 knob: prf-cad-engines is PINNED here
        # (node.hostname==dustin-etts-mesh-core), so its /system-info
        # reports THIS host. Routing mesh serves it on the core IP.
        'system_info_url': 'http://192.168.0.210:9600',
        'notes': '6-core i5 / 7.6G; also runs the Isle-Mesh project. '
                 'system_info_url -> the cad-engines service pinned '
                 'here.',
    },
    {
        # Renamed from 'lightweight' 2026-07-27 (names = mandates):
        # the BUSINESS-OPS/ECONOMICS core, and the Odoo host (od-0).
        'name': 'econ-core',
        'ssh_alias': 'econ-core',
        'arch': 'x86_64',
        'mem_gb': 7.5,
        'roles_json': json.dumps(['engines', 'remote-worker',
                                  'business-ops', 'economics']),
        'swarm_role': 'none',
        'repo_dir': '~/polari-suite',
        'source': 'nodes.yml',
        # res-1 knob: polari-engines_msci-engines is PINNED here
        # (node.labels.polari.machine==econ-core).
        'system_info_url': 'http://192.168.0.210:9500',
        'notes': 'N95 4-core / 7.5G; suspend disabled 2026-07-08 — '
                 'safe headless target. Business-ops/economics core; '
                 'Odoo + odoo-postgres land here '
                 '(ODOO_INTEGRATION_PLAN.md).',
    },
]

SEED_ORCHESTRATION_TARGETS = [
    {
        'name': 'compose',
        'display_name': 'Docker Compose',
        'available': True,
        'description': 'Per-node compose projects — the 13 generated '
                       'bundles (pol build render / pol suite up).',
    },
    {
        'name': 'swarm',
        'display_name': 'Docker Swarm',
        'available': True,
        'description': 'Swarm stacks via stackify (pol swarm deploy). '
                       'Single-node proven (polari-engines); '
                       'multi-node join is top-4.',
    },
    {
        'name': 'isle',
        'display_name': 'Isle-Mesh',
        'available': False,
        'description': 'Future isle-mesh orchestration — named in '
                       'the vocabulary, refused by validation until '
                       'it lands.',
    },
]

SEED_TOPOLOGY_DEFINITIONS = [
    {
        'name': 'staging-a',
        'description': 'Current reality: combined prf+psc compose '
                       'suite, twin-b + dask compose projects, and '
                       'the polari-engines swarm stack — all on the '
                       'staging-a host.',
        'default_target': 'compose',
        'status': 'applied',
        'is_active': True,
        'schema_version': '1',
        'notes': 'Seeded by top-1 to mirror the live 2026-07-09 '
                 'deployment; becomes the first portable package '
                 '(topologies/staging-a.topology.yml, top-3).',
    },
]

SEED_INSTANCE_DEFINITIONS = [
    {
        'name': 'prf-a',
        'kind': 'prf',
        'service_kinds_json': json.dumps([
            'prf-backend', 'prf-frontend']),
        'replicas': 1,
        'env_tier': 'staging',
        'machine_name': 'staging-a',
        'db_backend': 'sqlite',
        'image_tag': 'staging',
        'orchestration_target': 'compose',
        # Staging lives on the LAN behind nip.io — local by reality.
        # Operators flip this to 'web' when an instance is exposed.
        'accessibility_scope': 'local',
        'topology_name': 'staging-a',
        'notes': 'The CORE Polari instance (research framework). In '
                 'the combined suite it shares the shared-infra '
                 'pol-* services; standalone rf-node bundles add '
                 'prf-mariadb/prf-keycloak/prf-file-store/prf-proxy. '
                 'db_backend flips to mariadb+keydb via the dbcombo '
                 'overlay (`pol db`).',
    },
    {
        'name': 'psc-a',
        'kind': 'psc',
        'service_kinds_json': json.dumps([
            'psc-backend', 'psc-frontend', 'psc-redis']),
        'replicas': 1,
        'env_tier': 'staging',
        'machine_name': 'staging-a',
        'db_backend': 'mariadb',
        'image_tag': 'staging',
        'orchestration_target': 'compose',
        'topology_name': 'staging-a',
        'notes': 'Political Scorecard instance (backend/frontend/'
                 'redis); its mariadb/keycloak/minio live on '
                 'shared-infra.',
    },
    {
        'name': 'shared-infra',
        'kind': 'infra',
        'service_kinds_json': json.dumps([
            'pol-mariadb', 'pol-keycloak', 'pol-file-store',
            'pol-proxy']),
        'replicas': 1,
        'env_tier': 'staging',
        'machine_name': 'staging-a',
        'db_backend': 'mariadb',
        'image_tag': 'staging',
        'orchestration_target': 'compose',
        'topology_name': 'staging-a',
        'notes': 'The combined suite\'s shared infrastructure: '
                 'mariadb + keycloak + minio + the TLS-terminating '
                 'nginx proxy.',
    },
    {
        'name': 'prf-b',
        'kind': 'prf',
        'service_kinds_json': json.dumps([
            'prf-backend-b', 'prf-frontend-b', 'prf-keydb-b']),
        'replicas': 1,
        'env_tier': 'staging',
        'machine_name': 'staging-a',
        'db_backend': 'sqlite',
        'image_tag': 'staging',
        'orchestration_target': 'compose',
        # Staging lives on the LAN behind nip.io — local by reality.
        # Operators flip this to 'web' when an instance is exposed.
        'accessibility_scope': 'local',
        'topology_name': 'staging-a',
        'notes': 'Twin CHILD instance — reuses A\'s images + shared '
                 'infra, own identity (POLARI_INSTANCE_ID=b), '
                 'admitted via PeerAgreement (ports 8081/8083).',
    },
    {
        'name': 'prf-dask',
        'kind': 'worker',
        'service_kinds_json': json.dumps(['prf-dask']),
        'replicas': 1,
        'env_tier': 'staging',
        'machine_name': 'staging-a',
        'db_backend': 'sqlite',
        'image_tag': 'staging',
        'orchestration_target': 'compose',
        # Staging lives on the LAN behind nip.io — local by reality.
        # Operators flip this to 'web' when an instance is exposed.
        'accessibility_scope': 'local',
        'topology_name': 'staging-a',
        'notes': 'Dask parallel-search workers (6x speedup proven; '
                 'cross-instance 5/5 split proven).',
    },
    {
        'name': 'engines',
        'kind': 'worker',
        'service_kinds_json': json.dumps(['prf-msci-engines']),
        'replicas': 1,
        'env_tier': 'staging',
        'machine_name': 'staging-a',
        'db_backend': 'sqlite',
        'image_tag': 'staging',
        'orchestration_target': 'swarm',
        'topology_name': 'staging-a',
        'notes': 'The polari-engines swarm stack (:9500) — FEM/DFT '
                 'compute workers, deployed via `pol swarm deploy '
                 'engines` (single-node swarm today).',
    },
    {
        # mtg-1: the self-hosted LiveKit media server. Placement is a
        # NAMED host for v1 (Dustin's open question defaulted
        # 2026-08-12): pol-core/staging-a; a measured bandwidth
        # dimension on the resource ledger is the recorded follow-up,
        # not built. Media = 50000-50049/udp published DIRECTLY
        # (netledger range, mtg-0); signalling TLS at prf-proxy.
        'name': 'livekit',
        'kind': 'worker',
        'service_kinds_json': json.dumps(['pol-livekit']),
        'replicas': 1,
        'env_tier': 'staging',
        'machine_name': 'staging-a',
        'db_backend': 'sqlite',
        'image_tag': 'v1.9.12',
        'orchestration_target': 'compose',
        'accessibility_scope': 'local',
        'topology_name': 'staging-a',
        'notes': 'LiveKit media server (:7880 signalling, '
                 '50000-50049/udp media), `pol compose livekit up`; '
                 'LAN-only 2026, family-sized 4-8 '
                 '(LIVEKIT_COLLABORATION_PLAN.md v2).',
    },
    {
        # ret-2: the Reticulum mesh sidecar — THE LICENCE BOUNDARY
        # (rns/lxmf pinned to the last MIT releases, imported only in
        # this container; RETICULUM_LICENCE_GATE.md). Never in the
        # default up; RX-first posture; no radio until a DeviceLink
        # row carries real udev facts (§5j).
        'name': 'reticulum',
        'kind': 'worker',
        'service_kinds_json': json.dumps(['pol-reticulum']),
        'replicas': 1,
        'env_tier': 'staging',
        'machine_name': 'staging-a',
        'db_backend': 'sqlite',
        'image_tag': 'staging',
        'orchestration_target': 'compose',
        'accessibility_scope': 'local',
        'topology_name': 'staging-a',
        'notes': 'Reticulum mesh sidecar (:4242 RNS TCP bearer, :4285 '
                 'status), `pol compose reticulum up`; the backend\'s '
                 'rns_remote ladder resolves this instance for '
                 "'reticulum.mesh' (RETICULUM_TRANSPORT_PLAN.md).",
    },
    {
        'name': 'odoo',
        'kind': 'custom',
        'service_kinds_json': json.dumps(['odoo']),
        'replicas': 1,
        'env_tier': 'staging',
        'machine_name': 'econ-core',
        'db_backend': 'postgres',
        'image_tag': 'staging',
        'orchestration_target': 'compose',
        'topology_name': 'staging-a',
        'notes': 'Odoo 18 Community ERP (od-1) — backbone of business '
                 'SIMULATIONS (odoo_sim) and REAL ops (odoo_ops); the '
                 'two never blur. Compose profile "odoo": started via '
                 '`pol odoo up`, never by suite up. SSO = od-2, '
                 'odooconnect module = od-3.',
    },
    {
        'name': 'odoo-postgres',
        'kind': 'infra',
        'service_kinds_json': json.dumps(['odoo-postgres']),
        'replicas': 1,
        'env_tier': 'staging',
        'machine_name': 'econ-core',
        'db_backend': 'postgres',
        'image_tag': 'staging',
        'orchestration_target': 'compose',
        'topology_name': 'staging-a',
        'notes': 'PostgreSQL 16 for Odoo — the suite\'s FIRST '
                 'postgres (Odoo requires it). Volumes odoo-db-data + '
                 'odoo-filestore; credential volume-baked at first '
                 'init (drift rescue: pol-odoo/README.md); movers = '
                 'od-6.',
    },
]

SEED_MODULE_ASSIGNMENTS = [
    {'name': 'scoring@prf-a', 'module_name': 'scoring',
     'instance_name': 'prf-a', 'state': 'enabled',
     'topology_name': 'staging-a',
     'notes': 'Context scoring (scr-1..16).'},
    {'name': 'aquaponics@prf-a', 'module_name': 'aquaponics',
     'instance_name': 'prf-a', 'state': 'enabled',
     'topology_name': 'staging-a',
     'notes': 'Self-watering pot sim (aqp-1..6).'},
    {'name': 'simulations@prf-a', 'module_name': 'simulations',
     'instance_name': 'prf-a', 'state': 'enabled',
     'topology_name': 'staging-a',
     'notes': 'Multi-scale simulation framework.'},
    {'name': 'materialsScience@prf-a',
     'module_name': 'materialsScience',
     'instance_name': 'prf-a', 'state': 'enabled',
     'topology_name': 'staging-a',
     'notes': 'Materials basis + engine-model layer (msci-0..24).'},
    {'name': 'materialsScience.multiscale@prf-a',
     'module_name': 'materialsScience.multiscale',
     'instance_name': 'prf-a', 'state': 'enabled',
     'topology_name': 'staging-a',
     'notes': 'Multi-scale models (wax-multiscale) — the consumer '
              'of fem + dft in the seed demo.'},
    {'name': 'materialsScience.fem@engines',
     'module_name': 'materialsScience.fem',
     'instance_name': 'engines', 'state': 'enabled',
     'topology_name': 'staging-a',
     'notes': 'FEM engine capability on the engines worker.'},
    {'name': 'materialsScience.dft@engines',
     'module_name': 'materialsScience.dft',
     'instance_name': 'engines', 'state': 'enabled',
     'topology_name': 'staging-a',
     'notes': 'DFT engine capability on the engines worker.'},
    {'name': 'scorecard@psc-a', 'module_name': 'scorecard',
     'instance_name': 'psc-a', 'state': 'enabled',
     'topology_name': 'staging-a',
     'notes': 'Political Scorecard app (scr-7 seam consumes '
              'prf\'s scoring API).'},
    {'name': 'collab@prf-a', 'module_name': 'collab',
     'instance_name': 'prf-a', 'state': 'enabled',
     'topology_name': 'staging-a',
     'notes': 'Collaboration sessions (mtg-2): session rows + '
              'KC-verified LiveKit token minting.'},
    {'name': 'collab.media@livekit',
     'module_name': 'collab.media',
     'instance_name': 'livekit', 'state': 'enabled',
     'topology_name': 'staging-a',
     'notes': 'Media-server capability on the livekit worker '
              '(mtg-1) — what the LIVEKIT_URL-unset ladder '
              'resolves.'},
    {'name': 'reticulum@prf-a', 'module_name': 'reticulum',
     'instance_name': 'prf-a', 'state': 'enabled',
     'topology_name': 'staging-a',
     'notes': 'Reticulum mesh rows + capability/.arch/inbound seam '
              '(ret-1).'},
    {'name': 'reticulum.mesh@reticulum',
     'module_name': 'reticulum.mesh',
     'instance_name': 'reticulum', 'state': 'enabled',
     'topology_name': 'staging-a',
     'notes': 'Mesh-sidecar capability on the reticulum worker '
              '(ret-2) — what the RETICULUM_URL-unset ladder '
              'resolves.'},
]

SEED_MODULE_DEPENDENCY_EDGES = [
    {'name': 'materialsScience.multiscale@prf-a->materialsScience.fem',
     'module_name': 'materialsScience.multiscale',
     'consumer_instance_name': 'prf-a',
     'depends_on_module': 'materialsScience.fem',
     'provider_instance_name': 'engines',
     'status': 'resolved',
     'topology_name': 'staging-a',
     'notes': 'Multiscale FEM delegation — MSCI_ENGINES_URL seam '
              'today, registry-resolved routing in top-7.'},
    {'name': 'materialsScience.multiscale@prf-a->materialsScience.dft',
     'module_name': 'materialsScience.multiscale',
     'consumer_instance_name': 'prf-a',
     'depends_on_module': 'materialsScience.dft',
     'provider_instance_name': 'engines',
     'status': 'resolved',
     'topology_name': 'staging-a',
     'notes': 'Multiscale DFT delegation — same seam as fem.'},
    {'name': 'collab@prf-a->collab.media',
     'module_name': 'collab',
     'consumer_instance_name': 'prf-a',
     'depends_on_module': 'collab.media',
     'provider_instance_name': 'livekit',
     'status': 'resolved',
     'topology_name': 'staging-a',
     'notes': 'Meeting media delegation (mtg-2) — LIVEKIT_URL seam, '
              'registry-resolved like the msci/cad edges; media '
              'itself is direct UDP, only signalling/tokens ride '
              'this.'},
    {'name': 'reticulum@prf-a->reticulum.mesh',
     'module_name': 'reticulum',
     'consumer_instance_name': 'prf-a',
     'depends_on_module': 'reticulum.mesh',
     'provider_instance_name': 'reticulum',
     'status': 'resolved',
     'topology_name': 'staging-a',
     'notes': 'Mesh delegation (ret-2) — RETICULUM_URL seam, '
              'registry-resolved like the livekit edge; the sidecar '
              'holds the RNS stack, the backend holds the rows.'},
]

SEED_SERVICE_CONNECTIONS = [
    {'name': 'prf-frontend->prf-backend:prf-runtime-config',
     'interconnect_key': 'prf-runtime-config',
     'from_kind': 'prf-frontend', 'to_kind': 'prf-backend',
     'from_instance_name': 'prf-a', 'to_instance_name': 'prf-a',
     'artifact': '.generated/prf-runtime-config*.json',
     'topology_name': 'staging-a',
     'notes': 'frontend -> its backend + keycloak issuer.'},
    {'name': 'psc-frontend->psc-backend:psc-runtime-config',
     'interconnect_key': 'psc-runtime-config',
     'from_kind': 'psc-frontend', 'to_kind': 'psc-backend',
     'from_instance_name': 'psc-a', 'to_instance_name': 'psc-a',
     'artifact': '.generated/psc-runtime-config.json',
     'topology_name': 'staging-a',
     'notes': 'psc frontend -> psc backend + keycloak realm.'},
    {'name': 'prf-frontend-b->prf-backend-b:twin-runtime-config',
     'interconnect_key': 'twin-runtime-config',
     'from_kind': 'prf-frontend-b', 'to_kind': 'prf-backend-b',
     'from_instance_name': 'prf-b', 'to_instance_name': 'prf-b',
     'artifact': 'polari-rf-node/.generated/prf-b-runtime-config.json',
     'topology_name': 'staging-a',
     'notes': 'instance-B frontend -> instance-B backend '
              '(ports 8081/8083).'},
    {'name': 'prf-backend-b->prf-backend:peer-token',
     'interconnect_key': 'peer-token',
     'from_kind': 'prf-backend-b', 'to_kind': 'prf-backend',
     'from_instance_name': 'prf-b', 'to_instance_name': 'prf-a',
     'artifact': 'polari-rf-node/.generated/.polari-peer-token',
     'topology_name': 'staging-a',
     'notes': 'instance<->instance peer trust; admission flow = '
              'PeerAgreement (polariPeers/).'},
    {'name': 'prf-backend->prf-keycloak:keycloak-client-secrets',
     'interconnect_key': 'keycloak-client-secrets',
     'from_kind': 'prf-backend', 'to_kind': 'prf-keycloak',
     'from_instance_name': 'prf-a', 'to_instance_name': 'prf-a',
     'artifact': 'polari-rf-node/prf-keycloak/prf-keycloak-admin.env',
     'topology_name': 'staging-a',
     'notes': 'backend service-account -> keycloak admin API.'},
    {'name': 'psc-backend->pol-keycloak:keycloak-client-secrets',
     'interconnect_key': 'keycloak-client-secrets',
     'from_kind': 'psc-backend', 'to_kind': 'pol-keycloak',
     'from_instance_name': 'psc-a', 'to_instance_name': 'shared-infra',
     'artifact': 'pol-keycloak/keycloak-admin.env',
     'topology_name': 'staging-a',
     'notes': 'psc service-account -> keycloak admin API.'},
    {'name': 'prf-backend->prf-mariadb:db-credentials',
     'interconnect_key': 'db-credentials',
     'from_kind': 'prf-backend', 'to_kind': 'prf-mariadb',
     'from_instance_name': 'prf-a', 'to_instance_name': 'prf-a',
     'artifact': 'polari-rf-node/prf-mariadb/mariadb.env',
     'topology_name': 'staging-a',
     'notes': 'DB users, volume-baked at first init (dbcombo path).'},
    {'name': 'psc-backend->pol-mariadb:db-credentials',
     'interconnect_key': 'db-credentials',
     'from_kind': 'psc-backend', 'to_kind': 'pol-mariadb',
     'from_instance_name': 'psc-a', 'to_instance_name': 'shared-infra',
     'artifact': 'pol-mariadb/mariadb.env',
     'topology_name': 'staging-a',
     'notes': 'psc-scorecard-server DB user, volume-baked.'},
    {'name': 'prf-backend->prf-file-store:minio-credentials',
     'interconnect_key': 'minio-credentials',
     'from_kind': 'prf-backend', 'to_kind': 'prf-file-store',
     'from_instance_name': 'prf-a', 'to_instance_name': 'prf-a',
     'artifact': 'rf-node knobs POLARI_MINIO_ROOT_USER/_PASS',
     'topology_name': 'staging-a',
     'notes': 'object-storage client -> minio root.'},
    {'name': 'prf-proxy->prf-frontend:nginx-proxy-config',
     'interconnect_key': 'nginx-proxy-config',
     'from_kind': 'prf-proxy', 'to_kind': 'prf-frontend',
     'from_instance_name': 'prf-a', 'to_instance_name': 'prf-a',
     'artifact': '.generated/nginx.staging.conf (rf-node)',
     'topology_name': 'staging-a',
     'notes': 'subdomain routing + TLS termination (pol proxy '
              'render|check|promote).'},
    {'name': 'pol-proxy->psc-frontend:nginx-proxy-config',
     'interconnect_key': 'nginx-proxy-config',
     'from_kind': 'pol-proxy', 'to_kind': 'psc-frontend',
     'from_instance_name': 'shared-infra', 'to_instance_name': 'psc-a',
     'artifact': '.generated/nginx.staging.conf (suite)',
     'topology_name': 'staging-a',
     'notes': 'suite-side subdomain routing + TLS termination.'},
    {'name': 'psc-backend->prf-backend:scorecard-api-seam',
     'interconnect_key': 'scorecard-api-seam',
     'from_kind': 'psc-backend', 'to_kind': 'prf-backend',
     'from_instance_name': 'psc-a', 'to_instance_name': 'prf-a',
     'artifact': '(scr-7, designed not built)',
     'topology_name': 'staging-a',
     'notes': 'psc consumes prf\'s /api/scoring instead of its own '
              'mocks — designed, not built (scr-7).'},
    {'name': 'odoo->odoo-postgres:db-credentials',
     'interconnect_key': 'db-credentials',
     'from_kind': 'odoo', 'to_kind': 'odoo-postgres',
     'from_instance_name': 'odoo', 'to_instance_name': 'odoo-postgres',
     'artifact': 'pol-odoo-postgres/odoo-postgres.env',
     'topology_name': 'staging-a',
     'notes': 'One shared credential (mirrored into '
              'pol-odoo/odoo.env), volume-baked at first init — '
              'drift rescue in pol-odoo/README.md.'},
    {'name': 'pol-proxy->odoo:nginx-proxy-config',
     'interconnect_key': 'nginx-proxy-config',
     'from_kind': 'pol-proxy', 'to_kind': 'odoo',
     'from_instance_name': 'shared-infra', 'to_instance_name': 'odoo',
     'artifact': '.generated/nginx.staging.conf (suite)',
     'topology_name': 'staging-a',
     'notes': 'odoo.<domain> routes; VARIABLE proxy_pass so the '
              'proxy boots while the odoo profile is down; '
              '/websocket -> :8072.'},
    {'name': 'odoo->pol-keycloak:keycloak-client-secrets',
     'interconnect_key': 'keycloak-client-secrets',
     'from_kind': 'odoo', 'to_kind': 'pol-keycloak',
     'from_instance_name': 'odoo', 'to_instance_name': 'shared-infra',
     'artifact': 'KC client "odoo" (realm Polari) -> auth.oauth.provider '
                 'rows, written by pol odoo sso-setup (never a file)',
     'topology_name': 'staging-a',
     'notes': 'od-2 SSO: OIDC code flow via OCA auth_oidc; humans '
              'log in through auth.<domain>; role->group mapping is '
              'MANUAL in v1.'},
    {'name': 'prf-backend->odoo:erp-api-seam',
     'interconnect_key': 'erp-api-seam',
     'from_kind': 'prf-backend', 'to_kind': 'odoo',
     'from_instance_name': 'prf-a', 'to_instance_name': 'odoo',
     'artifact': '(od-3, designed not built) odooconnect JSON-RPC',
     'topology_name': 'staging-a',
     'notes': 'odooconnect module: pull free, push = knob + typed '
              'confirm; sim/ops handles never blur — designed, not '
              'built (od-3).'},
]
