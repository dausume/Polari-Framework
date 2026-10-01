"""
@module board.objects.board.InstallRecord

InstallRecord — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class InstallRecord(treeObject):
    """What it is: What one confirmed install DID (brd-fi, plan §7a): the plan it ran, the verdict (installed |
    failed | refused), the verify read-back (avrdude's verified byte count on a board; the twin's loaded flash byte
    count against the .hex), the firmware sha now on the device, elapsed time, the log tail, then the bridge that
    attached and the first frames it saw — so the page can show "this variant is running, and here is what it says".
    Related concepts: `InstallPlan`, `FirmwareBuild`, `BoardInstance` (stamped firmware_sha), grpcbridge bridges.
    """

    @treeObjectInit
    def __init__(self, name: str = '', plan: str = '', build: str = '', variant: str = '', instance: str = '',
                 target_kind: str = '', verdict: str = '', verify: str = '', verified_bytes: int = 0,
                 firmware_sha: str = '', elapsed_s: float = 0.0, log_tail: str = '', started_at: str = '',
                 finished_at: str = '', bridge_name: str = '', bridge_state: str = '', row_class: str = '',
                 row_name: str = '', first_frames_json: str = '[]', frames_per_s: float = 0.0, notes: str = '',
                 manager=None):
        self.name = name  # 'install-<build>-<n>'
        self.plan = plan
        self.build = build
        self.variant = variant
        self.instance = instance
        self.target_kind = target_kind  # board | twin
        self.verdict = verdict  # installed | failed | refused
        self.verify = verify  # plain words: what was read back and compared
        self.verified_bytes = verified_bytes
        self.firmware_sha = firmware_sha
        self.elapsed_s = elapsed_s
        self.log_tail = log_tail
        self.started_at = started_at
        self.finished_at = finished_at
        self.bridge_name = bridge_name
        self.bridge_state = bridge_state  # '' | attaching | attached | refused: <why>
        self.row_class = row_class  # the class whose row the board updates
        self.row_name = row_name
        self.first_frames_json = first_frames_json  # [{seq, uptime_ms, …}] as the bridge logged them
        self.frames_per_s = frames_per_s
        self.notes = notes
