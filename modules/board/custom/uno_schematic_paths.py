"""
@module board.custom.uno_schematic_paths

hsp-0 (L3): THE UNO R3's BOARD-LEVEL (E2) PATHS THAT ARE NOT A PLAIN LEG-TO-HEADER LINE — read 2026-10-17 from the RENDERED sheet 1 of the Arduino UNO R3
(A000066) schematic (the file whose sha256 is uno_evidence.SCH_SHA; page rendered at 300 dpi and read crop by crop, the PDF's text layer is positional only).
The plain lines (every 328P I/O leg -> its header pin(s), the power legs -> their rails) are DERIVED from the ConnectorPin / BoardPin / PackageContact
rows in board.custom.exposure; this file holds ONLY what the headers do not say: what sits between the two chips, what stops on the board, what the
16U2's legs go to. The schematic's own designators are Arduino's (the 328P is ZU4, the 16U2 is U3 there; ours are U1 / U2); part designators below
(RN4B, C5, U5B ...) are the schematic's.

What the render shows, per 16U2 leg (the schematic's U3, QFN pin numbers as drawn):
  1 XTAL1, 2 XTAL2(PC0) -> Y1 16MHz crystal with C9 / C11 22 pF to GND and R1 1M across (test pads TP_XT1..TP_XT4) ; 3 GND ; 4 VCC -> +5V ; 5 PC2, 6 PD0, 7 PD1 bare stubs ;
  8 PD2 (RXD1) <- M8TXD <- RN4A 1K <- 328P TXD ; 9 PD3 (TXD1) -> M8RXD -> RN4B 1K -> 328P RXD ; 10 PD4 -> RXLED -> RX LED -> RN2B 1K -> +5V ; 11 PD5 -> TXLED -> TX LED ->
  RN2C 1K -> +5V ; 12 PD6 bare stub ; 13 PD7 -> net DTR -> C5 100 nF -> 328P RESET (and RN2D 1K to GND, label "USB boot En", test pad TP_DTR) ; 14 PB0 bare stub ;
  15 PB1 SCK2, 16 PB2 MOSI2, 17 PB3 MISO2 -> the 16U2's own ICSP1 header pins 3 / 4 / 1 ; 18..21 PB4..PB7 -> test pads TP_PB4..TP_PB7 and the unpopulated 2x2 header JP2 ("M - NM") ;
  22 PC7, 23 PC6 bare stubs ; 24 RESET(PC1/DW) -> net RESET2 -> ICSP1 pin 5 ; 25 PC5, 26 PC4 bare stubs ; 27 UCAP -> C8 1u to GND ; 28 UGND -> the USB connector's shield pin 4 ;
  29 D+ -> RD+ -> RN3D 22R -> net D+ -> USB connector X2 pin 3 ; 30 D- -> RD- -> RN3A 22R -> net D- -> X2 pin 2 (ESD varistors Z1 / Z2 on D- / D+) ; 31 UVCC -> USBVCC <- F1 (MF-MSMF050-2 500mA)
  <- X2 pin 1 ; 32 AVCC -> +5V ; 33 PAD -> GND.
A "bare stub" is a short unlabeled line end on the symbol: read as unconnected (partial: the board layout was not read).
"""
from board.custom import uno_evidence as EV
from board.custom import packages_atmega328p as PK
from board.custom import packages_atmega16u2 as P2

BOARD = EV.BOARD
SCH = 'sheet 1 of the rendered schematic'


def u1(n):
    return 'PackageContact:%s:%d' % (PK.SPDIP, n)


def u2(n):
    return 'PackageContact:%s:%d' % (P2.QFN, n)


def net(n):
    return 'BoardNet:%s:%s' % (BOARD, n)


def part(ref, pin):
    return 'SchematicPart:%s:%s' % (ref, pin)


def _p(inner, outer, via, label, *, part='', value='', exposed=False, consumed='', ver='verified', where='', fact='', und='', notes=''):
    return {'inner_ref': inner, 'outer_ref': outer, 'via': via, 'label': label, 'via_part': part, 'via_value': value, 'exposed': exposed,
            'consumed_by': consumed, 'verification': ver, 'where': where, 'fact': fact, 'undetermined': und, 'notes': notes}


