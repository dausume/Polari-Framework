"""
@module board.chip_ladder_page

chp-0 (MISSION_GENERIC_PLAN.md section 13.1): `/display/chip-ladder` - the chips-and-levels page, configured tables only (no raw JSON, no new
component). Three tabs, and the RISC-V sample is kept CLEANLY APART from the convenience and cross-reference boards (his words 2026-10-24):

  RISC-V        the fixed sample, two chips per level (bare C, FreeRTOS, Zephyr, Ubuntu) + the named exceptions, each with its emulator
  Convenience   the AVR Arduinos (simavr twins), the SAMD21 boards (Arduino Zero, Feather M0 Express), the Xtensa ESP32 eval board, the bare iCE40
  Emulators     one row per emulator: what it covers, whether its pins are real or a stub, its licence, what is missing to simulate everything

Above the tabs: the four levels themselves. Every level cell is a word (yes / no / unverified / n/a) and the `_basis` column beside it says
where that word comes from; `in_polari` is derived from the board tables on every read.
"""
from polariApiServer.module_pages_seed import _page, _row, _table, _tab

DOOR = '/api/board/chip-ladder'
_LEVEL_COLS = 'slot,title,family,core,bare_c,freertos,zephyr,ubuntu,emulator,emulator_pins,on_hand,in_polari'
_BASIS_COLS = 'title,bare_c,bare_c_basis,freertos,freertos_basis,zephyr,zephyr_basis,ubuntu,ubuntu_basis'
_EMU_COLS = 'title,emulator,emulator_kind,emulator_status,emulator_pins,emulator_licence,emulator_basis'
_BOARD_COLS = 'title,chip,vendor,boards,on_hand,notes,source'

_LEVELS_TEXT = ('The four software levels a chip is sampled at. Bare C and FreeRTOS are the firmware tiers; Zephyr describes the board in a device tree; Ubuntu is the host tier where '
                'Polari itself can run. Each level names the open RISC-V core the cores survey picked for it.')


def _section_rows(section, prefix, word):
    """The four tables of one section: the ladder, the basis of every claim, the emulators, the boards."""
    q = DOOR + '?section=' + section
    return [
        _row(0, [_table(prefix + '-ladder', 0, 12, '%s - the chips and their levels' % word, '',
                        description='One row per chip. slot = which sample slot it fills (RISC-V: two per level; "exception" = kept beside the sample, not in it). The level columns are '
                                    'words: yes / no / unverified (nobody has checked) / n/a (a microcontroller cannot run Ubuntu, an application processor has no bare-C tier). '
                                    'emulator_pins says whether the twin\'s pins are real, a stub or unverified. in_polari is derived on every read: which rows Polari already holds for the chip.',
                        columns=_LEVEL_COLS, data_path=q)], min_height=360),
        _row(1, [_table(prefix + '-basis', 0, 12, '%s - where every level claim comes from' % word, '',
                        description='The same chips; beside every level word, its basis: a document URL, a Polari module, or the word unverified. Nothing here is guessed.',
                        columns=_BASIS_COLS, data_path=q)], min_height=320),
        _row(2, [_table(prefix + '-emulators', 0, 6, '%s - the emulator each chip has' % word, '',
                        description='Which emulator already exists for the chip, its kind and licence, its status (exists / exists with stub pins / planned / none) and the basis.',
                        columns=_EMU_COLS, data_path=q),
                 _table(prefix + '-boards', 1, 6, '%s - the boards and what is on the bench' % word, '',
                        description='The boards that carry each chip, which are on the bench (part names only), and the notes.',
                        columns=_BOARD_COLS, data_path=q)], min_height=320),
    ]


def _emulators_tab():
    return _tab('emulators', 'Emulators', [
        _row(0, [_table('chp-emulators', 0, 12, 'Every emulator the ladder names', '',
                        description='One row per emulator: its kind, licence, which chips it covers here, whether its pins are real or a stub, and what is missing before everything can '
                                    'be simulated (his rule: "we will need to be able to simulate them all if possible"). "none known" lists the chips that are hardware-proven only.',
                        columns='emulator,kind,licence,pins,status,chips_covered,what_is_missing', data_path=DOOR + '/emulators')], min_height=360),
    ], description='The twins that exist today, what they cover, and the gap to simulating every board on the page.')


CHIP_LADDER_PAGES = [
    _page('chip-ladder', 'chip-ladder',
          'Chips and levels - the RISC-V sample (two chips per software level: bare C, FreeRTOS, Zephyr, Ubuntu, preferring chips whose emulator already exists) kept apart from the '
          'convenience and cross-reference boards (the AVR Arduinos, the SAMD21 boards, the Xtensa ESP32, the bare iCE40 FPGA). Every level claim carries its basis; every chip '
          'names its emulator and whether the twin\'s pins are real. The doors: GET %s?section=riscv|convenience, %s/levels, %s/emulators.' % (DOOR, DOOR, DOOR),
          'ChipLadderEntry', [
              _row(0, [_table('chp-levels', 0, 12, 'The four software levels', '', description=_LEVELS_TEXT,
                              columns='title,what_it_means,open_core_pick,source', data_path=DOOR + '/levels')], min_height=240),
          ],
          title='Chips and levels',
          tabs=[_tab('riscv', 'RISC-V', _section_rows('riscv', 'chp-riscv', 'RISC-V sample'),
                     description='The fixed sample: two RISC-V chips per level, each preferring an emulator that already exists, plus the named exceptions (RP2350 for PIO, '
                                 'Milk-V Duo, CH32V003, the K1 hosts). Capability beyond the sample comes from peripherals and from more chips per board, never from a longer list.'),
                _tab('convenience', 'Convenience and cross-reference boards', _section_rows('convenience', 'chp-conv', 'Convenience boards'),
                     description='The boards kept because they are accessible and already on the bench: the AVR Arduinos simavr twins today, the SAMD21 Arduino Zero and Feather M0 '
                                 'Express, the Xtensa ESP32 eval board, the bare iCE40UP5K. None of these is RISC-V; the ESP32 here is the ORIGINAL Xtensa chip.'),
                _emulators_tab()]),
]
