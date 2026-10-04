"""
@module board.objects.board.SocDefinition

SocDefinition — one class per file (design §7); brd-bo, THE BOARD OBJECT.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SocDefinition(treeObject):
    """What it is: The SoC layer of THE BOARD OBJECT (PCB_FROM_SCRATCH_PLAN §2b): one chip, shared by every board that carries it —
    package, ISA, clocks, memory map, peripherals. Every number is a `DatasheetFact` (named in facts_json) or an ingested
    upstream file line (derive-or-cite); what could not be derived is said in `undetermined`.
    Related concepts: `SocPin` (its pins + alternate functions), `BoardDefinition.soc_definition` (the boards using it).
    """

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', vendor: str = '', package: str = '', isa: str = '',
                 cpu_clock_hz: int = 0, memory_map_json: str = '[]', peripherals_json: str = '[]',
                 clocks_json: str = '[]', pin_count: int = 0, facts_json: str = '[]', source: str = '',
                 zephyr_soc: str = '', vendor_target: str = '', undetermined: str = '', notes: str = '', manager=None):
        self.name = name  # the SoC key (kebab-case, e.g. atmega328p, esp32c3)
        self.title = title
        self.vendor = vendor
        self.package = package  # the package the board uses (28-SPDIP, QFN32 in a module …)
        self.isa = isa
        self.cpu_clock_hz = cpu_clock_hz  # the upstream / datasheet clock; the board clock is BoardHardware.crystal
        self.memory_map_json = memory_map_json  # [{region, start, size, fact}]
        self.peripherals_json = peripherals_json  # [{name, kind, reg, fact}]
        self.clocks_json = clocks_json  # [{name, hz, fact}]
        self.pin_count = pin_count  # I/O pins in the SocPin table
        self.facts_json = facts_json  # DatasheetFact names behind the fields
        self.source = source  # datasheet | zephyr-ingest:<tag> + datasheet
        self.zephyr_soc = zephyr_soc  # Zephyr's SoC name (board.yml socs) or '' when Zephyr has none
        self.vendor_target = vendor_target  # avr-gcc -mmcu / IDF_TARGET
        self.undetermined = undetermined  # what the sources did not give, said
        self.notes = notes
