"""
@cross-cutting
@module topology.topology_modules
@tags @xc:bindings

Module placement (top-1): which Polari module runs on which instance
(ModuleAssignment), and which module DEPENDS on which — resolved to a
concrete provider instance (ModuleDependencyEdge).

This lifts moduleService/module_dependency_tracker's inside-one-
instance edges to the CROSS-INSTANCE level: multiscale@prf-a depends
on fem + dft, provided by the engines instance. The Topology tab's
drag-and-drop (top-6) rewrites ModuleAssignment rows and re-resolves
edges; provider routing (top-7) reads resolved edges instead of
hardcoded MSCI_ENGINES_URL.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - topology.topology_analysis (resolve_edges / validation)
  - materialsScience.engines.remote (top-7 provider registry)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class ModuleAssignment(treeObject):
    """One module placed on one instance.

    This is the module enable/disable knob `pol modules` refuses
    honestly about today (modules.sh:63) — assignments are the rows
    that refusal points at once top-2 wires the CLI here.
    """

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<module>@<instance>'
        # ('materialsScience.fem@engines').
        name: str = '',
        # Module id — a top-level module ('scoring', 'aquaponics') or
        # a dotted capability inside one ('materialsScience.fem').
        module_name: str = '',
        # InstanceDefinition.name carrying the module.
        instance_name: str = '',
        # ASSIGNMENT_STATES entry.
        state: str = 'enabled',
        # TopologyDefinition.name this assignment belongs to.
        topology_name: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.module_name = module_name
        self.instance_name = instance_name
        self.state = state
        self.topology_name = topology_name
        self.notes = notes


class ModuleDependencyEdge(treeObject):
    """moduleA@instanceX DEPENDS-ON moduleB, resolved to a provider.

    provider_instance_name is COMPUTED by resolve_edges() from the
    enabled ModuleAssignments (deterministic: alphabetical first among
    candidates, keeping a still-valid existing provider). status is
    'unresolved' when no enabled assignment of depends_on_module
    exists anywhere — the validator turns that into an evidence-
    bearing finding naming the `pol allocate` knob.
    """

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally
        # '<module>@<instance>-><depends_on_module>'.
        name: str = '',
        # The consuming module + its instance.
        module_name: str = '',
        consumer_instance_name: str = '',
        # The module depended upon.
        depends_on_module: str = '',
        # InstanceDefinition.name providing it; '' = unresolved.
        provider_instance_name: str = '',
        # EDGE_STATUSES entry.
        status: str = 'unresolved',
        # tt-1 (designate_transients, deterministic like the provider
        # pick above): a dependency shared by N>1 consumers keeps ONE
        # primary edge; the other N-1 are transient copies (dashed in
        # the revamped renderer, duplicates intentional).
        is_primary: bool = False,
        is_transient: bool = False,
        # JSON evidence for the current status (candidate providers,
        # unreachability reports from top-7 routing).
        evidence_json: str = '[]',
        # TopologyDefinition.name this edge belongs to.
        topology_name: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.module_name = module_name
        self.consumer_instance_name = consumer_instance_name
        self.depends_on_module = depends_on_module
        self.provider_instance_name = provider_instance_name
        self.status = status
        self.is_primary = is_primary
        self.is_transient = is_transient
        self.evidence_json = evidence_json
        self.topology_name = topology_name
        self.notes = notes


class EngineProviderBinding(treeObject):
    """sep-4: an engine URL BOUND from an isle app deploy (the
    islemesh binder writes these — the row form of the *_ENGINES_URL
    env knob). The remotes' resolution ladder reads it between the
    env knob and the topology resolve, so an isle-deployed engine
    wires consumers without a redeploy."""

    @treeObjectInit
    def __init__(
        self,
        # Engine kind ('msci', 'cad', 'business-ops', ...).
        name: str = '',
        url: str = '',
        # The isle app the binder saw ('' = hand-written row).
        bound_from: str = '',
        bound_at: str = '',
        is_prior: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.url = url
        self.bound_from = bound_from
        self.bound_at = bound_at
        self.is_prior = is_prior
        self.notes = notes


class EngineUsageWindow(treeObject):
    """sep-4 (decision 9): metering at the *_remote seams — call
    counts / bytes / latency per HOUR window, rows not logs. One row
    per engine x window; the engine data page renders these (and
    says 'not tracked yet' where none exist). Observed data — never
    seeded."""

    @treeObjectInit
    def __init__(
        self,
        # '<engine>:<window_start>' (unique key).
        name: str = '',
        engine: str = '',
        # UTC hour bucket, ISO ('2026-08-15T14:00:00Z').
        window_start: str = '',
        calls: int = 0,
        errors: int = 0,
        bytes_out: int = 0,
        bytes_in: int = 0,
        latency_ms_sum: int = 0,
        latency_ms_max: int = 0,
        is_prior: bool = False,
        manager=None,
    ):
        self.name = name
        self.engine = engine
        self.window_start = window_start
        self.calls = calls
        self.errors = errors
        self.bytes_out = bytes_out
        self.bytes_in = bytes_in
        self.latency_ms_sum = latency_ms_sum
        self.latency_ms_max = latency_ms_max
        self.is_prior = is_prior
