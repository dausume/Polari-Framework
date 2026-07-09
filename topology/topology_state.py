"""
@cross-cutting
@module topology.topology_state
@tags @xc:bindings

The whole-graph classes (top-1): TopologyDefinition (DESIRED state —
the named graph every instance/assignment/edge/connection row belongs
to) and TopologyObservation (OBSERVED state — what a node actually
runs, reported by `pol topology report`, never guessed).

Drift = desired vs latest observation, surfaced with a suggested
`pol` command per row and NEVER auto-corrected
(knobs-and-suggestions).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - topology.topology_analysis (drift_report) / topology_api
  - polari-cli scripts/topology.sh (top-2 report/diff)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class TopologyDefinition(treeObject):
    """One named desired-state graph."""

    @treeObjectInit
    def __init__(
        self,
        # Unique topology key ('staging-a').
        name: str = '',
        description: str = '',
        # ORCHESTRATION_TARGETS entry instances default to when they
        # don't pick their own.
        default_target: str = 'compose',
        # DEFINITION_STATUSES entry.
        status: str = 'draft',
        # Exactly one topology should be active per core instance —
        # the one the tab shows and the CLI syncs by default.
        is_active: bool = False,
        # Latest validation findings (JSON list of finding dicts),
        # stamped by POST /api/topology/validate.
        validation_findings_json: str = '[]',
        # ISO timestamp of the last validation run ('' = never).
        validated_at: str = '',
        # Portable-package schema version this row round-trips as.
        schema_version: str = '1',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.default_target = default_target
        self.status = status
        self.is_active = is_active
        self.validation_findings_json = validation_findings_json
        self.validated_at = validated_at
        self.schema_version = schema_version
        self.notes = notes


class TopologyObservation(treeObject):
    """What one machine ACTUALLY runs at one moment.

    Posted by `pol topology report` (top-2). NOT seeded — observed
    state is reported, never guessed. Rows accumulate; drift reads
    the latest per machine (retention is the reporter's knob).
    """

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<node>@<observed_at>'.
        name: str = '',
        # TopologyDefinition.name the report was taken against.
        topology_name: str = '',
        # PolariNodeMachine.name that was observed.
        node_name: str = '',
        # ISO timestamp of the observation.
        observed_at: str = '',
        # JSON list of swarm stacks on the node ([{name, services}]).
        stacks_json: str = '[]',
        # JSON list of running services/containers
        # ([{name, state, image}] — compose containers AND swarm
        # tasks, normalized by the reporter).
        services_json: str = '[]',
        # JSON module inventory of backend instances on the node
        # ([{instance, modules: [...]}]), when reachable.
        modules_json: str = '[]',
        # What produced the row ('pol topology report').
        source: str = 'pol topology report',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.topology_name = topology_name
        self.node_name = node_name
        self.observed_at = observed_at
        self.stacks_json = stacks_json
        self.services_json = services_json
        self.modules_json = modules_json
        self.source = source
        self.notes = notes
