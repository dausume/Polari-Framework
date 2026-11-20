"""
@module board.objects.board.BlockBehaviour

BlockBehaviour — one class per file (design §7). pt-1a (PIN_TWIN_PLAN.md §2a, layer 2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BlockBehaviour(treeObject):
    """What it is: ONE KIND of peripheral behaviour a simulator can run from data - `pinbank` first (pads, output / enable / input, pulls, pad
    function, the output route, open drain, pin interrupts). Written once per kind, never per chip. It names the HAL roles it needs (bound per chip
    in hal.custom.soc_rules RULES[soc]['roles'], the same binding the firmware generator reads, so the two can never disagree about a bit) and the
    rules it follows in words. Code-owned: board.custom.sim_bindings.BLOCK_BEHAVIOURS (seeded, converged).
    Related concepts: `SimOverlay.behaviour`, `SimulatedChip`.
    """

    plain_words = ('What a part of a chip does when it is simulated, written once for every chip that has that kind of part: for the pins, how a pin '
                   'ends up high, low or floating from what the program wrote. Each chip says which of its register bits play each part.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', roles_json: str = '{}', rules: str = '', basis: str = '', manager=None):
        self.name = name                    # pinbank
        self.title = title
        self.roles_json = roles_json        # {"modelled": [role ...], "values": [role ...]}: modelled roles resolve to fields inside the overlay's spans,
                                            # value roles to a cited value only (C3 interrupt_source = 16, its register is the vendor's)
        self.rules = rules                  # the behaviour's rules in words (the pin-level rule)
        self.basis = basis
