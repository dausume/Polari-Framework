"""
@module hal.custom.operations

THE GENERALIZED HAL VOCABULARY, first family: GPIO (hal-0, HAL_CATOM_CATALOGUE_PLAN.md §4a). One HalOperation row per
operation an isotope can ask of a pin on ANY chip. Nothing here names a register: `role` + `action` say what is done, the
per-SoC rules (hal.custom.soc_rules) say which register plays the role on each chip, and the access mechanism
(hal.custom.mechanisms) says how the C is written.

  role       direction (output enable) | output (the driven level) | input (the read level) | pull_up | pull_down
  action     set (bit = 1) | clear (bit = 0) | toggle | read
  setup      a per-SoC setup an operation needs before its own write (the ESP32-C3's GPIO matrix + pad function), or ''

The names follow the API SHAPE of two existing HALs, cited, no code copied:
  Zephyr  include/zephyr/drivers/gpio.h (Apache-2.0): gpio_pin_configure(GPIO_OUTPUT / GPIO_INPUT / GPIO_PULL_UP / GPIO_PULL_DOWN),
          gpio_pin_set, gpio_pin_toggle, gpio_pin_get
  Arduino ArduinoCore-avr cores/arduino/wiring_digital.c (LGPL-2.1-or-later): pinMode(OUTPUT / INPUT / INPUT_PULLUP), digitalWrite,
          digitalRead
"""
ZEPHYR = 'Zephyr include/zephyr/drivers/gpio.h (Apache-2.0), API shape only'
ARDUINO = 'ArduinoCore-avr cores/arduino/wiring_digital.c (LGPL-2.1-or-later), API shape only'

OPERATIONS = [
    {'name': 'gpio.output', 'family': 'gpio', 'title': 'Make the pin an output', 'role': 'direction', 'action': 'set', 'setup': 'gpio-out',
     'returns': 'void', 'c_name': 'HAL_GPIO_OUTPUT',
     'intent': 'the pin drives its line from now on (its level is whatever gpio.set_high / gpio.set_low last wrote)',
     'basis': '%s: gpio_pin_configure(..., GPIO_OUTPUT); %s: pinMode(pin, OUTPUT)' % (ZEPHYR, ARDUINO)},
    {'name': 'gpio.input', 'family': 'gpio', 'title': 'Make the pin an input', 'role': 'direction', 'action': 'clear', 'setup': 'gpio-in',
     'returns': 'void', 'c_name': 'HAL_GPIO_INPUT',
     'intent': 'the pin stops driving its line and can be read',
     'basis': '%s: gpio_pin_configure(..., GPIO_INPUT); %s: pinMode(pin, INPUT)' % (ZEPHYR, ARDUINO)},
    {'name': 'gpio.set_high', 'family': 'gpio', 'title': 'Drive the pin high', 'role': 'output', 'action': 'set', 'setup': '',
     'returns': 'void', 'c_name': 'HAL_GPIO_SET_HIGH',
     'intent': 'an output pin drives a logic one',
     'basis': '%s: gpio_pin_set(..., 1); %s: digitalWrite(pin, HIGH)' % (ZEPHYR, ARDUINO)},
    {'name': 'gpio.set_low', 'family': 'gpio', 'title': 'Drive the pin low', 'role': 'output', 'action': 'clear', 'setup': '',
     'returns': 'void', 'c_name': 'HAL_GPIO_SET_LOW',
     'intent': 'an output pin drives a logic zero',
     'basis': '%s: gpio_pin_set(..., 0); %s: digitalWrite(pin, LOW)' % (ZEPHYR, ARDUINO)},
    {'name': 'gpio.toggle', 'family': 'gpio', 'title': 'Flip the pin', 'role': 'output', 'action': 'toggle', 'setup': '',
     'returns': 'void', 'c_name': 'HAL_GPIO_TOGGLE',
     'intent': 'an output pin drives the opposite of what it drove',
     'basis': '%s: gpio_pin_toggle (Arduino has no toggle call)' % ZEPHYR},
    {'name': 'gpio.read', 'family': 'gpio', 'title': 'Read the pin', 'role': 'input', 'action': 'read', 'setup': '',
     'returns': 'uint8_t (0 or 1)', 'c_name': 'HAL_GPIO_READ',
     'intent': 'the logic level on the pin now',
     'basis': '%s: gpio_pin_get; %s: digitalRead(pin)' % (ZEPHYR, ARDUINO)},
    {'name': 'gpio.pull_up', 'family': 'gpio', 'title': 'Turn the pull-up on', 'role': 'pull_up', 'action': 'set', 'setup': '',
     'returns': 'void', 'c_name': 'HAL_GPIO_PULL_UP',
     'intent': 'an input pin is held high through the chip\'s internal pull-up resistor when nothing drives it',
     'basis': '%s: GPIO_PULL_UP; %s: pinMode(pin, INPUT_PULLUP)' % (ZEPHYR, ARDUINO)},
    {'name': 'gpio.pull_down', 'family': 'gpio', 'title': 'Turn the pull-down on', 'role': 'pull_down', 'action': 'set', 'setup': '',
     'returns': 'void', 'c_name': 'HAL_GPIO_PULL_DOWN',
     'intent': 'an input pin is held low through the chip\'s internal pull-down resistor when nothing drives it',
     'basis': '%s: GPIO_PULL_DOWN (Arduino AVR has none)' % ZEPHYR},
    # hal-3b step 1 (read-button:analog-threshold onto the HAL): an input held only by an EXTERNAL resistor, and an analog pin's digital buffer off
    {'name': 'gpio.pull_none', 'family': 'gpio', 'title': 'No internal pull (the line is held by an external resistor)', 'setup': '',
     'parts': [{'role': 'pull_up', 'action': 'clear'}, {'role': 'pull_down', 'action': 'clear'}],
     'returns': 'void', 'c_name': 'HAL_GPIO_PULL_NONE',
     'intent': 'neither internal pull is on: the pin floats unless the circuit holds it (an external pull-up on an analog button)',
     'basis': '%s: GPIO_INPUT without GPIO_PULL_*; %s: pinMode(pin, INPUT)' % (ZEPHYR, ARDUINO)},
    {'name': 'gpio.digital_input_off', 'family': 'gpio', 'title': 'Turn the pin\'s digital input buffer off (analog use)', 'setup': '',
     'role': 'digital_input_disable', 'action': 'set', 'returns': 'void', 'c_name': 'HAL_GPIO_DIGITAL_INPUT_OFF',
     'intent': 'an analog pin\'s digital buffer draws no current at mid-rail levels; its PIN bit then reads 0',
     'basis': 'ArduinoCore-avr has no call for it (API shape: ours); DS40002061B §24.9.5 recommends it for ADC pins'},
]

