"""
@module board.custom.board_object_seed

THE BOARD OBJECT's seed rows (brd-bo, PCB_FROM_SCRATCH_PLAN §2b) — the UNO typed from Arduino's pinout + the ATmega328P datasheet
(board.custom.board_uno, board.custom.soc_atmega328p), the ESP32-C3 INGESTED from Zephyr's upstream board dir + the C3 datasheet
(board.custom.board_c3). The Identity layer is the existing BoardDefinition row; IDENTITY is what brd-bo adds to it.
"""
import json

from board.custom import board_c3 as C
from board.custom import board_uno as U
from board.custom import soc_atmega328p as A
from board.custom import packages_atmega328p as PK     # fgm-2: the UNO hardware truth
from board.custom import usb_interfaces as UI
from board.custom import electrical_atmega328p as EL
from board.custom import lifecycle_uno as LC
from board.custom import uno_evidence as EV
from board.custom import packages_atmega16u2 as P2     # hsp-0: the 16U2's QFN32 + its SocPins
from board.custom import soc_atmega16u2 as S2
from board.custom import memory_map_atmega328p as MM   # rp-0: the memory-map regions' cited facts
from board.custom import hardware_chain_c3 as HC3       # c3pf: the ESP32-C3's Peripheral / PeripheralSignal / PinFunction rows
from board.custom import esp32c3_evidence as EV3
from board.custom import lifecycle_c3 as LC3
from board.custom import packages_esp32c3 as PC3

IDENTITY = {
    # fgm-2 (his ruling 2026-10-15): the design allows these package / USB-interface variants INDEPENDENTLY; which pair is on the bench is PENDING
    U.BOARD: {'soc_definition': A.SOC, 'revision': 'R3 (A000066)', 'upstream_board': '',
              'allowed_packages_json': json.dumps([PK.SPDIP, PK.TQFP]), 'allowed_usb_interfaces_json': json.dumps([UI.BRIDGE_16U2, UI.BRIDGE_CH340]),
              'variant_status': 'pending'},
    C.BOARD: {'soc_definition': C.SOC, 'revision': 'DevKitM (the reference board — Zephyr esp32c3_devkitm; his board undetermined)',
              'upstream_board': 'zephyr:esp32c3_devkitm@%s' % C.TAG},
}


def _usb(board, boards):
    return next((b['usb_ids_json'] for b in boards if b['name'] == board), '[]')


def build(boards):
    """boards = the register's BoardDefinition dicts (the usb ids are copied from the Identity row, never typed twice).
    MUTATED IN PLACE: each gains `datasheets_json` (ucd-doc) once the Datasheet rows below are resolved — so both
    callers (board_seed.py's module-level seed AND board.custom.board_object.seed_tables()'s on-demand rebuild, the
    same `boards` list passed by reference in each) see the same coverage, computed once, here."""
    conns, cpins = U.connectors()
    c3c, c3p = C.connectors()   # c3-pv: the DevKitM-1's J1 / J3 (the user guide's Header Block)
    conns, cpins = conns + c3c, cpins + c3p
    nets, seen = [], set()
    for n in U.nets() + C.nets():
        if n['name'] not in seen:
            seen.add(n['name'])
            nets.append(n)
    out = _layers(boards, conns, cpins, nets)
    P2.link_soc_pins(out['SocPin'], out['PackageContact'])   # hsp-0: the 16U2's SocPins gain their package-contact refs
    PK.link_soc_pins(out['SocPin'], out['PackageContact'])   # fgm-2: SocPin gains its pad class + the package contacts it appears on (in place)
    PC3.link_soc_pins(out['SocPin'], out['PackageContact'])  # c3pf: the C3's SocPins gain their QFN32 legs
    # ucd-0a: THE HARDWARE CHAIN (board.custom.hardware_chain) — Peripheral / PeripheralSignal / PinFunction / Register /
    # RegisterField rows derived from the same sources, and the SocPin / BoardPin rows gain their reverse links in place
    from board.custom import hardware_chain as HC
    out.update(HC.build(out['SocPin'], out['BoardPin']))
    c3 = HC3.build(out['SocPin'], out['BoardPin'])           # c3pf: + the ESP32-C3's chain (its SocPin / BoardPin rows gain their links in place)
    for k, rows in c3.items():
        out[k] = out[k] + rows
    # ucd-doc: THE DATASHEETS, as rows — resolved from every DatasheetFact/RegisterField this build produced PLUS the
    # UNO's own uno_facts.SEED_UNO_FACTS (seeded separately, board_seed.BOARD_SEED_PAIRS's 'DatasheetFact' entry) —
    # mutates every one of those dicts in place, adding `datasheet`, so whichever entry point built them carries it.
    # hsp-0: THE ENCLOSURES — kinds (tentative), enclosures, the exposure maps, derived from the rows built above
    from board.custom import exposure as EXP
    out.update(EXP.build(out))
    from board.custom.uno_facts import SEED_UNO_FACTS
    from board.custom import datasheets as DS
    out['Datasheet'] = DS.rows(SEED_UNO_FACTS + out['DatasheetFact'], out['RegisterField'])
    for b in boards:
        b['datasheets_json'] = DS.board_coverage_json(b['name'], b.get('soc_definition', ''), out['Datasheet'])
    return out


def _layers(boards, conns, cpins, nets):
    contacts = PK.contacts()
    c3_soc_pins = C.soc_pins()
    c3_contacts = PC3.contacts(c3_soc_pins)
    return {
        'SocDefinition': [A.soc_definition(), C.soc_definition(), UI.soc_16u2()],
        # fgm-2: the UNO hardware truth (package + USB-interface axes, chips as rows, numbers per pad class, group budgets, lifecycle)
        'PackageContact': contacts + P2.contacts() + c3_contacts,
        'PackageDefinition': PK.package_definitions(contacts) + [P2.package_definition()] + [PC3.package_definition(c3_contacts)], 'UsbInterfaceDefinition': UI.usb_interfaces(),
        'BoardComponent': UI.components() + [PC3.component()], 'ElectricalCharacteristic': EL.characteristics(), 'PinGroupBudget': EL.budgets(),
        'PinLifecycleConstraint': LC.constraints() + LC3.constraints(),
        'SocPin': A.soc_pins() + c3_soc_pins + S2.soc_pins(),
        'BoardHardware': [U.hardware(_usb(U.BOARD, boards)), C.hardware(_usb(C.BOARD, boards))],
        'BoardNet': nets,
        'Connector': conns,
        'ConnectorPin': cpins,
        'BoardPin': U.board_pins() + C.board_pins(),
        'RuntimeProfile': U.runtime_profiles() + C.runtime_profiles(),
        'DatasheetFact': A.soc_facts() + U.facts() + C.facts() + EV.facts() + S2.soc_facts() + MM.facts() + HC3.facts() + EV3.board_facts(),   # rp-0: + the memory-map regions' cites
    }
