"""
@module board.objects.board.TwinSession

TwinSession — one class per file (design §7); sim-1 (HARDWARE_BENCH_CONVERGENCE_PLAN.md §3, §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TwinSession(treeObject):
    """What it is: ONE running simulated board you can interact with — the simavr twin started on an engines worker with a live control port, running the
    firmware of one configuration (a firmware variant such as `uno-light`). The firmware is LOCKED: the row stores the sha256 of the exact .hex the twin was
    loaded with, and nothing here edits or reflashes it while the session runs. You change the world around the firmware instead — press a button (a pin
    level), set a sensor voltage (an ADC channel), reset the power — and read what the board does back (the pins it drives, its serial report).
    The session is a participant of the Hardware System as `twin:<board>#<n>`.

    Fields: `config` is the firmware variant that was built and loaded; `board` the board design (a BoardDefinition name); `participant` the name the
    Hardware System lists (`twin:arduino-uno-r3#0`; `instance_index` is its number among the running sessions of that board); `state` is `running` | `ended`;
    `hex_sha256` / `hex_bytes` the locked firmware; `worker_url` the engines worker that runs the twin and `worker_session` its id there; `host`, `tcp_port`
    and `ctl_port` where the twin listens (the serial report on `tcp_port`, the control channel on `ctl_port`, both behind the session's token, which is
    derived on the server and never stored in this row); `started_at` / `expires_at` UTC seconds (a session that nobody stops ends at `expires_at`);
    `ended_at` / `end_reason` say when and why it stopped; `watch_json` the pins whose changes are streamed; `last_status_json` the twin's latest status line.

    Related concepts: FirmwareVariant (the config), FirmwareBuild (the build record), BoardInstance (`twin:<board>#<n>` names also appear on its bindings),
    HardwareSystem (lists the session as a participant), BoardSimCost (what a twin costs).
    """

    plain_words = ('A twin session is a simulated board that is switched on and waiting for you: the firmware is locked in, you can press its button or '
                   'turn its sensor, and you can watch what it does.')

    @treeObjectInit
    def __init__(self, name: str = '', config: str = '', board: str = '', participant: str = '', instance_index: int = 0, state: str = 'running',
                 hex_sha256: str = '', hex_bytes: int = 0, firmware_locked: bool = True, worker_url: str = '', worker_session: str = '', host: str = '',
                 tcp_port: int = 0, ctl_port: int = 0, owner: str = '', started_at: float = 0.0, expires_at: float = 0.0, ttl_s: int = 0,
                 ended_at: float = 0.0, end_reason: str = '', watch_json: str = '[]', last_status_json: str = '{}', manager=None):
        self.name = name  # '<config>-<6 hex>'
        self.config = config  # the firmware variant that was built and loaded
        self.board = board  # a BoardDefinition name
        self.participant = participant  # 'twin:<board>#<n>' — as the Hardware System lists it
        self.instance_index = instance_index
        self.state = state  # running | ended
        self.hex_sha256 = hex_sha256  # the LOCKED firmware
        self.hex_bytes = hex_bytes
        self.firmware_locked = firmware_locked
        self.worker_url = worker_url
        self.worker_session = worker_session
        self.host = host
        self.tcp_port = tcp_port  # the USART0 report
        self.ctl_port = ctl_port  # the control channel
        self.owner = owner
        self.started_at = started_at
        self.expires_at = expires_at
        self.ttl_s = ttl_s
        self.ended_at = ended_at
        self.end_reason = end_reason
        self.watch_json = watch_json
        self.last_status_json = last_status_json
