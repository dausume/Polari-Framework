"""
@module board.objects.board.BoardDefinition

BoardDefinition — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardDefinition(treeObject):
    """What it is: One device MODEL the board arc tracks — one row per register §1 entry (plan §2, §8a).
    A row is NOT a simulation: `simulated` is true only for a picked device (the UNO first). Register cells are
    copied verbatim; a register `?` stays empty and the notes say which column was unknown.
    Related concepts: `Road` (what is done / still to do for this device), `ProgrammerKind` (how it is flashed),
    `AdapterDefinition` (a USB adapter that closes the RULE 1 gap), `DatasheetFact` (cited numbers),
    `BoardSimCost` (the cost of its twin, measured before another twin is admitted), `BoardInstance` (one plugged in).
    RULE 1 (refined): reachable from the Polari host over USB, directly or through a known USB adapter —
    `usb_rule` is ok | undetermined | not-a-target, never guessed. RULE 2: `toolchain_engines` name only C or
    Verilog/SystemVerilog toolchains and flashers.
    brd-bo: the IDENTITY layer of THE BOARD OBJECT (PCB_FROM_SCRATCH_PLAN §2b) — the pin assignment and the other layers
    reference this row by name; `pol board pins <board>` shows them.
    """

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', register_id: str = '', device_class: str = '',
                 kind: str = '', register_status: str = '', soc: str = '', isa: str = '', mmu: str = '',
                 flash_sram: str = '', flash_kb: int = 0, ram_kb: int = 0, usb_ids_json: str = '[]',
                 by_id_hints_json: str = '[]', usb_route: str = '', programmer: str = '', adapter_needed: str = '',
                 adapter_ids_json: str = '[]', usb_rule: str = 'undetermined', usb_rule_citation: str = '',
                 toolchain_engines_json: str = '[]', transport: str = '', twin: str = '', simulated: bool = False,
                 core_rtl_open: str = '', board_design_open: str = '', silicon_origin: str = '',
                 board_origin: str = '', tiers_proven: str = '', radios: str = '', power_bms: str = '',
                 polari_role: str = '', relied_on: str = '', cost_measured: str = '', licence_notes: str = '',
                 designer: str = 'others', road: str = '', road_status: str = 'todo', notes: str = '',
                 soc_definition: str = '', revision: str = '', upstream_board: str = '',
                 datasheets_json: str = '{}', manager=None):
        self.name = name  # the register id (kebab-case)
        self.title = title
        self.register_id = register_id  # the register row key, verbatim
        self.device_class = device_class  # the register's class column (MCU-S, SoC-Linux, FPGA, radio-module, ...)
        self.kind = kind  # mcu | linux-soc-fpga | soc-linux | fpga | radio-module | peripheral
        self.register_status = register_status  # his decision state, verbatim (HIS PICK / advised / candidate ...)
        self.soc = soc  # the chip
        self.isa = isa
        self.mmu = mmu
        self.flash_sram = flash_sram  # verbatim (often nominal/unverified)
        self.flash_kb = flash_kb  # typed only when cited by a DatasheetFact (0 = not cited yet)
        self.ram_kb = ram_kb  # as flash_kb
        self.usb_ids_json = usb_ids_json  # JSON list of "vvvv:pppp", one per mode the board shows; [] = not in the register
        self.by_id_hints_json = by_id_hints_json  # JSON list of /dev/serial/by-id substrings that identify it when sysfs cannot
        self.usb_route = usb_route  # the register's USB programming cell, verbatim
        self.programmer = programmer  # a ProgrammerKind name ('' = the adapter's engine drives it, or undetermined)
        self.adapter_needed = adapter_needed  # the register's adapter cell, verbatim
        self.adapter_ids_json = adapter_ids_json  # the AdapterDefinition names its chain may use
        self.usb_rule = usb_rule  # ok | undetermined | not-a-target
        self.usb_rule_citation = usb_rule_citation  # why, in one line
        self.toolchain_engines_json = toolchain_engines_json  # engine names for the ladder (board.custom.board_engines)
        self.transport = transport  # usb-cdc-serial | usb-network+ssh | (empty until known)
        self.twin = twin  # renode:<platform> | simavr:<mcu> | verilator | (empty)
        self.simulated = simulated  # picked for simulation (plan §8a)
        self.core_rtl_open = core_rtl_open
        self.board_design_open = board_design_open
        self.silicon_origin = silicon_origin
        self.board_origin = board_origin
        self.tiers_proven = tiers_proven
        self.radios = radios
        self.power_bms = power_bms
        self.polari_role = polari_role
        self.relied_on = relied_on  # relied-on resources, verbatim
        self.cost_measured = cost_measured
        self.licence_notes = licence_notes
        self.designer = designer  # 'others' until our own boards (plan §8a)
        self.road = road  # the Road row name
        self.road_status = road_status  # mirror of the Road's status for the table
        self.notes = notes  # register notes, verbatim, + which columns were ? in the register
        # brd-bo (THE BOARD OBJECT, PCB_FROM_SCRATCH_PLAN §2b): this row IS the Identity layer — no second board class.
        # The other layers hang on it by name: SocDefinition (soc_definition), BoardHardware / BoardNet / Connector /
        # ConnectorPin, BoardPin (the pin assignment), RuntimeProfile, BoardView / BoardConflict.
        self.soc_definition = soc_definition  # the SocDefinition row ('' = not modelled yet)
        self.revision = revision  # the board revision the pin rows describe (R3, DevKitM …)
        self.upstream_board = upstream_board  # an upstream board the rows were ingested from (zephyr:esp32c3_devkitm@v4.4.2)
        # ucd-doc: {"soc": slug|"", "board": slug|"", "programming": slug|"", "combined": slug|""} — which Datasheet row
        # covers each of the three kinds for THIS board (board.custom.datasheets.board_coverage), '' = missing, named
        self.datasheets_json = datasheets_json
