"""
@module board.objects.board.MemoryRegion

MemoryRegion — one class per file (design §7); ucd-0b2a, UNO_CORE_DEMO_PLAN.md §5h B3/D-ucd-9.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MemoryRegion(treeObject):
    """What it is: ONE OF THE SoC's THREE MEMORIES (flash, sram, eeprom) as its own row — `SocDefinition.
    memory_map_json` already carries this as a JSON column (board.custom.soc_atmega328p.soc_definition()); this row
    makes it a page a person can open and a ref another row can point at. `address_space` names the AddressSpace
    row this region is addressed through when it has one (sram is reached through the SAME data space LD/ST/LDS/
    STS/LDD/STD the I/O registers alias into); flash and eeprom have NEITHER an io NOR a data address — flash is
    program memory (fetched by the instruction unit, §8.1), eeprom is addressed through its own EEAR/EEDR register
    pair (§8.4), never through LD/ST — `address_space` stays '' for both, said so in `undetermined` rather than
    guessed. `fact` names the cited `DatasheetFact` row the size/range comes from.
    Related concepts: `AddressSpace`, `SocDefinition`, `DatasheetFact`.
    """

    plain_words = ('A memory region is one of the chip\'s three memories — program (flash), working (sram) or '
                   'non-volatile (eeprom) — with its address range and size, cited.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', region: str = '', start: str = '', size: int = 0,
                 address_space: str = '', fact: str = '', origin: str = '', undetermined: str = '', notes: str = '',
                 manager=None):
        self.name = name                # '<soc>:flash' | '<soc>:sram' | '<soc>:eeprom'
        self.soc = soc
        self.region = region            # flash | sram | eeprom
        self.start = start              # hex
        self.size = size                # bytes
        self.address_space = address_space  # the AddressSpace row name ('<soc>:data' for sram), '' for flash/eeprom
        self.fact = fact                # the DatasheetFact row naming the cited size/range
        self.origin = origin
        self.undetermined = undetermined  # why address_space is '' (flash: program memory; eeprom: EEAR/EEDR, not LD/ST)
        self.notes = notes
