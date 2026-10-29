"""
@module board.custom.esp32c3_chain_meta

c3pf: WHAT THE ESP32-C3's PERIPHERALS ARE CALLED and where each is cited - the vocabulary board.custom.hardware_chain_c3 builds the Peripheral /
PeripheralSignal / PinFunction rows from. Every peripheral cites a document + page (datasheet = 'ds', TRM = 'trm'); the signal -> peripheral assignment is
DERIVED from the signal name's prefix in TRM Table 5.11-1 (said on each row: `origin`), never typed per signal.
"""
#: peripheral id -> (kind, title, (doc, page/table cite), plain words, Table 2-7 interface column or '')
PERIPHERALS = {
    'GPIO': ('gpio-port', 'GPIO (22 pads, IO MUX + GPIO matrix)', ('trm', 'Chapter 5 IO MUX and GPIO Matrix, §5.1-5.2 pp.159-160; datasheet §4.1.3.1 p.36'),
             'The 22 pads: every pad is a general digital input/output; the GPIO matrix routes any peripheral signal to any pad.', ''),
    'GPIO_INT': ('gpio-int', 'GPIO interrupts (per-pad, through the interrupt matrix)', ('trm', 'Register 5.14 GPIO_PINn_REG (n: 0-21) GPIO_PINn_INT_TYPE, p.184; datasheet §4.1.3.1 p.36, §4.1.3.4 Interrupt Matrix p.37'),
                 'Any pad can raise a CPU interrupt on a rising edge, a falling edge, any edge, or a low or high level (GPIO_PINn_INT_TYPE).', ''),
    'UART0': ('usart', 'UART0', ('ds', '§4.2.1.1 UART Controller, p.46'), 'The first serial port; its IO MUX pins are GPIO20 (U0RXD) and GPIO21 (U0TXD).', 'UART0'),
    'UART1': ('usart', 'UART1', ('ds', '§4.2.1.1 UART Controller, p.46'), 'The second serial port; it has no IO MUX pins, so it reaches a pad only through the GPIO matrix.', 'UART1'),
    'SPI0_1': ('spi-flash', 'SPI0/SPI1 (the flash bus)', ('ds', '§4.2.1.2 SPI Controller, p.46; Table 2-12 p.29'), 'The memory bus to the flash; on a chip with in-package flash its pads belong to the flash.', 'SPI0/1'),
    'SPI2': ('spi', 'SPI2 (the general-purpose SPI)', ('ds', '§4.2.1.2 SPI Controller, pp.46-47'), 'The general-purpose SPI controller: master or slave, with six chip selects as a master.', 'SPI2'),
    'I2C0': ('twi', 'I2C (I2CEXT0)', ('ds', '§4.2.1.3 I2C Controller, p.47'), 'The two-wire bus controller, master or slave.', 'I2C'),
    'I2S': ('i2s', 'I2S', ('ds', '§4.2.1.4 I2S Controller, p.47'), 'The audio serial interface.', 'I2S'),
    'USB_SERIAL_JTAG': ('usb', 'USB Serial/JTAG controller', ('ds', '§4.2.1.5 USB Serial/JTAG Controller, p.48; Table 2-5 p.21'),
                        'A full-speed USB device on GPIO18 (USB_D-) and GPIO19 (USB_D+): a serial port and a JTAG adapter, with an integrated PHY.', ''),
    'TWAI': ('can', 'TWAI (CAN) controller', ('ds', '§4.2.1.6 Two-wire Automotive Interface, p.48'), 'A CAN 2.0 controller (ISO 11898-1).', 'TWAI'),
    'LEDC': ('timer', 'LED PWM controller (LEDC)', ('ds', '§4.2.1.7 LED PWM Controller, pp.48-49; TRM §32.2 Features, p.827'),
             'Six independent PWM channels from four timers, up to 14-bit duty resolution: the C3\'s PWM.', 'LEDPWM'),
    'RMT': ('rmt', 'Remote control peripheral (RMT)', ('ds', '§4.2.1.8 Remote Control Peripheral, p.49'), 'Two transmit and two receive channels of pulse waveforms (infrared and other single-wire protocols).', 'RMT'),
    'ADC1': ('adc', 'SAR ADC1', ('ds', '§4.2.2.1 SAR ADC, p.49; TRM §34.2 SAR ADCs, pp.868-869'), 'A 12-bit ADC with 5 channels (GPIO0-4), factory-calibrated; the TRM\'s threshold monitor can interrupt on a high/low threshold.', ''),
    'ADC2': ('adc', 'SAR ADC2', ('ds', '§4.2.2.1 SAR ADC, p.49; TRM §34.2.1 note p.868'), 'A 12-bit ADC with 1 channel (GPIO5); the TRM notes its DIG ADC controller "does not work properly" (see the SoC Errata).', ''),
    'JTAG': ('jtag', 'JTAG (MTCK/MTDO/MTDI/MTMS)', ('ds', 'Table 2-3 Peripheral Signals Routed via IO MUX, p.19'), 'The debug port on GPIO4-7, routed by the IO MUX only.', ''),
    'SDM': ('sdm', 'Sigma-delta modulated outputs', ('trm', '§5.5.4 Sigma Delta Modulated Output, p.165; Table 5.11-1 signals 55-58 p.171'), 'Four 1-bit second-order sigma-delta (PDM) outputs.', ''),
    'CPU_GPIO': ('cpu-gpio', 'CPU GPIO (direct CPU access)', ('trm', 'Table 5.11-1 signals 28-35, p.170'), 'Eight lines the CPU itself can read and drive through the matrix.', ''),
    'COEX': ('coexistence', 'Wi-Fi / Bluetooth coexistence lines', ('trm', 'Table 5.11-1 signals 18-19, p.169'), 'Priority and activity lines for an external radio coexistence scheme.', ''),
    'ANT_SEL': ('antenna-switch', 'Antenna select outputs', ('trm', 'Table 5.11-1 signals 89-96, p.172'), 'Eight outputs for an external antenna switch.', ''),
    'CLK_OUT': ('clock', 'Clock outputs', ('trm', 'Table 5.11-1 signals 123-125, p.173'), 'Three clock outputs.', ''),
    'GPIO_LOOPBACK': ('gpio-loopback', 'GPIO-to-GPIO loopback', ('trm', '§5.5.1 Note (signals 97-100), p.164'), 'Four signals wired input to output inside the matrix, so one pad\'s input can be sent straight to another pad.', ''),
    'XTAL32K': ('clock', '32 kHz crystal pads', ('ds', 'Table 2-5 Analog Signals Routed to Analog Functions, p.21'), 'The 32 kHz external clock pads (XTAL_32K_P on GPIO0, XTAL_32K_N on GPIO1).', ''),
    # rm-2b: the blocks the C3 drawing-set registers belong to that carry no pad signal (registers_esp32c3; TRM v1.4 chapter starts from its contents)
    'SYSTIMER': ('timer', 'System timer (52-bit, the IDF tick)', ('trm', 'Chapter 10 System Timer (SYSTIMER), p.270'), 'The 52-bit system timer FreeRTOS and esp_timer count on: UNIT0 is the count software latches and reads.', ''),
    'SYSTEM': ('system', 'System registers (clock gating + peripheral resets)', ('trm', 'Chapter 16 System Registers (SYSREG), p.427; Table 16.3-2 p.430'), 'Per-peripheral clock-enable and reset bits: a peripheral needs its clock on and its reset released before use.', ''),
    'RTC_CNTL': ('system', 'Low-power management (RTC control: reset state)', ('trm', 'Chapter 9 Low-power Management, p.219'), 'The RTC control block; here only its CPU reset-state register (the reset cause).', ''),
    'INTMTX': ('interrupt', 'Interrupt matrix', ('trm', 'Chapter 8 Interrupt Matrix (INTERRUPT), p.202'), 'Maps each peripheral interrupt source to one of the CPU interrupts (one map register per source).', ''),
}

