"""
@module board.custom.profile_overlap_cites

pp-1 (MISSION_PROFILE_SOLVER_PLAN.md §2.3): the CITATIONS the profile-overlap table stands on. Every rule in
board.custom.profile_overlap_rules names one or more keys of CITES; nothing is cited by memory.

Two kinds of source:
  - the ATmega328P datasheet (Microchip DS40002061B, 2020): `section`, `page` (the printed page number), and a short verbatim `quote`
    read from the document text on 2026-10-18 (the same document and revision board.custom.soc_atmega328p cites). The
    quote is what the rule leans on, so a reviewer can find it in seconds.
  - an existing rule of this code base (`kind: 'code'`): named by module and rule, never re-implemented here.

Tables 14-4 and 14-5 (Port B overriding signals) print an overbar on MSTR that the text of the datasheet loses; no rule here reads a
master/slave direction from them - SPI directions come from Table 19-1, p.171, which prints them in words.
"""
DOC = 'Microchip DS40002061B (ATmega48A/PA/88A/PA/168A/PA/328/P Data Sheet Complete, 2020)'


def _ds(section, page, quote):
    return {'kind': 'datasheet', 'doc': DOC, 'section': section, 'page': page, 'quote': quote}


def _code(where, rule):
    return {'kind': 'code', 'doc': where, 'section': rule, 'page': '', 'quote': ''}


