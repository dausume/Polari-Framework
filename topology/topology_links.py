"""
@cross-cutting
@module topology.topology_links
@tags @xc:bindings

ServiceConnection (top-1): one typed wire between two service
endpoints, typed by the registry `interconnects:` vocabulary
(INTERCONNECT_KEYS). Clicking a connection in the Topology tab shows
the generated artifact that wires it — full accountability of "what
config makes this link". Secrets NEVER live here: the artifact field
is a PATH/PATTERN, the credential substrate generates the content on
the target.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - topology.topology_analysis (validation) / topology_api
"""

from objectTreeDecorators import treeObject, treeObjectInit


class ServiceConnection(treeObject):
    """One instance-wiring artifact between two service endpoints."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally
        # '<from_kind>-><to_kind>:<interconnect>@<topology scope>'.
        name: str = '',
        # INTERCONNECT_KEYS entry — the wire's TYPE.
        interconnect_key: str = '',
        # Registry service kinds at each end.
        from_kind: str = '',
        to_kind: str = '',
        # InstanceDefinition.name at each end ('' = same-instance
        # internal wiring).
        from_instance_name: str = '',
        to_instance_name: str = '',
        # The generated artifact path/pattern that carries the wiring
        # (mirrors the registry interconnect's `artifact:` field).
        artifact: str = '',
        # TopologyDefinition.name this connection belongs to.
        topology_name: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.interconnect_key = interconnect_key
        self.from_kind = from_kind
        self.to_kind = to_kind
        self.from_instance_name = from_instance_name
        self.to_instance_name = to_instance_name
        self.artifact = artifact
        self.topology_name = topology_name
        self.notes = notes