# hal-1: the INTERRUPT family. An operation with several register writes lists them as `parts`, in the order they are written
# (the datasheet's: mask the pin, clear a stale flag, then enable the bank / unit). action lookup = find a field only to learn
# from it (which bank a pin is in); action symbol = a name (the vector), not a register.
_ZI = 'Zephyr include/zephyr/drivers/gpio.h (Apache-2.0): gpio_pin_interrupt_configure(GPIO_INT_EDGE_BOTH), API shape only'
_AI = 'ArduinoCore-avr cores/arduino/WInterrupts.c (LGPL-2.1-or-later): attachInterrupt(n, isr, CHANGE), API shape only'
OPERATIONS += [
    {'name': 'int.pin_change_enable', 'family': 'interrupt', 'title': 'Interrupt on any change of the pin (pin-change unit)', 'setup': '',
     'parts': [{'role': 'pcint_mask', 'action': 'set'}, {'role': 'pcint_flag', 'action': 'clear'}, {'role': 'pcint_bank', 'action': 'set'}],
     'returns': 'void', 'c_name': 'HAL_INT_PIN_CHANGE_ENABLE',
     'intent': 'a change of the pin\'s level raises the pin-change interrupt (a stale request is cleared first)',
     'basis': '%s; the AVR pin-change unit has no Arduino call (PCINT libraries do this by hand)' % _ZI},
    {'name': 'int.pin_change_disable', 'family': 'interrupt', 'title': 'Stop interrupting on changes of the pin', 'setup': '',
     'parts': [{'role': 'pcint_mask', 'action': 'clear'}], 'returns': 'void', 'c_name': 'HAL_INT_PIN_CHANGE_DISABLE',
     'intent': 'the pin no longer raises the pin-change interrupt (other pins of its bank are untouched)',
     'basis': '%s (GPIO_INT_DISABLE)' % _ZI},
    {'name': 'int.pin_change_clear', 'family': 'interrupt', 'title': 'Clear the pin-change request', 'setup': '',
     'parts': [{'role': 'pcint_mask', 'action': 'lookup'}, {'role': 'pcint_flag', 'action': 'clear'}], 'returns': 'void',
     'c_name': 'HAL_INT_PIN_CHANGE_CLEAR', 'intent': 'a pending pin-change request for the pin\'s bank is dropped',
     'basis': 'no Arduino / Zephyr call: the flag register of the chip'},
    {'name': 'int.pin_change_vector', 'family': 'interrupt', 'title': 'The pin-change interrupt vector', 'setup': '',
     'parts': [{'role': 'pcint_mask', 'action': 'lookup'}, {'role': 'pcint_vector', 'action': 'symbol'}], 'returns': 'vector name',
     'c_name': 'HAL_INT_PIN_CHANGE_VECTOR', 'intent': 'the name an ISR() for this pin\'s pin-change interrupt is declared with',
     'basis': 'avr-libc <avr/interrupt.h> ISR(vector) naming'},
    {'name': 'int.edge_enable', 'family': 'interrupt', 'title': 'Interrupt on any edge (dedicated external interrupt)', 'setup': '',
     'parts': [{'role': 'edge_sense', 'action': 'set', 'value': 'any_edge'}, {'role': 'edge_flag', 'action': 'clear'}, {'role': 'edge_mask', 'action': 'set'}],
     'returns': 'void', 'c_name': 'HAL_INT_EDGE_ENABLE',
     'intent': 'either edge on the pin raises its own external interrupt (a stale request is cleared first)',
     'basis': '%s; %s' % (_ZI, _AI)},
    {'name': 'int.edge_enable_falling', 'family': 'interrupt', 'title': 'Interrupt on the falling edge (dedicated external interrupt)', 'setup': '',
     'parts': [{'role': 'edge_sense', 'action': 'set', 'value': 'falling'}, {'role': 'edge_flag', 'action': 'clear'}, {'role': 'edge_mask', 'action': 'set'}],
     'returns': 'void', 'c_name': 'HAL_INT_EDGE_ENABLE_FALLING',
     'intent': 'a high-to-low edge on the pin raises its external interrupt (a button pulling a pulled-up pin to ground)',
     'basis': '%s (GPIO_INT_EDGE_FALLING); %s (FALLING)' % (_ZI, _AI)},
    {'name': 'int.edge_enable_rising', 'family': 'interrupt', 'title': 'Interrupt on the rising edge (dedicated external interrupt)', 'setup': '',
     'parts': [{'role': 'edge_sense', 'action': 'set', 'value': 'rising'}, {'role': 'edge_flag', 'action': 'clear'}, {'role': 'edge_mask', 'action': 'set'}],
     'returns': 'void', 'c_name': 'HAL_INT_EDGE_ENABLE_RISING',
     'intent': 'a low-to-high edge on the pin raises its external interrupt',
     'basis': '%s (GPIO_INT_EDGE_RISING); %s (RISING)' % (_ZI, _AI)},
    # hal-iso (2026-11-14): the LEVEL triggers. Same flag + mask parts as the edge ops; the chip rules say which levels exist
    # (the 328P has low only, cited `lacks` high; the C3 has both), so an isotope needing one is answered per chip, never assumed.
    # A level request re-asserts while the level holds: the isotope must mask or clear in its handler (ESP-IDF gpio.c:491-504).
    {'name': 'int.level_enable_low', 'family': 'interrupt', 'title': 'Interrupt while the pin is low (dedicated external interrupt)', 'setup': '',
     'parts': [{'role': 'level_sense', 'action': 'set', 'value': 'low_level'}, {'role': 'edge_flag', 'action': 'clear'}, {'role': 'edge_mask', 'action': 'set'}],
     'returns': 'void', 'c_name': 'HAL_INT_LEVEL_ENABLE_LOW',
     'intent': 'the pin raises its external interrupt for as long as it is held low (it re-asserts until masked or released)',
     'basis': 'Zephyr include/zephyr/drivers/gpio.h (Apache-2.0): GPIO_INT_LEVEL_LOW, API shape only'},
    {'name': 'int.level_enable_high', 'family': 'interrupt', 'title': 'Interrupt while the pin is high (dedicated external interrupt)', 'setup': '',
     'parts': [{'role': 'level_sense', 'action': 'set', 'value': 'high_level'}, {'role': 'edge_flag', 'action': 'clear'}, {'role': 'edge_mask', 'action': 'set'}],
     'returns': 'void', 'c_name': 'HAL_INT_LEVEL_ENABLE_HIGH',
     'intent': 'the pin raises its external interrupt for as long as it is held high (it re-asserts until masked or released)',
     'basis': 'Zephyr include/zephyr/drivers/gpio.h (Apache-2.0): GPIO_INT_LEVEL_HIGH, API shape only'},
    {'name': 'int.edge_disable', 'family': 'interrupt', 'title': 'Stop the pin\'s external interrupt', 'setup': '',
     'parts': [{'role': 'edge_mask', 'action': 'clear'}], 'returns': 'void', 'c_name': 'HAL_INT_EDGE_DISABLE',
     'intent': 'the pin\'s external interrupt is masked', 'basis': '%s (GPIO_INT_DISABLE); %s (detachInterrupt)' % (_ZI, _AI)},
    {'name': 'int.edge_clear', 'family': 'interrupt', 'title': 'Clear the external-interrupt request', 'setup': '',
     'parts': [{'role': 'edge_flag', 'action': 'clear'}], 'returns': 'void', 'c_name': 'HAL_INT_EDGE_CLEAR',
     'intent': 'a pending external-interrupt request for the pin is dropped', 'basis': 'no Arduino / Zephyr call: the flag register of the chip'},
    {'name': 'int.edge_vector', 'family': 'interrupt', 'title': 'The external interrupt vector', 'setup': '',
     'parts': [{'role': 'edge_mask', 'action': 'lookup'}, {'role': 'edge_vector', 'action': 'symbol'}], 'returns': 'vector name',
     'c_name': 'HAL_INT_EDGE_VECTOR', 'intent': 'the name an ISR() for this pin\'s external interrupt is declared with',
     'basis': 'avr-libc <avr/interrupt.h> ISR(vector) naming'},
]

