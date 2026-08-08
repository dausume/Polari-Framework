"""
@module islemesh.islemesh_basis

Object model for the isle-mesh convergence (mac-1): the polari-side
rows that ACCEPT isle-mesh's data so the topology-idiom pages can
show the isle coming online layer by layer (Dustin 2026-08-07 —
the visualization is the verification instrument for the arc).

Authority split (MESH_APP_CONVERGENCE_HANDOFF §7): isle-mesh is
authoritative over NETWORKING — these rows are polari's ACCEPTED
COPY of what isle reports (via /api/islemesh/ingest/*), plus the
mac-1 mesh-app model (one app, many realizations). Rows are
ingest-owned: `pol isle sync` (real) or `pol isle mock` (flagged)
replace them wholesale per device; nothing here is hand-curated.

Every class carries `is_mock`: real isle data NEVER sets it — only
the mock feed does — and the summary API turns any live mock row
into a large MOCK NETWORK banner (islemesh_constants.MOCK_BANNER).

@consumers
  - islemesh.islemesh_api (ingest + read surface)
  - polariServer defClassList (tables + CRUDE)
  - islemesh.selftest_islemesh
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


class IsleUplink(treeObject):
    """One isle uplink on one device (handoff §10: the uplink is an
    abstraction — cable or wifi). Link quality feeds placement."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<device>@<interface>' ('pol-core@eno1').
        name: str = '',
        device_name: str = '',
        interface: str = '',
        # UPLINK_KINDS entry.
        kind: str = 'ethernet',
        link_up: bool = False,
        # Link quality — 0.0 = unmeasured (never a fake number).
        latency_ms: float = 0.0,
        jitter_ms: float = 0.0,
        loss_pct: float = 0.0,
        measured_at: str = '',
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.interface = interface
        self.kind = kind
        self.link_up = link_up
        self.latency_ms = latency_ms
        self.jitter_ms = jitter_ms
        self.loss_pct = loss_pct
        self.measured_at = measured_at
        self.is_mock = is_mock
        self.notes = notes


class IsleApp(treeObject):
    """One mesh-app as isle knows it (a registry.json entry) plus
    the mac-1 convergence fields (orchestrator, availability triple,
    automation knob). One app — many realizations (see
    MeshAppRealization)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: the isle app name ('myapp').
        name: str = '',
        # Primary domain ('myapp.local' today; '<app>.isle' is the
        # convergence target — both may exist during transition).
        domain: str = '',
        # Device currently hosting the containers ('' = unknown).
        device_name: str = '',
        # JSON list of APP_MODES entries (registry 'modes').
        modes_json: str = '[]',
        # ORCHESTRATORS entry.
        orchestrator: str = 'compose',
        # AVAILABILITY_MODES preset as isle records it today.
        availability_mode: str = 'always-available',
        # The general trigger triple (isle AVAILABILITY-MODES
        # vocabulary; presets above are shorthands for these).
        up_trigger: str = 'boot',
        down_trigger: str = 'never',
        placement: str = 'single-host',
        # The per-app auto/manual knob (handoff §2b.1): what auto
        # may touch. {'triggers_allowed': [...], 'may_relocate':
        # false} — manual-everything by default (knobs rule).
        automation_json: str = '{"triggers_allowed": [], '
                               '"may_relocate": false}',
        # Observed run state as last ingested ('' = unknown;
        # 'up'|'down'|'waking' once the isle side reports it).
        status: str = '',
        # Registry updated_at, as isle recorded it.
        updated_at: str = '',
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.domain = domain
        self.device_name = device_name
        self.modes_json = modes_json
        self.orchestrator = orchestrator
        self.availability_mode = availability_mode
        self.up_trigger = up_trigger
        self.down_trigger = down_trigger
        self.placement = placement
        self.automation_json = automation_json
        self.status = status
        self.updated_at = updated_at
        self.is_mock = is_mock
        self.notes = notes


class IsleAppService(treeObject):
    """One service row of one isle app (registry services[]): the
    containers behind the app's subdomains."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<app>/<service>' ('myapp/api').
        name: str = '',
        app_name: str = '',
        # The device whose registry declared this service — makes
        # the per-device replace semantics reach services too.
        device_name: str = '',
        service: str = '',
        subdomain: str = '',
        container: str = '',
        port: int = 0,
        protocol: str = 'http',
        is_mock: bool = False,
        manager=None,
    ):
        self.name = name
        self.app_name = app_name
        self.device_name = device_name
        self.service = service
        self.subdomain = subdomain
        self.container = container
        self.port = port
        self.protocol = protocol
        self.is_mock = is_mock


