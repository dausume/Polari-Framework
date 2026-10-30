"""
@module board.custom.exposure_e2_c3

c3-pv (2026-10-29): THE E2 (BOARD) EXPOSURE MAP of the ESP32-C3-DevKitM-1 - DERIVED, the C3's own (exposure_e2 is the UNO's: its cite is the UNO schematic and
its typed paths are the UNO's parts, so it never runs for this board):
  * every I/O leg whose GPIO a BoardPin carries -> one `direct` crossing per ConnectorPin wired to that BoardPin (J1 / J3, board_c3.HEADERS);
  * CHIP_EN -> the CHIP_PU net (the header's RST pin) and the ground pad -> GND.
  * PATHS: what else sits on a line, read 2026-10-29 from sheet 2 of the DevKitM-1 schematic (the rendered page): GPIO8 -> R17 0 Ohm -> the RGB LED D6 (DIN) +
    R20 10 kOhm to 3V3; GPIO9 -> the Boot button SW1 + Q2 (auto-program); CHIP_EN -> the Reset button SW2 + R5 10 kOhm / C6 1 uF + Q1; U0TXD / U0RXD ->
    R22 / R21 0 Ohm -> the CP2102N (U3); GPIO18 / GPIO19 -> R2 / R3 0 Ohm marked NC (not fitted). Every other header GPIO goes to its header pin only.
Header lines cite the user guide's Header Block (its Function column names the GPIO on each pin); the board trace agrees with the schematic. Verification stays PARTIAL:
between the chip's leg and the board sits the ESP32-C3-MINI-1 module, whose pin table is not traced leg by leg.
Left out, said: the supply legs (VDD3P3*, VDDA: through the module's 3V3 pad), the crystal legs (inside the module) and LNA_IN (the module's antenna).
"""
from board.custom import board_c3 as C
from board.custom.enclosures import board_enclosure_name
from board.custom.exposure_names import row

CITE = {'document': C.UG_DOC, 'url': C.UG_URL}
WHY = 'chip leg -> MINI-1 module pad: the module\'s pin table is not traced leg by leg (the board trace from the module pad on is read)'
SCH = {'document': 'Espressif ESP32-C3-DevKitM-1 schematic V1.0 (SCH_ESP32-C3-DEVKITM-1_V1_20200915A.pdf, sha256 '
                   'd2ac6d649cbea3ce4b2295a261f78823bf61e536f69fe4bee2b6e4142bd86542)',
       'url': 'https://dl.espressif.com/dl/schematics/SCH_ESP32-C3-DEVKITM-1_V1_20200915A.pdf'}


