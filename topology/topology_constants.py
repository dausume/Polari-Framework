"""
@cross-cutting
@module topology.topology_constants

Shared vocabulary for the topology module (top-1). Pure constants —
NO framework imports, so selftests and analysis functions can run
stdlib-only (outside the prf-backend container).

The interconnect keys and service kinds MIRROR
pol-build/registry/services.yml (the CLI-side static vocabulary).
The registry file is not present inside the backend container, so the
vocabulary is embedded here; `pol topology push` (top-2) refreshes
rows FROM the registry and will surface any drift between the two.

@consumers
  - topology.* (basis classes, analysis, seeds, API)
  - polari-cli scripts/topology.sh (top-2; via /api/topology/*)
"""

#: Portable-package schema version (top-3 export format).
SCHEMA_VERSION = '1'

#: How a group of services gets orchestrated. 'isle' is the future
#: isle-mesh target — present in the vocabulary, seeded unavailable.
ORCHESTRATION_TARGETS = ('compose', 'swarm', 'isle')

#: The `pol db` vocabulary — per-instance RELATIONAL backend choice.
#: This is the one storage tier an instance MUST declare; everything
#: an instance owns lands here.
DB_BACKENDS = ('sqlite', 'mariadb', 'mariadb+keydb', 'postgres')

#: Relational backends that ALSO bind a cache, as one combined choice.
#: `mariadb+keydb` predates the separate cache tier and already means
#: "mariadb relational, keydb cache" — so the cache is IMPLIED and
#: must not be double-declared. Mapping it here keeps one source of
#: truth instead of letting cache_backend silently contradict it.
DB_BACKEND_IMPLIED_CACHE = {'mariadb+keydb': 'keydb'}

#: Cache tier. The technology is NOT a choice — the cache is always
#: KeyDB (Dustin, 2026-08-04; the bitnami/redis base is dead and must
#: never be reintroduced). So the only knob is WHETHER an instance is
#: bound to one: '' = NOT ASSIGNED, which is legal, since unlike
#: relational a cache is optional.
CACHE_BACKENDS = ('', 'keydb')

#: Blob / object store. Also not a choice of technology — always
#: MinIO, the store already backing map tiles (the 'polari-tiles'
#: bucket) and arbitrary object storage. '' = NOT ASSIGNED.
BLOB_BACKENDS = ('', 'minio')

#: Storage that is local to its instance by construction and can
#: therefore NEVER be shared or repointed. sqlite means the file THAT
#: instance creates. Naming it once keeps the ownership page and
#: validation agreeing about it.
LOCAL_BY_CONSTRUCTION = ('sqlite',)

#: App-shell reachability (appstore reads, topology owns). 'mesh' is
#: the future isle-mesh path — present in the vocabulary, refused by
#: validation until it lands (the OrchestrationTarget 'isle' idiom).
ACCESSIBILITY_SCOPES = ('local', 'web', 'mesh')

#: What kind of network a local-only instance lives on. The shell
#: quotes this in its advisory ("you need to be on the <name> home
#: network"). '' is legal when accessibility_scope is 'web' — a web
#: instance has no home network.
NETWORK_KINDS = ('', 'home', 'business', 'other')

#: Swarm membership of a machine.
SWARM_ROLES = ('manager', 'worker', 'none')

#: Environment tiers the render pipeline knows.
ENV_TIERS = ('dev', 'staging', 'prod', 'test')

#: Instance families. 'prf' = Polari research framework instance,
#: 'psc' = political scorecard instance, 'worker' = headless compute
#: (dask / msci-engines), 'infra' = shared infra grouping, 'custom'
#: = anything else.
INSTANCE_KINDS = ('prf', 'psc', 'worker', 'infra', 'custom')

#: tt-14 placement coherence (Dustin 2026-07-18): only POLARI
#: instances can receive modules. Workers (prf-dask) and engines
#: (dft/fem hosts) ARE Polari instances — a Polari wrapped the
#: engine from the beginning — so they can carry other modules too.
#: 'psc' (SpringBoot/Angular public server) and 'infra' (mariadb/
#: keycloak/minio/proxy containers) are NON-ADAPTIVE apps that
#: integrate with Polari at fixed points — never module targets.
POLARI_RECEPTIVE_KINDS = ('prf', 'worker', 'engines', 'prf-backend')
INTEGRATED_APP_KINDS = ('psc', 'psc-backend')
INFRA_KINDS = ('infra', 'shared-infra')
#: Auth-oriented containers (Keycloak etc.) are their own category:
#: separate color in the graph and NEVER a module target.
AUTH_KINDS = ('auth', 'keycloak')

#: Engine-capability modules can ONLY live on engine/worker
#: instances (the Polari-wrapped engines) — matching PROVIDER_PORTS'
#: routing world.
ENGINE_CAPABILITY_MODULES = ('materialsScience.fem',
                             'materialsScience.dft')
ENGINE_HOST_KINDS = ('worker', 'engines')

#: ModuleAssignment lifecycle. 'planned' = desired but not applied.
#: 'transient' (tt-13) = the module MOVED away — this row is the
#: dashed ghost at its former location: visible in the graph,
#: excluded from resolution/tests, and the one-click way back.
ASSIGNMENT_STATES = ('enabled', 'planned', 'disabled', 'transient')

#: ModuleDependencyEdge resolution states. 'degraded' = provider
#: assigned but observed unreachable (top-7 wires this in).
EDGE_STATUSES = ('resolved', 'unresolved', 'degraded')

#: TopologyDefinition lifecycle.
DEFINITION_STATUSES = ('draft', 'validated', 'applied')

#: Typed instance-wiring artifacts — mirror of registry
#: `interconnects:` keys (pol-build/registry/services.yml:38).
INTERCONNECT_KEYS = (
    'prf-runtime-config',
    'psc-runtime-config',
    'twin-runtime-config',
    'peer-token',
    'keycloak-client-secrets',
    'db-credentials',
    'minio-credentials',
    'nginx-proxy-config',
    'scorecard-api-seam',
    'erp-api-seam',
)

#: Compose/swarm service LABELS -> registry kinds, for observation
#: matching (mirror of registry.sh's ALIASES + DASK_MSCI mapping —
#: compose service names differ per bundle file).
SERVICE_LABEL_ALIASES = {
    'backend': 'prf-backend',
    'frontend': 'prf-frontend',
    'backend-b': 'prf-backend-b',
    'frontend-b': 'prf-frontend-b',
    'keydb-b': 'prf-keydb-b',
    'dask-scheduler': 'prf-dask',
    'dask-worker-a': 'prf-dask',
    'dask-worker-b': 'prf-dask',
    'dask-worker': 'prf-dask',
    'msci-engines': 'prf-msci-engines',
    'remote-worker': 'prf-msci-engines',
}

#: The 21 registry service kinds (pol-build/registry/services.yml:93).
KNOWN_SERVICE_KINDS = (
    'pol-mariadb', 'pol-keycloak', 'pol-file-store', 'pol-proxy',
    'psc-redis', 'psc-backend', 'psc-frontend',
    'prf-backend', 'prf-frontend', 'prf-mariadb', 'prf-keycloak',
    'prf-file-store', 'prf-proxy',
    'prf-backend-b', 'prf-frontend-b', 'prf-keydb-b',
    'prf-dask', 'prf-msci-engines', 'prf-test-harness',
    'odoo', 'odoo-postgres',
)
