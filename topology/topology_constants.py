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

#: The `pol db` vocabulary — per-instance DB backend choice.
DB_BACKENDS = ('sqlite', 'mariadb', 'mariadb+keydb')

#: Swarm membership of a machine.
SWARM_ROLES = ('manager', 'worker', 'none')

#: Environment tiers the render pipeline knows.
ENV_TIERS = ('dev', 'staging', 'prod', 'test')

#: Instance families. 'prf' = Polari research framework instance,
#: 'psc' = political scorecard instance, 'worker' = headless compute
#: (dask / msci-engines), 'infra' = shared infra grouping, 'custom'
#: = anything else.
INSTANCE_KINDS = ('prf', 'psc', 'worker', 'infra', 'custom')

#: ModuleAssignment lifecycle. 'planned' = desired but not applied.
ASSIGNMENT_STATES = ('enabled', 'planned', 'disabled')

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

#: The 19 registry service kinds (pol-build/registry/services.yml:93).
KNOWN_SERVICE_KINDS = (
    'pol-mariadb', 'pol-keycloak', 'pol-file-store', 'pol-proxy',
    'psc-redis', 'psc-backend', 'psc-frontend',
    'prf-backend', 'prf-frontend', 'prf-mariadb', 'prf-keycloak',
    'prf-file-store', 'prf-proxy',
    'prf-backend-b', 'prf-frontend-b', 'prf-keydb-b',
    'prf-dask', 'prf-msci-engines', 'prf-test-harness',
)
