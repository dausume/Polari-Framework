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
from board.board_basis import HardwareSystem, SystemLink, SignalPath   # hsp-1: Hardware System, links, signal paths
from board.board_basis import ConfigurationEvent   # pv-4
from board.board_basis import TwinSession, BenchInteraction   # sim-1; sim-3
from board.board_basis import SimInstallConfirmation   # ins-1
from board.board_basis import FirmwareStateObject, FirmwareStateField   # fst-0
from board.board_basis import BoardFoothold, BenchConnection   # bob-0, bob-2
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
    ('BenchConnection', BenchConnection, []),   # bob-2: a person's wires on a bench (observed, never seeded)   # bob-0: derived on read (board.custom.footholds) or stored by a PCB ingest, never seeded
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
# hsp-1: the Hardware System, its links and its three signal paths — code-owned and RECOMPUTED on every seed (board.custom.hardware_system.seed_rows: derived from the rows above
# and from the owners of each check; a path is never typed)
from board.custom import hardware_system as _HWS   # noqa: E402
_HW_SYSTEM = _HWS.seed_rows()
BOARD_SEED_PAIRS += [(c, cls, _register_owned(_HW_SYSTEM[c])) for c, cls in (('HardwareSystem', HardwareSystem), ('SystemLink', SystemLink), ('SignalPath', SignalPath))]
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
