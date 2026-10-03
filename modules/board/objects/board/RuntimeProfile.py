"""
@module board.objects.board.RuntimeProfile

RuntimeProfile — one class per file (design §7); brd-bo, THE BOARD OBJECT.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RuntimeProfile(treeObject):
    """What it is: The RuntimeProfile layer (§2b): one row per board × `firmware_runtime` (bare-c | freertos | esp-idf | zephyr) —
    the peripherals enabled, clocks, console UART, stack/heap, the twin, the Kconfig / sdkconfig lines it owns — or a
    REFUSAL with its reason (supported false), never a silent gap.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', runtime: str = '', supported: bool = False, refusal: str = '',
                 peripherals_json: str = '[]', clock_hz: int = 0, tick_hz: int = 0, console_uart: str = '',
                 stack_bytes: int = 0, heap_bytes: int = 0, config_json: str = '[]', twin: str = '', origin: str = '',
                 notes: str = '', manager=None):
        self.name = name  # '<board>:<runtime>'
        self.board = board
        self.runtime = runtime  # bare-c | freertos | esp-idf | zephyr
        self.supported = supported
        self.refusal = refusal  # why not, when supported is false
        self.peripherals_json = peripherals_json  # the peripherals this runtime enables (status okay)
        self.clock_hz = clock_hz  # the CPU clock it runs at
        self.tick_hz = tick_hz  # the kernel tick (0 = no kernel)
        self.console_uart = console_uart  # the console device ('none' = none)
        self.stack_bytes = stack_bytes  # 0 = the runtime default (said in notes)
        self.heap_bytes = heap_bytes
        self.config_json = config_json  # Kconfig / sdkconfig lines this profile owns
        self.twin = twin  # the twin engine
        self.origin = origin
        self.notes = notes
