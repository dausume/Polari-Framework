"""
@module board.custom.memory_map_atmega328p

rp-0 (MISSION_PROFILE_SOLVER_PLAN.md §2.4): the ATmega328P's memory map as MemoryRegion rows beyond the three the SoC
definition already carries (flash, sram, eeprom): the register file, the I/O registers, the extended I/O registers, and
flash split into the application section and the boot loader section. CODE-OWNED and CITED page by page from
Microchip DS40002061B (sha256 b9b9d83c…9320e, the file every other board fact cites), `pdftotext -layout`, the page numbers
are the PDF's own "DS40002061B-page N" footers:

  register file R0-R31          data space 0x0000-0x001F   §7.4 General Purpose Register File, Figure 7-2, p.21; §8.3 Figure 8-3, p.28
  I/O registers (64)            data space 0x0020-0x005F   §8.3 Figure 8-3, p.28; §8.5 I/O Memory, p.30 (IN/OUT 0x00-0x3F, +0x20 as data)
  extended I/O registers (160)  data space 0x0060-0x00FF   §8.3 Figure 8-3, p.28; §8.5 I/O Memory, p.30 (ST/LD only)
  internal data SRAM            data space 0x0100-0x08FF   §8.3 Figure 8-3, p.28 (the existing `sram` row)
  flash, two sections           §8.2 Figure 8-2, p.27: "Application Flash Section" and "Boot Flash Section";
                                the split is set by the BOOTSZ fuses, Table 27-13 "Boot Size Configuration, ATmega328/328P", p.286

The boot loader section is NOT a fixed size: BOOTSZ[1:0] picks one of four (Table 27-13). The rows carry the chip's shipped
default — the default value of BOOTSZ[1:0] "results in maximum Boot Size" (fuse table note 4, p.292), i.e. 2048 words =
4096 bytes — and `BOOT_OPTIONS` lists all four. What a BOARD does with it (the UNO's 512-byte Optiboot) is that board's cited
fact (boards.txt upload.maximum_size = 32256, Optiboot size 512, board.custom.uno_facts), applied by the memory-map view,
never by these rows. Which BOOTSZ fuse value the UNO actually ships with is `undetermined` (boards.txt high_fuses was not read).

Word addresses in Table 27-13 are program-memory WORDS (16-bit); the rows are in bytes (x2): 0x3F00 words = 0x7E00 bytes.
"""
from board.custom.soc_atmega328p import SOC, _fact

DS = 'DS40002061B'
#: Table 27-13, p.286, verbatim columns: (BOOTSZ1, BOOTSZ0, boot size in words, pages, application section words, boot loader section words, boot reset address words)
BOOT_OPTIONS = (
    ('11', 256, 4, ('0x0000', '0x3EFF'), ('0x3F00', '0x3FFF'), '0x3F00'),
    ('10', 512, 8, ('0x0000', '0x3DFF'), ('0x3E00', '0x3FFF'), '0x3E00'),
    ('01', 1024, 16, ('0x0000', '0x3BFF'), ('0x3C00', '0x3FFF'), '0x3C00'),
    ('00', 2048, 32, ('0x0000', '0x37FF'), ('0x3800', '0x3FFF'), '0x3800'),
)
#: the chip's shipped fuse: BOOTSZ1 = BOOTSZ0 = 0 (programmed) — "The default value of BOOTSZ[1:0] results in maximum Boot Size", p.292
DEFAULT_BOOTSZ = '00'
FLASH_BYTES = 32768
DATA_SPACE = '%s:data' % SOC

_REGFILE = '§7.4 General Purpose Register File, Figure 7-2, p.21; §8.3 SRAM Data Memory, Figure 8-3 Data Memory Map "32 Registers 0x0000 - 0x001F", p.28'
_IO = '§8.3 Figure 8-3 "64 I/O Registers 0x0020 - 0x005F", p.28; §8.5 I/O Memory, p.30 (IN/OUT use 0x00 - 0x3F; LD/ST add 0x20)'
_EXT = '§8.3 Figure 8-3 "160 Ext I/O Reg. 0x0060 - 0x00FF", p.28; §8.5 I/O Memory, p.30 (only ST/STS/STD and LD/LDS/LDD)'
_FLASH = '§8.2 Figure 8-2 Program Memory Map (Application Flash Section / Boot Flash Section), p.27; Table 27-13 Boot Size Configuration, p.286'


def boot_bytes(option):
    return option[1] * 2


def boot_start_bytes(option):
    return FLASH_BYTES - boot_bytes(option)


def option_for(bootsz):
    return next(o for o in BOOT_OPTIONS if o[0] == bootsz)


