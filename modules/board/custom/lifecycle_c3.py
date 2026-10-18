"""
@module board.custom.lifecycle_c3

c3pf: THE ESP32-C3 (DevKitM reference board)'s PIN LIFECYCLE CONSTRAINTS as rows - pin x phase x policy x reason x citation, the same class and phases as the UNO's
(board.custom.lifecycle_uno). Every row cites a document and a page/table; a pin the sources give no constraint for carries NO row (free) - never a guessed one.

  GPIO2 / GPIO8 / GPIO9   strapping pins, sampled when reset is released (datasheet §3 p.30, Table 3-1 defaults, Table 3-3 p.31 boot modes) - phase `reset`
  GPIO20 / GPIO21         UART0 = the ROM download link (Joint download boot: UART0 or USB, p.31) and, on the DevKitM, the transport through the USB-UART bridge
  GPIO18 / GPIO19         the USB Serial/JTAG pads: by default connected to that controller; to be GPIOs they "need to be reconfigured" (§2.3.3 p.22, Table 2-1 note 5 p.17)
  GPIO4-7                 the JTAG pads (MTMS/MTDI/MTCK/MTDO): in use while debugging over JTAG pins (§2.3.3 p.22) - phase `debug`
  GPIO12-17               the SPI0/1 pads of the IN-PACKAGE flash: "Do not use the pins connected to in-package flash for any other purposes" (Table 2-12 p.29); the
                          ESP32-C3-MINI-1 module's flash "is integrated in the chip's package" (MINI-1 datasheet p.4 note 4) and its Table 3-1 (p.11) lists those pins as NC
  GPIO11 (VDD_SPI)       the flash supply by default; a GPIO only if the flash has its own supply (Table 2-1 note 8 p.17, §2.3.3 p.22)
  GPIO8 / GPIO9           the DevKitM's RGB LED (driven by GPIO8) and boot button (GPIO9 in Zephyr's dts)
  power-up glitches       Table 2-2 p.18: MTCK, MTDO, GPIO10, U0RXD low for ~5 ns; GPIO18 high for ~50 us

Which module sits on the board he buys is undetermined (the register: "no C3 on hand"); the rows are the reference board's (Zephyr esp32c3_devkitm = the
ESP32-C3-MINI-1 N4 module). The `condition` vocabulary: 'transport=usb-serial' (UART0 through the USB-UART bridge), 'transport=usb-serial-jtag' (the chip's own
USB), 'debug=jtag-pins'.
"""
from board.custom import esp32c3_evidence as EV
from board.custom.lifecycle_uno import PHASES, POLICIES

BOARD = EV.BOARD
SOC = EV.SOC
DS = dict(document=EV.DS_DOC, datasheet='espressif-esp32-c3-datasheet', url=EV.DS_URL)
MINI = dict(document=EV.MINI_DOC, datasheet='espressif-esp32-c3-mini-1-datasheet', url=EV.MINI_URL)
KIT = dict(document=EV.KIT_DOC, datasheet='espressif-esp32-c3-devkitm-user-guide', url=EV.KIT_URL)
ZEPHYR = dict(document='Zephyr RTOS (Apache-2.0) esp32c3_devkitm.dts', datasheet='zephyr-esp32c3-devkitm-ingest', url='https://github.com/zephyrproject-rtos/zephyr/tree/%s/' % EV.C.TAG)


def _c(n, phase, policy, reason, cite, where, *, condition='', ack='', verification='verified', undetermined='', notes=''):
    pin = 'GPIO%d' % n
    suffix = (':' + condition.partition('=')[2]) if condition and phase in ('init', 'runtime') and pin in ('GPIO18', 'GPIO19') else ''   # two rows of one phase differ by condition
    return {'name': '%s:%s:%s%s' % (BOARD, pin, phase, suffix), 'board': BOARD, 'pin': pin, 'soc_pin': '%s:%s' % (SOC, pin), 'phase': phase, 'policy': policy, 'condition': condition,
            'reason': reason, 'acknowledgment': ack, 'verification': verification, 'page_table': where, 'undetermined': undetermined, 'notes': notes, **cite}


