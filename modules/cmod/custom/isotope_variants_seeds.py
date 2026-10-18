"""
@module cmod.custom.isotope_variants_seeds

The DECLARED catalogue (iso-0, MISSION_PROFILE_SOLVER_PLAN.md section 8.3): the jobs a C atom does and every route that can do each one. Only what a
person or the plan declares lives here: the words, the pin profiles (TASK_KINDS kinds), the chip blocks and extra parts a route needs, the lowest
runtime tier, the ESTIMATED / UNDETERMINED costs (each with its basis) and the links to the atoms that implement it today. Everything that follows
from what EXISTS (status, on-bench, measured costs, eligibility) is worked out in `cmod.custom.isotope_variants` and has no field in these rows.

Cost entries are {kind: estimated|undetermined, value, unit, basis}. The pins / peripherals / parts counts are not stored at all: they are counted
from the route's own lists when asked. The sizes (flash, RAM) are `undetermined` until a build exists to measure, except where another route's
measured C is the very same code (`shares_c_with`).
"""
import json

#: the route vocabulary (the name after the colon in '<job>:<route>')
ROUTES = ('gpio-poll', 'ext-interrupt', 'pin-change-interrupt', 'analog-threshold', 'analog-comparator', 'spi-shift-register', 'i2c-expander',
          'gpio-out', 'pwm', 'transistor-switch', 'analog-sensor', 'one-wire', 'i2c-sensor', 'spi-sensor', 'analog-read', 'uart-tx', 'uart-rx-interrupt')
#: the on-chip block kinds a route can claim (checked against the board's Peripheral rows, or the dts list on a board without them)
PERIPHERAL_KINDS = ('gpio-port', 'exint', 'pcint', 'adc', 'comparator', 'spi', 'twi', 'timer-pwm', 'usart')

_WIKI = {'interrupt': ('Wikipedia - Interrupt', 'https://en.wikipedia.org/wiki/Interrupt'),
         'shift': ('Wikipedia - Shift register', 'https://en.wikipedia.org/wiki/Shift_register'),
         'spi': ('Wikipedia - Serial Peripheral Interface', 'https://en.wikipedia.org/wiki/Serial_Peripheral_Interface'),
         'i2c': ('Wikipedia - I2C', 'https://en.wikipedia.org/wiki/I%C2%B2C'),
         'onewire': ('Wikipedia - 1-Wire', 'https://en.wikipedia.org/wiki/1-Wire'),
         'pwm': ('Wikipedia - Pulse-width modulation', 'https://en.wikipedia.org/wiki/Pulse-width_modulation'),
         'comparator': ('Wikipedia - Comparator', 'https://en.wikipedia.org/wiki/Comparator'),
         'adc': ('Wikipedia - Analog-to-digital converter', 'https://en.wikipedia.org/wiki/Analog-to-digital_converter'),
         'uart': ('Wikipedia - UART', 'https://en.wikipedia.org/wiki/Universal_asynchronous_receiver-transmitter')}
_DS = 'ATmega328P datasheet DS40002061B'


def _c(key):
    label, url = _WIKI[key]
    return {'label': label, 'ref': url}


def _est(value, unit, basis):
    return {'kind': 'estimated', 'value': value, 'unit': unit, 'basis': basis}


def _und(basis):
    return {'kind': 'undetermined', 'value': None, 'unit': '', 'basis': basis}


_NO_BUILD = 'no atom or template for this route has been built yet, so there is nothing to measure (fgm-5 builds templates; the twin then measures them)'


def _pr(kind, role, count=1, note='', **extra):
    return dict({'kind': kind, 'role': role, 'count': count, 'note': note}, **extra)


def _pt(klass, why, kit_keys=(), terms=(), spec=None):
    return {'class': klass, 'why': why, 'kit_keys': list(kit_keys), 'terms': list(terms), 'spec': spec}


def _pe(kind, why):
    return {'kind': kind, 'why': why}


