"""
@module pcb.objects.pcb.PcbNetClass

PcbNetClass — one class per file (design §7); kxc-4, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PcbNetClass(treeObject):
    """What it is: ONE NET CLASS of an ingested project (its .kicad_pro) - clearance, track width, via and micro-via sizes, differential-pair width and gap,
    priority - and the nets it holds (explicit assignments, then name patterns, else Default). -1 = the class does not set that value.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', netclass: str = '', clearance: float = -1.0, track_width: float = -1.0, via_diameter: float = -1.0,
                 via_drill: float = -1.0, microvia_diameter: float = -1.0, microvia_drill: float = -1.0, diff_pair_width: float = -1.0, diff_pair_gap: float
                 = -1.0, priority: float = -1.0, nets_json: str = '[]', net_count: int = 0, notes: str = '', manager=None):
        self.name = name
        self.board = board
        self.netclass = netclass
        self.clearance = clearance
        self.track_width = track_width
        self.via_diameter = via_diameter
        self.via_drill = via_drill
        self.microvia_diameter = microvia_diameter
        self.microvia_drill = microvia_drill
        self.diff_pair_width = diff_pair_width
        self.diff_pair_gap = diff_pair_gap
        self.priority = priority
        self.nets_json = nets_json
        self.net_count = net_count
        self.notes = notes