# hal-3b: the PWM family, pin-keyed: the pin's own compare-output function (OCnx on the AVR; an LEDC channel on the C3) names the
# timer. Arguments are the physical quantities (a prescaler division factor, a compare level 0..TOP), never register codes.
_ZP = 'Zephyr include/zephyr/drivers/pwm.h (Apache-2.0): pwm_set(dev, channel, period, pulse, flags), API shape only'
_AP = 'ArduinoCore-avr cores/arduino/wiring_analog.c (LGPL-2.1-or-later): analogWrite(pin, value), API shape only'
OPERATIONS += [
    {'name': 'pwm.init_fast', 'family': 'pwm', 'title': 'Set the pin\'s timer to fast PWM (8-bit) at a prescaler', 'setup': '',
     'args': [{'name': 'prescaler', 'ctype': 'unsigned', 'meaning': 'the clock division factor (1, 8, 64, 256, 1024 on the ATmega328P)'}],
     'parts': [{'role': 'pwm_mode', 'action': 'write', 'value': '@derive:mode:fast_pwm_8bit'},
               {'role': 'pwm_clock', 'action': 'write', 'value': '@derive:divider:{prescaler}'}],
     'returns': 'void', 'c_name': 'HAL_PWM_INIT_FAST',
     'intent': 'the timer that drives this pin counts 0..TOP and the output can switch once per count (single-slope, 8-bit TOP)',
     'basis': '%s; %s (init(): fast PWM on Timer0, phase correct on Timer1/2)' % (_ZP, _AP)},
    {'name': 'pwm.init_phase', 'family': 'pwm', 'title': 'Set the pin\'s timer to phase-correct PWM (8-bit) at a prescaler', 'setup': '',
     'args': [{'name': 'prescaler', 'ctype': 'unsigned', 'meaning': 'the clock division factor'}],
     'parts': [{'role': 'pwm_mode', 'action': 'write', 'value': '@derive:mode:phase_correct_8bit'},
               {'role': 'pwm_clock', 'action': 'write', 'value': '@derive:divider:{prescaler}'}],
     'returns': 'void', 'c_name': 'HAL_PWM_INIT_PHASE',
     'intent': 'the timer counts up then down (dual-slope): half the frequency of fast PWM, with a symmetric output',
     'basis': '%s; %s' % (_ZP, _AP)},
    {'name': 'pwm.connect', 'family': 'pwm', 'title': 'Connect the PWM output to the pin (non-inverting)', 'setup': '',
     'parts': [{'role': 'pwm_output', 'action': 'set', 'value': 'non_inverting'}], 'returns': 'void', 'c_name': 'HAL_PWM_CONNECT',
     'intent': 'the compare output overrides the pin\'s port function: high until the compare level, low after (the pin must be an output)',
     'basis': '%s (PWM_POLARITY_NORMAL); %s' % (_ZP, _AP)},
    {'name': 'pwm.disconnect', 'family': 'pwm', 'title': 'Disconnect the PWM output (the port drives the pin again)', 'setup': '',
     'parts': [{'role': 'pwm_output', 'action': 'set', 'value': 'disconnected'}], 'returns': 'void', 'c_name': 'HAL_PWM_DISCONNECT',
     'intent': 'normal port operation returns: the pin shows its PORT bit',
     'basis': '%s (turnOffPWM in wiring_digital.c)' % _AP},
    {'name': 'pwm.set_duty', 'family': 'pwm', 'title': 'Set the compare level (the duty)', 'setup': '',
     'args': [{'name': 'level', 'ctype': 'unsigned', 'meaning': 'the compare level 0..TOP (255 for the 8-bit modes)'}],
     'parts': [{'role': 'pwm_duty', 'action': 'write', 'value': '{level}'}, {'role': 'pwm_update', 'action': 'strobe'}],
     'returns': 'void', 'c_name': 'HAL_PWM_SET_DUTY',
     'intent': 'the output is high for level / (TOP + 1) of each period (non-inverting)', 'basis': '%s (pulse); %s (OCRnx = val)' % (_ZP, _AP)},
]

