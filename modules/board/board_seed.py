"""
@module board.board_seed

THE REGISTER AS ROWS (plan §8a: track all, simulate few). Every register §1 device → a BoardDefinition + its Road;
every §1a adapter → an AdapterDefinition; the ProgrammerKinds; the UNO's DatasheetFacts (the only device with facts
in brd-0; brd-bo: + THE BOARD OBJECT's layers — SoCs, pins, nets, connectors, runtime profiles). BoardInstance / FirmwareBuild / InstallPlan / InstallRecord / UnoAnalogState are never seeded (observed / built);
brd-fi seeds the four UNO FirmwareVariants (sc-3: + the six ESP32-C3 ones, custom/variants_c3.py); BoardSimCost carries the
committed measurements (brd-1: the UNO twin, custom/sim_cost_uno.json; sc-3: the C3's QEMU twin, custom/sim_cost_c3.json).
The 'board-roads' tech tree (one concept node per device) is seeded only when techtree is present.
"""
from board.board_basis import (BoardDefinition, BoardInstance, FirmwareBuild, ProgrammerKind, AdapterDefinition, DatasheetFact, BoardSimCost, Road,
                               FirmwareVariant, InstallPlan, InstallRecord, UnoAnalogState, SocDefinition, SocPin, BoardHardware, BoardNet,
                               Connector, ConnectorPin, BoardPin, RuntimeProfile, BoardConflict, BoardView, TargetCompatibilityRule, KitPart, ChipLadderEntry, Bench,
                               Datasheet)   # ucd-doc: datasheets as documents
from board.board_basis import (PackageDefinition, PackageContact, UsbInterfaceDefinition, BoardComponent, ElectricalCharacteristic, PinGroupBudget,
                               PinLifecycleConstraint)   # fgm-2: the UNO hardware truth
from board.board_basis import EnclosureKind, HardwareEnclosure, EnclosureContact   # hsp-0: enclosures + exposure maps
from board.board_basis import HardwareSolution, SystemLink, SignalPath   # hsp-1: Hardware Solution, links, signal paths
from board.board_basis import ConfigurationEvent   # pv-4
from board.board_basis import TwinSession, BenchInteraction   # sim-1; sim-3
from board.board_basis import SimInstallConfirmation   # ins-1
from board.board_basis import FirmwareStateObject, FirmwareStateField   # fst-0
from board.board_basis import BoardFoothold, BenchConnection, PartBoard, EsdProtectionArea, ProtectionPart   # bob-0, bob-2, drv-0, esd-0, esd-3
from board.board_basis import BenchSolution, BenchConditions, HardwareSystem, ThermalSystem, ThermalMitigation, ThermalSolution, BenchSystem   # cfg-0, bss-0
from board.board_basis import ClockSource, ClockPeer   # cfg-1
from board.board_basis import ButtonClockState, ButtonClockEvent, LightState   # ucd-0e1: the wire contract's two new classes
from board.custom.register_map import board_rows, adapter_rows, road_rows, tech_tree_rows
from board.board_basis import (Peripheral, PeripheralSignal, PinFunction, SignalRoute, Register, RegisterField, RegisterSetting,
                               RegisterFieldSetting, BoardPinNet, RegisterAccessKind)   # ucd-0a: the hardware chain (+ rm-2a the access vocabulary)
from board.board_basis import AddressSpace, RegisterAddressMapping, RegisterBlock, MemoryRegion   # ucd-0b2a: address space as rows
from board.custom.programmers import SEED_PROGRAMMER_KINDS
from board.custom.uno_facts import SEED_UNO_FACTS
from board.custom.sim_cost import SEED_BOARD_SIM_COSTS
from board.custom.variants import SEED_FIRMWARE_VARIANTS
from board.custom.variants_c3 import SEED_C3_VARIANTS
from board.custom.sim_cost_c3 import SEED_C3_SIM_COSTS
from board.custom import board_object_seed
from board.custom import target_compat as TC
from board.custom import kit_parts as KP
from board.custom.chip_ladder_seed import SEED_CHIP_LADDER   # chp-0
from board.custom.part_boards import SEED as SEED_PART_BOARDS   # drv-0: the cited driver catalogue
from board.custom.protection_parts import SEED as SEED_PROTECTION_PARTS   # esd-3: the cited protection catalogue
from board.custom.bench_seed import SEED_BENCHES   # bench-0 (its breadboard models moved to electrodevice BoardModel, D-bob-3)
from board.custom import board_pin_nets as BPN
from board.custom import register_access as RACC   # rm-2a