#: signal-name prefix -> peripheral id; the first prefix that matches wins (FSPI before SPI: 'FSPIQ_in' starts with 'F')
PREFIX = (('FSPI', 'SPI2'), ('SPI', 'SPI0_1'), ('U0', 'UART0'), ('U1', 'UART1'), ('I2SO', 'I2S'), ('I2SI', 'I2S'), ('I2S_', 'I2S'), ('I2CEXT0', 'I2C0'),
          ('ledc_', 'LEDC'), ('rmt_', 'RMT'), ('twai_', 'TWAI'), ('usb_jtag', 'USB_SERIAL_JTAG'), ('cpu_gpio', 'CPU_GPIO'), ('gpio_sd', 'SDM'),
          ('gpio_bt', 'COEX'), ('gpio_wlan', 'COEX'), ('ant_sel', 'ANT_SEL'), ('CLK_OUT', 'CLK_OUT'), ('sig_in_func', 'GPIO_LOOPBACK'), ('ext_adc_start', 'ADC1'))


def peripheral_of_signal(name):
    for prefix, pid in PREFIX:
        if name.startswith(prefix):
            return pid
    raise KeyError('no peripheral for matrix signal %r' % name)


#: IO MUX function (datasheet Table 2-4 names) -> (peripheral, Table 5.11-1 INPUT signal or '', OUTPUT signal or '')
IOMUX = {
    'MTMS': ('JTAG', 'MTMS', ''), 'MTDI': ('JTAG', 'MTDI', ''), 'MTCK': ('JTAG', 'MTCK', ''), 'MTDO': ('JTAG', '', 'MTDO'),
    'U0RXD': ('UART0', 'U0RXD_in', ''), 'U0TXD': ('UART0', '', 'U0TXD_out'),
    'FSPIQ': ('SPI2', 'FSPIQ_in', 'FSPIQ_out'), 'FSPID': ('SPI2', 'FSPID_in', 'FSPID_out'), 'FSPIHD': ('SPI2', 'FSPIHD_in', 'FSPIHD_out'),
    'FSPIWP': ('SPI2', 'FSPIWP_in', 'FSPIWP_out'), 'FSPICLK': ('SPI2', 'FSPICLK_in', 'FSPICLK_out_mux'), 'FSPICS0': ('SPI2', 'FSPICS0_in', 'FSPICS0_out'),
    'SPIQ': ('SPI0_1', 'SPIQ_in', 'SPIQ_out'), 'SPID': ('SPI0_1', 'SPID_in', 'SPID_out'), 'SPIHD': ('SPI0_1', 'SPIHD_in', 'SPIHD_out'),
    'SPIWP': ('SPI0_1', 'SPIWP_in', 'SPIWP_out'), 'SPICLK': ('SPI0_1', '', 'SPICLK_out_mux'), 'SPICS0': ('SPI0_1', '', 'SPICS0_out'),
}
#: the Table 2-4 type column ('I1/O/T' ...) per IO MUX function name that has one (pp.19-20)
IOMUX_TYPE = {'MTMS': 'I1', 'MTDI': 'I1', 'MTCK': 'I1', 'MTDO': 'O/T', 'U0RXD': 'I1', 'U0TXD': 'O', 'FSPIQ': 'I1/O/T', 'FSPID': 'I1/O/T', 'FSPIHD': 'I1/O/T',
              'FSPIWP': 'I1/O/T', 'FSPICLK': 'I1/O/T', 'FSPICS0': 'I1/O/T', 'SPIQ': 'I1/O/T', 'SPID': 'I1/O/T', 'SPIHD': 'I1/O/T', 'SPIWP': 'I1/O/T',
              'SPICLK': 'O/T', 'SPICS0': 'O/T'}