# hal-3b step 1: the PERIPHERAL families (target 'peripheral': the unit's "pin" is the instance - USART0, TIMER2, ADC on the
# ATmega328P; UART0 / SYSTIMER / APB_SARADC on the C3). Arguments are physical quantities (a baud rate, a tick rate, a division
# factor, a channel number); the chip's role rules turn them into register values (its own cited formula, value_expr).
_ZU = 'Zephyr include/zephyr/drivers/uart.h (Apache-2.0): uart_configure / uart_poll_out / uart_poll_in / uart_irq_rx_enable, API shape only'
_AH = 'ArduinoCore-avr cores/arduino/HardwareSerial.cpp (LGPL-2.1-or-later): begin(baud, config), write, the RX ISR, API shape only'
_P = {'target': 'peripheral', 'setup': ''}
OPERATIONS += [
    dict(_P, name='uart.set_baud', family='uart', title='Set the baud rate (normal speed: 16 samples per bit)',
         args=[{'name': 'baud', 'ctype': 'unsigned long', 'meaning': 'bits per second (a constant: it is checked at compile time)'}],
         parts=[{'role': 'uart_double_speed', 'action': 'clear'}, {'role': 'uart_baud', 'action': 'write', 'value': 'value_expr'}],
         returns='void', c_name='HAL_UART_SET_BAUD',
         intent='the receiver samples each bit 16 times; the divider is the chip\'s own formula rounded to the nearest setting',
         basis='%s (uart_config.baudrate); %s (begin: U2X0 off branch)' % (_ZU, _AH)),
    dict(_P, name='uart.set_baud_x2', family='uart', title='Set the baud rate at double speed (8 samples per bit)',
         args=[{'name': 'baud', 'ctype': 'unsigned long', 'meaning': 'bits per second (a constant: it is checked at compile time)'}],
         parts=[{'role': 'uart_double_speed', 'action': 'set'}, {'role': 'uart_baud_x2', 'action': 'write', 'value': 'value_expr'}],
         returns='void', c_name='HAL_UART_SET_BAUD_X2',
         intent='half the samples per bit, so a finer divider: a smaller rate error at high baud rates, on chips that offer it',
         basis='%s (begin: U2X0 on, the default for most rates)' % _AH),
    dict(_P, name='uart.frame_8n1', family='uart', title='8 data bits, no parity, 1 stop bit',
         parts=[{'role': 'uart_frame_bits', 'action': 'set', 'value': 'eight'}, {'role': 'uart_parity', 'action': 'set', 'value': 'none'},
                {'role': 'uart_stop_bits', 'action': 'set', 'value': 'one'}],
         returns='void', c_name='HAL_UART_FRAME_8N1', intent='the frame both ends agree on (SERIAL_8N1)',
         basis='%s (UART_CFG_DATA_BITS_8, PARITY_NONE, STOP_BITS_1); %s (SERIAL_8N1)' % (_ZU, _AH)),
    dict(_P, name='uart.tx_enable', family='uart', title='Enable the transmitter', parts=[{'role': 'uart_tx_enable', 'action': 'set'}],
         returns='void', c_name='HAL_UART_TX_ENABLE', intent='the TX pin becomes the UART\'s output', basis=_AH),
    dict(_P, name='uart.rx_enable', family='uart', title='Enable the receiver', parts=[{'role': 'uart_rx_enable', 'action': 'set'}],
         returns='void', c_name='HAL_UART_RX_ENABLE', intent='the RX pin becomes the UART\'s input', basis=_AH),
    dict(_P, name='uart.rx_disable', family='uart', title='Disable the receiver and its interrupt',
         parts=[{'role': 'uart_rx_irq', 'action': 'clear'}, {'role': 'uart_rx_enable', 'action': 'clear'}],
         returns='void', c_name='HAL_UART_RX_DISABLE', intent='a transmit-only build: nothing received can raise an interrupt (a bootloader may have left it on)',
         basis='%s (end)' % _AH),
    dict(_P, name='uart.rx_irq_enable', family='uart', title='Interrupt on a received byte', parts=[{'role': 'uart_rx_irq', 'action': 'set'}],
         returns='void', c_name='HAL_UART_RX_IRQ_ENABLE', intent='the RX vector runs once per received byte', basis='%s (uart_irq_rx_enable)' % _ZU),
    dict(_P, name='uart.tx_ready', family='uart', title='Can a byte be written now?', parts=[{'role': 'uart_tx_ready', 'action': 'read'}],
         returns='flag', c_name='HAL_UART_TX_READY', intent='nonzero when the transmit buffer has room for one byte', basis='%s (write: UDRE0 wait)' % _AH),
    dict(_P, name='uart.write', family='uart', title='Queue one byte for transmission',
         args=[{'name': 'byte', 'ctype': 'uint8_t', 'meaning': 'the byte'}], parts=[{'role': 'uart_data', 'action': 'write', 'value': '{byte}'}],
         returns='void', c_name='HAL_UART_WRITE', intent='a push into the transmit buffer (call when tx_ready)', basis='%s (uart_poll_out)' % _ZU),
    dict(_P, name='uart.read', family='uart', title='Take the oldest received byte', parts=[{'role': 'uart_data', 'action': 'read_value'}],
         returns='byte', c_name='HAL_UART_READ', intent='a pop from the receive buffer (the error flags of that byte must be read first)',
         basis='%s (uart_poll_in)' % _ZU),
    dict(_P, name='uart.frame_error', family='uart', title='Did the oldest byte have a bad stop bit?', parts=[{'role': 'uart_frame_error', 'action': 'read'}],
         returns='flag', c_name='HAL_UART_FRAME_ERROR', intent='nonzero = framing error on the byte at the head of the buffer (read before uart.read)',
         basis='%s (uart_err_check UART_ERROR_FRAMING)' % _ZU),
    dict(_P, name='uart.overrun', family='uart', title='Was a byte lost because the buffer was full?', parts=[{'role': 'uart_overrun', 'action': 'read'}],
         returns='flag', c_name='HAL_UART_OVERRUN', intent='nonzero = a byte arrived while the receive buffer was full (read before uart.read)',
         basis='%s (uart_err_check UART_ERROR_OVERRUN)' % _ZU),
    dict(_P, name='uart.rx_vector', family='uart', title='The received-byte interrupt vector', parts=[{'role': 'uart_rx_vector', 'action': 'symbol'}],
         returns='vector name', c_name='HAL_UART_RX_VECTOR', intent='the name an ISR() for a received byte is declared with', basis='avr-libc ISR(vector) naming'),
]

