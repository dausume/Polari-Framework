"""
@module board.register_profile_page

rp-0: the two pages of the register profile, as CONFIGURED tables over the derived doors (no raw JSON, no new component):

/display/register-profile  Register profile - what each register of the SoC is FOR: pin configuration, peripheral operation,
                           memory / non-volatile memory, CPU / system, or mixed - the classes, the mixed registers, every register
                           and every field, each with its reason and its datasheet citation.
/display/memory-map        Memory map - the register file, I/O, extended I/O, SRAM, flash (application + boot loader) and EEPROM
                           with start, size, address space, what lives there and where it is cited; which registers live in which
                           region; which registers control the memories. Firmware use (used vs available, bootloader subtracted)
                           needs a measured build: GET /api/board/socs/atmega328p/memory-map?board=arduino-uno-r3&build=NAME.
Both read GET /api/board/socs/atmega328p/... (board.register_profile_api); another SoC is another door name, not another page.
"""
from polariApiServer.module_pages_seed import _page, _row, _table

_RP = '/api/board/socs/atmega328p/register-profile'
_MM = '/api/board/socs/atmega328p/memory-map'

REGISTER_PROFILE_PAGES = [
    _page('register-profile', 'register-profile',
          'Register profile - what each register of the ATmega328P is for. Every register field is sorted into one of four classes: pin configuration '
          '(it configures a pin or takes one over), peripheral operation (counts, compare values, baud, flags), memory (EEPROM, flash self-programming, '
          'the stack pointer) or CPU / system (status, sleep, clock, watchdog); a register whose fields fall in two classes is mixed. The sorting is '
          'derived from the datasheet rows, never typed by name, and every verdict says why and cites the page. For where the memories sit, open the '
          'Memory map (/display/memory-map).',
          'Register', [
              _row(0, [_table('rp-classes', 0, 12, 'The four classes - how many registers and fields fall in each', '',
                              description='What this is for: the totals of the register profile. One row = one class (plus a row for mixed). '
                                          'Columns: registers_pure (registers whose every field is this class), registers_touching (registers with at least one field '
                                          'of this class, mixed ones included), fields (fields in this class), means (what the class covers). '
                                          'GET %s?list=classes.' % _RP,
                              columns='class,registers_pure,registers_touching,fields,means', data_path='%s?list=classes' % _RP)]),
              _row(1, [_table('rp-mixed', 0, 12, 'Mixed registers - one register, more than one job', '',
                              description='What this is for: the registers whose fields are not all one class, e.g. MCUCR (PUD disables every pull-up = pin '
                                          'configuration; the vector-select and brown-out bits = CPU / system). One row = one register. Columns: classes '
                                          '(each class with its field count), fields_note (whether the bit fields are datasheet-cited rows or only named from the '
                                          'Register Summary), reason (which fields fall where and why), cite (datasheet section and page).',
                              columns='register,address,peripheral,classes,fields_note,reason,cite,ref', column_formats='ref:refs',
                              filter_field='class', filter_value='mixed', data_path=_RP)]),
              _row(2, [_table('rp-registers', 0, 12, 'Every register - its class, why, and where it is cited', '',
                              description='What this is for: the whole register file of the chip, one row = one register (address is the data-space address '
                                          'the program uses; io_address the short IN/OUT address, empty for the extended I/O). Columns: class (pin-configuration | '
                                          'peripheral-operation | memory-nvm | cpu-system | mixed), classes (with field counts), fields_note (`fields not modelled` '
                                          'when no cited bit-field rows exist yet), reason, cite. 16-bit registers (ADC, TCNT1 ...) appear beside their low and high bytes.',
                              columns='register,address,io_address,peripheral,width_bytes,class,classes,fields_note,reason,cite,ref', column_formats='ref:refs',
                              data_path=_RP)]),
              _row(3, [_table('rp-fields', 0, 12, 'Every field - its own class, where the verdict came from, why', '',
                              description='What this is for: the bit fields behind the register verdicts. One row = one field (or bit group). Columns: bits, '
                                          'class (the field\'s own class), register_class (its register\'s roll-up), source (RegisterField = a cited row classified '
                                          'from its own pin/signal tags; rule = a cited alternate-function enable such as RXEN0, SPE, TWEN, COMnx, DIDR0; '
                                          'register-summary = named from the datasheet Register Summary and classified by its register), reason, cite. '
                                          'GET %s?list=fields.' % _RP,
                              columns='register,field,bits,class,register_class,source,reason,cite', data_path='%s?list=fields' % _RP)]),
          ], title='Register profile'),
    _page('memory-map', 'memory-map',
          'Memory map - where everything lives on the ATmega328P: the 32 working registers, the 64 I/O registers and the 160 extended I/O registers (the '
          'first 256 bytes of the data space), the 2 KB of SRAM, the 32 KB of flash split into the application and the boot loader section, and the 1 KB '
          'of EEPROM. The first table is the UNO (its 512-byte Optiboot subtracted from the application); the second is the bare chip. Which registers '
          'live in which region and which registers control the memories are below. Use of each region by a firmware needs a measured build and reads '
          '`unmeasured` until one is given. For what each register is for, open the Register profile (/display/register-profile).',
          'MemoryRegion', [
              _row(0, [_table('mm-uno', 0, 12, 'Memory map of the Arduino UNO R3 - the bootloader subtracted from flash', '',
                              description='What this is for: every memory region of the UNO\'s chip. One row = one region. Columns: space (data | program | eeprom), '
                                          'start/end/size (bytes), holds (what lives there), registers (how many registers sit in it), controlled_by (the '
                                          'registers that address or program it), use/used/available/free (firmware use: unmeasured, measured or reserved - never a guess), '
                                          'cite (datasheet section and page), undetermined (what no source says). GET %s?board=arduino-uno-r3.' % _MM,
                              columns='space,region,start,end,size,holds,registers,controlled_by,use,used,available,free,cite,undetermined',
                              data_path='%s?board=arduino-uno-r3' % _MM)]),
              _row(1, [_table('mm-chip', 0, 12, 'Memory map of the bare chip - flash split at the shipped boot-size default', '',
                              description='What this is for: the same regions without a board - the boot loader section at the chip\'s shipped fuse default '
                                          '(BOOTSZ=00, 4096 bytes, the maximum), so the application section is the smaller 28672 bytes. A board with a '
                                          'smaller bootloader (the UNO\'s 512-byte Optiboot) is the table above. Columns as above.',
                              columns='space,region,start,end,size,holds,registers,controlled_by,use,cite,undetermined', data_path=_MM)]),
              _row(2, [_table('mm-registers', 0, 12, 'Which registers live in which region', '',
                              description='What this is for: every register placed in its region by its data-space address (from the register address mapping '
                                          'rows). One row = one register. Columns: region (io-registers 0x0020-0x005F or ext-io-registers 0x0060-0x00FF), '
                                          'address (data space), io_address (the IN/OUT address, empty for extended I/O), width_bytes. GET %s?list=registers.' % _MM,
                              columns='region,register,address,io_address,width_bytes', data_path='%s?list=registers' % _MM)]),
          ], title='Memory map'),
]