#: Table 2-6 analog function -> (peripheral, direction)
ANALOG = {'ADC1_CH0': ('ADC1', 'in'), 'ADC1_CH1': ('ADC1', 'in'), 'ADC1_CH2': ('ADC1', 'in'), 'ADC1_CH3': ('ADC1', 'in'), 'ADC1_CH4': ('ADC1', 'in'),
          'ADC2_CH0': ('ADC2', 'in'), 'USB_D-': ('USB_SERIAL_JTAG', 'inout'), 'USB_D+': ('USB_SERIAL_JTAG', 'inout'),
          'XTAL_32K_P': ('XTAL32K', 'inout'), 'XTAL_32K_N': ('XTAL32K', 'inout')}
#: Table 2-7 p.23 reasons a pad is priority 3 / 4 for a matrix-routed interface (the section 2.3.4 bullets, verbatim in substance)
CAUTION = {2: 'strapping pin', 8: 'strapping pin', 9: 'strapping pin', 18: 'USB Serial/JTAG pad', 19: 'USB Serial/JTAG pad', 4: 'JTAG pad (MTMS)', 5: 'JTAG pad (MTDI)',
           6: 'JTAG pad (MTCK)', 7: 'JTAG pad (MTDO)', 20: 'UART0 pad (U0RXD)', 21: 'UART0 pad (U0TXD)', 11: 'VDD_SPI pin (the flash supply by default)',
           12: 'SPI0/1 flash pad', 13: 'SPI0/1 flash pad', 14: 'SPI0/1 flash pad', 15: 'SPI0/1 flash pad', 16: 'SPI0/1 flash pad', 17: 'SPI0/1 flash pad'}
