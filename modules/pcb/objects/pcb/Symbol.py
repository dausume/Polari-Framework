"""
@module pcb.objects.pcb.Symbol

Symbol — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Symbol(treeObject):
    """What it is: A schematic SYMBOL by KiCad library reference (plan §2): `Device:R`, `Sensor_Temperature:LM35-LP` — the
    library nickname + symbol name, where the library came from (kicad-official | project | ours), the library's version and
    the sha256 of the library FILE it was read from, its licence, and its pins. Official KiCad libraries are CC-BY-SA-4.0
    with the design exception (https://www.kicad.org/libraries/license/: the holder "waives article 3 of the license with
    respect to these designs and any generated files").
    """

    @treeObjectInit
    def __init__(self, name: str = '', lib: str = '', symbol: str = '', source: str = '', lib_version: str = '',
                 lib_sha256: str = '', licence: str = '', pin_count: int = 0, pins_json: str = '[]', description: str = '',
                 notes: str = '', manager=None):
        self.name = name  # lib:symbol
        self.lib = lib  # library nickname
        self.symbol = symbol  # symbol name
        self.source = source  # kicad-official | project | ours
        self.lib_version = lib_version  # kicad-symbols 9.0.2-1 | the project's file
        self.lib_sha256 = lib_sha256  # sha256 of the .kicad_sym file it came from
        self.licence = licence
        self.pin_count = pin_count
        self.pins_json = pins_json  # [{number, name, type}]
        self.description = description
        self.notes = notes