class MeshAppRealization(treeObject):
    """One way one app is delivered (handoff §9/§11): simultaneous,
    not exclusive — the same app can be a local .deb stub, a shell
    install, the plain website, and (hardware apps) a KVM. All
    carry the same .isle URL once converged."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<app>@<kind>' ('myapp@website').
        name: str = '',
        app_name: str = '',
        # REALIZATION_KINDS entry.
        kind: str = 'website',
        # The URL this realization opens ('' until known).
        url: str = '',
        # PACKAGE_KINDS entry ('' = not delivered as a package).
        package_kind: str = '',
        # kvm only: hardware-affinity pin — the device the physical
        # USB device is plugged into. The mover REFUSES to move a
        # pinned realization (suggest replug-at-target instead).
        hardware_pin_device: str = '',
        status: str = '',
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.app_name = app_name
        self.kind = kind
        self.url = url
        self.package_kind = package_kind
        self.hardware_pin_device = hardware_pin_device
        self.status = status
        self.is_mock = is_mock
        self.notes = notes


class IsleProtocolPermit(treeObject):
    """One permitted protocol path, DERIVED from the agent nginx
    fragments isle controls (handoff §11: the proxies ARE the
    policy — these rows make it visible as the protocol matrix).
    Never hand-written: parse output only."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<device>/<server_name>:<port>'.
        name: str = '',
        # The device whose agent enforces this permit.
        device_name: str = '',
        # The app the fragment belongs to ('' if unattributed).
        app_name: str = '',
        # nginx server_name this vhost answers to.
        server_name: str = '',
        listen_port: int = 0,
        # PERMIT_PROTOCOLS entry (https-mtls = client cert required).
        protocol: str = 'http',
        # Where the proxy sends it ('http://myapp_backend' or an
        # upstream member 'backend:8443'; comma-joined if several).
        upstream: str = '',
        # Source fragment filename ('myapp.conf') — provenance.
        fragment_ref: str = '',
        is_mock: bool = False,
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.app_name = app_name
        self.server_name = server_name
        self.listen_port = listen_port
        self.protocol = protocol
        self.upstream = upstream
        self.fragment_ref = fragment_ref
        self.is_mock = is_mock


class IsleCatalogEntry(treeObject):
    """One store listing (handoff §20.1/§20.3 — the general isle app
    store, appstore-1 generalized from shells to mesh-apps). An entry
    describes WHAT an app is and HOW it installs; the actual install
    runs on the host (`isle store install`, the mover-on-host
    discipline), never in the backend container.

    kind partitions the two proven variants + modules:
      'mesh-app'      — a compose app deployed to the isle (the
                        `isle app deploy` pipeline; source_ref = a
                        compose file/url or an image name)
      'polari-app'    — a polari or .isle web app installed as a
                        shared-shell launcher .deb (source_ref = the
                        app's .isle URL; the §22 launcher build)
      'polari-module' — a polari module .deb (source_ref = module
                        name; the module_bundle install, mac-8)
    """

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('books', 'polari', 'whoami').
        name: str = '',
        title: str = '',
        description: str = '',
        # IsleCatalogEntry kind (see class doc).
        kind: str = 'mesh-app',
        # What install consumes, per kind: compose ref / image
        # (mesh-app), .isle URL (polari-app), module name (module).
        source_ref: str = '',
        # For mesh-app: the primary service + port (deploy args).
        service: str = '',
        port: int = 0,
        # Desired .isle domain ('' → <name>.isle).
        domain: str = '',
        # Engine capability this app provides once installed
        # ('business-ops' → wires OdooInstanceConfig); '' = none.
        provides_engine: str = '',
        # Presentation.
        icon: str = '',
        category: str = '',
        # Store bookkeeping: published (listed) + who curated it.
        published: bool = True,
        source: str = 'official',
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.kind = kind
        self.source_ref = source_ref
        self.service = service
        self.port = port
        self.domain = domain
        self.provides_engine = provides_engine
        self.icon = icon
        self.category = category
        self.published = published
        self.source = source
        self.is_mock = is_mock
        self.notes = notes


class IsleEngine(treeObject):
    """An isle app that DECLARES it provides a polari engine
    (handoff §20.4): `isle app deploy --engine <kind>=<url>` emits
    the declaration, the pusher ingests it, and the binder wires it
    into whatever polari surface consumes that kind (odoo →
    OdooInstanceConfig.base_url; generic → the provider ladder).

    `bound` records whether the polari-side consumer was actually
    wired (the consuming module may be absent — then the engine is
    available-but-unbound, stated honestly, not silently dropped)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<app>@<kind>' ('books@business-ops').
        name: str = '',
        app_name: str = '',
        device_name: str = '',
        # The engine capability provided: 'business-ops' (odoo),
        # 'compute', 'scoring', … — a polari-recognized kind.
        provides: str = '',
        # Where polari reaches the engine (an .isle URL or an
        # in-mesh container:port).
        url: str = '',
        # Which polari surface got wired, '' if none was available.
        bound_to: str = '',
        bound: bool = False,
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.app_name = app_name
        self.device_name = device_name
        self.provides = provides
        self.url = url
        self.bound_to = bound_to
        self.bound = bound
        self.is_mock = is_mock
        self.notes = notes


class IsleIngestReceipt(treeObject):
    """One accepted ingest — the ledger the freshness/mock banner is
    derived from. Receipts are append-only history; the data rows
    they produced are replace-per-device."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<device>/<kind>/<sha256[:12]>'.
        name: str = '',
        device_name: str = '',
        # INGEST_KINDS entry.
        kind: str = 'registry',
        payload_sha256: str = '',
        # {'IsleApp': n, ...} — what this ingest upserted.
        row_counts_json: str = '{}',
        # THE mock flag (Dustin 2026-08-07): true only when the
        # sender declared mock_network — real isle data never does.
        mock_network: bool = False,
        ingested_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.kind = kind
        self.payload_sha256 = payload_sha256
        self.row_counts_json = row_counts_json
        self.mock_network = mock_network
        self.ingested_at = ingested_at
        self.notes = notes
