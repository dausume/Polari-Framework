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
                               Connector, ConnectorPin, BoardPin, RuntimeProfile, BoardConflict, BoardView, TargetCompatibilityRule, KitPart,
                               Datasheet)   # ucd-doc: datasheets as documents
from board.board_basis import ButtonClockState, ButtonClockEvent   # ucd-0e1: the wire contract's two new classes
from board.custom.register_map import board_rows, adapter_rows, road_rows, tech_tree_rows
from board.board_basis import (Peripheral, PeripheralSignal, PinFunction, SignalRoute, Register, RegisterField, RegisterSetting,
                               RegisterFieldSetting, BoardPinNet)   # ucd-0a: the hardware chain
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
from board.custom import board_pin_nets as BPN

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
    ('UnoAnalogState', UnoAnalogState, []),
    # ucd-0e1: the two new wire classes are observed, never seeded — the device fills them (ButtonClockState) or the
    # bridge appends them (ButtonClockEvent), exactly like UnoAnalogState above
    ('ButtonClockState', ButtonClockState, []),
    ('ButtonClockEvent', ButtonClockEvent, []),
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
    # ucd-0a: THE HARDWARE CHAIN — code-owned (derived from the register snapshot + the cited field table + the SoC pin table;
    # re-derive the source, the rows follow); the settings/route/circuit-link rows are observed (filled by ucd-0b/0c), never seeded
] + [(c, cls, _register_owned(SEED_BOARD_OBJECT[c])) for c, cls in (('Peripheral', Peripheral), ('PeripheralSignal', PeripheralSignal),
                                                                     ('PinFunction', PinFunction), ('Register', Register), ('RegisterField', RegisterField))] + [
    ('SignalRoute', SignalRoute, []), ('RegisterSetting', RegisterSetting, []), ('RegisterFieldSetting', RegisterFieldSetting, []),
    # ucd-0c: the demo bench's four BoardPinNet rows — code-owned (board.custom.board_pin_nets.SEED_BOARD_PIN_NETS,
    # cited to the plan's bench + board_uno's own facts); a person's own canvas wiring is kept, never converged away
    ('BoardPinNet', BoardPinNet, _register_owned(BPN.SEED_BOARD_PIN_NETS)),
    # ucd-0b2a: address space as rows — code-owned (derived from the same register snapshot + the cited §8.5 rule;
    # re-derive the source, the rows follow)
] + [(c, cls, _register_owned(SEED_BOARD_OBJECT[c])) for c, cls in (('AddressSpace', AddressSpace), ('RegisterAddressMapping', RegisterAddressMapping),
                                                                     ('RegisterBlock', RegisterBlock), ('MemoryRegion', MemoryRegion))]
try:   # the tree rows belong to the techtree module; seeded only when it is present
    from techtree.techtree_basis import TechTreeDefinition, TechNode
    BOARD_SEED_PAIRS += [('TechTreeDefinition', TechTreeDefinition, SEED_BOARD_TECH_TREES),
                         ('TechNode', TechNode, SEED_BOARD_TECH_NODES)]
except Exception:   # pragma: no cover — techtree absent: the roads still seed, the concept tree waits
    pass
