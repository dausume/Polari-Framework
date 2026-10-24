"""
@module board.objects.board.ChipLadderEntry

ChipLadderEntry - one class per file (design section 7). chp-0 (MISSION_GENERIC_PLAN.md section 13.1): one chip (or one core of a
chip) on the chips-and-levels page, in ONE of two sections that never mix - `riscv` (the fixed RISC-V sample: two chips per software
level, plus the named exceptions) and `convenience` (the convenience and cross-reference boards: the AVR Arduinos, the SAMD21 boards,
the Xtensa ESP32, the bare FPGA). His rules 2026-10-24: "2 risc-v chips per level as samples (bare, FreeRTOS, Zephyr, Ubuntu)";
"preferring solutions where those already exist but are RISCV" (the emulator); "keep our existing already emulatabale devices as well,
the arduinos"; "the RISCV seperated out cleanly from the other convenience and cross-reference Boards"; "we will need to be able to
simulate them all if possible".
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ChipLadderEntry(treeObject):
    """What it is: ONE ROW of the chips-and-levels ladder - a chip (or one core of a heterogeneous chip), the boards that carry it,
    which of the four software levels it supports (bare C, FreeRTOS, Zephyr, Ubuntu) each with its BASIS (a document or a Polari row,
    never a guess; `unverified` when nobody has checked), the emulator that already exists for it (name, kind, licence, whether its pins
    are real or a stub) and the boards of it on the bench. Code-owned seed (`board.custom.chip_ladder_seed`); what Polari already holds
    for the chip (SoC rows, pin functions, registers, board rows) is DERIVED when asked (`board.custom.chip_ladder`) and has no field here.
    Related concepts: `SocDefinition` (the chip's own rows), `BoardDefinition` (its boards), `KitPart` (what is in the kit),
    `BoardSimCost` (what a twin costs to run).
    """

    plain_words = ('One chip on the chips-and-levels page: which software levels it can run, with the source for each claim, which '
                   'emulator already exists for it, and which of its boards are on the bench.')

    SECTIONS = ('riscv', 'convenience')
    LEVELS = ('bare_c', 'freertos', 'zephyr', 'ubuntu')
    STATUSES = ('yes', 'no', 'unverified', 'n/a')
    EMULATOR_STATUSES = ('exists', 'exists (pins stub)', 'planned', 'none')

    @treeObjectInit
    def __init__(self, name: str = '', section: str = 'riscv', slot: str = '', title: str = '', chip: str = '', vendor: str = '',
                 family: str = '', core: str = '', soc_key: str = '', boards_json: str = '[]', levels_json: str = '{}',
                 emulator_json: str = '{}', notes: str = '', source: str = '', manager=None):
        self.name = name                    # kebab-case key, e.g. 'esp32c3', 'polarfire-soc-u54', 'samd21g18a'
        self.section = section              # riscv | convenience - a chip is in ONE section
        self.slot = slot                    # riscv: 'bare-c 1' .. 'ubuntu 2' | 'exception'; convenience: the family word
        self.title = title
        self.chip = chip                    # the vendor's part name
        self.vendor = vendor
        self.family = family                # RISC-V | AVR | ARM Cortex-M0+ | Xtensa LX6 | FPGA
        self.core = core                    # the core and ISA words, e.g. 'RV32IMC 160 MHz', 'Hazard3 RV32IMAC (open)'
        self.soc_key = soc_key              # the SocDefinition name when Polari holds the chip's rows ('' otherwise)
        self.boards_json = boards_json      # [{board, title, on_hand: bool, note, price_usd?}] - board = BoardDefinition name when one exists
        self.levels_json = levels_json      # {bare_c|freertos|zephyr|ubuntu: {status: yes|no|unverified|n/a, basis}}
        self.emulator_json = emulator_json  # {name, kind, pins: real|stub|unverified|none, licence, status, module, basis}
        self.notes = notes
        self.source = source                # where the row's words come from (plan section, date)
