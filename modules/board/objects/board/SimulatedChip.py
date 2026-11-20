"""
@module board.objects.board.SimulatedChip

SimulatedChip — one class per file (design §7). pt-1a (PIN_TWIN_PLAN.md §2a, layer 3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SimulatedChip(treeObject):
    """What it is: ONE CHIP AS ONE SIMULATED DEVICE - a SocDefinition plus the simulator that carries its CPU and the blocks it models itself
    (the C3: Espressif's QEMU fork, `-machine esp32c3`; a custom chip: a plain RISC-V machine). Its SimOverlay rows say, block by block, who models
    what; together they export as one device layout (board.custom.sim_layout) that the generic `polari-block` QEMU device loads, so the firmware
    sees one chip. Code-owned: board.custom.sim_bindings.SIMULATED_CHIPS (seeded, converged).
    Related concepts: `SocDefinition`, `SimOverlay`, `BlockBehaviour`.
    """

    plain_words = ('A chip as the simulator runs it: which simulator carries the processor and its own parts, and which parts Polari adds on top '
                   'so the whole thing behaves like the real chip.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', simulator: str = '', machine: str = '', engine: str = '', notes: str = '', basis: str = '',
                 manager=None):
        self.name = name                    # esp32c3-qemu
        self.soc = soc                      # SocDefinition name (esp32c3)
        self.simulator = simulator          # qemu:esp32c3 | qemu:virt (a custom chip)
        self.machine = machine              # the simulator's machine argument (-machine esp32c3)
        self.engine = engine                # the board engine that runs it (c3-run)
        self.notes = notes
        self.basis = basis
