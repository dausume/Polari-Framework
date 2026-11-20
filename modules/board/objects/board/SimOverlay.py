"""
@module board.objects.board.SimOverlay

SimOverlay — one class per file (design §7). pt-1a (PIN_TWIN_PLAN.md §2a, layer 3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SimOverlay(treeObject):
    """What it is: WHO MODELS ONE ADDRESS SPAN of a simulated chip. `vendor` = the simulator's own model, untouched; `overlay` = ours, mapped
    over the vendor's span at a higher priority - only the registers we model are mapped, so every other offset falls through to the vendor
    model unchanged (the C3's GPIO_STRAP still answers from Espressif's code); `native` = ours alone (a custom chip's blocks). Spans with the same
    `device` form one instance of their `behaviour` (the C3's GPIO and IO_MUX spans are one pinbank). Each row gives its span, the reason and the
    evidence that proved it. Code-owned: board.custom.sim_bindings.SIM_OVERLAYS (seeded, converged).
    Related concepts: `SimulatedChip.name` (chip), `Peripheral`, `BlockBehaviour` (behaviour), `Register` (selected by address inside the span).
    """

    plain_words = ('For one part of a simulated chip: does the simulator\'s own model answer, does Polari\'s model sit on top of it, or is it '
                   'Polari\'s alone - and why.')

    @treeObjectInit
    def __init__(self, name: str = '', chip: str = '', peripheral: str = '', mode: str = 'vendor', behaviour: str = '', device: str = '',
                 base: str = '', size: str = '', params_json: str = '{}', why: str = '', evidence: str = '', manager=None):
        self.name = name                    # esp32c3-qemu:GPIO
        self.chip = chip                    # SimulatedChip name
        self.peripheral = peripheral        # Peripheral name (esp32c3:GPIO)
        self.mode = mode                    # vendor | overlay | native
        self.behaviour = behaviour          # BlockBehaviour name ('' for vendor)
        self.device = device                # spans with the same device are one behaviour instance ('pins')
        self.base = base                    # '0x60004000'
        self.size = size                    # '0x1000'
        self.params_json = params_json      # {"pins": 22, "leave_to_vendor": ["GPIO_STRAP_REG"]}
        self.why = why
        self.evidence = evidence