_ZC = 'Zephyr include/zephyr/drivers/counter.h (Apache-2.0): counter_set_top_value / counter_start, API shape only'
_AW = 'ArduinoCore-avr cores/arduino/wiring.c (LGPL-2.1-or-later): init() + the TIMER0_OVF millis ISR, API shape only'
OPERATIONS += [
    dict(_P, name='timer.init_ctc', family='timer', title='A periodic timer: count to a top then restart, at a rate in Hz',
         args=[{'name': 'prescaler', 'ctype': 'unsigned', 'meaning': 'the clock division factor (a constant)'},
               {'name': 'hz', 'ctype': 'unsigned long', 'meaning': 'periods per second (a constant: the top is checked at compile time)'}],
         parts=[{'role': 'timer_mode', 'action': 'write', 'value': '@derive:mode:ctc_top_ocra'},
                {'role': 'timer_clock', 'action': 'write', 'value': '@derive:divider:{prescaler}'},
                {'role': 'timer_top', 'action': 'write', 'value': 'value_expr'}],
         returns='void', c_name='HAL_TIMER_INIT_CTC', intent='the counter restarts every 1/hz s (clear timer on compare match)',
         basis='%s; %s' % (_ZC, _AW)),
    dict(_P, name='timer.irq_enable', family='timer', title='Interrupt once per period', parts=[{'role': 'timer_irq_enable', 'action': 'set'}],
         returns='void', c_name='HAL_TIMER_IRQ_ENABLE', intent='the period vector runs at every restart', basis=_ZC),
    dict(_P, name='timer.vector', family='timer', title='The period interrupt vector', parts=[{'role': 'timer_vector', 'action': 'symbol'}],
         returns='vector name', c_name='HAL_TIMER_VECTOR', intent='the name an ISR() for the period is declared with', basis='avr-libc ISR(vector) naming'),
]