SEED_BOARD_DEFINITIONS = board_rows()
for _b in SEED_BOARD_DEFINITIONS:   # brd-bo: the Identity layer gains the board object's links (soc, revision, upstream board)
    _b.update(board_object_seed.IDENTITY.get(_b['name'], {}))
#: brd-bo: THE BOARD OBJECT's layers (custom/board_object_seed.py — the UNO cited, the C3 ingested from Zephyr upstream).
#: ucd-doc: build() ALSO resolves THE DATASHEETS (board.custom.datasheets) from every DatasheetFact/RegisterField this
#: produces plus uno_facts.SEED_UNO_FACTS, mutating each in place with its own `datasheet` slug, and sets each board
#: definition's own `datasheets_json` — all BEFORE _register_owned() wraps these lists below, so every resolved field
#: converges with everything else code-owned.
SEED_BOARD_OBJECT = board_object_seed.build(SEED_BOARD_DEFINITIONS)
SEED_DATASHEETS = SEED_BOARD_OBJECT['Datasheet']
SEED_ADAPTER_DEFINITIONS = adapter_rows()
SEED_BOARD_ROADS = road_rows(SEED_BOARD_DEFINITIONS)
SEED_BOARD_TECH_TREES, SEED_BOARD_TECH_NODES = tech_tree_rows(SEED_BOARD_DEFINITIONS)


def _register_owned(rows, keep=()):
    """Register-derived fields are code-owned (re-import the register, the rows follow); `keep` stays as the instance has it."""
    return [dict(r, _converge=[k for k in r if k != 'name' and k not in keep]) for r in rows]


# bss-8 (BENCH_SOLUTION_SIM_PLAN.md section 7): the UNO light bench as rows. The Systems are templates (choices open); the Bench Solutions bind one firmware
# variant each - the button route differs (D2 external interrupt / D4 pin-change interrupt / a voltage on A0), the states are the same (the topology spec).
# The Firmware Solution of the two route variants is the VARIANT NAME standing in for a FirmwareSolution row (cfg-1 makes the configuration drive the build).
SEED_BENCH_CONDITIONS = [{'name': 'room', 'title': 'a room, open air', 'air': 'open', 'ambient_min_c': 18.0, 'ambient_max_c': 30.0, 'supply_v': 5.0, 'aging_years': 0.0,
                          'notes': 'the desk: open air, USB 5 V, new parts'}]
SEED_HARDWARE_SYSTEMS = [{'name': 'uno-class-led', 'title': 'an UNO-class board, one LED, one pushbutton', 'boards': 'arduino-uno-r3',
                          'circuit': 'LED + series resistor from one digital pin to GND; a pushbutton to GND on an input with the pull-up; optionally the LED line jumpered back to a sense pin',
                          'notes': 'the family of the light test: the pin numbers, the button route and the LED route are the Solution\'s choices'}]
SEED_THERMAL_SYSTEMS = [{'name': 'open-air-desk', 'title': 'open air on a desk', 'air': 'open', 'mitigations_allowed': 'none,sink,fan', 'ambient_min_c': 15.0, 'ambient_max_c': 35.0,
                         'notes': 'a clip-on sink and a breadboard fan are allowed; nothing is required'}]
SEED_THERMAL_SOLUTIONS = [{'name': 'uno-light-bare', 'title': 'open air, nothing added', 'system': 'open-air-desk', 'mitigations': '', 'notes': 'the light test needs no mitigation'}]
SEED_BENCH_SYSTEMS = [{'name': 'uno-light-bench', 'title': 'UNO light bench', 'hardware_system': 'uno-class-led', 'firmware_system': 'uno-light-graph', 'thermal_system': 'open-air-desk',
                       'notes': 'the topology spec cmod custom/topologies/uno-light-bench.json applies to every Bench Solution of this System: the same states, every route'}]
# cfg-1 (CATOM_CONFIG_PLAN.md "The clock group in detail"): the clock sources, as board.custom.timing_drift cites them, as rows (timing_drift reads the rows
# when a server has them; CLOCKS stays the seed), and the far ends of the UNO's serial link
from board.custom.timing_drift import CLOCKS as _CLOCKS   # noqa: E402
_CLOCK_KIND = {'cstce16m0v53-r0': ('resonator', 'arduino-uno-r3'), 'atmega328p-rc-user': ('rc', ''), 'atmega328p-rc-factory': ('rc', '')}
SEED_CLOCK_SOURCES = [dict(name=n, kind=_CLOCK_KIND.get(n, ('crystal', ''))[0], boards=_CLOCK_KIND.get(n, ('', ''))[1], f_hz=c['f_hz'], initial_pct=c['initial_pct'],
                           temp_pct=c['temp_pct'], t_min_c=c['t_min_c'], t_max_c=c['t_max_c'], aging_pct=c['aging_pct'], what=c['what'], source=c['source'], notes='')
                      for n, c in sorted(_CLOCKS.items())]
