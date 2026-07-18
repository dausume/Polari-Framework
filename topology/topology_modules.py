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
