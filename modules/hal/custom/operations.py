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

ROLES = ('direction', 'output', 'input', 'pull_up', 'pull_down', 'pcint_mask', 'pcint_flag', 'pcint_bank', 'pcint_vector',
         'edge_sense', 'edge_flag', 'edge_mask', 'edge_vector')
ACTIONS = ('set', 'clear', 'toggle', 'read', 'lookup', 'symbol')


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
