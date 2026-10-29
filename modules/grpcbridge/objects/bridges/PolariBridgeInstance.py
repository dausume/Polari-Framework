"""
@module grpcbridge.objects.bridges.PolariBridgeInstance

PolariBridgeInstance - one class per file (design section 7). HARDWARE_SYSTEM_PINS_PLAN.md section 7 (hsp-3a; his refinement 2026-10-28).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PolariBridgeInstance(treeObject):
    """What it is: one Polari Hardware Bridge as a row (his words, 2026-10-28: "the Polari Bridge instance should specify an id for the hardware it is bound
    to, as well as the Polari instance it binds to (since any Bridge should have a Polari Node it is bound to, which should have a named url on the isle)").
    `hardware_id` = the bound hardware (the bench entry, + the USB serial hwmap scanned, or the twin session id when simulated); `polari_node` = the Polari
    instance's NAME (polari-pol) and `polari_node_url` its isle URL (https://api.<name>.isle - what `isle polari instance deploy` registers); every bridge
    has one, a bridge without refuses. `mode` serial | simulated; `path` = the BridgePath it rides; `bench` + `pins` = where it attaches; `maps` = the
    StructObjectMap names it USES (references, never copies: D-hsp-8); `status` bound | unreachable | gap, `status_why` in words.
    Related concepts: BridgePath, StructObjectMap + CatomAssertion (cmod), HardwareBridgeDefinition (what is generated), HostedBridge (a running hosted one).
    """

    plain_words = ('A Polari bridge instance is one live link between a piece of hardware and one Polari node on the isle: which board it listens to, '
                   'which Polari it reports to, and the path its data takes.')

    @treeObjectInit
    def __init__(self, name: str = '', hardware_id: str = '', polari_node: str = '', polari_node_url: str = '', mode: str = 'serial', path: str = '',
                 bench: str = '', pins: str = '', maps: str = '', bridge_definition: str = '', status: str = 'gap', status_why: str = '', basis: str = '',
                 notes: str = '', manager=None):
        self.name = name                        # '<label slug>-bridge'
        self.hardware_id = hardware_id          # 'home-bench/UNO #1' (+ '#usb:<serial>' once hwmap scanned it; 'twin:<session>' when simulated)
        self.polari_node = polari_node          # polari-pol
        self.polari_node_url = polari_node_url  # https://api.polari-pol.isle
        self.mode = mode                        # serial | simulated
        self.path = path                        # a BridgePath name
        self.bench = bench
        self.pins = pins                        # comma separated: PD0, PD1
        self.maps = maps                        # comma separated StructObjectMap names
        self.bridge_definition = bridge_definition   # the HardwareBridgeDefinition generated for it (uno-light)
        self.status = status                    # bound | unreachable | gap
        self.status_why = status_why
        self.basis = basis
        self.notes = notes
