"""
@module board.objects.board.FirmwareStateField

FirmwareStateField — one class per file (design §7); fst-0 (HARDWARE_BENCH_CONVERGENCE_PLAN.md §12).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FirmwareStateField(treeObject):
    """What it is: ONE FIELD of a firmware state object (a struct member), DERIVED by board.custom.firmware_state: its C type and size, its wire tag
    and proto type when it is a wire field, its DIRECTION (command = the host sets it through a decoded frame; telemetry = the board reports it;
    command+telemetry = both, like `led_on`; internal = never on the wire), the pin or task it CONTROLS (the struct-controls-the-hardware rule:
    `led_on` controls D6 through led_follow_state), whether it is PERSISTED (EEPROM, through which function), its WRITERS and READERS (the
    functions whose bodies touch it, pointer hand-offs followed), the enum its values come from, and a FINDING when nobody writes it beyond
    zeroing or nobody reads it. Never typed by hand.
    Related concepts: `FirmwareStateObject` (the struct), `ProtoContractVersion` (tag + proto type), `EnumMapping` (the enum), `BoardPin` (controls).
    """

    plain_words = ('A field is one slot in a state struct. This row says its type, whether the screen can set it or only read it, which pin it moves, '
                   'whether it survives a reset, and which functions change or use it.')

    @treeObjectInit
    def __init__(self, name: str = '', config: str = '', object: str = '', field_name: str = '', c_type: str = '', size_bytes: int = 0, tag: str = '',
                 proto_type: str = '', direction: str = 'internal', controls: str = '', persisted: str = '', writers: str = '', readers: str = '',
                 enum: str = '', finding: str = '', source: str = '', manager=None):
        self.name = name  # '<config>:<object>.<field>'
        self.config = config
        self.object = object
        self.field_name = field_name
        self.c_type = c_type
        self.size_bytes = size_bytes
        self.tag = tag  # the wire tag (a wire field), '' otherwise
        self.proto_type = proto_type
        self.direction = direction  # command | telemetry | command+telemetry | internal (+ ' (omitted when KNOB is 0)')
        self.controls = controls  # 'D6 (LED_PIN) via led_follow_state'
        self.persisted = persisted  # 'EEPROM EEPROM_BOOT_SESSION_ADDR = … via boot_session_mint (eeprom_read_dword, eeprom_write_dword)'
        self.writers = writers
        self.readers = readers
        self.enum = enum  # 'LIGHTSTATE_SOURCE_*' when the values are an enum
        self.finding = finding
        self.source = source