_BUTTON = _pt('pushbutton', 'the switch being read', ('pushbutton',))
_PULL = _pt('resistors', 'a pull-up or pull-down (the internal pull-up can replace it on a direct pin)', ('resistors',))
_LED = _pt('led', 'the light', ('led',))
_LED_R = _pt('series resistor 220 ohm', 'limits the LED current', ('resistors',), spec={'ohms': 220})
_SR_IN = _pt('74HC165-class parallel-in shift register', 'reads 8 switches onto a serial line', (), ('74hc165', 'parallel-in', 'shift register'))
_SR_OUT = _pt('74HC595-class serial-in shift register', 'drives 8 outputs from a serial line', (), ('74hc595', 'serial-in', 'shift register'))
_EXPANDER = _pt('PCF8574-class I2C I/O expander', 'puts 8 inputs/outputs on the two-wire bus', (), ('pcf8574', 'mcp23', 'expander'))
_I2C_PULL = _pt('I2C pull-up resistors (4.7 kohm)', 'the bus lines idle high through them', ('resistors',), spec={'ohms': 4700})


def _v(job, route, title, plain, profiles, peripherals, parts, wasteful, cost, minimum_level='bare-c', implemented=None, cites=(), notes=''):
    full = {'flash_bytes': _und(_NO_BUILD), 'ram_bytes': _und(_NO_BUILD)}
    full.update(cost)
    return {'name': '%s:%s' % (job, route), 'job': job, 'route': route, 'title': title, 'plain': plain,
            'profiles_json': json.dumps(profiles), 'peripherals_json': json.dumps(peripherals), 'parts_json': json.dumps(parts),
            'minimum_level': minimum_level, 'cost_json': json.dumps(full), 'wastefulness_note': wasteful,
            'implemented_by_json': json.dumps(implemented or {}), 'citations_json': json.dumps(list(cites)), 'notes': notes}


#: a route that is only the same C as another, wired differently (the cost is borrowed, the status is not)
def _shares(variant, note):
    return {'shares_c_with': variant, 'shares_note': note}


JOB_SEEDS = [
    {'name': 'read-button', 'title': 'Read the button', 'direction': 'in', 'uses_macro': 'BUTTON_PIN',
     'plain': 'Know when a person presses the button, so the firmware can react.',
     'purposes_json': json.dumps(['ensure-button-controls-light', 'light-from-button', 'button-clock-to-os']),
     'atoms_json': json.dumps(['uno:hal.hal_button_init', 'uno:hal.hal_presses', 'uno:hal.INT0_vect']),
     'notes': 'Seeded from the atoms of the UNO button demo (D2 on INT0).'},
    {'name': 'drive-led', 'title': 'Drive the LED', 'direction': 'out', 'uses_macro': 'LED_PIN',
     'plain': 'Switch a light on and off (or set how bright it is) when the firmware says so.',
     'purposes_json': json.dumps(['ensure-polari-can-control-light', 'light-from-polari', 'blink-on-command', 'ensure-button-controls-light']),
     'atoms_json': json.dumps(['uno:hal.hal_led_init', 'uno:hal.hal_led', 'uno:hal.hal_pwm_init', 'uno:hal.hal_pwm_apply']),
     'notes': 'Seeded from the atoms of the UNO light demo (the LED on D6 / D13).'},
    {'name': 'sense-led-line', 'title': 'Sense the LED line', 'direction': 'in', 'uses_macro': 'SENSE_PIN',
     'plain': 'Watch the wire that powers the light, so the firmware has its own independent proof that the light really switched.',
     'purposes_json': json.dumps(['ensure-polari-observes-hardware-state', 'button-clock-to-os']),
     'atoms_json': json.dumps(['uno:hal.hal_sense_init', 'uno:hal.hal_sense_read', 'uno:hal.INT1_vect']),
     'notes': 'Seeded from the atoms of the UNO button-clock demo (the D6 to D3 jumper, INT1).'},
    {'name': 'read-temperature', 'title': 'Read the temperature', 'direction': 'in', 'uses_macro': '',
     'plain': 'Measure how warm it is and hand the number up.',
     'purposes_json': json.dumps(['temp-sensor-to-os', 'uno-sim-rig-graph:temperature-sensor-solution']),
     'atoms_json': json.dumps(['uno:hal.hal_adc_init', 'uno:hal.hal_adc_read']),
     'notes': 'Seeded from the atoms of the UNO sim-rig (the TMP36 on A0).'},
    {'name': 'report-state', 'title': 'Report the state upward', 'direction': 'transport', 'uses_macro': '',
     'plain': 'Send the board\'s state to Polari as a frame, so Polari can see what the board did.',
     'purposes_json': json.dumps(['ensure-polari-observes-hardware-state', 'light-from-polari', 'sim-rig-serial-link']),
     'atoms_json': json.dumps(['uno:hal.hal_usart_send']),
     'notes': 'Only the serial route exists as an atom; other transports (SPI, I2C, USB-CDC on a board that has it) are not catalogued yet.'},
    {'name': 'receive-command', 'title': 'Receive a command', 'direction': 'transport', 'uses_macro': '',
     'plain': 'Take a command frame from Polari (for example "turn the light on") and hand it to the firmware.',
     'purposes_json': json.dumps(['ensure-polari-can-control-light', 'light-from-polari', 'blink-on-command', 'sim-rig-serial-link']),
     'atoms_json': json.dumps(['uno:hal.hal_rx_pop', 'uno:hal.USART_RX_vect']),
     'notes': 'Only the serial route exists as an atom; other transports are not catalogued yet.'},
]

