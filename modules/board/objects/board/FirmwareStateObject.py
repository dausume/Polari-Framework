"""
@module board.objects.board.FirmwareStateObject

FirmwareStateObject — one class per file (design §7); fst-0 (HARDWARE_BENCH_CONVERGENCE_PLAN.md §12).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FirmwareStateObject(treeObject):
    """What it is: ONE STATE OBJECT of one firmware config — a struct instance (the wire struct `state`, the rx parser `rx`), a file-scope
    static (`g_sensed`, `g_seq`, the hal's ring buffer), a static kept inside a function (`led_follow_state.pin`), an enum block or an enum-like
    group of defines (the presence bits, the framing constants), or an EEPROM record. DERIVED on every read by board.custom.firmware_state from
    the config's rendered sources (cmod's preprocessor + pycparser), the pinned wire contract and the generated header; never typed by hand.
    `writers` / `readers` are the functions whose bodies touch it (pointer hand-offs followed). `finding` is set when nobody writes or nobody
    reads it. Rows are refreshed from the derivation; editing one changes nothing in the firmware.
    Related concepts: `FirmwareStateField` (its members / values), `FirmwareVariant` (the config), `CAtom` (the functions named here),
    `ProtoContractVersion` (the wire struct's contract).
    """

    plain_words = ('A state object is one piece of memory the firmware keeps: the struct it reports, a counter, a flag, a saved number in EEPROM. '
                   'This row says what it is, how big it is, where it is declared, and which functions write and read it.')

    @treeObjectInit
    def __init__(self, name: str = '', config: str = '', object: str = '', kind: str = '', c_type: str = '', size_bytes: int = 0,
                 declared_in: str = '', fields_count: int = 0, writers: str = '', readers: str = '', words: str = '', source: str = '',
                 finding: str = '', manager=None):
        self.name = name  # '<config>:<object>' e.g. 'uno-light:wire:LightState'
        self.config = config
        self.object = object  # 'wire:LightState' | 'struct:rx' | 'static:g_seq' | 'local-static:led_follow_state.pin' | 'enum:LIGHTSTATE_SOURCE' | 'defines:LIGHTSTATE_F_*' | 'eeprom:…'
        self.kind = kind  # wire-struct | struct | static | local-static | enum | enum-defines | eeprom
        self.c_type = c_type
        self.size_bytes = size_bytes
        self.declared_in = declared_in
        self.fields_count = fields_count
        self.writers = writers  # csv of functions (how, in parentheses, when not direct)
        self.readers = readers
        self.words = words
        self.source = source  # where the derivation read it from
        self.finding = finding
