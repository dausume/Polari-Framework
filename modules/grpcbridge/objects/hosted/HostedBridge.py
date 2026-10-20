"""
@module grpcbridge.objects.hosted.HostedBridge

HostedBridge - one class per file (design section 7); sim-2 (HARDWARE_BENCH_CONVERGENCE_PLAN.md section 3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HostedBridge(treeObject):
    """What it is: the generated Polari Hardware Bridge running ON A SERVER beside one twin session, so the simulated board talks to Polari with no desktop
    app. The bridge reads the session's serial report over TCP, decodes it into the same struct a real board would send (for the light: LightState), pushes
    it to the Polari backend over gRPC, and carries the backend's commands back down to the board. The page alone is then a complete test: a press on the
    simulated button changes the LightState row, and the light button on the page reaches the simulated LED.

    Fields: `name` is `<bridge>-<6 hex>`; `session` the TwinSession it is attached to; `bridge_name` the HardwareBridgeDefinition whose generated project runs
    (for example uno-light); `state` is `building` (the jar is being made, or found in the worker's cache) | `running` | `failed` | `ended`; `worker_url` and
    `worker_bridge` the bridge-engines worker and the bridge's id there; `twin_host` / `twin_port` the session's serial port the bridge reads; `grpc_target`
    the Polari backend gRPC port the bridge pushes to (empty = the bridge only logs what it decodes); `build_fp` the fingerprint (sha256 prefix) of the
    generated code, the key of the worker's jar cache, and `jar_sha256` the jar that runs; `owner`; `started_at` / `expires_at` UTC seconds (a bridge nobody
    stops ends at `expires_at`, or when its session ends); `ended_at` / `end_reason` say when and why it stopped.

    Related concepts: TwinSession (the simulated board it reads), HardwareBridgeDefinition (what is generated), LightState (the row it keeps current).
    """

    plain_words = ('A hosted bridge is the link between a simulated board and Polari, run for you on a server: it listens to the board, updates the Polari '
                   'rows, and passes your commands back to the board.')

    @treeObjectInit
    def __init__(self, name: str = '', session: str = '', bridge_name: str = '', state: str = 'building', worker_url: str = '', worker_bridge: str = '',
                 twin_host: str = '', twin_port: int = 0, grpc_target: str = '', build_fp: str = '', jar_sha256: str = '', owner: str = '',
                 started_at: float = 0.0, expires_at: float = 0.0, ttl_s: int = 0, ended_at: float = 0.0, end_reason: str = '', manager=None):
        self.name = name  # '<bridge>-<6 hex>'
        self.session = session  # a TwinSession name
        self.bridge_name = bridge_name  # a HardwareBridgeDefinition name
        self.state = state  # building | running | failed | ended
        self.worker_url = worker_url
        self.worker_bridge = worker_bridge
        self.twin_host = twin_host
        self.twin_port = twin_port
        self.grpc_target = grpc_target
        self.build_fp = build_fp
        self.jar_sha256 = jar_sha256
        self.owner = owner
        self.started_at = started_at
        self.expires_at = expires_at
        self.ttl_s = ttl_s
        self.ended_at = ended_at
        self.end_reason = end_reason
