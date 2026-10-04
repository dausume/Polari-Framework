"""
@module board.custom.board_object_seed

THE BOARD OBJECT's seed rows (brd-bo, PCB_FROM_SCRATCH_PLAN §2b) — the UNO typed from Arduino's pinout + the ATmega328P datasheet
(board.custom.board_uno, board.custom.soc_atmega328p), the ESP32-C3 INGESTED from Zephyr's upstream board dir + the C3 datasheet
(board.custom.board_c3). The Identity layer is the existing BoardDefinition row; IDENTITY is what brd-bo adds to it.
"""
from board.custom import board_c3 as C
from board.custom import board_uno as U
from board.custom import soc_atmega328p as A

IDENTITY = {
    U.BOARD: {'soc_definition': A.SOC, 'revision': 'R3 (A000066)', 'upstream_board': ''},
    C.BOARD: {'soc_definition': C.SOC, 'revision': 'DevKitM (the reference board — Zephyr esp32c3_devkitm; his board undetermined)',
              'upstream_board': 'zephyr:esp32c3_devkitm@%s' % C.TAG},
}


def _usb(board, boards):
    return next((b['usb_ids_json'] for b in boards if b['name'] == board), '[]')


def build(boards):
    """boards = the register's BoardDefinition dicts (the usb ids are copied from the Identity row, never typed twice)."""
    conns, cpins = U.connectors()
    nets, seen = [], set()
    for n in U.nets() + C.nets():
        if n['name'] not in seen:
            seen.add(n['name'])
            nets.append(n)
    return {
        'SocDefinition': [A.soc_definition(), C.soc_definition()],
        'SocPin': A.soc_pins() + C.soc_pins(),
        'BoardHardware': [U.hardware(_usb(U.BOARD, boards)), C.hardware(_usb(C.BOARD, boards))],
        'BoardNet': nets,
        'Connector': conns,
        'ConnectorPin': cpins,
        'BoardPin': U.board_pins() + C.board_pins(),
        'RuntimeProfile': U.runtime_profiles() + C.runtime_profiles(),
        'DatasheetFact': A.soc_facts() + U.facts() + C.facts(),
    }
