"""
@module board.objects.board.Register

Register — one class per file (design §7); ucd-0a, THE HARDWARE CHAIN.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Register(treeObject):
    """What it is: ONE HARDWARE REGISTER of a SoC — EICRA, DDRD, TCCR2A — with its address in the chip's address space.
    DERIVED one row per entry of the register snapshot (board.custom.registers: `avr-gcc -E -dM <avr/io.h>` read through
    the engines seam, committed with the avr-libc version and the sha of the text it came from) — never typed in; the
    AVR's two addressings are kept as the snapshot carries them (`space` io = an I/O-space address reachable by IN/OUT,
    mem = a data-memory address; `addr` is the one avr-libc defines, `addr_mem` the data-space view when the datasheet
    prints both, e.g. "0x1D (0x3D)"). `peripheral` groups it by the datasheet's own naming rules. `fields_refs_json` is
    the reverse link to the cited `RegisterField` rows (only the registers the firmware configures carry fields so far —
    the rest say so in `undetermined`). `reset_value` comes from the datasheet's "Initial Value" line when cited.
    Related concepts: `Peripheral`, `RegisterField`, `RegisterSetting` (a solution's value for it), cmod's atoms
    (their `resources` name these same registers by the same names).
    """

    plain_words = ('A register is one small memory cell inside the chip that firmware writes to set up a block or reads '
                   'to see its state. Its page shows its address, which block it belongs to, and its bit fields.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', register: str = '', peripheral: str = '', addr: str = '',
                 addr_mem: str = '', space: str = '', width_bytes: int = 1, reset_value: str = '', description: str = '',
                 fields_refs_json: str = '[]', document: str = '', page_table: str = '', url: str = '', origin: str = '',
                 undetermined: str = '', notes: str = '', manager=None):
        self.name = name                    # '<soc>:<REGISTER>' (atmega328p:EICRA)
        self.soc = soc
        self.register = register            # EICRA
        self.peripheral = peripheral        # the Peripheral row name ('<soc>:EXINT')
        self.addr = addr                    # the address avr-libc defines ('0x69' mem, '0x1D' io)
        self.addr_mem = addr_mem            # the data-space address when the io one is given ('0x3D'), else ''
        self.space = space                  # io | mem
        self.width_bytes = width_bytes      # 1 | 2
        self.reset_value = reset_value      # '0x00' when the datasheet's Initial Value line is cited, else ''
        self.description = description      # the datasheet's register title ("External Interrupt Control Register A")
        self.fields_refs_json = fields_refs_json  # ["RegisterField:<soc>:<REG>.<FIELD>", …] — reverse link
        self.document = document            # the datasheet (when a register description is cited)
        self.page_table = page_table        # "§13.2.1, p.80"
        self.url = url
        self.origin = origin                # derived:registers_<mcu>.json sha=… avr-libc=…
        self.undetermined = undetermined    # 'bit fields not captured yet' for registers without RegisterField rows
        self.notes = notes