def facts():
    """The DatasheetFact rows the regions cite (same shape as soc_atmega328p.soc_facts; added to the seed beside them)."""
    d = option_for(DEFAULT_BOOTSZ)
    return [
        _fact('memory.register_file', '0x0000-0x001F', '', _REGFILE),
        _fact('memory.io_registers', '0x0020-0x005F', '', _IO),
        _fact('memory.ext_io_registers', '0x0060-0x00FF', '', _EXT),
        _fact('memory.flash_sections', 'application + boot loader', '', _FLASH,
              'the boundary is the BOOTSZ fuses (Table 27-13); the rows carry the shipped default, BOOTSZ=%s = %d bytes of boot' % (DEFAULT_BOOTSZ, boot_bytes(d))),
        _fact('memory.boot_sizes', '; '.join('BOOTSZ=%s %d words (%d B) boot reset address %s words' % (o[0], o[1], boot_bytes(o), o[5]) for o in BOOT_OPTIONS), '',
              'Table 27-13 Boot Size Configuration, ATmega328/328P, p.286; BOOTSZ[1:0] fuse default "results in maximum Boot Size", fuse table note 4, p.292'),
    ]


def region_rows():
    """The five added MemoryRegion rows (dicts in MemoryRegion's own fields)."""
    d = option_for(DEFAULT_BOOTSZ)
    app_size, boot_size, boot_start = boot_start_bytes(d), boot_bytes(d), boot_start_bytes(d)
    fk = lambda k: '%s:%s' % (SOC, k)   # noqa: E731
    return [
        {'name': '%s:register-file' % SOC, 'soc': SOC, 'region': 'register-file', 'start': '0x0000', 'size': 32, 'address_space': DATA_SPACE,
         'fact': fk('memory.register_file'), 'origin': 'cited:' + _REGFILE, 'undetermined': '',
         'notes': 'R0-R31, the 32 general purpose working registers; mapped into the first 32 data locations although not physically SRAM; R26-R31 double as the X/Y/Z pointers (Figure 7-2, p.21)'},
        {'name': '%s:io-registers' % SOC, 'soc': SOC, 'region': 'io-registers', 'start': '0x0020', 'size': 64, 'address_space': DATA_SPACE,
         'fact': fk('memory.io_registers'), 'origin': 'cited:' + _IO, 'undetermined': '',
         'notes': 'the 64 I/O registers: IN/OUT address 0x00-0x3F, the same registers at +0x20 as data (EIMSK 0x1D (0x3D))'},
        {'name': '%s:ext-io-registers' % SOC, 'soc': SOC, 'region': 'ext-io-registers', 'start': '0x0060', 'size': 160, 'address_space': DATA_SPACE,
         'fact': fk('memory.ext_io_registers'), 'origin': 'cited:' + _EXT, 'undetermined': '',
         'notes': 'the 160 extended I/O registers (timers 1/2, ADC, USART0, TWI ...): no IN/OUT alias, LD/ST only'},
        {'name': '%s:flash.application' % SOC, 'soc': SOC, 'region': 'flash-application', 'start': '0x0000', 'size': app_size, 'address_space': '',
         'fact': fk('memory.flash_sections'), 'origin': 'cited:' + _FLASH + '; shipped fuse BOOTSZ=%s, p.292' % DEFAULT_BOOTSZ,
         'undetermined': 'program memory (§8.1) - not addressed through the io/data space; the application/boot boundary moves with the BOOTSZ fuses (the memory-map view applies a board\'s cited bootloader)',
         'notes': 'the Application Flash Section: byte addresses 0x0000-0x%04X (words 0x0000-0x%04X); part of the `flash` row' % (app_size - 1, app_size // 2 - 1)},
        {'name': '%s:flash.boot' % SOC, 'soc': SOC, 'region': 'flash-boot', 'start': '0x%04X' % boot_start, 'size': boot_size, 'address_space': '',
         'fact': fk('memory.boot_sizes'), 'origin': 'cited:' + _FLASH + '; shipped fuse BOOTSZ=%s, p.292' % DEFAULT_BOOTSZ,
         'undetermined': 'program memory (§8.1); size = the shipped BOOTSZ default (maximum), one of four options: ' + '; '.join('BOOTSZ=%s %d B' % (o[0], boot_bytes(o)) for o in BOOT_OPTIONS),
         'notes': 'the Boot Flash Section (boot loader): byte addresses 0x%04X-0x7FFF (words 0x%04X-0x3FFF); part of the `flash` row; boot reset address %s words with BOOTRST' % (boot_start, boot_start // 2, d[5])},
    ]