_INT = 'External Interrupts and Pin Change Interrupt chapters of the %s - exact page not reconfirmed (see board.custom.target_compat.INT_DOC_NOTE)' % _DS
VARIANT_SEEDS = [
    # ------------------------------------------------------------------ read the button (7)
    _v('read-button', 'gpio-poll', 'Watch the pin in the main loop',
       'The main loop reads the pin each pass and notices when it changed. No interrupt and no chip block beyond the pin itself.',
       [_pr('digital-in', 'the button')], [_pe('gpio-port', 'the port that reads the pin')], [_BUTTON, _PULL],
       'A fine default when the loop runs fast and a missed press does not matter. Poor when the loop sleeps or blocks, because a press between two looks is lost; the only route that needs no scarce pin or block.',
       {'cpu_share': _est('one register read per main-loop pass', 'per pass', 'structure of the route: a read and a compare each pass; no measurement of the loop period exists'),
        'latency': _est('up to one main-loop pass; a press shorter than a pass can be missed', '', 'structure of the route (polling)')},
       cites=[_c('interrupt')]),
    _v('read-button', 'ext-interrupt', 'External interrupt (INT0 / INT1)',
       'A dedicated interrupt pin raises an interrupt on the press; the ISR counts and marks it and the main loop reacts. This is how the UNO button demo does it today (D2 on INT0, falling edge, internal pull-up).',
       [_pr('interrupt-in', 'the button', note='must be a pin that carries INT0 or INT1', functions_any=['INT0', 'INT1'])],
       [_pe('exint', 'the external-interrupt unit'), _pe('gpio-port', 'the port that holds the pin')], [_BUTTON],
       'Usually the best choice for a button: nothing to poll and no press is missed. But only two pins can do it on the UNO (INT0, INT1), so it is a poor use of a scarce pin when there are many buttons; pin-change is the next choice.',
       {'cpu_share': _est('none while idle; one short ISR per edge', '', 'structure of the route: the hardware calls the ISR on the edge'),
        'latency': _est('the next instruction boundary after the edge (no polling delay)', '', '%s; the response in clock cycles was not re-read this session' % _INT)},
       implemented={'atoms': ['uno:hal.hal_button_init', 'uno:hal.hal_presses', 'uno:hal.INT0_vect'], 'config': 'uno-button-clock',
                    'proof_purposes': ['ensure-button-controls-light', 'light-from-button', 'button-clock-to-os']},
       cites=[{'label': 'target_compat INT_DOC_NOTE', 'ref': _INT}, _c('interrupt')]),
    _v('read-button', 'pin-change-interrupt', 'Pin-change interrupt (PCINT)',
       'Almost any pin can raise a pin-change interrupt; one vector serves a whole group of pins, so the ISR reads the group to see which pin moved.',
       [_pr('interrupt-in', 'the button', note='any pin that carries a PCINTn function', functions_any=['PCINT*'])],
       [_pe('pcint', 'the pin-change interrupt unit (one enable per bank, one mask bit per pin)'), _pe('gpio-port', 'the port that holds the pin')], [_BUTTON],
       'The first fallback when INT0 / INT1 are taken: almost every pin can do it. Slightly more work in the ISR (it must find which pin of the bank changed and which edge), and it fires on both edges.',
       {'cpu_share': _est('none while idle; one ISR per edge on any pin of the bank', '', 'structure of the route'),
        'latency': _est('the next instruction boundary after the edge, plus the ISR deciding which pin moved', '', '%s' % _INT)},
       cites=[{'label': 'target_compat INT_DOC_NOTE', 'ref': _INT}, _c('interrupt')]),
    _v('read-button', 'analog-threshold', 'Read it as a voltage on an ADC pin and compare',
       'The button pulls an analog pin through a resistor divider; the firmware does an ADC conversion and decides "pressed" when the number passes a threshold.',
       [_pr('analog-in', 'the button (as a voltage)', functions_any=['ADC*'])], [_pe('adc', 'one conversion per look'), ],
       [_BUTTON, _pt('divider resistor 10 kohm', 'makes the button a voltage the ADC can read', ('resistors',), spec={'ohms': 10000})],
       'Wasteful: it ties up an ADC channel and a conversion per look to answer a yes/no question. Right only when every digital-capable pin is taken and an ADC pin is free; it also lets several buttons share one pin through different resistor values.',
       {'cpu_share': _est('one blocking ADC conversion per look', 'per look', 'the measured hal_adc_read is a blocking conversion (its text size is measured; its duration is not)'),
        'latency': _est('one polling pass plus one conversion', '', 'structure of the route (polled ADC)'),
        'flash_bytes': _est(50, 'bytes', 'LOWER BOUND: the measured ADC init + read atoms of read-temperature:analog-sensor (14 + 36 B); the threshold compare is not measured'),
        'ram_bytes': _est(0, 'bytes', 'LOWER BOUND: the measured ADC atoms touch no file-scope global')},
       cites=[_c('adc')], notes='Shares its C (hal_adc_init / hal_adc_read) with read-temperature:analog-sensor; no firmware wires it to a button.'),
    _v('read-button', 'analog-comparator', 'Analog comparator (AIN0 / AIN1)',
       'The chip\'s comparator compares the button\'s voltage with a reference on the other input and raises a flag or an interrupt when it crosses. No conversion needed.',
       [_pr('analog-in', 'the button (as a voltage on AIN1) and its reference (AIN0)', 2,
            note='AIN0 / AIN1 feed the Analog Comparator, not the ADC multiplexer: TASK_KINDS has no comparator kind, so analog-in is the closest entry (a vocabulary gap for pp-0)',
            functions_all=['AIN0', 'AIN1'])],
       [_pe('comparator', 'the analog comparator'), _pe('gpio-port', 'the port that holds the two pins')],
       [_BUTTON, _pt('reference divider (potentiometer or two resistors)', 'sets the threshold on the other input', ('potentiometer', 'resistors'))],
       'Wasteful for one button: it takes both comparator pins and a reference voltage. It can be the only route left when only the AIN pins are free, and it keeps the ADC free; it also wakes the chip without a conversion.',
       {'cpu_share': _est('none while idle (hardware compares); an optional interrupt on the crossing', '', 'structure of the route'),
        'latency': _est('hardware-compared; no conversion delay', '', 'structure of the route; the comparator\'s propagation delay was not read')},
       cites=[{'label': '%s - Analog Comparator chapter (register_profile cites DIDR1 at section 23.3.3, p.245)' % _DS, 'ref': 'board.custom.register_profile'}, _c('comparator')]),
    _v('read-button', 'spi-shift-register', 'Through an SPI shift register (74HC165 class)',
       'The button sits on one input of a parallel-in shift register; the firmware pulses its load pin, then clocks the bits in over SPI and picks out the button\'s bit.',
       [_pr('spi-sck', 'the register\'s clock'), _pr('spi-miso', 'the register\'s serial output'), _pr('digital-out', 'the register\'s load pin')],
       [_pe('spi', 'the SPI block'), _pe('gpio-port', 'the port that holds the load pin')], [_BUTTON, _SR_IN, _PULL],
       'Very wasteful for a button: three pins, the whole SPI block and an extra chip to read one switch. It pays off at scale (one chip reads 8 inputs on the same 3 pins) and is the route left when no direct pin is free but the SPI block is. Needs a part the bench does not have.',
       {'cpu_share': _est('one bus transaction per look (a load pulse and a clocked byte)', 'per look', 'structure of the route'),
        'latency': _est('one polling pass plus one bus transaction', '', 'structure of the route')},
       cites=[_c('shift'), _c('spi')]),
    _v('read-button', 'i2c-expander', 'Through an I2C I/O expander (PCF8574 class)',
       'The button sits on an input of an I2C expander chip; the firmware reads the chip over the two-wire bus (or gets an interrupt line from it).',
       [_pr('i2c-sda', 'the bus data line'), _pr('i2c-scl', 'the bus clock line')],
       [_pe('twi', 'the two-wire (I2C) block')], [_BUTTON, _EXPANDER, _I2C_PULL],
       'Wasteful for one button: two pins, the bus block and an extra chip. It pays off with many inputs (8 per chip on the same 2 pins, shared with other devices) and is the route left when only the bus pins are free. Needs a part the bench does not have.',
       {'cpu_share': _est('one bus transaction per look', 'per look', 'structure of the route (blocking bus read)'),
        'latency': _est('one polling pass plus one bus transaction', '', 'structure of the route')},
       cites=[_c('i2c')]),
    # ------------------------------------------------------------------ drive the LED (5)
    _v('drive-led', 'gpio-out', 'A plain output pin',
       'The firmware sets one output pin high or low; the LED (with its resistor) is wired to it. This is how the UNO light demo does it (D6, and the on-board L on D13).',
       [_pr('digital-out', 'the LED')], [_pe('gpio-port', 'the port that drives the pin')], [_LED, _LED_R],
       'The best default for on/off: one pin, no chip block, no extra part. Limited to the current one pin may source (the UNO pinout lists 20 mA per pin); for more, use the transistor route.',
       {'cpu_share': _est('one register write per change', 'per change', 'structure of the route'),
        'latency': _est('one register write after the decision', '', 'structure of the route')},
       implemented={'atoms': ['uno:hal.hal_led_init', 'uno:hal.hal_led'], 'config': 'uno-light',
                    'proof_purposes': ['ensure-polari-can-control-light', 'light-from-polari', 'blink-on-command']},
       cites=[{'label': 'board.custom.uno_facts pinout.max_current_io', 'ref': 'the UNO pinout (per-pin current limit)'}]),
    _v('drive-led', 'pwm', 'A timer\'s PWM output (dimming)',
       'A timer compare output switches the pin on and off very fast; the duty cycle sets the brightness. The UNO sim-rig does this on D6 (Timer0).',
       [_pr('pwm-out', 'the LED', functions_any=['OC*'])], [_pe('timer-pwm', 'a timer in PWM mode'), _pe('gpio-port', 'the port that holds the pin')], [_LED, _LED_R],
       'Only worth it when brightness is needed: it occupies a timer and one of the few PWM pins, which a plain on/off LED does not need. The only route that dims.',
       {'cpu_share': _est('none while running (the timer switches the pin); a register write to change the duty', '', 'structure of the route'),
        'latency': _est('one register write; the new duty applies within one PWM period', '', 'structure of the route; the PWM period was not measured here')},
       implemented={'atoms': ['uno:hal.hal_pwm_init', 'uno:hal.hal_pwm_apply'], 'config': 'uno-sim-rig', 'proof_purposes': []},
       cites=[_c('pwm')]),
    _v('drive-led', 'spi-shift-register', 'Through an SPI shift register (74HC595 class)',
       'The firmware clocks a byte into a serial-in shift register over SPI and pulses its latch; the LED is on one of the register\'s outputs.',
       [_pr('spi-mosi', 'the register\'s serial input'), _pr('spi-sck', 'the register\'s clock'), _pr('digital-out', 'the register\'s latch pin')],
       [_pe('spi', 'the SPI block'), _pe('gpio-port', 'the port that holds the latch pin')], [_LED, _LED_R, _SR_OUT],
       'Very wasteful for one LED: three pins, the SPI block and an extra chip. It pays off at scale (8 outputs from the same 3 pins) and is the route left when no direct pin is free. Needs a part the bench does not have.',
       {'cpu_share': _est('one bus transaction per change', 'per change', 'structure of the route'),
        'latency': _est('one clocked byte plus a latch pulse after the decision', '', 'structure of the route')},
       cites=[_c('shift'), _c('spi')]),
    _v('drive-led', 'i2c-expander', 'Through an I2C I/O expander (PCF8574 class)',
       'The firmware writes the LED\'s bit to an I2C expander chip over the two-wire bus; the LED is on one of its outputs.',
       [_pr('i2c-sda', 'the bus data line'), _pr('i2c-scl', 'the bus clock line')], [_pe('twi', 'the two-wire (I2C) block')], [_LED, _LED_R, _EXPANDER, _I2C_PULL],
       'Wasteful for one LED: two pins, the bus block and an extra chip. It pays off with many outputs (shared with other bus devices) and is the route left when only the bus pins are free. Needs a part the bench does not have.',
       {'cpu_share': _est('one bus transaction per change', 'per change', 'structure of the route'),
        'latency': _est('one bus write after the decision', '', 'structure of the route')},
       cites=[_c('i2c')]),
    _v('drive-led', 'transistor-switch', 'A pin through a transistor or MOSFET (more current)',
       'The firmware sets one output pin as before, but the pin drives the base (or gate) of a transistor or MOSFET that switches the LED (or a bigger light) from the supply.',
       [_pr('digital-out', 'the transistor\'s base / gate')], [_pe('gpio-port', 'the port that drives the pin')],
       [_pt('transistor or MOSFET', 'switches a load the pin cannot drive', ('transistor', 'mosfet')), _pt('base resistor', 'limits the pin\'s current into the base', ('resistors',)), _LED, _LED_R],
       'Not wasteful on pins (still one) but it adds parts. The right route when the load needs more current than one pin may give; one LED does not.',
       {'cpu_share': _est('one register write per change', 'per change', 'same C as drive-led:gpio-out'),
        'latency': _est('one register write after the decision, plus the transistor\'s switching time', '', 'structure of the route'),
        'flash_bytes': _est(16, 'bytes', 'the same C as drive-led:gpio-out (hal_led_init 4 B + hal_led 12 B, measured in uno-sim-rig); only the wiring differs'),
        'ram_bytes': _est(0, 'bytes', 'the same C as drive-led:gpio-out (no file-scope global touched)')},
       implemented=_shares('drive-led:gpio-out', 'the C is the plain output atoms; no firmware or circuit wires a transistor yet'),
       cites=[{'label': 'board.custom.kit_parts (transistor, MOSFET)', 'ref': 'Arduino Starter Kit book, Parts in your kit'}]),
    # ------------------------------------------------------------------ read the temperature (4)
    _v('read-temperature', 'analog-sensor', 'Analog sensor on an ADC pin (TMP36)',
       'The sensor outputs a voltage that follows the temperature; the firmware does one ADC conversion and turns the number into degrees. The UNO sim-rig does this on A0.',
       [_pr('analog-in', 'the temperature sensor', functions_any=['ADC*'])], [_pe('adc', 'one conversion per sample')], [_pt('TMP36 analog temperature sensor', 'the sensor', ('tmp36',))],
       'The cheapest route and the one the bench supports: one ADC pin, no bus, a part in the kit. Limited by the converter\'s resolution and reference.',
       {'cpu_share': _est('one blocking conversion per sample', 'per sample', 'hal_adc_read is a blocking conversion; its duration was not measured'),
        'latency': _est('one conversion per sample', '', 'structure of the route')},
       implemented={'atoms': ['uno:hal.hal_adc_init', 'uno:hal.hal_adc_read'], 'config': 'uno-sim-rig', 'proof_purposes': ['temp-sensor-to-os']},
       cites=[_c('adc')]),
    _v('read-temperature', 'one-wire', '1-Wire digital sensor (DS18B20 class)',
       'A digital sensor on one data wire answers a command with the temperature as a number; several sensors can share the wire.',
       [_pr('digital-out', 'the data wire, driven while sending', note='the same pin as the line below (one bidirectional wire)'),
        _pr('digital-in', 'the data wire, read while listening', note='the same pin as the line above', same_pin=True)],
       [_pe('gpio-port', 'the port that holds the pin')], [_pt('DS18B20-class 1-Wire temperature sensor', 'the sensor', (), ('ds18b20', '1-wire', 'one-wire')),
                                                          _pt('pull-up resistor 4.7 kohm', 'the wire idles high through it', ('resistors',), spec={'ohms': 4700})],
       'Spends one pin and needs timing-exact code, but gives a ready number and scales to many sensors on the same wire. A good route when the analog route has no free ADC pin. Needs a part the bench does not have.',
       {'cpu_share': _est('busy for the whole timed exchange (the bit timing is done in software)', 'per sample', 'structure of the route: the protocol is bit-timed'),
        'latency': _est('one exchange per sample (conversion time is the part\'s, not read)', '', 'structure of the route')},
       cites=[_c('onewire')]),
    _v('read-temperature', 'i2c-sensor', 'I2C digital sensor (TMP102 class)',
       'A digital sensor on the two-wire bus answers a read with the temperature as a number.',
       [_pr('i2c-sda', 'the bus data line'), _pr('i2c-scl', 'the bus clock line')], [_pe('twi', 'the two-wire (I2C) block')],
       [_pt('TMP102-class I2C temperature sensor', 'the sensor', (), ('tmp102', 'i2c temperature')), _I2C_PULL],
       'Two pins and the bus block, but the bus is shared with other devices, so the cost of a second I2C sensor is almost nothing. Needs a part the bench does not have.',
       {'cpu_share': _est('one bus transaction per sample', 'per sample', 'structure of the route'),
        'latency': _est('one bus read per sample', '', 'structure of the route')},
       cites=[_c('i2c')]),
    _v('read-temperature', 'spi-sensor', 'SPI digital sensor (thermocouple-converter class)',
       'A converter chip reads a thermocouple and hands the temperature out over SPI when selected.',
       [_pr('spi-sck', 'the converter\'s clock'), _pr('spi-miso', 'the converter\'s serial output'), _pr('spi-ss', 'the converter\'s select line')],
       [_pe('spi', 'the SPI block')], [_pt('thermocouple-converter-class SPI sensor (MAX31855 class)', 'the sensor and its thermocouple', (), ('max31855', 'thermocouple'))],
       'Three pins and the SPI block (shared, with one select line per device); the route for high temperatures a TMP-class part cannot reach. Needs a part the bench does not have.',
       {'cpu_share': _est('one bus transaction per sample', 'per sample', 'structure of the route'),
        'latency': _est('one bus read per sample', '', 'structure of the route')},
       cites=[_c('spi')]),
    # ------------------------------------------------------------------ sense the LED line (4)
    _v('sense-led-line', 'ext-interrupt', 'External interrupt (INT1)',
       'The LED line is jumpered to an interrupt pin; the ISR counts and time-stamps every edge. The UNO button-clock demo does this on D3 (INT1, any edge).',
       [_pr('interrupt-in', 'the LED line', note='must be a pin that carries INT0 or INT1', functions_any=['INT0', 'INT1'])],
       [_pe('exint', 'the external-interrupt unit'), _pe('gpio-port', 'the port that holds the pin')], [_pt('jumper wire', 'joins the LED line to the sensing pin', ('jumper-wires',))],
       'Catches every edge, even short blinks, with no polling. Spends one of the two INT pins; pin-change is the fallback.',
       {'cpu_share': _est('none while idle; one ISR per edge', '', 'structure of the route'),
        'latency': _est('the next instruction boundary after the edge', '', '%s' % _INT)},
       implemented={'atoms': ['uno:hal.hal_sense_init', 'uno:hal.hal_sense_read', 'uno:hal.INT1_vect'], 'config': 'uno-button-clock',
                    'proof_purposes': ['button-clock-to-os']},
       cites=[{'label': 'target_compat INT_DOC_NOTE', 'ref': _INT}]),
    _v('sense-led-line', 'pin-change-interrupt', 'Pin-change interrupt (PCINT)',
       'The LED line is jumpered to any pin-change-capable pin; the ISR finds which pin of its bank moved.',
       [_pr('interrupt-in', 'the LED line', note='any pin that carries a PCINTn function', functions_any=['PCINT*'])],
       [_pe('pcint', 'the pin-change interrupt unit'), _pe('gpio-port', 'the port that holds the pin')], [_pt('jumper wire', 'joins the LED line to the sensing pin', ('jumper-wires',))],
       'The fallback when INT0 / INT1 are taken. The ISR has more to do (which pin, which edge).',
       {'cpu_share': _est('none while idle; one ISR per edge on any pin of the bank', '', 'structure of the route'),
        'latency': _est('the next instruction boundary after the edge, plus the ISR deciding which pin moved', '', '%s' % _INT)},
       cites=[{'label': 'target_compat INT_DOC_NOTE', 'ref': _INT}]),
    _v('sense-led-line', 'gpio-poll', 'Watch the pin in the main loop',
       'The main loop reads the sensing pin each pass and notices a change.',
       [_pr('digital-in', 'the LED line')], [_pe('gpio-port', 'the port that reads the pin')], [_pt('jumper wire', 'joins the LED line to the sensing pin', ('jumper-wires',))],
       'Needs nothing scarce, but a blink shorter than one main-loop pass is missed, so it can under-count. Fine when the LED only changes slowly (a person-driven toggle).',
       {'cpu_share': _est('one register read per main-loop pass', 'per pass', 'structure of the route'),
        'latency': _est('up to one main-loop pass', '', 'structure of the route (polling)')}),
    _v('sense-led-line', 'analog-read', 'Read the line as a voltage on an ADC pin',
       'The LED line is jumpered to an ADC pin; the firmware converts it and compares with a threshold (and so also sees a dimmed level).',
       [_pr('analog-in', 'the LED line', functions_any=['ADC*'])], [_pe('adc', 'one conversion per look')], [_pt('jumper wire', 'joins the LED line to the sensing pin', ('jumper-wires',))],
       'Wasteful for a yes/no question (an ADC channel and a conversion per look), but it is the only route that sees how bright a PWM-dimmed LED is, and the one left when only ADC pins are free.',
       {'cpu_share': _est('one blocking conversion per look', 'per look', 'hal_adc_read is a blocking conversion; its duration was not measured'),
        'latency': _est('one polling pass plus one conversion', '', 'structure of the route'),
        'flash_bytes': _est(50, 'bytes', 'LOWER BOUND: the measured ADC init + read atoms of read-temperature:analog-sensor (14 + 36 B); the threshold compare is not measured'),
        'ram_bytes': _est(0, 'bytes', 'LOWER BOUND: the measured ADC atoms touch no file-scope global')},
       cites=[_c('adc')], notes='Shares its C (hal_adc_init / hal_adc_read) with read-temperature:analog-sensor; no firmware wires it to the LED line.'),
    # ------------------------------------------------------------------ transport (the atoms that exist; other transports are not catalogued)
    _v('report-state', 'uart-tx', 'Serial transmit (USART0)',
       'The firmware sends the state frame byte by byte on the serial port, which the board\'s USB bridge carries to the host. The only route catalogued; others (SPI, I2C, a native USB port) are not.',
       [_pr('uart-tx', 'the state frame out')], [_pe('usart', 'the serial block')], [_pt('USB cable to the host (through the board\'s USB bridge)', 'carries the serial line', ('usb-cable',))],
       'The only route catalogued, so nothing to call wasteful; it takes the board\'s one serial port, which a debug console would also want.',
       {'cpu_share': _est('blocks per byte while sending', 'per byte', 'hal_usart_send waits on the data-register-empty flag per byte (stated in its atom role)'),
        'latency': _und('no measurement of a frame\'s send time exists as a number for this route')},
       implemented={'atoms': ['uno:hal.hal_usart_send'], 'config': 'uno-light', 'proof_purposes': ['light-from-polari']}, cites=[_c('uart')]),
    _v('receive-command', 'uart-rx-interrupt', 'Serial receive by interrupt into a ring (USART0)',
       'An ISR drops each received byte into a ring; the main loop drains the ring into the frame parser.',
       [_pr('uart-rx', 'the command frame in')], [_pe('usart', 'the serial block')], [_pt('USB cable to the host (through the board\'s USB bridge)', 'carries the serial line', ('usb-cable',))],
       'The only route catalogued, so nothing to call wasteful; it takes the board\'s one serial port.',
       {'cpu_share': _est('one short ISR per received byte', 'per byte', 'structure of the route'),
        'latency': _und('no measurement of command latency exists as a number for this route')},
       implemented={'atoms': ['uno:hal.hal_rx_pop', 'uno:hal.USART_RX_vect'], 'config': 'uno-light', 'proof_purposes': ['light-from-polari']}, cites=[_c('uart')]),
]