_ZA = 'Zephyr include/zephyr/drivers/adc.h (Apache-2.0): adc_channel_setup / adc_read, API shape only'
_AA = 'ArduinoCore-avr cores/arduino/wiring_analog.c (LGPL-2.1-or-later): analogRead(pin), API shape only'
OPERATIONS += [
    dict(_P, name='adc.init', family='adc', title='Power the converter with the supply as reference, at a clock division factor',
         args=[{'name': 'prescaler', 'ctype': 'unsigned', 'meaning': 'the clock division factor (a constant)'}],
         parts=[{'role': 'adc_reference', 'action': 'set', 'value': 'supply'}, {'role': 'adc_enable', 'action': 'set'},
                {'role': 'adc_prescaler', 'action': 'write', 'value': '@derive:divider:{prescaler}'}],
         returns='void', c_name='HAL_ADC_INIT', intent='the converter is on, full scale = the supply voltage', basis='%s; %s (init(): ADC prescaler)' % (_ZA, _AW)),
    dict(_P, name='adc.select', family='adc', title='Choose the input channel',
         args=[{'name': 'channel', 'ctype': 'uint8_t', 'meaning': 'the analog input number (A0 = 0)'}],
         parts=[{'role': 'adc_channel', 'action': 'write', 'value': '{channel}'}],
         returns='void', c_name='HAL_ADC_SELECT', intent='the next conversion measures this input', basis='%s (ADMUX = ...)' % _AA),
    dict(_P, name='adc.start', family='adc', title='Start one conversion', parts=[{'role': 'adc_start', 'action': 'set'}],
         returns='void', c_name='HAL_ADC_START', intent='one conversion begins; adc.busy reads nonzero until it is done', basis='%s (sbi ADSC)' % _AA),
    dict(_P, name='adc.busy', family='adc', title='Is a conversion in progress?', parts=[{'role': 'adc_busy', 'action': 'read'}],
         returns='flag', c_name='HAL_ADC_BUSY', intent='nonzero until the started conversion completes', basis='%s (while bit_is_set ADSC)' % _AA),
    dict(_P, name='adc.result', family='adc', title='The last conversion\'s result', parts=[{'role': 'adc_result', 'action': 'read_value'}],
         returns='count', c_name='HAL_ADC_RESULT', intent='the converted count (10-bit on the ATmega328P: Vin * 1024 / Vref)', basis='%s (ADCL then ADCH)' % _AA),
]