CITES = {
    # ---- the general digital I/O pin (chapter 14.2)
    'pin-config': _ds('14.2.1 Configuring the Pin', 85, 'If PORTxn is written logic one when the pin is configured as an input pin, the pull-up resistor is activated'),
    'pin-toggle': _ds('14.2.2 Toggling the Pin', 85, 'the SBI instruction can be used to toggle one single bit in a port'),
    'pin-table': _ds('Table 14-1 Port Pin Configurations', 86, 'Pxn will source current if ext. pulled low'),
    'pinx-read': _ds('14.2.4 Reading the Pin Value', 86, 'Independent of the setting of Data Direction bit DDxn, the port pin can be read through the PINxn Register bit'),
    'sleep-int': _ds('14.2.5 Digital Input Enable and Sleep Modes', 88, 'SLEEP is overridden for port pins enabled as external interrupt pins'),
    # ---- alternate port functions (14.3)
    'alt-override': _ds('14.3 Alternate Port Functions', 89, 'pin control signals from the simplified Figure 14-2 on page 85 can be overridden by alternate functions'),
    'alt-signals': _ds('Table 14-2 Generic Description of Overriding Signals for Alternate Functions', 90, 'Generic Description of Overriding Signals for Alternate Functions'),
    'alt-c-twi': _ds('14.3.2 Alternate Functions of Port C (SCL/SDA)', 95, 'pin PC5 is disconnected from the port and becomes the Serial Clock I/O pin'),
    'alt-c-adc-twi': _ds('14.3.2 Alternate Functions of Port C (SDA/ADC4)', 95, 'PC4 can also be used as ADC input Channel 4'),
    'tbl-c-twi': _ds('Table 14-7 Overriding Signals for Alternate Functions in PC6...PC4', 96, 'PC5/SCL/ADC5/PCINT13'),
    'tbl-c-adc': _ds('Table 14-8 Overriding Signals for Alternate Functions in PC3...PC0', 97, 'PCINT11 • PCIE1'),
    'tbl-d-ain': _ds('Table 14-10 Overriding Signals for Alternate Functions PD7...PD4', 99, 'PD6/AIN0/'),
    'tbl-d-uart': _ds('Table 14-11 Overriding Signals for Alternate Functions in PD3...PD0', 99, 'PD1/TXD/'),
    'pin-tables': _ds('Tables 14-3 / 14-6 / 14-9 (alternate functions of Port B / C / D)', 91, 'Port B Pins Alternate Functions'),
    # ---- external interrupts (13)
    'exint-output': _ds('13 External Interrupts', 79, 'the interrupts will trigger even if the INT0 and INT1 or PCINT23...0 pins are configured as outputs'),
    'exint-sense': _ds('13.2.1 EICRA - External Interrupt Control Register A', 80, 'Interrupt Sense Control 0 Bit 1 and Bit 0'),
    'pcint-mask': _ds('13 External Interrupts (pin change vectors)', 79, 'The pin change interrupt PCI0 will trigger if any enabled PCINT[7:0] pin toggles'),
    # ---- analog
    'adc-didr-power': _ds('10.10.6 Port Pins', 52, 'For analog input pins, the digital input buffer should be disabled at all times'),
    'didr0': _ds('24.9.5 DIDR0 - Digital Input Disable Register 0', 261, 'The corresponding PIN Register bit will always read as zero when this bit is set'),
    'didr1': _ds('23.3.3 DIDR1 - Digital Input Disable Register 1', 245, 'The corresponding PIN Register bit will always read as zero when this bit is set'),
    'adc-output': _ds('24.6.2 Analog Noise Canceling Techniques (d)', 253, 'it is essential that these do not switch while a'),
    'adc-twi': _ds('24.6.2 Analog Noise Canceling Techniques (d)', 253, 'using the 2-wire Interface (ADC4 and ADC5) will only affect the'),
    'adc-mux': _ds('24.9.1 ADMUX - ADC Multiplexer Selection Register', 258, 'Single Ended Input'),
    'ac-mux': _ds('23.2 Analog Comparator Multiplexed Input', 243, 'the ADC must be switched off to utilize this'),
    # ---- timers
    'oc0': _ds('15.6 Compare Match Output Unit (Timer/Counter0)', 106, 'The general I/O port function is overridden by the Output Compare (OC0x) from the Waveform Generator'),
    'oc1': _ds('16.8 Compare Match Output Unit (Timer/Counter1)', 130, 'The general I/O port function is overridden by the Output Compare (OC1x) from the Waveform Generator'),
    'oc2': _ds('18.6 Compare Match Output Unit (Timer/Counter2)', 154, 'The general I/O port function is overridden by the Output Compare (OC2x) from the Waveform Generator'),
    'timer-mode': _ds('15.7 Modes of Operation (Timer/Counter0)', 107, 'The Compare Output mode bits do not affect the counting sequence, while the Waveform Generation mode bits do'),
    'timer-prescaler': _ds('17.2 Prescaler Reset', 147, 'it is shared by Timer/Counter1 and Timer/Counter0'),
    'timer-ext-clock': _ds('17.3 External Clock Source', 147, 'An external clock source applied to the T1/T0'),
    # ---- serial
    'spi-pins': _ds('19.2 Overview, Table 19-1 SPI Pin Overrides', 171, 'Direction, Master SPI'),
    'spi-override': _ds('19.2 Overview (SPI pin overrides)', 170, 'the data direction of the MOSI, MISO, SCK, and SS pins is overridden'),
    'spi-ss-master': _ds('19.3.2 Master Mode', 174, 'If SS is configured as an output, the pin is a general output pin which does not affect the SPI system'),
    'usart-tx': _ds('20.6 Data Transmission - The USART Transmitter', 185, 'the normal port operation of the TxDn pin is overridden by the USART'),
    'usart-rx': _ds('20.7 Data Reception - The USART Receiver', 188, 'the normal pin operation of the RxDn pin is overridden'),
    'usart-tx-off': _ds('20.6.5 Disabling the Transmitter', 188, 'the Transmitter will no longer override the TxDn pin'),
    'usart-rx-off': _ds('20.7.6 Disabling the Receiver', 191, 'the Receiver will no longer override the normal'),
    'usart-xck': _ds('20.3 Clock Generation (XCKn)', 180, 'controls whether the clock source is internal (Master mode) or external'),
    'twi-wired-and': _ds('22.2.2 Electrical Interconnection', 216, 'The bus drivers of all TWI-compliant devices are open-drain or open-collector'),
    # ---- code rules (named, never re-implemented)
    'single-output': _code('board.custom.electrical_check', "rule (b) single_output: a net with an output-role pin has EXACTLY one output"),
    'compat': _code('board.custom.target_compat', 'compatible(): which pin offers which task kind (SocPin alternate functions)'),
    'claims-timer': _code('cmod.custom.claims', "peripheral_claims rule 'timer-channel-split': Timer0/1 channels A and B are claimed apart, the clock/mode registers are shared-config"),
    'claims-usart': _code('cmod.custom.claims', "_USAGE_BY_PERIPHERAL: USART0, SPI, TWI, EXINT, PCINT are exclusive; ADC shared-read; GPIO ports shared-config"),
    'lifecycle': _code('board PinLifecycleConstraint rows (cmod.custom.pin_profile_mission._reserved_transport)',
                       "policy 'reserved' on the transport pins; condition transport=usb-serial (init, runtime), unconditional in the bootloader phase"),
    'pull-rule': _code('board.custom.electrical_check', 'rule (e): the button pull is DEFINED - external resistor or a PinClaim pull=up'),
}


def render(key):
    """One plain-words citation line for a CITES key."""
    c = CITES[key]
    if c['kind'] == 'datasheet':
        return 'ATmega328P datasheet DS40002061B, %s, p.%s' % (c['section'], c['page'])
    return '%s - %s' % (c['doc'], c['section'])
