"""
@module board.objects.board.RegisterAddressMapping

RegisterAddressMapping — one class per file (design §7); ucd-0b2a, UNO_CORE_DEMO_PLAN.md §5h B3/D-ucd-9.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RegisterAddressMapping(treeObject):
    """What it is: ONE REGISTER REACHABLE THROUGH ONE ADDRESS SPACE, as its own row — the alias `Register.addr`/
    `addr_mem` used to carry as two columns is now TWO ROWS (an io-space register gets BOTH an io mapping and a
    data mapping at io+0x20, per the datasheet's own dual-print, e.g. "EIMSK 0x1D (0x3D)"; a mem-space register
    (the extended I/O, 0x60-0xFF) gets ONE data mapping only — it has no io alias, never invented). DERIVED from the
    register snapshot (board.custom.registers, the committed `registers_<mcu>.json`) + the io+0x20 rule CITED to
    Microchip DS40002061B §8.5, p.30. `register`/`address_space` are plain row names (not Class:name refs — the
    object page's own convention for forward columns); `Register.mappings_refs_json` is the reverse link.
    Related concepts: `Register`, `AddressSpace`.
    """

    plain_words = ('A register address mapping says: this register, reached through THIS address space, lives at '
                   'THIS address — one row per register per space it can be reached from.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', register: str = '', address_space: str = '', address: str = '',
                 how: str = '', origin: str = '', undetermined: str = '', notes: str = '', manager=None):
        self.name = name                # '<soc>:<REG>@io' | '<soc>:<REG>@data'
        self.soc = soc
        self.register = register        # the Register row name ('<soc>:<REG>')
        self.address_space = address_space  # the AddressSpace row name ('<soc>:io' | '<soc>:data')
        self.address = address          # hex, as this space addresses it
        self.how = how                  # the instruction family this mapping is reached by
        self.origin = origin            # derived:registers_<mcu>.json sha=… (+ "io+0x20 per §8.5 p.30" for the derived data alias)
        self.undetermined = undetermined
        self.notes = notes
