"""
@module board.objects.board.ProgrammerKind

ProgrammerKind — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ProgrammerKind(treeObject):
    """What it is: HOW a device is flashed (plan §7a): programmer kind -> the engine that does it -> the adapter kind it
    needs (if any) -> the exact DRY-RUN argv template (the installer prints it before any real run; a real run needs
    the device present AND an explicit confirm). Flashing always runs on the host holding the USB port.
    Related concepts: `BoardDefinition.programmer`, `AdapterDefinition`, board.custom.board_engines (resolution).
    """

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', engine: str = '', engine_kind: str = '',
                 adapter_kind: str = '', host_side: str = 'usb', dry_run_template: str = '',
                 placement: str = 'usb-host', needs_confirm: bool = True, licence: str = '', citation: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.title = title
        self.engine = engine  # engine name (board_engines.ENGINES)
        self.engine_kind = engine_kind  # flasher | c-compiler | hdl-toolchain (RULE 2)
        self.adapter_kind = adapter_kind  # '' = none needed
        self.host_side = host_side  # RULE 1: the Polari host side
        self.dry_run_template = dry_run_template  # argv with {placeholders}
        self.placement = placement  # usb-host = the machine holding the port (a remote worker is refused)
        self.needs_confirm = needs_confirm
        self.licence = licence
        self.citation = citation
        self.notes = notes
