"""
@module board.custom.lifecycle_uno

fgm-2 (REVIEW_R2 Part 3 items 6/7, FIRMWARE_GENERATION_MODULE_PLAN.md §7.7): THE UNO R3's PIN LIFECYCLE CONSTRAINTS as rows — pin x phase x policy x
reason x citation. Phases: power-up | reset | bootloader | init | runtime | programming | debug. Policy: prohibited | conditional | reserved | preserve | free.
`condition` empty = always; `condition` 'transport=usb-serial' = applies while the design's transport to the host is the USB-serial line; no row for a
(pin, phase) = free. A person's override is a DerivedOverride row (who/when/why) — NEVER a policy on this row, and NEVER past an electrical refusal.

  RESET     the reset input: C5 100 nF from the 16U2's DTR (auto-reset: opening the serial port reboots the board — every reconnect is a reboot);
            PC6 is RESET unless the RSTDISBL fuse is programmed (DS40002061B p.95); the ICSP header and debugWIRE (p.262-263) use the same pin
  D0/D1     USART0 = the USB-serial transport (through 1 kOhm to the 16U2) AND the bootloader link (Optiboot, 115200 Bd): reserved whenever the transport
            is USB-serial
  D13       SCK; drives the buffer of the on-board L LED (the LED follows D13 — the load on the pin is the buffer's INPUT, not the LED); also ICSP SCK
  D11/D12   MOSI/MISO shared with the ICSP header
  AREF      the ADC reference pin: directly connected to the ADC's reference (DS p.252): an external voltage on it with an internal/AVCC reference selected
            fights the chip
  PB6/PB7   XTAL1/XTAL2 — the 16 MHz clock part sits on them and they are not on any UNO header
Pins the sources give no constraint for carry NO row (free) — never a guessed one.
"""
from board.custom.uno_facts import M328_DOC, M328_URL
from board.custom import uno_evidence as EV
from board.custom import board_uno as U

BOARD = EV.BOARD
PHASES = ('power-up', 'reset', 'bootloader', 'init', 'runtime', 'programming', 'debug')
POLICIES = ('prohibited', 'conditional', 'reserved', 'preserve', 'free')
DS = 'atmega328p-ds40002061b'
SCH = dict(document=EV.SCH_DOC, datasheet='arduino-uno-r3-schematic', url=EV.SCH_URL)
D328 = dict(document=M328_DOC, datasheet=DS, url=M328_URL)
PINOUT = dict(document=U.DOC, datasheet='arduino-uno-r3-pinout', url=U.URL)


def _c(pin, soc_pin, phase, policy, reason, cite, where, *, condition='', ack='', verification='verified', undetermined='', notes=''):
    return {'name': '%s:%s:%s' % (BOARD, pin, phase), 'board': BOARD, 'pin': pin, 'soc_pin': 'atmega328p:%s' % soc_pin if soc_pin else '', 'phase': phase, 'policy': policy,
            'condition': condition, 'reason': reason, 'acknowledgment': ack, 'verification': verification, 'page_table': where, 'undetermined': undetermined, 'notes': notes, **cite}