#: (leg label, outer ref ('' = stops on the board), via, label, part, value, exposed, consumed_by, verification, where, undetermined) - sheet 2, read by eye
PATHS = [
    ('GPIO8', 'SchematicPart:D6:DIN', 'series-resistor', 'GPIO8 -> the RGB LED D6 (net RGB_CTRL)', 'R17', '0 Ohm', False, 'D6 SK68XXMINI-HS addressable RGB LED, DIN',
     'verified', 'sheet 2, lower middle: GPIO8 -> R17 0(1%) -> RGB_CTRL -> D6 DIN', ''),
    ('GPIO8', '', 'internal-only', 'GPIO8: its pull-up', 'R20', '10 kOhm', False, 'R20 10 kOhm pull-up to VCC_3V3 (GPIO8 is a strapping pin)',
     'verified', 'sheet 2, middle: VCC_3V3 -> R20 10K(1%) -> GPIO8', ''),
    ('GPIO9', 'SchematicPart:SW1:3', 'direct', 'GPIO9 -> the Boot button SW1', '', '', True, 'SW1 Boot button (to GND)',
     'partial', 'sheet 2, lower right: SW1 pin 3 on GPIO9, pin 1 / 2 to GND', 'which contacts of the 4-pin switch close on a press is not read; the drawing pulls GPIO9 to GND'),
    ('GPIO9', '', 'internal-only', 'GPIO9: the auto-program transistor', 'Q2', 'L8050QLT1G', False, 'Q2 collector (RTS / DTR of the CP2102N pull GPIO9 low to enter download mode)',
     'verified', 'sheet 2, "Auto program": RTS -> R12 10K -> Q2 -> GPIO9 (truth table DTR RTS -> EN IO9)', ''),
    ('CHIP_EN', 'SchematicPart:SW2:3', 'direct', 'CHIP_EN -> the Reset button SW2', '', '', True, 'SW2 Reset button (to GND)',
     'partial', 'sheet 2, lower right: SW2 pin 3 on CHIP_PU, pin 1 / 2 to GND', 'which contacts of the 4-pin switch close on a press is not read'),
    ('CHIP_EN', '', 'internal-only', 'CHIP_PU: the RC and the auto-reset transistor', 'R5', '10 kOhm', False,
     'R5 10 kOhm pull-up to VCC_3V3, C6 1 uF to GND, Q1 (DTR -> R10 10K -> Q1 pulls CHIP_PU low)', 'verified', 'sheet 2: VCC_3V3 -> R5 10K -> CHIP_PU, C6 1uF; Auto program Q1', ''),
    ('GPIO21', 'SchematicPart:U3:RXD', 'series-resistor', 'U0TXD (GPIO21) -> the CP2102N', 'R22', '0 Ohm', False, 'U3 CP2102N-A02-GQFN28 USB-UART bridge',
     'partial', 'sheet 2, lower left: U0TXD -> R22 0(1%) -> U3', 'the U3 pin the line lands on is read as RXD by function (the TX of one side is the RX of the other); its pin number is not read'),
    ('GPIO20', 'SchematicPart:U3:TXD', 'series-resistor', 'U0RXD (GPIO20) <- the CP2102N', 'R21', '0 Ohm', False, 'U3 CP2102N-A02-GQFN28 USB-UART bridge',
     'partial', 'sheet 2, lower left: U0RXD -> R21 0(1%) -> U3', 'the U3 pin the line lands on is read as TXD by function; its pin number is not read'),
    ('GPIO18', '', 'internal-only', 'GPIO18: the USB connector link, NOT FITTED', 'R2', '0 Ohm (NC)', False, 'R2 0 Ohm marked NC: the micro-USB D- reaches the CP2102N, not GPIO18',
     'verified', 'sheet 2, upper left: J2 D- -> R2 0(1%)(NC) -> GPIO18', ''),
    ('GPIO19', '', 'internal-only', 'GPIO19: the USB connector link, NOT FITTED', 'R3', '0 Ohm (NC)', False, 'R3 0 Ohm marked NC: the micro-USB D+ reaches the CP2102N, not GPIO19',
     'verified', 'sheet 2, upper left: J2 D+ -> R3 0(1%)(NC) -> GPIO19', ''),
]
NET_OF_LEG = {'CHIP_EN': 'CHIP_PU', 'GND': 'GND'}


def rows(tables, board, u1_package):
    enc = board_enclosure_name(board)
    contacts = [c for c in tables.get('PackageContact', []) if c['package'] == u1_package]
    bpins = {b['soc_pin']: b for b in tables.get('BoardPin', []) if b['board'] == board}
    cpins = [c for c in tables.get('ConnectorPin', []) if c['board'] == board]
    out = []
    for c in sorted(contacts, key=lambda c: c['number']):
        leg = 'PackageContact:%s' % c['name']
        if c['kind'] == 'io' and c['label'] in bpins:
            bp = bpins[c['label']]
            for cp in [x for x in cpins if x.get('board_pin') == bp['canonical']]:
                out.append(row(enc, 'E2', leg, 'ConnectorPin:%s' % cp['name'], 'direct', exposed=True, verification='partial', **CITE,
                               label='%s: %s (%s) -> header %s pin %d (%s)' % (c['label'], bp['canonical'], bp['net'], cp['connector'], cp['number'], cp['label']),
                               page_table='Header Block, table %s (No. %d = %s)' % (cp['connector'], cp['number'], cp['label']), fact=cp['fact'], undetermined=WHY))
            continue
        net = NET_OF_LEG.get(c['label'])
        if net:
            out.append(row(enc, 'E2', leg, 'BoardNet:%s:%s' % (board, net), 'direct', exposed=True, verification='partial', **CITE,
                           label='%s -> %s (the header\'s %s pins)' % (c['label'], net, 'RST' if net == 'CHIP_PU' else 'GND'),
                           page_table='Header Block (J1 RST = CHIP_PU; GND = Ground)', fact='%s:devkit.header.J1' % board, undetermined=WHY))
    legs = {c['label']: 'PackageContact:%s' % c['name'] for c in contacts}
    for lab, outer, via, label, part, value, exposed, consumed, ver, where, und in PATHS:
        if lab in legs:
            out.append(row(enc, 'E2', legs[lab], outer, via, via_part=part, via_value=value, exposed=exposed, consumed_by=consumed, label=label, verification=ver, **SCH,
                           page_table=where, fact='%s:devkit.schematic' % board, undetermined='; '.join(x for x in (und, WHY) if x)))
    return out
