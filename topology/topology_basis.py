"""
@cross-cutting
@module topology.topology_basis
@tags @xc:bindings

Topology basis classes (top-1): the machines work runs on, the
orchestration targets that can run it, and the instance definitions
that group services into deployable Polari instances.

Topology is DATA in the object tree (object-coherence): desired state
lives as these CRUDE-exposed rows on the CORE instance; files
(registry/services.yml, manifests/*, nodes.yml) are the INTERCHANGE
format the CLI renders FROM these rows. Observed state is reported
(TopologyObservation), never guessed; drift is surfaced, never
auto-corrected (knobs-and-suggestions).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - topology.topology_analysis / topology.topology_api
  - polari-cli scripts/topology.sh (top-2)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PolariNodeMachine(treeObject):
    """One physical/VM host a topology can place work on.

    Seeded from pol-build/manifests/nodes.yml (+ the local core host,
    which nodes.yml omits because ssh-deploy never targets itself).
    """

    @treeObjectInit
    def __init__(
        self,
        # Unique machine key ('staging-a', 'isle-core', 'lightweight').
        name: str = '',
        # ~/.ssh/config alias for key-auth deploys; '' = the local
        # host itself (no ssh hop).
        ssh_alias: str = '',
        # CPU arch ('x86_64', 'aarch64', '') — preflight-reported.
        arch: str = '',
        # Memory in GB (0 = unknown until preflight/observe reports).
        # Kept for back-compat; res-1 mirrors total_ram_mb into it.
        mem_gb: float = 0.0,
        # --- res-1: observed device resources (0/'' = not yet
        # observed — honest absence, never fabricated) ---
        logical_cpus: int = 0,
        physical_cpus: int = 0,
        total_ram_mb: float = 0.0,
        available_ram_mb: float = 0.0,
        total_disk_mb: float = 0.0,
        free_disk_mb: float = 0.0,
        # cgroup memory ceiling seen by the reporting process
        # (0 = none/unlimited) — a containerized backend reports its
        # container budget, which is what admission must respect.
        cgroup_ram_limit_mb: float = 0.0,
        # Latest utilization sample: {"cpuPct", "ramPct", "ts"}.
        load_snapshot_json: str = '{}',
        # How the resource fields were obtained: 'observed-local'
        # (this backend's own isoSys), 'observed-remote' (pulled from
        # the node's system_info_url), 'observed-push' (the node
        # reported itself, pol-CLI style), 'manual', or 'unknown'.
        resource_source: str = 'unknown',
        resource_observed_at: str = '',
        # KNOB: where this node's /system-info answers, for remote
        # pull ('http://192.168.0.24:9501' or a full .../system-info
        # URL). '' = no remote pull configured — swarm's routing mesh
        # makes ip:port ambiguous, so a human names the address.
        system_info_url: str = '',
        # JSON list of deploy roles ('engines', 'remote-worker',
        # 'node', 'core') — mirrors nodes.yml roles.
        roles_json: str = '[]',
        # SWARM_ROLES entry: docker-swarm membership of this machine.
        swarm_role: str = 'none',
        # Where the public repo lives on the target.
        repo_dir: str = '~/polari-suite',
        # Where this row came from ('nodes.yml', 'manual', 'observed').
        source: str = 'manual',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.ssh_alias = ssh_alias
        self.arch = arch
        self.mem_gb = mem_gb
        self.logical_cpus = logical_cpus
        self.physical_cpus = physical_cpus
        self.total_ram_mb = total_ram_mb
        self.available_ram_mb = available_ram_mb
        self.total_disk_mb = total_disk_mb
        self.free_disk_mb = free_disk_mb
        self.cgroup_ram_limit_mb = cgroup_ram_limit_mb
        self.load_snapshot_json = load_snapshot_json
        self.resource_source = resource_source
        self.resource_observed_at = resource_observed_at
        self.system_info_url = system_info_url
        self.roles_json = roles_json
        self.swarm_role = swarm_role
        self.repo_dir = repo_dir
        self.source = source
        self.notes = notes


class OrchestrationTarget(treeObject):
    """One way of running a service group: compose | swarm | isle.

    A row per target keeps the vocabulary configurable AT the object
    (object-coherence) — the Topology tab binds its target picker to
    these rows, and 'isle' can flip available=True the day isle-mesh
    orchestration lands, with no code change.
    """

    @treeObjectInit
    def __init__(
        self,
        # ORCHESTRATION_TARGETS entry ('compose', 'swarm', 'isle').
        name: str = '',
        display_name: str = '',
        # False = named but not yet usable — validation refuses
        # instances that pick an unavailable target (honest absence).
        available: bool = True,
        description: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.available = available
        self.description = description
        self.notes = notes


class InstanceDefinition(treeObject):
    """One deployable Polari instance: a named group of registry
    service kinds with a DB choice, an env tier, and a host binding.

    prf-a (the core), psc-a (scorecard), prf-b (twin child), dask and
    engines workers are the seeded reality; the Topology tab's count
    steppers create more rows of these shapes.
    """

    @treeObjectInit
    def __init__(
        self,
        # Unique instance key ('prf-a', 'psc-a', 'engines').
        name: str = '',
        # INSTANCE_KINDS entry.
        kind: str = 'custom',
        # JSON list of registry service kinds composing the instance
        # (KNOWN_SERVICE_KINDS entries).
        service_kinds_json: str = '[]',
        # Swarm replica count (compose instances are always 1).
        replicas: int = 1,
        # ENV_TIERS entry.
        env_tier: str = 'staging',
        # PolariNodeMachine.name this instance is pinned to; '' =
        # unpinned (swarm scheduler places it).
        machine_name: str = '',
        # Raw swarm placement constraint emitted into the stack
        # ('node.hostname == lightweight'); derived from machine_name
        # when empty.
        placement_constraint: str = '',
        # DB_BACKENDS entry — the `pol db` choice for this instance.
        # The RELATIONAL tier: the only storage an instance is
        # REQUIRED to declare, because everything it owns lands there.
        db_backend: str = 'sqlite',
        # CACHE_BACKENDS entry; '' = not assigned, which is legal.
        # Left empty when db_backend already implies one (the
        # 'mariadb+keydb' combo) — see DB_BACKEND_IMPLIED_CACHE.
        cache_backend: str = '',
        # BLOB_BACKENDS entry; '' = not assigned, which is legal.
        blob_backend: str = '',
        # Image tag the instance runs (':staging' family today).
        image_tag: str = 'staging',
        # ORCHESTRATION_TARGETS entry.
        orchestration_target: str = 'compose',
        # TopologyDefinition.name this instance belongs to.
        topology_name: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.kind = kind
        self.service_kinds_json = service_kinds_json
        self.replicas = replicas
        self.env_tier = env_tier
        self.machine_name = machine_name
        self.placement_constraint = placement_constraint
        self.db_backend = db_backend
        self.image_tag = image_tag
        self.orchestration_target = orchestration_target
        self.topology_name = topology_name
        self.notes = notes