SEED_CLOCK_PEERS = [
    {'name': 'uno-16u2-usbserial', 'title': 'the UNO R3\'s ATmega16U2 running arduino-usbserial', 'kind': 'usb-serial-chip', 'boards': 'arduino-uno-r3', 'clock': '',
     'f_hz': 16e6, 'divisor_rule': 'arduino-usbserial', 'error_pct': 0.0,
     'undetermined': 'its 16 MHz crystal\'s tolerance (Y1 with C9 / C11 22 pF and R1 1M, board.custom.uno_schematic_paths; no part number on the schematic): 0 % until read',
     'source': 'Arduino-usbserial.c USART1 setup (U2X1 = 1, UBRR1 = SERIAL_2X_UBBRVAL(baud); 57600 in normal mode) - board.custom.clock_skew_run.peer_divisor; the UNO R3 schematic',
     'notes': 'the peer of USART0 on every UNO R3 variant: the host sees what this chip latches'},
    {'name': 'exact', 'title': 'an ideal peer (no clock error, the same divisor)', 'kind': 'exact', 'boards': '', 'clock': '', 'f_hz': 0.0, 'divisor_rule': 'exact', 'error_pct': 0.0,
     'undetermined': '', 'source': 'a knob: the far end taken as perfect, to see the chip\'s own share of the error alone', 'notes': ''},
]
SEED_BENCH_SOLUTIONS = [
    {'name': 'uno-light-on-desk', 'title': 'UNO light on the desk: the button on D2 (external interrupt)', 'system': 'uno-light-bench', 'bench': 'home-bench',
     'hardware_solution': 'uno-light-system', 'firmware_solution': 'uno-light', 'thermal_solution': 'uno-light-bare', 'conditions': 'room',
     'notes': 'the sample bench: the Firmware Solution uno-light (its graph builds the unsensed light; the variant uno-light carries the sense jumper D6 -> D3)'},
    {'name': 'uno-light-pcint-on-desk', 'title': 'UNO light on the desk: the button on D4 (pin-change interrupt)', 'system': 'uno-light-bench', 'bench': 'home-bench',
     'hardware_solution': 'uno-light-system', 'firmware_solution': 'uno-light-pcint', 'thermal_solution': 'uno-light-bare', 'conditions': 'room',
     'notes': 'the variant build uno-light-pcint stands in for a Firmware Solution row (cfg-1): the same light, the button read by the pin-change-interrupt isotope on D4'},
    {'name': 'uno-light-analog-on-desk', 'title': 'UNO light on the desk: the button as a voltage on A0 (analog threshold)', 'system': 'uno-light-bench', 'bench': 'home-bench',
     'hardware_solution': 'uno-light-system', 'firmware_solution': 'uno-light-analog', 'thermal_solution': 'uno-light-bare', 'conditions': 'room',
     'notes': 'the variant build uno-light-analog stands in for a Firmware Solution row (cfg-1): a 10 kohm pull-up on A0, the switch to ground; a press is the level below 1500 mV'},
    # bss-9: the LED routes and the sense route the variants file ships, each proven by run-all (cmod_light_topology_selftest)
    {'name': 'uno-light-pwm-on-desk', 'title': 'UNO light on the desk: the LED on the timer PWM, the button as a voltage on A0', 'system': 'uno-light-bench', 'bench': 'home-bench',
     'hardware_solution': 'uno-light-system', 'firmware_solution': 'uno-light-pwm-analog', 'thermal_solution': 'uno-light-bare', 'conditions': 'room',
     'notes': 'the variant build uno-light-pwm-analog (sample S3) stands in for a Firmware Solution row (cfg-1): drive-led:pwm, read-button:analog-threshold, the sense jumper D6 -> D3'},
    {'name': 'uno-light-transistor-on-desk', 'title': 'UNO light on the desk: the LED switched through the kit\'s transistor', 'system': 'uno-light-bench', 'bench': 'home-bench',
     'hardware_solution': 'uno-light-system', 'firmware_solution': 'uno-light-transistor', 'thermal_solution': 'uno-light-bare', 'conditions': 'room',
     'notes': 'the variant build uno-light-transistor (sample S4) stands in for a Firmware Solution row (cfg-1): drive-led:transistor-switch; the jumper D6 -> D3 senses the drive pin, not the LED current'},
    {'name': 'uno-light-all-pcint-on-desk', 'title': 'UNO light on the desk: the button on D4 and the sense line on D8, both pin-change interrupts', 'system': 'uno-light-bench',
     'bench': 'home-bench', 'hardware_solution': 'uno-light-system', 'firmware_solution': 'uno-light-all-pcint', 'thermal_solution': 'uno-light-bare', 'conditions': 'room',
     'notes': 'the variant build uno-light-all-pcint (sample S2) stands in for a Firmware Solution row (cfg-1): read-button and sense-led-line both pin-change-interrupt, two PCINT banks'},
]


