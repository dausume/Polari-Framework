"""
@module board.objects.board.SocPin

SocPin — one class per file (design §7); brd-bo, THE BOARD OBJECT.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SocPin(treeObject):
    """What it is: One pin of a SoC (§2b SoC layer): its port/bit, the package pin, and its alternate functions verbatim from the
    datasheet table (or the upstream pinctrl header) — the land pattern and the Zephyr pinctrl cite the same fact.
    Related concepts: `SocDefinition`, `BoardPin.soc_pin` (where a board wires it).
    """

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', pin: str = '', port: str = '', bit: int = 0,
                 package_pin: str = '', functions_json: str = '[]', default_function: str = '', fact: str = '',
                 notes: str = '', manager=None):
        self.name = name  # '<soc>:<pin>'
        self.soc = soc
        self.pin = pin  # PD6 | GPIO21
        self.port = port  # B | C | D | GPIO
        self.bit = bit
        self.package_pin = package_pin  # the package's pin number (28-SPDIP: '12')
        self.functions_json = functions_json  # alternate functions, datasheet order
        self.default_function = default_function  # after reset / boot
        self.fact = fact  # the DatasheetFact name
        self.notes = notes
