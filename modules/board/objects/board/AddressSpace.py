"""
@module board.objects.board.AddressSpace

AddressSpace — one class per file (design §7); ucd-0b2a, UNO_CORE_DEMO_PLAN.md §5h B3/D-ucd-9.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class AddressSpace(treeObject):
    """What it is: ONE WAY A SoC's CPU ADDRESSES ITS REGISTERS — the AVR has TWO: `io` (IN/OUT, SBI/CBI/SBIS/SBIC,
    0x00-0x3F) and `data` (LD/ST/LDS/STS/LDD/STD, the SAME I/O registers seen at +0x20, plus the extended I/O space
    0x60-0xFF that has NO io alias at all). CITED: Microchip DS40002061B §8.5 "I/O Memory", p.30 ("When using the I/O
    specific commands IN and OUT, the I/O addresses 0x00 - 0x3F must be used. When addressing I/O Registers as data
    space using LD and ST instructions, 0x20 must be added to these addresses ... For the Extended I/O space from
    0x60 - 0xFF in SRAM, only the ST/STS/STD and LD/LDS/LDD instructions can be used"). Two rows per SoC today
    ('<soc>:io', '<soc>:data'); `RegisterAddressMapping` names which space(s) reach which register.
    Related concepts: `RegisterAddressMapping`, `Register` (addr/addr_mem/space), `MemoryRegion`.
    """

    plain_words = ('An address space is one way the chip\'s instructions reach a register — the AVR has two, a '
                   'short I/O one (IN/OUT) and a longer data one (LD/ST) that also sees the I/O registers, offset.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', space: str = '', title: str = '', access_instructions: str = '',
                 range_lo: str = '', range_hi: str = '', offset_from_io: str = '', description: str = '',
                 document: str = '', page_table: str = '', url: str = '', origin: str = '', undetermined: str = '',
                 notes: str = '', manager=None):
        self.name = name                        # '<soc>:io' | '<soc>:data'
        self.soc = soc
        self.space = space                      # io | data
        self.title = title                      # 'I/O space' | 'Data space'
        self.access_instructions = access_instructions  # the instruction family this space is reached by
        self.range_lo = range_lo                # the lowest address a register of this space carries, hex
        self.range_hi = range_hi                # the highest, hex
        self.offset_from_io = offset_from_io    # '0x20' for data (the io-register alias offset), '' for io
        self.description = description
        self.document = document
        self.page_table = page_table
        self.url = url
        self.origin = origin
        self.undetermined = undetermined
        self.notes = notes
