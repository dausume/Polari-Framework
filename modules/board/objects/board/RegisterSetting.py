"""
@module board.objects.board.RegisterSetting

RegisterSetting — one class per file (design §7); ucd-0a defines it, ucd-0b populates it (UNO_CORE_DEMO_PLAN.md §5g A).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RegisterSetting(treeObject):
    """What it is: THE VALUE ONE FIRMWARE SOLUTION WRITES TO ONE REGISTER IN ONE PHASE — "uno-button-clock writes EICRA =
    0b00000101 at init". One row per (solution, register, phase); the row a novice reads to see the final bits and, through
    `field_settings_refs_json`, WHY each field has its value (one `RegisterFieldSetting` per field, each naming the claim
    and the task). `write_mask` says which bits this solution sets — bits outside it are left at the chip's reset value
    and the page says so; two field settings whose bits overlap make `status` conflict (never last-write-wins). DERIVED
    from the solution's PinClaim/PeripheralClaim rows (ucd-0b), rendered into the generated `pin_config.c` whose line
    the row cites (`source_line`), so the chain reaches the C: setting → line → built firmware.
    Related concepts: `Register`, `RegisterFieldSetting`, cmod's `PinClaim`/`PeripheralClaim`, `FirmwareSolution`.
    """

    plain_words = ('A register setting is the exact value one firmware writes into one register when it starts (or '
                   'later, at run time), with a line per bit field saying why that field has that value.')

    @treeObjectInit
    def __init__(self, name: str = '', solution: str = '', register: str = '', phase: str = 'init', value: str = '',
                 value_bits: str = '', write_mask: str = '', field_settings_refs_json: str = '[]', source_file: str = '',
                 source_line: int = 0, status: str = 'planned', provenance: str = 'derived', binding: str = '',
                 notes: str = '', manager=None):
        self.name = name                    # '<solution>:<REGISTER>:<phase>' (uno-button-clock:EICRA:init)
        self.solution = solution            # the FirmwareSolution row
        self.binding = binding              # ucd-0b2b: the HardwareBinding row this setting belongs to ('' pre-0b2b rows)
        self.register = register            # the Register row name ('<soc>:EICRA')
        self.phase = phase                  # init | runtime
        self.value = value                  # '0x05'
        self.value_bits = value_bits        # '00000101' (msb first), for the bit strip
        self.write_mask = write_mask        # '0x0F' — the bits this solution sets
        self.field_settings_refs_json = field_settings_refs_json  # ["RegisterFieldSetting:…", …]
        self.source_file = source_file      # pin_config.c
        self.source_line = source_line      # the line in the generated file
        self.status = status                # planned | generated | conflict
        self.provenance = provenance        # derived
        self.notes = notes