def constraints():
    out = []
    # ---- RESET <- DTR
    out += [
        _c('RESET', 'PC6', 'reset', 'reserved', 'RESET is the reset input: the button, the ICSP header and (through C5 100 nF, jumper RESET-EN) the USB interface\'s DTR all pull it low', SCH,
           'sheet 1: DTR / C5 100n / RESET-EN / RESET'),
        _c('RESET', 'PC6', 'bootloader', 'reserved', 'a host opening the serial port pulses DTR and RESETS the board into the bootloader: every serial reconnect is a reboot (the relay must treat reconnect = reboot)', SCH,
           'sheet 1: DTR / C5 100n', condition='dtr=resets-mcu', notes='true for the 16U2 bridge; a CH340 variant is undetermined (UsbInterfaceDefinition.dtr_resets_mcu)'),
        _c('RESET', 'PC6', 'runtime', 'prohibited', 'PC6 is the RESET pin unless the RSTDISBL fuse is programmed; programming it would disable reset — and with it auto-reset and uploading', D328, 'Table 14-6 and the RESET/PCINT14 alternate-function text, p.94-95',
           verification='partial', undetermined='the fuse state of the bench board is not read (a fresh UNO ships with the reset circuit connected, not stated in the cited sources)'),
        _c('RESET', 'PC6', 'programming', 'reserved', 'the ICSP header\'s pin 5 is RESET (ISP programming holds it low)', PINOUT, 'p.4 ICSP header (5 RESET); DS Table 28-17 Pin Mapping Serial Programming, p.304'),
        _c('RESET', 'PC6', 'debug', 'conditional', 'with the DWEN fuse programmed RESET becomes the debugWIRE open-drain bidirectional line (pull-up must be >= 10 kOhm; an external reset source is then not supported)',
           D328, '§25.3 Physical Interface p.262; §25.4-25.5 p.263', condition='dwen=programmed', ack='debugwire', verification='partial', undetermined='whether the 100 nF DTR capacitor on RESET is compatible with debugWIRE is not stated in the sources'),
    ]
    # ---- D0/D1 = USART0 = the transport AND the bootloader link
    for pin, soc, fn in (('D0', 'PD0', 'RXD'), ('D1', 'PD1', 'TXD')):
        out += [
            _c(pin, soc, 'bootloader', 'reserved', 'the bootloader (Optiboot) talks to the host over USART0 %s at 115200 Bd' % fn, dict(document='ArduinoCore-avr boards.txt (uno entry)', datasheet='arduino-boards-txt', url=''),
               'uno.upload.speed = 115200 (line 91); uno.upload.protocol = arduino (line 88)', verification='partial', undetermined='Optiboot README not re-fetched (uno_facts.OPTIBOOT): that the bootloader uses USART0 is the standard Optiboot behaviour, not re-read here'),
            _c(pin, soc, 'init', 'reserved', 'USART0 is the USB-serial transport: the init must configure it, not claim the pin as GPIO', SCH, 'sheet 1: 16U2 M8RXD/M8TXD -> 1K RN4B/RN4A -> IO0/IO1',
               condition='transport=usb-serial'),
            _c(pin, soc, 'runtime', 'reserved', 'D0/D1 are wired through 1 kOhm to the 16U2\'s serial lines — the USB-serial transport; a GPIO claim fights the 16U2 and corrupts the frames to the host', SCH,
               'sheet 1: M8RXD / M8TXD -> RN4B / RN4A (1K) -> IO0 / IO1; pinout p.1/p.3 (D0 RXD, D1 TXD)', condition='transport=usb-serial'),
        ]
    # ---- D13 SCK + the L LED buffer
    out += [
        _c('D13', 'PB5', 'init', 'conditional', 'D13 is SCK AND the input of the buffer (LMV358 U5B) that lights the on-board L LED: the LED follows D13 whatever uses the pin, and a pin used as SPI SCK will blink it',
           SCH, 'sheet 1: SCK -> U5B -> RN2A 1K -> L LED', ack='l-led', undetermined='the LMV358 input current / capacitance on SCK (its datasheet was not read)'),
        _c('D13', 'PB5', 'runtime', 'conditional', 'as above: SPI SCK on D13 (or reading D13 as an input) must acknowledge the L LED buffer on the line; D13 as an output to a load adds to what the buffer already does',
           SCH, 'sheet 1: SCK -> U5B -> RN2A 1K -> L LED; pinout p.1 (LED_BUILTIN = PB5)', ack='l-led', undetermined='the LMV358 input current / capacitance on SCK (its datasheet was not read)'),
        _c('D13', 'PB5', 'programming', 'reserved', 'D13 is ICSP SCK (header pin 3) and the ISP clock: a connected programmer drives it', PINOUT,
           'p.4 ICSP (3 SCK PB5); DS Table 28-17, p.304', condition='icsp=connected'),
    ]
    for pin, soc, sig, num in (('D11', 'PB3', 'MOSI (COPI)', '4'), ('D12', 'PB4', 'MISO (CIPO)', '1')):
        out += [
            _c(pin, soc, 'programming', 'reserved', '%s is ICSP %s (header pin %s): a connected programmer drives or reads it' % (pin, sig, num), PINOUT, 'p.4 ICSP; DS Table 28-17, p.304', condition='icsp=connected'),
            _c(pin, soc, 'runtime', 'conditional', '%s shares its net with the ICSP header (pin %s): anything plugged into the header loads/drives the line' % (pin, num), PINOUT, 'p.4 ICSP header',
               ack='icsp-shared', verification='partial', undetermined='what a connected programmer\'s outputs do at runtime is not stated in the sources'),
        ]
    # ---- AREF
    out += [_c('AREF', '', 'runtime', 'conditional', 'AREF is directly connected to the ADC\'s reference: with a voltage on it the program must select the external-AREF reference (REFS1:0 = 00); '
               'selecting AVCC or the 1.1 V reference with a voltage applied to AREF shorts the sources', D328,
               '§24.5.2 ADC Voltage Reference, p.252 ("If the user has a fixed voltage source connected to the AREF pin, the user may not use the other reference voltage options ... they will be shorted to the external voltage"); ADMUX REFS table, p.257', ack='aref-external', verification='partial',
               undetermined='what the UNO drives onto the AREF header pin by default (nothing on the schematic page read: AREF header only) is not analysed')]
    # ---- crystal pins, not exposed on the UNO
    for pin, fn in (('PB6', 'XTAL1'), ('PB7', 'XTAL2')):
        for ph in ('init', 'runtime'):
            out.append(_c(pin, pin, ph, 'prohibited', '%s (%s) carries the 16 MHz clock part (CSTCE16M0V53-R0 with a 1 MOhm across XTAL1/XTAL2, schematic) and is on no UNO header; the internal RC oscillator is only 8 MHz (Table 29-9) so a '
                          '16 MHz board must use the external source' % (pin, fn), SCH, 'sheet 1: CSTCE16M0V53-R0 16MHZ / R2 1M; DS Table 29-9, p.313; boards.txt build.f_cpu = 16000000L',
                          verification='verified', notes='as GPIO the pin is unusable on this board; its datasheet GPIO class is atmega328p:io-standard'))
    for r in out:
        assert r['phase'] in PHASES and r['policy'] in POLICIES, r['name']
    return out