BOARD_SEED_PAIRS = [
    ('BoardDefinition', BoardDefinition, _register_owned(SEED_BOARD_DEFINITIONS, keep=('road_status',))),
    ('AdapterDefinition', AdapterDefinition, _register_owned(SEED_ADAPTER_DEFINITIONS)),
    ('ProgrammerKind', ProgrammerKind, _register_owned(SEED_PROGRAMMER_KINDS)),
    ('DatasheetFact', DatasheetFact, _register_owned(SEED_UNO_FACTS + SEED_BOARD_OBJECT['DatasheetFact'])),   # brd-bo: + the SoC / pinout / Zephyr-file facts
    # ucd-doc: the documents themselves — code-owned (board.custom.datasheets.rows(), derived from the same fact/field
    # rows above; an undetermined row a person renamed is still code-owned — re-deriving just adds the citation back)
    ('Datasheet', Datasheet, _register_owned(SEED_DATASHEETS)),
    ('Road', Road, SEED_BOARD_ROADS),             # a road's progress belongs to the instance once seeded (no converge)
    ('BoardInstance', BoardInstance, []),
    ('FirmwareBuild', FirmwareBuild, []),
    ('BoardSimCost', BoardSimCost, _register_owned(SEED_BOARD_SIM_COSTS + SEED_C3_SIM_COSTS)),   # brd-1 + sc-3 (the C3's QEMU twin): measured, code-owned
    # brd-fi: the four seeded UNO variants are code-owned (a person's OWN variant is a row added on the page, never converged);
    # plans, records and the second class's rows are observed, never seeded
    ('FirmwareVariant', FirmwareVariant, _register_owned(SEED_FIRMWARE_VARIANTS + SEED_C3_VARIANTS)),   # sc-3: + the six ESP32-C3 variants
    ('InstallPlan', InstallPlan, []),
    ('InstallRecord', InstallRecord, []),
    ('SimInstallConfirmation', SimInstallConfirmation, []),   # ins-1: a person's tick (observed, never seeded)
    ('BoardFoothold', BoardFoothold, []),
    ('PartBoard', PartBoard, SEED_PART_BOARDS),   # drv-0: the cited catalogue (ULN2003A)
    ('EsdProtectionArea', EsdProtectionArea, []),   # esd-0: flagged by a person, never seeded
    ('ProtectionPart', ProtectionPart, SEED_PROTECTION_PARTS),   # esd-3: the cited catalogue (SMBJ5.0A, CG0603MLC-05E)
    ('BenchConnection', BenchConnection, []),   # bob-2: a person's wires on a bench (observed, never seeded)   # bob-0: derived on read (board.custom.footholds) or stored by a PCB ingest, never seeded
    # bss-8: the UNO light bench AS DATA - the System rows (templates) and one sample Bench Solution per button route the variants file ships, so the
    # topology spec (cmod custom/topologies/uno-light-bench.json) applies to each on a fresh instance. A person's title / notes are kept.
    ('BenchSolution', BenchSolution, _register_owned(SEED_BENCH_SOLUTIONS, keep=('title', 'notes'))),
    ('BenchConditions', BenchConditions, _register_owned(SEED_BENCH_CONDITIONS, keep=('title', 'notes'))),
    ('HardwareSystem', HardwareSystem, _register_owned(SEED_HARDWARE_SYSTEMS, keep=('title', 'notes'))),
    ('ThermalSystem', ThermalSystem, _register_owned(SEED_THERMAL_SYSTEMS, keep=('title', 'notes'))),
    ('ThermalMitigation', ThermalMitigation, []),   # bss-0: a person's rows
    ('ThermalSolution', ThermalSolution, _register_owned(SEED_THERMAL_SOLUTIONS, keep=('title', 'notes'))),
    ('BenchSystem', BenchSystem, _register_owned(SEED_BENCH_SYSTEMS, keep=('title', 'notes'))),
    ('ClockSource', ClockSource, _register_owned(SEED_CLOCK_SOURCES, keep=('notes',))),   # cfg-1: cited; a person's own rows stay
    ('ClockPeer', ClockPeer, _register_owned(SEED_CLOCK_PEERS, keep=('error_pct', 'notes'))),   # cfg-1: a person may set an adapter's measured error
    ('FirmwareStateObject', FirmwareStateObject, []),   # fst-0: derived on read (board.custom.firmware_state), never seeded
    ('FirmwareStateField', FirmwareStateField, []),
    ('UnoAnalogState', UnoAnalogState, []),
    # ucd-0e1: the two new wire classes are observed, never seeded — the device fills them (ButtonClockState) or the
    # bridge appends them (ButtonClockEvent), exactly like UnoAnalogState above
    ('ButtonClockState', ButtonClockState, []),
    ('ButtonClockEvent', ButtonClockEvent, []),
    # ucd-light: ONE placeholder row per light so the screen has its indicator before the board's first report (the
    # demo page showed "No LightState rows" on a fresh instance, 2026-10-11). Only `name` is code-owned: every other
    # field is the board's (or a person's SET_LED) and is never overwritten by a later boot.
    ('LightState', LightState, _register_owned([{'name': 'uno-light', 'seq': 0, 'boot_session': 0, 'led_on': False,
                                                 'toggles': 0, 'source': '', 'status': 'idle'}],
                                               keep=('seq', 'boot_session', 'led_on', 'toggles', 'source', 'status'))),
    # brd-bo: the board object's layers are code-owned (cited / ingested — re-read the source, the rows follow); a person's edit of a
    # BoardPin on a server is the instance's until the next seed converges it back (the edit belongs in the source: the seed file or
    # an ingested view). Views and conflicts are observed, never seeded.
] + [(c, cls, _register_owned(SEED_BOARD_OBJECT[c])) for c, cls in (('SocDefinition', SocDefinition), ('SocPin', SocPin), ('BoardHardware', BoardHardware),
                                                                     ('BoardNet', BoardNet), ('Connector', Connector), ('ConnectorPin', ConnectorPin),
                                                                     ('BoardPin', BoardPin), ('RuntimeProfile', RuntimeProfile))] + [
    ('BoardView', BoardView, []), ('BoardConflict', BoardConflict, []),
    # fs-2a: the compatibility table (code-owned: board.custom.target_compat.rows(), never hand-edited)
    ('TargetCompatibilityRule', TargetCompatibilityRule, _register_owned(TC.rows())),
    # fs-2d: the kit parts register (code-owned: board.custom.kit_parts.rows(), cited to the kit's own book;
    # sample_capabilities is re-derived from cmod's seeded Capabilities every time rows() is first called)
    ('KitPart', KitPart, _register_owned(KP.rows())),
    ('ChipLadderEntry', ChipLadderEntry, _register_owned(SEED_CHIP_LADDER)),   # chp-0: code-owned, the two sections never mix
    ('Bench', Bench, _register_owned(SEED_BENCHES, keep=('boards_json', 'breadboards_json', 'notes'))),   # bench-0: a person's additions are never converged away
    # ucd-0a: THE HARDWARE CHAIN — code-owned (derived from the register snapshot + the cited field table + the SoC pin table;
    # re-derive the source, the rows follow); the settings/route/circuit-link rows are observed (filled by ucd-0b/0c), never seeded
] + [(c, cls, _register_owned(SEED_BOARD_OBJECT[c])) for c, cls in (('Peripheral', Peripheral), ('PeripheralSignal', PeripheralSignal),
                                                                     ('PinFunction', PinFunction), ('Register', Register), ('RegisterField', RegisterField))] + [
    ('SignalRoute', SignalRoute, []), ('RegisterSetting', RegisterSetting, []), ('RegisterFieldSetting', RegisterFieldSetting, []),
    # rm-2a: the access vocabulary - code-owned (board.custom.register_access.ACCESS_KINDS), every RegisterField.access names one row
    ('RegisterAccessKind', RegisterAccessKind, _register_owned(RACC.ACCESS_KINDS)),
    # ucd-0c: the demo bench's four BoardPinNet rows — code-owned (board.custom.board_pin_nets.SEED_BOARD_PIN_NETS,
    # cited to the plan's bench + board_uno's own facts); a person's own canvas wiring is kept, never converged away
    ('BoardPinNet', BoardPinNet, _register_owned(BPN.SEED_BOARD_PIN_NETS)),
    # ucd-0b2a: address space as rows — code-owned (derived from the same register snapshot + the cited §8.5 rule;
    # re-derive the source, the rows follow)
] + [(c, cls, _register_owned(SEED_BOARD_OBJECT[c])) for c, cls in (('AddressSpace', AddressSpace), ('RegisterAddressMapping', RegisterAddressMapping),
                                                                     ('RegisterBlock', RegisterBlock), ('MemoryRegion', MemoryRegion))]
