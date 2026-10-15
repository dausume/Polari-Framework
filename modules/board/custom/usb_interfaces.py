"""
@module board.custom.usb_interfaces

fgm-2 (his ruling 2026-10-15, FIRMWARE_GENERATION_MODULE_PLAN.md §7.8.1): THE USB-INTERFACE AXIS, independent of the package axis — and the
board's chips as rows (BoardComponent): U1 the ATmega328P (role mcu), U2 the ATmega16U2 (role usb-bridge, a programmable MCU of its own).

THE PHYSICAL BOARD'S ACTUAL (package, USB interface) PAIR IS PENDING (his ruling). Nothing here says which is on the bench: BoardDefinition
lists what the DESIGN allows, BoardInstance.package_variant / usb_interface stay '' with variant_status='pending' until Detect reads the USB id
and a person attests the package (the box in his photos is evidence, not confirmation: §7.10).

  atmega16u2-bridge   VID:PIDs 2341:0043 (the genuine R3's — his statement §7.8, boards.txt lists it), 2341:0001 and 2a03:0043 (boards.txt uno.vid/pid
                      lines 63-72 list all three for the uno entry; WHICH chip each one identifies is not stated there → noted, not asserted).
                      DTR resets the MCU: TRUE for the R3 circuit — schematic sheet 1: 16U2 PD7 (net DTR) -> C5 100 nF -> 328P RESET.
  ch340-bridge        1a86:7523 as his brief states it (§7.8) — NOT verified against a document here (the CH340 datasheet and a clone's schematic were
                      not read): verification 'unverified'; dtr_resets_mcu 'undetermined' (clones differ).
"""
import json

from board.custom import uno_evidence as EV
from board.custom import soc_atmega328p as A
from board.custom import packages_atmega328p as PK

BOARD = EV.BOARD
BRIDGE_16U2 = 'atmega16u2-bridge'
BRIDGE_CH340 = 'ch340-bridge'


def usb_interfaces():
    return [
        {'name': BRIDGE_16U2, 'title': 'ATmega16U2 USB-serial bridge (the genuine UNO R3)', 'bridge_chip': 'ATmega16U2', 'programmable': True, 'programmable_soc': EV.U2,
         'usb_ids_json': json.dumps([{'id': '2341:0043', 'note': 'the genuine R3\'s id (his statement, plan §7.8; boards.txt uno.vid.0/pid.0, line 63-64)'},
                                     {'id': '2341:0001', 'note': 'listed for the uno entry in boards.txt (lines 65-66); which bridge chip it identifies is not stated there'},
                                     {'id': '2a03:0043', 'note': 'listed for the uno entry in boards.txt (lines 67-68); which bridge chip it identifies is not stated there'}]),
         'serial_transport': 'ATmega328P USART0 (D0 RXD / D1 TXD) through 1 kOhm series resistors', 'dtr_resets_mcu': 'true',
         'dtr_path': '16U2 pin 13 (PD7, net DTR) -> C5 100 nF -> 328P RESET; the RESET-EN solder jumper is in the path (cut = no auto-reset)',
         'firmware': 'USB-serial (the product page: "usb_serial_chip ATmega16U2"; the firmware image itself is not cited here)', 'allowed_boards_json': json.dumps([BOARD]),
         'verification': 'verified', 'document': EV.SCH_DOC, 'datasheet': 'arduino-uno-r3-schematic',
         'page_table': 'sheet 1: DTR / C5 / RESET-EN; M8RXD/M8TXD -> RN4A/RN4B; ATMEGA16U2-MU(R) (=32M1-A, ATmega16U2 datasheet p.295)', 'url': EV.SCH_URL,
         'undetermined': 'the 16U2 firmware image/version on a given board; boards.txt also lists 2341:0243 and 2341:006a for the uno entry (lines 69-72) — which interface they mean is not stated',
         'notes': 'the 16U2 is itself a programmable MCU (its own SocDefinition atmega16u2); milestone-1 firmware targets U1 only'},
        {'name': BRIDGE_CH340, 'title': 'CH340 USB-serial bridge (a common clone variant)', 'bridge_chip': 'CH340', 'programmable': False, 'programmable_soc': '',
         'usb_ids_json': json.dumps([{'id': '1a86:7523', 'note': 'as his brief states it (plan §7.8); not verified against a document in this repo'}]),
         'serial_transport': 'undetermined (a clone\'s schematic was not read; normally the 328P USART0)', 'dtr_resets_mcu': 'undetermined', 'dtr_path': '',
         'firmware': '', 'allowed_boards_json': json.dumps([BOARD]), 'verification': 'unverified', 'document': '', 'datasheet': '', 'page_table': '(no document read)', 'url': '',
         'undetermined': 'the CH340 datasheet and a clone board\'s schematic were not read: the USB id, whether DTR resets the MCU, and the series resistors are unverified',
         'notes': 'the Hardware Bridge panel\'s Detect step today matches only the three 16U2 ids (BoardDetector.java); reading this table instead is the small app change that follows'},
    ]


