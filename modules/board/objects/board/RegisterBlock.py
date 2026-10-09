"""
@module board.objects.board.RegisterBlock

RegisterBlock — one class per file (design §7); ucd-0b2a, UNO_CORE_DEMO_PLAN.md §5h B3/D-ucd-9.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RegisterBlock(treeObject):
    """What it is: the datasheet's OWN register-summary GROUPING of one peripheral's registers, as its own row (the
    review's RegisterBlock — `Register.peripheral` already named the grouping; this row makes it addressable and
    gives it a reverse list). One block per Peripheral today (`board.custom.registers.PERIPHERAL_RULES` / datasheet
    chapter §36 register summary); `registers_refs_json` is the reverse link from every Register whose `peripheral`
    names this block's own peripheral. `shared_with_refs_json` names OTHER Peripheral rows that configure THROUGH
    this block's registers — e.g. the CPU block's MCUCR.PUD (Pull-up Disable) configures every GPIO port's pull-ups,
    cited DS40002061B §14.4.1 MCUCR, p.100 ("...even if the DDxn and PORTxn Registers are configured to enable
    them"); nothing else is guessed shared.
    Related concepts: `Peripheral`, `Register`, `RegisterField`.
    """

    plain_words = ('A register block is the chip\'s own grouping of the registers that belong to one functional '
                   'block — most blocks are theirs alone; a few (like the pull-up disable bit) are shared by others.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', peripheral: str = '', title: str = '',
                 registers_refs_json: str = '[]', shared_with_refs_json: str = '[]', origin: str = '',
                 undetermined: str = '', notes: str = '', manager=None):
        self.name = name                        # '<soc>:<peripheral>-block'
        self.soc = soc
        self.peripheral = peripheral            # the Peripheral row name this block belongs to ('<soc>:<peripheral>')
        self.title = title                      # the peripheral's own title, reused
        self.registers_refs_json = registers_refs_json      # ["Register:<soc>:<REG>", …] — reverse link
        self.shared_with_refs_json = shared_with_refs_json  # ["Peripheral:<soc>:<id>", …] — other peripherals configured through this block
        self.origin = origin                    # derived: one block per peripheral = the datasheet's register-summary grouping
        self.undetermined = undetermined
        self.notes = notes