# fgm-2: the UNO hardware truth — code-owned (cited to the datasheets / schematic / box; re-derive the source, the rows follow). The physical board's
# actual (package, USB interface) pair is NOT a seed row: it is BoardInstance.package_variant / usb_interface, PENDING until Detect + attestation.
BOARD_SEED_PAIRS += [(c, cls, _register_owned(SEED_BOARD_OBJECT[c])) for c, cls in (
    ('PackageDefinition', PackageDefinition), ('PackageContact', PackageContact), ('UsbInterfaceDefinition', UsbInterfaceDefinition),
    ('BoardComponent', BoardComponent), ('ElectricalCharacteristic', ElectricalCharacteristic), ('PinGroupBudget', PinGroupBudget),
    ('PinLifecycleConstraint', PinLifecycleConstraint),
    # hsp-0: kinds catalogue (tentative), the enclosures, the exposure maps — derived from the rows above (board.custom.exposure)
    ('EnclosureKind', EnclosureKind), ('HardwareEnclosure', HardwareEnclosure), ('EnclosureContact', EnclosureContact))]
# hsp-1: the Hardware Solution, its links and its three signal paths — code-owned and RECOMPUTED on every seed (board.custom.hardware_system.seed_rows: derived from the rows above
# and from the owners of each check; a path is never typed)
from board.custom import hardware_system as _HWS   # noqa: E402
_HW_SYSTEM = _HWS.seed_rows()
BOARD_SEED_PAIRS += [(c, cls, _register_owned(_HW_SYSTEM[c])) for c, cls in (('HardwareSolution', HardwareSolution), ('SystemLink', SystemLink), ('SignalPath', SignalPath))]
BOARD_SEED_PAIRS += [('ConfigurationEvent', ConfigurationEvent, [])]   # pv-4: observed (a person's or a bridge's report of a real-world change), never seeded
BOARD_SEED_PAIRS += [('BenchInteraction', BenchInteraction, [])]   # sim-3: observed, never seeded
BOARD_SEED_PAIRS += [('TwinSession', TwinSession, [])]   # sim-1: observed (a session is started, never seeded)
try:   # pv-0: the pin view's math-defined shapes (board.custom.pv_shapes) are MathShapeDefinition rows of the mathshapes module — code-owned, derived from the rows above; skipped when mathshapes is absent
    from mathshapes.shape_basis import MathShapeDefinition as _MSD
    from board.custom import pv_shapes as _PVS
    BOARD_SEED_PAIRS += [('MathShapeDefinition', _MSD, _register_owned(_PVS.seed_rows()))]
except Exception:   # pragma: no cover — mathshapes absent: the pin view still computes its shapes from the same generators
    pass
try:   # the tree rows belong to the techtree module; seeded only when it is present
    from techtree.techtree_basis import TechTreeDefinition, TechNode
    BOARD_SEED_PAIRS += [('TechTreeDefinition', TechTreeDefinition, SEED_BOARD_TECH_TREES),
                         ('TechNode', TechNode, SEED_BOARD_TECH_NODES)]
except Exception:   # pragma: no cover — techtree absent: the roads still seed, the concept tree waits
    pass
try:   # kxc-3b: the Board Details page's run chart is a GraphDefinition row (code-owned, as hwnocode's and instruments' graphs)
    from polariApiServer.graphDefinition import GraphDefinition as _GD
    from board.board_details_page import SEED_BOARD_DETAILS_GRAPHS as _BDG
    BOARD_SEED_PAIRS += [('GraphDefinition', _GD, [dict(r, _converge=[k for k in r if k not in ('name', 'description')]) for r in _BDG])]
except Exception:   # pragma: no cover — the graph store absent: the chart door still answers
    pass