def soc_16u2():
    fk = lambda k: '%s:%s' % (EV.U2, k)   # noqa: E731
    return {'name': EV.U2, 'title': 'Microchip (Atmel) ATmega16U2 — the UNO R3\'s USB bridge', 'vendor': 'Microchip (Atmel)', 'package': '32M1-A QFN32 (the "-MU" code on the schematic)',
            'isa': 'AVR8', 'cpu_clock_hz': 16000000,
            'memory_map_json': json.dumps([{'region': 'flash', 'size': 16384, 'fact': fk('memory.flash')}, {'region': 'sram', 'size': 512, 'fact': fk('memory.sram')},
                                           {'region': 'eeprom', 'size': 512, 'fact': fk('memory.eeprom')}]),
            'peripherals_json': json.dumps([{'name': 'USB', 'fact': fk('usb')}]), 'clocks_json': '[]', 'pin_count': 0,
            'facts_json': json.dumps([fk(k) for k in ('memory.flash', 'memory.eeprom', 'memory.sram', 'signature', 'packages', 'usb')]),
            'source': 'datasheet %s' % EV.U2_REV.split(',')[0], 'zephyr_soc': '', 'vendor_target': '',
            'undetermined': 'its pins are NOT modelled (pin_count 0): milestone-1 firmware targets U1 only; the 16U2 appears as the transport participant and the cause of the DTR reset. '
                            'cpu_clock_hz 16 MHz is the datasheet\'s top speed grade for the part (ordering table p.295: 16 MHz, 2.7-5.5 V), the board\'s own clock for U2 is the schematic\'s Y1 (product datasheet: ECS-160-20-4X-DU oscillator, not analysed)',
            'notes': 'a SocDefinition so U2 is a row of its own; programmed by the bridge-firmware path, never by the sample firmware'}


def components():
    u1_options = [PK.SPDIP, PK.TQFP]
    return [
        {'name': '%s:U1' % BOARD, 'board': BOARD, 'ref': 'U1', 'value': 'ATmega328P-PU', 'role': 'mcu', 'soc': A.SOC, 'package': PK.SPDIP,
         'package_options_json': json.dumps(u1_options), 'programmable': True, 'targeted_by_firmware': True, 'usb_interface': '',
         'fact': '%s:package.power_pins' % A.SOC, 'origin': 'derived:BoardHardware.components_json U1 (board_uno.hardware)',
         'undetermined': 'which package is on the bench board is PENDING identification (his ruling 2026-10-15); this row models the design\'s package (28-SPDIP)',
         'notes': 'the schematic\'s own designator is ZU4 (ATMEGA328P-PU); ours is U1'},
        {'name': '%s:U2' % BOARD, 'board': BOARD, 'ref': 'U2', 'value': 'ATmega16U2', 'role': 'usb-bridge', 'soc': EV.U2, 'package': '',
         'package_options_json': '[]', 'programmable': True, 'targeted_by_firmware': False, 'usb_interface': BRIDGE_16U2,
         'fact': '%s:schematic.usb_bridge_part' % BOARD, 'origin': 'derived:BoardHardware.components_json U2 (board_uno.hardware)',
         'undetermined': 'a PackageDefinition row for the 16U2 is not modelled (the schematic says 32M1-A QFN32; the PackageDefinition rows are the ATmega328P\'s); '
                         'which USB interface variant is on the bench board is PENDING (a CH340 board has no 16U2 at all)',
         'notes': 'the schematic\'s designator is U3 (product datasheet §3.1); ours is U2. It runs the USB-serial firmware and causes the DTR reset of U1'},
    ]