# hal-3b step 1: the WATCHDOG family. The change sequence is timed (a library call where the chip rules declare one); the reset flags are
# cleared by one store. ORDER (econ's review, DS40002061B p.64): WDRF overrides WDE, so disable clears WDRF first.
_ZW = 'Zephyr include/zephyr/drivers/watchdog.h (Apache-2.0): wdt_install_timeout / wdt_setup / wdt_feed / wdt_disable, API shape only'
OPERATIONS += [
    dict(_P, name='wdt.enable', family='wdt', title='Turn the watchdog on (reset mode) with a time-out',
         args=[{'name': 'period', 'ctype': 'uint8_t', 'meaning': 'the time-out code (avr-libc WDTO_*: 0 = 15 ms .. 9 = 8 s; a constant)'}],
         parts=[{'role': 'wdt_enable', 'action': 'call'}],
         returns='void', c_name='HAL_WDT_ENABLE', intent='the chip resets unless kicked within the time-out', basis='%s (wdt_setup)' % _ZW),
    dict(_P, name='wdt.kick', family='wdt', title='Restart the watchdog time-out', parts=[{'role': 'wdt_kick', 'action': 'call'}],
         returns='void', c_name='HAL_WDT_KICK', intent='the time-out starts again from zero', basis='%s (wdt_feed)' % _ZW),
    dict(_P, name='wdt.disable', family='wdt', title='Turn the watchdog off',
         parts=[{'role': 'wdt_reset_flag', 'action': 'clear'}, {'role': 'wdt_disable', 'action': 'call'}],
         returns='void', c_name='HAL_WDT_DISABLE', intent='no watchdog reset; WDRF is cleared first, since it would hold WDE on', basis='%s (wdt_disable)' % _ZW),
    dict(_P, name='wdt.reset_flags_clear', family='wdt', title='Clear every reset-source flag', parts=[{'role': 'wdt_reset_flags', 'action': 'clear'}],
         returns='void', c_name='HAL_WDT_RESET_FLAGS_CLEAR', intent='the next reset\'s cause can be read cleanly', basis='avr-libc FAQ / ArduinoCore-avr '
         'optiboot: MCUSR = 0 early in boot, API shape only'),
]