def constraints():
    out = []
    # ---- strapping pins, sampled at reset
    strap = {2: ('floating by default', 'GPIO2 must be 1 for SPI boot and for joint download boot; the datasheet says it "actually does not determine" the mode but recommends a pull-up because of glitches'),
             8: ('floating by default', 'GPIO8 is 1 for joint download boot (any value for SPI boot); with EFUSE_UART_PRINT_CONTROL it also decides whether the ROM prints to UART0 (Table 3-4)'),
             9: ('weak pull-up by default (bit value 1)', 'GPIO9 = 1 selects SPI boot, GPIO9 = 0 selects joint download boot (UART0 or USB): a circuit that holds it low at reset puts the chip in download mode')}
    for n, (dflt, why) in sorted(strap.items()):
        out.append(_c(n, 'reset', 'conditional', 'strapping pin (%s): %s; the level is latched when reset is released and the pin is a normal I/O afterwards' % (dflt, why), DS,
                      '§3 Boot Configurations Table 3-1 p.30, Table 3-3 Chip Boot Mode Control p.31, Table 3-4 p.32; §2.3.3 p.22', ack='strapping-level',
                      notes='the module datasheet excerpts the same tables (MINI-1 v2.2 Table 4-1, p.12); the DevKitM marks GPIO2/8/9 as strapping pins (user guide, Header Block note 2)'))
    # ---- UART0: ROM download link + the DevKitM's USB-UART transport
    for n, fn in ((20, 'U0RXD'), (21, 'U0TXD')):
        out += [
            _c(n, 'bootloader', 'reserved', '%s (UART0) is one of the two download links of the joint download boot mode ("download binary files into flash using UART0 or USB")' % fn, DS,
               'Table 3-3 note 3 and the text below it, p.31', condition='transport=usb-serial'),
            _c(n, 'init', 'reserved', 'UART0 is the transport: the init must configure it, not claim %s as GPIO. On the DevKitM the USB connector reaches the chip through a USB-to-UART bridge '
               '(the TX/RX header pins are GPIO21 U0TXD / GPIO20 U0RXD)' % fn, KIT, 'Header Block, J3 table (TX = GPIO21, U0TXD; RX = GPIO20, U0RXD); component list "USB-to-UART Bridge"',
               condition='transport=usb-serial', verification='partial',
               undetermined='the guide does not name the bridge chip\'s two wires; that they are GPIO20/21 (UART0) follows from Zephyr\'s chosen console (uart0) and the TX/RX header labels'),
            _c(n, 'runtime', 'reserved', '%s carries the UART0 transport to the USB-UART bridge: a GPIO claim fights the bridge and corrupts the frames to the host' % fn, KIT,
               'Header Block, J3 table; component list "USB-to-UART Bridge"', condition='transport=usb-serial', verification='partial',
               undetermined='the bridge wiring (which pins, any series resistors) is not in the guide text; the schematic PDF was not read')]
    # ---- USB Serial/JTAG pads
    for n, fn in ((18, 'USB_D-'), (19, 'USB_D+')):
        out += [
            _c(n, 'init', 'conditional', '%s is, by default, connected to the USB Serial/JTAG controller; to be a GPIO the pad must be reconfigured (and the chip\'s own USB link is then gone)' % fn, DS,
               '§2.3.3 Restrictions for GPIOs p.22; Table 2-1 note 5 p.17', ack='usb-pads-as-gpio', notes='the module breaks the pad out as IO%d (MINI-1 Table 3-1 p.11)' % n),
            _c(n, 'runtime', 'conditional', 'as above: claiming %s as GPIO disables the USB Serial/JTAG function on it (USB pull-up controlled by USB_SERIAL_JTAG_DP/DM_PULLUP)' % fn, DS,
               '§2.3.3 p.22; Table 2-1 note 5 p.17', ack='usb-pads-as-gpio'),
            _c(n, 'runtime', 'reserved', '%s is the chip\'s own USB data line, and the USB link is the transport' % fn, DS, '§2.3.3 p.22; Table 2-7 note 1 p.24 (USB_D- / USB_D+ can be swapped)',
               condition='transport=usb-serial-jtag'),
            _c(n, 'debug', 'reserved', '%s carries the USB Serial/JTAG controller\'s JTAG adapter and flashing path' % fn, DS, '§4.2.1.5 USB Serial/JTAG Controller p.48', condition='transport=usb-serial-jtag'),
            _c(n, 'power-up', 'conditional', '%s: %s' % (fn, 'a HIGH-level glitch of about 50 us on GPIO18 at power-up' if n == 18 else 'the pull-up of GPIO19 is enabled by the USB pull-up (USB_PU) after reset'), DS,
               'Table 2-2 Power-Up Glitches on Pins p.18' if n == 18 else 'Table 2-1 "After Reset" column p.17 (USB_PU)', ack='power-up-glitch' if n == 18 else 'usb-pullup')]
    # ---- JTAG pads
    for n, fn in ((4, 'MTMS'), (5, 'MTDI'), (6, 'MTCK'), (7, 'MTDO')):
        out.append(_c(n, 'debug', 'conditional', '%s is a JTAG pad: "JTAG interface - often used for debugging"; the USB Serial/JTAG pins can be used instead to free these pads' % fn, DS,
                      '§2.3.3 Restrictions for GPIOs p.22; Table 2-3 p.19', condition='debug=jtag-pins', ack='jtag-pins-free'))
    # ---- power-up glitches (Table 2-2)
    for n, fn, g in ((6, 'MTCK', 'low-level glitch of about 5 ns'), (7, 'MTDO', 'low-level glitch of about 5 ns'), (10, 'GPIO10', 'low-level glitch of about 5 ns'), (20, 'U0RXD', 'low-level glitch of about 5 ns')):
        out.append(_c(n, 'power-up', 'conditional', '%s: %s at power-up (the pad is at a low output status during it): a load that reacts to 5 ns pulses sees it' % (fn, g), DS,
                      'Table 2-2 Power-Up Glitches on Pins p.18', ack='power-up-glitch'))
    # ---- the in-package flash
    mod = 'the ESP32-C3-MINI-1 module\'s flash is "integrated in the chip\'s package" (MINI-1 datasheet v2.2 p.4 note 4) and its Table 3-1 (p.11) lists no pin for it: NC'
    for n in range(12, 18):
        pn = {12: 'SPIHD', 13: 'SPIWP', 14: 'SPICS0', 15: 'SPICLK', 16: 'SPID', 17: 'SPIQ'}[n]
        for ph in ('init', 'runtime'):
            out.append(_c(n, ph, 'reserved', 'GPIO%d (%s) is wired to the in-package flash: "Do not use the pins connected to in-package flash for any other purposes"; %s' % (n, pn, mod), DS,
                          'Table 2-12 Pin Mapping Between Chip and In-package Flash p.29; §2.3.3 p.22; Table 2-7 priority P4, p.23-24',
                          undetermined='which chip variant is under his module is not read from the board; a variant with no bonded flash pads (ESP32-C3FH4X / FH4AZ: pins 19-24 not bonded, p.17 note 9) has none of these pads at all'))
    for ph in ('init', 'runtime'):
        out.append(_c(11, ph, 'reserved', 'GPIO11 is the VDD_SPI pin, "the power supply pin for flash by default, and can only be used as a GPIO pin if the flash is powered by an external power supply"; '
                      'the module breaks out no pin for it (NC)', DS, '§2.3.3 p.22; Table 2-1 note 8 p.17; MINI-1 Table 3-1 p.11',
                      undetermined='an off-package flash on its own supply would free the pin; this board\'s module has in-package flash'))
    # ---- the DevKitM's own loads
    out.append(_c(8, 'runtime', 'conditional', 'GPIO8 drives the DevKitM-1\'s addressable RGB LED ("Addressable RGB LED, driven by GPIO8") and is also a strapping pin: the LED is a load on the line', KIT,
                  'component list "RGB LED"; Header Block J3 pin 6 (IO8, "RGB LED")', ack='rgb-led', undetermined='the LED\'s data-line load is not in the guide text; the schematic PDF was not read'))
    out.append(_c(9, 'runtime', 'conditional', 'GPIO9 is the DevKitM\'s boot/user button (Zephyr devicetree: sw0 = user_button1 on gpio0 pin 9) and a strapping pin: pressing it pulls the line to the button\'s level',
                  ZEPHYR, 'esp32c3_devkitm.dts aliases sw0 / user_button1 (ingested verbatim); user guide component list "Boot Button" (download button)', ack='boot-button', verification='partial',
                  undetermined='the user guide names the Boot button but not its GPIO; the pin is Zephyr\'s'))
    for r in out:
        assert r['phase'] in PHASES and r['policy'] in POLICIES, r['name']
    return out
