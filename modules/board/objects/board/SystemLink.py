"""
@module board.objects.board.SystemLink

SystemLink — one class per file (design §7); hsp-1 (HARDWARE_SYSTEM_PINS_PLAN.md L6).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SystemLink(treeObject):
    """What it is: ONE CONNECTION BETWEEN TWO PARTICIPANTS of a `HardwareSystem` — U1's serial pins to the 16U2's through two 1 kOhm resistors, the 16U2's
    USB to the host, the DTR line through C5 to U1's RESET, the bench jumper from D6 to D3, the button, the LED branch, the bridge to the backend. Each
    endpoint is {participant, refs, what}: the pin set as refs (BoardPin / PackageContact / ConnectorPin / circuit net / runtime port). `medium` and
    `signal_kind` say what it is; `protocol` names the contract when one exists (LightState v1); `via_refs_json` lists the `EnclosureContact` rows the link
    rides on — derived from the exposure maps, never retyped. A link whose source rows are gone from the tables is not listed.
    Related concepts: `HardwareSystem`, `SignalPath`, `EnclosureContact`, `BoardPinNet`, `WireContract`.
    """

    plain_words = ('A system link is one connection in a hardware system: what is at each end, what carries it (a trace, a resistor, a wire, USB, a '
                   'network call), what kind of signal it is and what rules the messages follow.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', system: str = '', endpoint_a_json: str = '{}', endpoint_b_json: str = '{}', medium: str = 'trace',
                 signal_kind: str = 'digital', protocol: str = '', via_refs_json: str = '[]', verification: str = 'unverified', undetermined: str = '',
                 citations_json: str = '[]', notes: str = '', manager=None):
        self.name = name  # '<system>:<slug>'
        self.title = title
        self.system = system  # the HardwareSystem row
        self.endpoint_a_json = endpoint_a_json  # {participant, refs: [Class:name], what}
        self.endpoint_b_json = endpoint_b_json
        self.medium = medium  # trace | series-resistor | capacitor | jumper-wire | usb | serial-port | grpc | http
        self.signal_kind = signal_kind  # digital | analog | uart | usb | rpc | reset
        self.protocol = protocol  # '' or the contract, e.g. 'LightState v1 (contract hash ...)'
        self.via_refs_json = via_refs_json  # ["EnclosureContact:<name>"] — DERIVED from the exposure maps
        self.verification = verification  # verified | partial | unverified | conflicted
        self.undetermined = undetermined
        self.citations_json = citations_json  # [document / page / DatasheetFact strings], derived from the via crossings
        self.notes = notes