STUB = ('the render shows a bare, unlabeled stub on this leg and no part on it: read as unconnected, NOT proven — the board layout was not read')


def _stub(n, lab):
    return _p(u2(n), '', 'internal-only', 'U2 leg %d %s (unused)' % (n, lab), ver='partial', where='sheet 1, U3 symbol, leg %d (bare stub)' % n, und=STUB)


def paths():
    out = [
        # ---- the two chips talk (USART0 <-> the 16U2's USART1), through 1 kOhm
        _p(u1(2), u2(9), 'series-resistor', 'D0 / PD0 RXD <- U2 PD3 TXD1 (net M8RXD)', part='RN4B', value='1 kOhm', consumed='U2 (ATmega16U2) leg 9 PD3/TXD1',
           where='sheet 1: 16U2 pin 9 M8RXD -> RN4B 1K -> IO0 (328P pin 2)', fact='%s:schematic.serial_resistors' % BOARD,
           notes='the header pin D0 is on the IO0 net on the 328P side of RN4B: an external driver on D0 contends with the 16U2 through this resistor'),
        _p(u1(3), u2(8), 'series-resistor', 'D1 / PD1 TXD -> U2 PD2 RXD1 (net M8TXD)', part='RN4A', value='1 kOhm', consumed='U2 (ATmega16U2) leg 8 PD2/RXD1',
           where='sheet 1: 16U2 pin 8 M8TXD -> RN4A 1K -> IO1 (328P pin 3)', fact='%s:schematic.serial_resistors' % BOARD),
        # ---- the auto-reset
        _p(u2(13), u1(1), 'capacitor', 'U2 PD7 (net DTR) -> U1 RESET', part='C5', value='100 nF', consumed='U1 (ATmega328P) leg 1 RESET (auto-reset)',
           where='sheet 1, reset area: DTR / C5 100n / RESET-EN / RESET', fact='%s:schematic.dtr_reset' % BOARD,
           und='whether RESET-EN is in series with C5 or bridges it is not resolved by the render; the existing row says it "sits in the RESET path" (cut = no auto-reset)',
           ver='verified', notes='a host opening the serial port pulses DTR, which resets the 328P; RESET-EN is the solder jumper that disables it'),
        _p(u2(13), '', 'internal-only', 'U2 PD7 DTR net: its pull-down branch', part='RN2D', value='1 kOhm',
           consumed='RN2D 1 kOhm to GND (schematic label "USB boot En") and test pad TP_DTR', ver='partial', where='sheet 1, left of C5: RN2D 1K to GND, label "USB boot En", TP_DTR',
           und='what the 1 kOhm to ground on the DTR net is for is not read beyond its label'),
        # ---- the L LED buffer
        _p(u1(19), part('U5B', 'non-inverting input'), 'buffer', 'D13 / PB5 SCK -> the L LED', part='U5B LMV358IDGKR', consumed='L LED (yellow) through RN2A 1 kOhm to GND',
           where='sheet 1, top middle: SCK -> U5B -> RN2A 1K -> L', fact='%s:schematic.l_led' % BOARD,
           und='the LMV358 input current / capacitance on SCK (its datasheet was not read)',
           notes='the LED follows D13 whatever uses the pin; the load on D13 is the buffer input, not the LED'),
        # ---- the clock
        _p(u1(9), '', 'internal-only', 'PB6 XTAL1', part='CSTCE16M0V53-R0', consumed='CSTCE16M0V53-R0 16 MHz clock part (R2 1 MOhm across XTAL1/XTAL2)',
           where='sheet 1, middle: ZU4 pins 9/10 -> CSTCE16M0V53-R0 16MHZ, R2 1M', fact='%s:schematic.clock' % BOARD, notes='a test pad TP_XT1 is drawn on the net (a probe point, not a header)'),
        _p(u1(10), '', 'internal-only', 'PB7 XTAL2', part='CSTCE16M0V53-R0', consumed='CSTCE16M0V53-R0 16 MHz clock part (R2 1 MOhm across XTAL1/XTAL2)',
           where='sheet 1, middle: ZU4 pins 9/10 -> CSTCE16M0V53-R0 16MHZ, R2 1M', fact='%s:schematic.clock' % BOARD, notes='a test pad TP_XT2 is drawn on the net (a probe point, not a header)'),
        # ---- RESET: the button, the pull-up and diode
        _p(u1(1), part('RESET button TS42031-160R-TR-7260', '1'), 'direct', 'RESET -> the reset button', exposed=True, ver='partial',
           where='sheet 1, reset area: the RESET switch (TS42031-160R-TR-7260) between the RESET net and GND', fact='%s:schematic.dtr_reset' % BOARD,
           und='which contacts of the 4-pin switch are bridged when pressed is not read; the part pulls RESET to GND in the drawing'),
        _p(u1(1), '', 'internal-only', 'RESET net: the pull-up and the diode', part='RN1D', value='10 kOhm', consumed='RN1D 10 kOhm pull-up to +5V and diode D2 on the RESET net',
           ver='partial', where='sheet 1, reset area: RN1D 10K, D2', fact='%s:schematic.dtr_reset' % BOARD, und='the pull-up and diode are drawn on the net; their exact connection is not analysed'),
        # ---- the analog supply and reference
        _p(u1(20), net('+5V'), 'series-inductor', 'AVCC <- +5V', part='L2', value='10 uH', exposed=True, where='sheet 1, middle: +5V -> L2 10uH -> AVCC (pin 20), C10 100n to GND',
           notes='reaches the +5V rail through the inductor (DC); its 100 nF to GND (C10) is a bypass, not modelled as a crossing'),
        _p(u1(21), '', 'internal-only', 'AREF net: its capacitor', part='C4', value='100 nF', consumed='C4 100 nF to GND on the AREF net',
           where='sheet 1, right of the 328P: AREF -> C4 100n to GND', notes='AREF itself is exposed on the header (the derived rail crossing)'),
        # ---- the 16U2: clock, supply, USB, programming, indicators; every leg accounted for
        _p(u2(1), '', 'internal-only', 'U2 XTAL1', part='Y1', value='16 MHz', consumed='Y1 16 MHz crystal (C9, C11 22 pF to GND; R1 1 MOhm across)',
           where='sheet 1, left middle: U3 XTAL1 / XTAL2(PC0) -> Y1 16MHz, C9 22p, C11 22p, R1 1M'),
        _p(u2(2), '', 'internal-only', 'U2 PC0 / XTAL2', part='Y1', value='16 MHz', consumed='Y1 16 MHz crystal (C9, C11 22 pF to GND; R1 1 MOhm across)',
           where='sheet 1, left middle: U3 XTAL1 / XTAL2(PC0) -> Y1 16MHz, C9 22p, C11 22p, R1 1M'),
        _p(u2(3), net('GND'), 'direct', 'U2 GND', exposed=True, where='sheet 1, left middle: U3 GND (pin 3) -> GND'),
        _p(u2(4), net('+5V'), 'direct', 'U2 VCC', exposed=True, where='sheet 1, left middle: U3 VCC (pin 4) -> +5V'),
        _stub(5, 'PC2'), _stub(6, 'PD0'), _stub(7, 'PD1'),
        _p(u2(10), '', 'internal-only', 'U2 PD4 (net RXLED)', consumed='RX LED (yellow) through RN2B 1 kOhm to +5V', where='sheet 1, lower middle: U3 pin 10 RXLED -> RX LED -> RN2B 1K -> +5V'),
        _p(u2(11), '', 'internal-only', 'U2 PD5 (net TXLED)', consumed='TX LED (yellow) through RN2C 1 kOhm to +5V', where='sheet 1, lower middle: U3 pin 11 TXLED -> TX LED -> RN2C 1K -> +5V'),
        _stub(12, 'PD6'), _stub(14, 'PB0'),
        _p(u2(15), part('ICSP1', '3'), 'direct', 'U2 PB1 SCK2 -> its ICSP1 header pin 3', exposed=True, where='sheet 1: U3 pin 15 SCK2 -> ICSP1 (6-pin 2x3) pin 3',
           und='the ICSP1 pin numbers are read from the schematic\'s pin labels (MISO2 1, SCK2 3, MOSI2 4, RESET2 5); pins 2 and 6 (supply / ground) are not modelled'),
        _p(u2(16), part('ICSP1', '4'), 'direct', 'U2 PB2 MOSI2 -> its ICSP1 header pin 4', exposed=True, where='sheet 1: U3 pin 16 MOSI2 -> ICSP1 pin 4'),
        _p(u2(17), part('ICSP1', '1'), 'direct', 'U2 PB3 MISO2 -> its ICSP1 header pin 1', exposed=True, where='sheet 1: U3 pin 17 MISO2 -> ICSP1 pin 1'),
        _p(u2(24), part('ICSP1', '5'), 'direct', 'U2 RESET (PC1) -> net RESET2 -> its ICSP1 header pin 5', exposed=True, ver='partial', where='sheet 1: U3 pin 24 RESET(PC1/DW) -> RESET2 -> ICSP1 pin 5',
           und='other parts on the RESET2 net (a pull-up, a diode) are drawn but not analysed'),
    ]
    for n, lab in ((18, 'PB4'), (19, 'PB5'), (20, 'PB6'), (21, 'PB7')):
        out.append(_p(u2(n), part('TP_%s' % lab, '1'), 'direct', 'U2 %s -> test pad TP_%s' % (lab, lab), exposed=True, ver='partial',
                      where='sheet 1: U3 pin %d %s -> TP_%s and the unpopulated header JP2 (2x2 "M - NM")' % (n, lab, lab),
                      und='which pin of JP2 this line also reaches is not resolved by the render (JP2 is marked not mounted)',
                      notes='a test pad is a probe point on the board (E2 kind test-pad), not a header'))
    out += [_stub(22, 'PC7'), _stub(23, 'PC6'), _stub(25, 'PC5'), _stub(26, 'PC4'),
            _p(u2(27), '', 'internal-only', 'U2 UCAP (USB regulator output)', part='C8', value='1 uF', consumed='C8 1 uF to GND (the datasheet asks for an external 1 uF capacitor on UCAP)',
               where='sheet 1, lower left: UCAP (pin 27) -> C8 1u to GND, test pad TP_VUCAP'),
            _p(u2(28), part('X2', '4'), 'direct', 'U2 UGND -> USB connector shield/ground pin 4', exposed=True, ver='partial', where='sheet 1, lower left: UGND (pin 28) -> the UGND net -> X2 pin 4',
               und='the "GROUND" solder-jumper pair that joins the UGND and GND nets is drawn but its state is not analysed'),
            _p(u2(29), part('X2', '3'), 'series-resistor', 'U2 D+ -> USB connector D+', part='RN3D', value='22 Ohm', exposed=True, where='sheet 1, lower left: U3 D+ (29) -> RD+ -> RN3D 22R -> D+ -> X2 pin 3',
               notes='an ESD varistor (Z2, CG0603MLC-05E) is also drawn on the D+ net'),
            _p(u2(30), part('X2', '2'), 'series-resistor', 'U2 D- -> USB connector D-', part='RN3A', value='22 Ohm', exposed=True, where='sheet 1, lower left: U3 D- (30) -> RD- -> RN3A 22R -> D- -> X2 pin 2',
               notes='an ESD varistor (Z1, CG0603MLC-05E) is also drawn on the D- net'),
            _p(u2(31), part('X2', '1'), 'series-fuse', 'U2 UVCC <- USB VBUS', part='F1 MF-MSMF050-2', value='500 mA', exposed=True,
               where='sheet 1, lower left: X2 pin 1 (XUSB) -> F1 MF-MSMF050-2 500mA -> USBVCC -> U3 UVCC (31)', und='USBVCC also feeds the board power path (T1 FDN340P): not analysed here'),
            _p(u2(32), net('+5V'), 'direct', 'U2 AVCC', exposed=True, where='sheet 1: U3 AVCC (pin 32) -> +5V'),
            _p(u2(33), net('GND'), 'direct', 'U2 centre pad (PAD, 33)', exposed=True, where='sheet 1: U3 PAD (33) -> GND',
               und='whether the pad is electrically the die ground is not stated by the datasheet (only "soldered to ground ... mechanical stability")')]
    return out
