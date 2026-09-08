"""
@module islemesh.objects.islemesh.IsleDevice

Row class IsleDevice of the islemesh module — one class per file (design §7), split
from islemesh_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IsleDevice(treeObject):
    """One device on (or known to) the isle — the mesh map's nodes.
    Mirrors isle's device inventory; `machine_name` links the row to
    the PolariNodeMachine when the device is also a polari machine."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: the device's isle hostname ('isle-core').
        name: str = '',
        # The device's .isle name ('' until registered on the mesh).
        isle_name: str = '',
        # PolariNodeMachine.name when this device is a polari machine
        # ('pol-core'/'isle-core'/'econ-core'); '' for other devices.
        machine_name: str = '',
        # AGENT_MODES entry; '' = no agent seen.
        agent_mode: str = '',
        agent_present: bool = False,
        # Whether the OpenWRT router (VM or box) runs HERE.
        hosts_router: bool = False,
        router_running: bool = False,
        # CONNECTIVITY_MODES entry ('' = not yet declared).
        connectivity_mode: str = '',
        # ISO timestamp of the last accepted ingest for this device.
        last_seen: str = '',
        is_mock: bool = False,
        notes: str = '',
        # This device is a DESIGNATED web ENTRYPOINT (may open
        # outside doors — exposure is regulated to these).
        is_entrypoint: bool = False,
        # JSON list of outside doors this device serves:
        # [{port, internal, protocol, access:{level,user|group}}].
        # The isle stays contained; these are the only crossings.
        exposures_json: str = '[]',
        # NETWORK RESOURCE LEDGER (so near-arbitrary apps/engines can
        # be added without collision). JSON list of docker network
        # pools on this device [{name, cidr}] and published host
        # ports [{port, container}] — the allocator + conflict
        # assessments read these.
        pools_json: str = '[]',
        ports_json: str = '[]',
        manager=None,
    ):
        self.name = name
        self.isle_name = isle_name
        self.machine_name = machine_name
        self.agent_mode = agent_mode
        self.agent_present = agent_present
        self.hosts_router = hosts_router
        self.router_running = router_running
        self.connectivity_mode = connectivity_mode
        self.last_seen = last_seen
        self.is_mock = is_mock
        self.notes = notes
        self.is_entrypoint = is_entrypoint
        self.exposures_json = exposures_json
        self.pools_json = pools_json
        self.ports_json = ports_json