ROLES = ('direction', 'output', 'input', 'pull_up', 'pull_down', 'digital_input_disable', 'pcint_mask', 'pcint_flag', 'pcint_bank', 'pcint_vector',
         'edge_sense', 'level_sense', 'edge_flag', 'edge_mask', 'edge_vector',
         'pwm_output', 'pwm_duty', 'pwm_mode', 'pwm_clock', 'pwm_update', 'route_out', 'route_in', 'io_mux_func',
         'uart_baud', 'uart_baud_x2', 'uart_double_speed', 'uart_frame_bits', 'uart_parity', 'uart_stop_bits', 'uart_tx_enable',
         'uart_rx_enable', 'uart_rx_irq', 'uart_tx_ready', 'uart_data', 'uart_frame_error', 'uart_overrun', 'uart_rx_vector',
         'timer_mode', 'timer_clock', 'timer_top', 'timer_irq_enable', 'timer_vector',
         'adc_reference', 'adc_enable', 'adc_prescaler', 'adc_channel', 'adc_start', 'adc_busy', 'adc_result',
         'wdt_enable', 'wdt_kick', 'wdt_disable', 'wdt_reset_flag', 'wdt_reset_flags')
ACTIONS = ('set', 'clear', 'toggle', 'read', 'lookup', 'symbol', 'write', 'read_value', 'strobe', 'wait', 'call')


def parts(op):
    """The ordered parts of an operation: its own `parts`, else the one (role, action) of a single-write operation."""
    return op.get('parts') or [{'role': op['role'], 'action': op['action']}]


def seed_rows():
    """HalOperation seed rows: parts as readable text, role / action = the first part (for the operations table)."""
    out = []
    for o in OPERATIONS:
        ps = parts(o)
        out.append({'name': o['name'], 'family': o['family'], 'title': o['title'], 'intent': o['intent'], 'role': ps[0]['role'],
                    'action': ps[0]['action'], 'setup': o.get('setup', ''), 'returns': o['returns'], 'c_name': o['c_name'], 'basis': o['basis'],
                    'parts': '; '.join('%s %s%s' % (p['role'], p['action'], '=' + p['value'] if p.get('value') else '') for p in ps)})
    return out


def by_name(name):
    return next((o for o in OPERATIONS if o['name'] == name), None)
