"""
@module board.objects.board.SignalPath

SignalPath — one class per file (design §7); hsp-1 (HARDWARE_SYSTEM_PINS_PLAN.md L7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SignalPath(treeObject):
    """What it is: ONE LOGICAL SIGNAL WALKED END TO END across a `HardwareSystem` — button press to the Polari page, the page's toggle to the LED, the LED line to
    the sense pin. DERIVED (recomputed on every seed and on every read of the door, never typed): `hops_json` is the ordered list of
    {n, kind (participant | pin | enclosure-crossing | net | link | contract | firmware), ref, what, check, verdict, detail}. Each hop's verdict comes from
    the code that owns that check — the availability ladder's rung, an electrical rule, the pin lifecycle, the contract hash, a twin proof — or says
    `unchecked`; a ref that does not resolve is an explicit blocked / undetermined hop naming what is missing, never a gap. The path verdict is the worst hop.
    Related concepts: `HardwareSystem`, `SystemLink`, `EnclosureContact`, `PinFunction`, `WireContract`.
    """

    plain_words = ('A signal path follows one signal from where it starts to where it ends, hop by hop — each pin, wall, wire, program and message on '
                   'the way — and says for each hop whether it is fine, blocked, conditional or not yet checked.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', system: str = '', direction: str = 'up', origin: str = '', destination: str = '',
                 hops_json: str = '[]', hop_count: int = 0, verdict: str = 'unchecked', blocked_at: int = 0, gap_free: bool = False,
                 summary: str = '', notes: str = '', manager=None):
        self.name = name  # '<system>:<slug>'
        self.title = title
        self.system = system  # the HardwareSystem row
        self.direction = direction  # up (device -> Polari) | down (Polari -> device) | loop (device -> device)
        self.origin = origin
        self.destination = destination
        self.hops_json = hops_json  # [{n, kind, ref, what, check, verdict, detail, resolved, ...}]
        self.hop_count = hop_count
        self.verdict = verdict  # the worst hop: blocked > unchecked > conditional > undetermined > not-yet > ok
        self.blocked_at = blocked_at  # n of the first blocked hop (0 = none)
        self.gap_free = gap_free  # every hop resolves to a row or is an explicit blocked / undetermined hop
        self.summary = summary
        self.notes = notes
