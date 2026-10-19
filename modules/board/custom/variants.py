"""
@module board.custom.variants

FIRMWARE VARIANTS (brd-fi, plan §7a): his intent — "that way we can test different kinds of things on the arduino uno
to see if it works". A variant is a named recipe over the UNO template: which app (`firmware/uno/apps/<app>.c`, copied
as main.c), which classes it speaks (each gets its generated header; order = msg_type), which features are compiled
in, its knobs and extra build defines. Every knob is validated here with the reason a value is refused — a variant is
never "fixed up" silently.

The four seeded UNO variants are four DIFFERENT things to try on one board:
  uno-sim-rig     brd-1's firmware: the TMP36 on A0, the LED on D13, PWM on D6, commands applied — the whole rig
  uno-blink-only  the LED toggles by itself; telemetry only; no ADC, no PWM, no command path — the smallest
  uno-adc-sweep   raw ADC of A0, A1, A2 as a SECOND class (UnoAnalogState) — the analog front end + the generator
  uno-echo        no sensors; a command comes back whole — the protocol test
  uno-pair        brd-wire: the whole rig built twice (instance_index 0 / 1) for two interfaces bound on ONE bridge

Adding one: a FirmwareVariant row (CRUDE on /display/firmware-installer, or a dict appended here for a seeded one) —
pick an app, list its class, set features/knobs; `pol board gen uno --variant <name>` validates it.
"""
import json
import re

#: app → the classes its C is written for (a generated header alone is not firmware)
APP_CLASSES = {'sim_rig': ('SimRigState',), 'blink': ('SimRigState',), 'echo': ('SimRigState',), 'analog': ('UnoAnalogState',),
               # sc-1 (module firmwarefaults): the SCENARIO app — one latent bug or its technique per build flag; no seeded
               # board variant uses it (its variants are seeded by firmwarefaults, each marked SCENARIO ONLY)
               'scenario_rig': ('SimRigState',),
               # ucd-0e2: the button-clock demo — one app, TWO classes (telemetry + the event stream)
               'button_clock': ('ButtonClockState', 'ButtonClockEvent'),
               # ucd-light: the light test — one app, ONE class (the light's state, both directions)
               'light': ('LightState',),
               # fgm-6a: the light with command confirmation -- a NEW app + class beside light/LightState (v1 untouched)
               'light_v2': ('LightStateV2',)}
#: app → the features it can use (a feature an app cannot use is refused, not ignored)
APP_FEATURES = {'sim_rig': {'led', 'pwm', 'adc', 'commands'}, 'blink': {'led'}, 'echo': {'commands'}, 'analog': {'adc'},
                'scenario_rig': {'led', 'commands'}, 'button_clock': {'led', 'commands', 'button', 'sense'},
                'light': {'led', 'commands', 'button', 'sense'}, 'light_v2': {'led', 'commands', 'button'}}      # smp-1: the light app can carry the sense line (the report's led_on is then the SENSED level)
#: app → the features it cannot work without
APP_NEEDS = {'sim_rig': {'commands'}, 'blink': {'led'}, 'echo': {'commands'}, 'analog': {'adc'}, 'scenario_rig': {'commands'},
             'button_clock': {'led', 'commands', 'button', 'sense'}, 'light': {'led', 'commands', 'button'},
             'light_v2': {'led', 'commands', 'button'}}
#: sc-1: the generated header's RX parser (grpcbridge.custom.c_twin_v2.RX_PARSERS). A knob only a variant that sets it
#: carries (absent = 'resync', so every existing build's repro block is unchanged)
RX_PARSERS = ('resync', 'keep-tail')
#: smp-1: how the LED is driven (absent = 'gpio', a plain output pin). `transistor` is the SAME C as gpio - the pin drives a transistor's base, which is wiring - and says so in the config's routes
LED_ROUTES = ('gpio', 'pwm', 'transistor')
FEATURES = ('led', 'pwm', 'adc', 'commands', 'button', 'sense')
DEFAULT_VARIANT = 'uno-sim-rig'
DEFAULT_KNOBS = {'rig_name': 'uno-rig', 'device_id': 3, 'usart_u2x': 1, 'telemetry_hz': 10, 'temp_formula': 'tmp36', 'blink_ms': 0,
                 # brd-wire (grpc-j4): the bridge whose bindings set the instance-index width ('' = one instance, 0 bits),
                 # THIS build's index, and whether telemetry carries `name` (a bound interface's identity is its binding)
                 'bridge': '', 'instance_index': 0, 'send_name': 1,
                 # ucd-0e2: the button-clock demo's own pins (D2 = INT0, D3 = INT1 — hardware-fixed, never derived from
                 # BoardPin rows the way led_pin/pwm_pin/adc_channel are) and its two knobs
                 'button_pin': 2, 'sense_pin': 3, 'debounce_ms': 30, 'event_queue_len': 16}


def _board_pins():
    """brd-bo (THE BOARD OBJECT): the pin knobs LED_PIN / PWM_PIN / ADC_CHANNEL come from the UNO's BoardPin rows (the pins
    carrying those firmware symbols — D13, D6, A0 in the seed), and the PWM-capable pins are DERIVED from the SocPin rows (an
    Output Compare of Timer0/1; Timer2 is reserved by the bare-C runtime profile for the 1 ms tick) — no pin literal here."""
    from board.custom import board_object as bo
    from board.custom.soc_atmega328p import pwm_functions, FUNCTION_PERIPHERAL
    r = bo.rows_for('arduino-uno-r3')
    reserved = {x['name'] for x in json.loads(r['profiles']['bare-c']['peripherals_json']) if x.get('reserved')}
    pwm = tuple(sorted(int(p['number']) for p in r['pins'] if p['canonical'].startswith('D')
                       and [f for f in pwm_functions(r['soc_pins'], p['soc_pin']) if FUNCTION_PERIPHERAL[f][0] not in reserved]))
    return bo.pin_knobs('arduino-uno-r3')[0], pwm


ROW_PIN_KNOBS, PWM_PINS = _board_pins()   # ({'led_pin': 13, 'pwm_pin': 6, 'adc_channel': 0}, (5, 6, 9, 10)) from the seed rows
DEFAULT_KNOBS.update(ROW_PIN_KNOBS)
PIN_KNOBS = ('led_pin', 'pwm_pin', 'adc_channel')
#: fgm-5a: the button ROUTE knob (absent = 'int0', hal.c's hand-written INT0 button, so every existing variant is unchanged) and the apps
#: whose button code is written against hal.h's three button functions only (light.c) - the others also use INT0-only facts
ROUTE_APPS = ('light', 'button_clock')   # smp-1: button_clock too - it calls hal.h's three button functions and nothing else of the button (checked in its source)
ROUTE_KNOB_DEFAULTS = {'button_route': 'int0'}
#: fgm-5b: the sense ROUTE knob (absent = 'int1', hal.c's hand-written INT1 sense on D3) and the apps whose sense code is written against hal.h's two sense functions only (button_clock)
SENSE_ROUTE_APPS = ('button_clock', 'light')
ROUTE_KNOB_DEFAULTS['sense_route'] = 'int1'
ROUTE_INT_KNOBS = ('button_adc_channel', 'adc_press_below_mv', 'adc_release_above_mv', 'adc_pullup_ohms')
FLAG_RE = re.compile(r'^([A-Z_][A-Z0-9_]{0,31})=(-?\d{1,9})$')
#: names a build flag may not redefine (they are the knobs; set the knob instead)
RESERVED = {'RIG_NAME', 'DEVICE_ID', 'USART_U2X', 'TELEMETRY_HZ', 'FEATURE_LED', 'FEATURE_PWM', 'FEATURE_ADC', 'LED_PIN',
            'PWM_PIN', 'ADC_CHANNEL', 'TEMP_TMP36', 'BLINK_MS', 'F_CPU', 'INSTANCE_INDEX', 'SEND_NAME', 'FEATURE_COMMANDS',
            # ucd-0e2's own new knobs — NOT HAL_INT0/HAL_INT0_DEBOUNCE_MS, which firmwarefaults' own sc-1 scenario
            # variants (uno-button-count etc.) already set directly as build flags, predating the 'button' feature
            'FEATURE_BUTTON', 'FEATURE_SENSE', 'BUTTON_PIN', 'SENSE_PIN', 'HAL_INT1', 'EVENT_QUEUE_LEN',
            # fgm-5a: the button route (hal_button_*.c rendered from catoms/read-button/)
            'HAL_BUTTON_ROUTE',
            # smp-1: the LED route (Timer0 PWM output) and the sample failure's slow main loop
            'LED_ROUTE_PWM', 'LOOP_DELAY_MS',
            # fgm-5b: the sense route (hal_sense_*.c rendered from catoms/sense-led-line/)
            'HAL_SENSE_ROUTE'}


class VariantRefused(ValueError):
    pass


def _v(name, title, purpose, app, classes, features, knobs, watch, stimulus, notes=''):
    return {'name': name, 'board_definition': 'arduino-uno-r3', 'title': title, 'purpose': purpose, 'app': app,
            'classes_json': json.dumps(classes), 'features_json': json.dumps(features), 'knobs_json': json.dumps(knobs),
            'build_flags_json': '[]', 'what_to_watch': watch, 'twin_stimulus_json': json.dumps(stimulus), 'origin': 'seeded',
            'notes': notes}


SEED_FIRMWARE_VARIANTS = [
    _v('uno-sim-rig', 'The whole rig: temperature, LED, PWM, commands',
       'brd-1\'s firmware. Tests the kit\'s TMP36 on A0, the on-board LED (D13) and a dimmable LED on D6, and the '
       'command path: a change made in Polari reaches the board and the board says so.',
       'sim_rig', ['SimRigState'], {'led': True, 'pwm': True, 'adc': True, 'commands': True},
       {'rig_name': 'uno-rig', 'telemetry_hz': 10, 'temp_formula': 'tmp36'},   # brd-bo: the pins come from the BoardPin rows
       'temp_c follows a finger on the TMP36; setting led_on lights D13, pwm_duty dims the LED on D6; status turns '
       '"commanded".', {'adc0_mv': 750}),
    _v('uno-blink-only', 'Blink: the LED toggles by itself, nothing else',
       'The smallest firmware worth flashing: no ADC, no PWM, no command path. Tests only that frames reach the row and '
       'that a pin moves — the first thing to try on a board you are not sure about.',
       'blink', ['SimRigState'], {'led': True, 'pwm': False, 'adc': False, 'commands': False},
       {'rig_name': 'uno-blink', 'telemetry_hz': 10, 'blink_ms': 500},
       'D13 blinks twice a second; led_on flips true / false in the frames AND in the row (brd-wire: the presence mask '
       'sends a false that is present — the old proto3 drop is gone); uptime_ms climbs; temp_c and pwm_duty are not sent '
       '(absent from the frame), so the row keeps whatever it had.',
       {}),
    _v('uno-adc-sweep', 'Three analog inputs, raw (a second class)',
       'Reads A0, A1 and A2 as raw 10-bit counts into UnoAnalogState — a pot, a photoresistor, the TMP36, whatever is '
       'wired. Tests the analog front end, and that the header generator handles a class other than SimRigState.',
       'analog', ['UnoAnalogState'], {'led': False, 'pwm': False, 'adc': True, 'commands': False},
       {'rig_name': 'uno-analog', 'telemetry_hz': 10},
       'a0, a1, a2 move as you turn a pot or cover a photoresistor (0..1023; count = mV × 1024 / 5000 on the chip; the '
       'simavr twin rounds with 1023, so 1500 mV reads 306 there, 307 on a real UNO).',
       {'adc0_mv': 750, 'adc_mv': {'1': 1500, '2': 3000}}),
    _v('uno-pair', 'Two UNOs on one bridge: the same firmware, instance 0 and instance 1',
       'brd-wire (his ruling 2026-10-02): the whole rig firmware built TWICE — instance_index 0 and 1 — for the two '
       'interfaces bound on bridge uno-pair (HardwareInterfaceBinding rows uno-twin-0 / uno-twin-1). Two instances → a '
       '1-bit index in the frame; the struct carries no identity (no name either — the binding is the identity); the '
       'bridge re-attaches it. Tests that each row follows ITS board and a change reaches only the board it names.',
       'sim_rig', ['SimRigState'], {'led': True, 'pwm': True, 'adc': True, 'commands': True},
       {'rig_name': 'uno-pair', 'telemetry_hz': 10, 'temp_formula': 'tmp36',
        'bridge': 'uno-pair', 'instance_index': 0, 'send_name': 0},
       'rows uno-twin-0 and uno-twin-1 each follow their own board; setting pwm_duty on uno-twin-1 dims only board 1 '
       '(index 1 on the wire); led_on set back to false comes back false.', {'adc0_mv': 750},
       notes='build it twice: pol board gen uno --variant uno-pair --instance-index 0 | 1'),
    _v('uno-button-clock', 'The button-clock demo: a software clock synced from the host, a debounced button that '
       'toggles an LED, and a second pin (D3) that independently witnesses the LED line switching',
       'UNO_CORE_DEMO_PLAN.md §1 (ucd-0e2): the core demo/proof for a Polari Hardware App. D2 (INT0, debounced) toggles '
       'D6 + D13; a jumper D6->D3 (INT1, any edge) counts the LED line\'s own rises/falls as an independent witness; '
       'SET_TIME/SNAPSHOT/SET_LED commands; a bounded ButtonClockEvent queue (drop-oldest) carries every press/LED '
       'change/sensed edge/sync with the device\'s own clock.',
       'button_clock', ['ButtonClockState', 'ButtonClockEvent'],
       {'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': True},
       {'rig_name': 'uno-button-clock', 'telemetry_hz': 10, 'led_pin': 6, 'button_pin': 2, 'sense_pin': 3,
        'debounce_ms': 30, 'event_queue_len': 16},
       'pressing the button on D2 flips D6 + D13 and bumps button_presses; with D6 wired to D3, sense_rises + '
       'sense_falls tracks button_presses 1:1 and led_on == (sense_rises > sense_falls); SET_TIME syncs the clock '
       '(drift_ms reported from the second sync on); SNAPSHOT replays the full state + queued events now.', {}),
    _v('uno-light-sense-poll', 'The button-clock demo with the sense pin (D3) POLLED in the main loop instead of read by an interrupt',
       'fgm-5b (MISSION_PROFILE_SOLVER_PLAN.md section 16): the uno-button-clock behaviour with the LED-line witness read by the GPIO-POLL isotope of sense-led-line, rendered from a Jinja2 template '
       '(catoms/sense-led-line): the main loop looks at D3 once per pass and counts a change as one edge, so INT1 is left free. The button is still INT0 on D2 and the LED on D6; with the jumper D6->D3 '
       'every press is one counted edge. Opt-in: uno-button-clock itself is unchanged.',
       'button_clock', ['ButtonClockState', 'ButtonClockEvent'],
       {'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': True},
       {'rig_name': 'uno-light-sense-poll', 'telemetry_hz': 10, 'led_pin': 6, 'button_pin': 2, 'sense_pin': 3, 'sense_route': 'poll', 'debounce_ms': 30, 'event_queue_len': 16},
       'with D6 wired to D3, sense_rises + sense_falls tracks button_presses 1:1 and led_on == (sense_rises > sense_falls), exactly as uno-button-clock does with INT1; with no wire the sense counters stay 0. '
       'A line that changes twice within one main-loop pass would be seen as no change (the cost of polling).', {},
       notes='the sense route is the template sense-led-line/isotopes/gpio-poll (rendered to hal_sense_poll.c)'),
    _v('uno-light-sense-pcint', 'The button-clock demo with the sense pin on a pin-change interrupt (D8, wired from D6)',
       'fgm-5b: the uno-button-clock behaviour with the LED-line witness read by the PIN-CHANGE-INTERRUPT isotope of sense-led-line, rendered from a Jinja2 template (catoms/sense-led-line), on D8 '
       '(PB0, PCINT0) - a pin with no INT0/INT1 - so both external-interrupt pins stay free. The button is INT0 on D2 and the LED on D6; the jumper is D6->D8. Opt-in.',
       'button_clock', ['ButtonClockState', 'ButtonClockEvent'],
       {'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': True},
       {'rig_name': 'uno-light-sense-pcint', 'telemetry_hz': 10, 'led_pin': 6, 'button_pin': 2, 'sense_pin': 8, 'sense_route': 'pcint', 'debounce_ms': 30, 'event_queue_len': 16},
       'with D6 wired to D8, sense_rises + sense_falls tracks button_presses 1:1 and led_on == (sense_rises > sense_falls); with the old D6->D3 wire (or none) the sense counters stay 0.', {},
       notes='the sense route is the template sense-led-line/isotopes/pin-change-interrupt (rendered to hal_sense_pcint.c)'),
    _v('uno-light', 'The light test: a light on D6 that the screen and the board\'s pushbutton both switch, with a sense line that reports what the LED really is',
       'The simplest two-way test of a Polari Hardware App, and the core demo. D6 carries the light; a person can switch it from a Polari screen (the SET_LED command down), and the pushbutton on D2 (debounced) '
       'switches the same light and the board reports the change up. One struct, LightState, carries the light\'s state both ways and is what CONTROLS the light (led_follow_state is the only pin writer). '
       'smp-1: a jumper from the light pin D6 to D3 lets the board read the LED line itself (polled in the main loop): the report\'s led_on is the SENSED level, not the commanded one. '
       'The wire contract is unchanged (LightState v1). No clock, no event queue.',
       'light', ['LightState'],
       {'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': True},
       {'rig_name': 'uno-light', 'telemetry_hz': 10, 'led_pin': 6, 'button_pin': 2, 'sense_pin': 3, 'sense_route': 'poll', 'debounce_ms': 30},
       'pressing the button on D2 flips the light on D6, bumps toggles and reports source=button; setting led_on from the screen (SET_LED) switches the light and reports source=command; toggles counts every change. '
       'With the jumper D6->D3 the reported led_on follows the light pin; with NO jumper the board still drives D6 but reports led_on false (it reports what it senses).', {},
       notes='wiring: LED + 220 ohm from D6 to GND; pushbutton between D2 and GND (the internal pull-up holds D2 high); JUMPER D6 -> D3 (the sense line; D3 is polled). Without the jumper Polari cannot observe the light '
             '(the unsensed build is uno-light-unsensed, sample failure F1). Routes: drive-led:gpio-out, read-button:ext-interrupt, sense-led-line:gpio-poll'),
    _v('uno-light-unsensed', 'The light test with NO sense line: a light on D6 that the screen and the board\'s pushbutton both switch (sample failure F1)',
       'smp-1: the light test as it was before the sense line (kept as the sample failure F1): the board reports what it COMMANDED, with no way to read the LED line, so Polari cannot observe the hardware state. The simplest two-way test of a Polari Hardware App. D6 carries the light; a person can switch it from a Polari '
       'screen (the SET_LED command down), and the pushbutton on D2 (debounced) switches the same light and the board '
       'reports the change up. One struct, LightState, carries the light\'s state both ways. No clock, no sense pin, '
       'no event queue.',
       'light', ['LightState'],
       {'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': False},
       {'rig_name': 'uno-light', 'telemetry_hz': 10, 'led_pin': 6, 'button_pin': 2, 'debounce_ms': 30},
       'pressing the button on D2 flips the light on D6, bumps toggles and reports source=button; setting led_on from '
       'the screen (SET_LED) switches the light and reports source=command; toggles counts every change.', {}),
    # ---- smp-1: the sample solutions S2..S4 and the sample failure F2 (FIRMWARE_SCORE_PROFILES_PLAN.md section 13). All are the LIGHT app (LightState v1) with the sense line, like S1 = uno-light: the struct
    # ---- controls the light (led_follow_state is the only pin writer) and the report's led_on is the SENSED level.
    _v('uno-light-all-pcint', 'The light with the button AND the sense line on pin-change interrupts (sample S2)',
       'smp-1 (sample S2): the light with BOTH inputs on pin-change interrupts and no external-interrupt pin used: the button on D4 (PD4, PCINT20, bank PCMSK2) read by the pin-change-interrupt isotope of '
       'read-button, the LED-line witness on D8 (PB0, PCINT0, bank PCMSK0) read by the pin-change-interrupt isotope of sense-led-line, the LED on D6. Two different PCINT banks, so the two vectors do not share a bank. '
       'INT0 and INT1 are left free. Opt-in.',
       'light', ['LightState'],
       {'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': True},
       {'rig_name': 'uno-light', 'telemetry_hz': 10, 'led_pin': 6, 'button_route': 'pcint', 'button_pin': 4, 'sense_pin': 8, 'sense_route': 'pcint', 'debounce_ms': 30},
       'a press on D4 flips the light on D6 and bumps toggles; with the jumper D6->D8 the reported led_on follows the light pin; a press on D2 does nothing (INT0 is not armed here); with no jumper led_on stays false.', {},
       notes='wiring: pushbutton between D4 and GND (the internal pull-up holds D4 high); jumper D6 -> D8; LED + 220 ohm from D6 to GND. Routes: read-button:pin-change-interrupt, sense-led-line:pin-change-interrupt, drive-led:gpio-out'),
    _v('uno-light-pwm-analog', 'The light with the button read as a voltage on A0 and the LED on the timer PWM output (sample S3)',
       'smp-1 (sample S3): the light with the button read as a voltage on A0 by the analog-threshold isotope of read-button (a 10 kohm resistor holds A0 at 5 V, the switch pulls it to ground; below 1500 mV = '
       'pressed, above 3500 mV = released) and the LED driven by Timer0\'s PWM output on D6 (OC0A). The struct decides on/off: led_follow_state is the only writer, and the pin driver connects the PWM output at 100 % duty for on '
       '(phase-correct PWM: the pin stays high, so the sense line counts one edge per change, not the PWM edges) and disconnects it for off. The sense line is polled on D3. Opt-in.',
       'light', ['LightState'],
       {'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': True},
       {'rig_name': 'uno-light', 'telemetry_hz': 10, 'led_pin': 6, 'led_route': 'pwm', 'button_route': 'adc', 'button_adc_channel': 0, 'adc_press_below_mv': 1500, 'adc_release_above_mv': 3500,
        'adc_pullup_ohms': 10000, 'button_pin': 2, 'sense_pin': 3, 'sense_route': 'poll', 'debounce_ms': 30},
       'pulling A0 below 1500 mV (a press) flips the light on D6 and bumps toggles; the light pin is Timer0\'s output (OCR0A 255, output connected) while on and disconnected and low while off; with the jumper D6->D3 the reported led_on follows it.', {},
       notes='wiring: 10 kohm from A0 to 5 V, pushbutton from A0 to GND; LED + 220 ohm from D6 to GND; jumper D6 -> D3. Routes: read-button:analog-threshold, drive-led:pwm, sense-led-line:gpio-poll. '
             'Only on/off is driven (the wire struct has no brightness field): a duty below 100 % would put PWM edges on the sense line.'),
    _v('uno-light-transistor', 'The light switched through the kit\'s transistor, with the sense line (sample S4)',
       'smp-1 (sample S4): the light with the LED driven THROUGH A TRANSISTOR (drive-led:transistor-switch): D6 drives the base of one of the kit\'s transistors through a base resistor and the transistor '
       'switches the LED from 5 V. The firmware is the plain output pin of S1 (the same C, the same led_follow_state); only the wiring differs, so the twin runs the same code and cannot show the transistor switching. '
       'The button is INT0 on D2, the sense line is polled on D3. Opt-in.',
       'light', ['LightState'],
       {'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': True},
       {'rig_name': 'uno-light', 'telemetry_hz': 10, 'led_pin': 6, 'led_route': 'transistor', 'button_pin': 2, 'sense_pin': 3, 'sense_route': 'poll', 'debounce_ms': 30},
       'a press on D2 flips D6 (the transistor base drive) and bumps toggles; with the jumper D6->D3 the reported led_on follows the pin. The twin sees the pin, not the transistor: whether the LED lights is the '
       'wiring\'s part, not the firmware\'s.', {},
       notes='wiring (a bipolar transistor of the kit; its part number and pin order are not printed on the cited page, so read them off the part): D6 -> base resistor -> base; emitter -> GND; LED + 220 ohm from 5 V to the collector; '
             'jumper D6 -> D3 senses the drive pin (the command), not the LED current. The kit has 5 transistors and 2 MOSFETs (board.custom.kit_parts). Routes: drive-led:transistor-switch, read-button:ext-interrupt, sense-led-line:gpio-poll'),
    _v('uno-light-slow-loop', 'The light with a deliberately slow main loop (sample failure F2)',
       'smp-1 (sample failure F2): uno-light with every main-loop pass held for 250 ms. The button\'s interrupt only marks the press; the main loop is what acts on it, so a press is acted on up to one slow '
       'pass late. It is a firmware that works but is too slow for a deadline: the sample entry F2 flags the button deadline safety-critical for the sample only, and this build misses it. Do not flash it for real use. Opt-in.',
       'light', ['LightState'],
       {'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': True},
       {'rig_name': 'uno-light', 'telemetry_hz': 10, 'led_pin': 6, 'button_pin': 2, 'sense_pin': 3, 'sense_route': 'poll', 'loop_delay_ms': 250, 'debounce_ms': 30},
       'a press is acted on, on average, half a slow pass late and at most one pass (250 ms) late: the light follows the press, but later than the 100 ms the button Purpose states.', {},
       notes='the delay is the LOOP_DELAY_MS build define (board.custom.variants, knob loop_delay_ms); same wiring as uno-light (jumper D6 -> D3)'),
    _v('uno-light-pcint', 'The light test with the button on a pin-change interrupt (D4)',
       'fgm-5a (MISSION_PROFILE_SOLVER_PLAN.md 8.5): the uno-light behaviour with the button read by the PIN-CHANGE-INTERRUPT isotope '
       'of read-button, rendered from a Jinja2 template (catoms/read-button), on D4 - a pin with no INT0/INT1 - and the light still '
       'on D6. The same debounce lockout as the INT0 isotope. Opt-in: uno-light itself is unchanged.',
       'light', ['LightState'],
       {'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': False},
       {'rig_name': 'uno-light-pcint', 'telemetry_hz': 10, 'led_pin': 6, 'button_route': 'pcint', 'button_pin': 4, 'debounce_ms': 30},
       'pressing the button on D4 flips the light on D6, bumps toggles and reports source=button, exactly as uno-light does with D2; '
       'SET_LED from the screen still works.', {},
       notes='the button route is the template read-button/isotopes/pin-change-interrupt (rendered to hal_button_pcint.c)'),
    _v('uno-light-analog', 'The light test with the button read as a voltage on A0 (analog threshold)',
       'fgm-5a: the uno-light behaviour with the button read by the ANALOG-THRESHOLD isotope of read-button: a 10 kohm resistor holds A0 '
       'at 5 V, the switch pulls it to ground, and the firmware does one ADC conversion per main-loop pass (below 1500 mV = pressed, '
       'above 3500 mV = released, the gap is the hysteresis). No interrupt and no digital pin; the light stays on D6. Opt-in.',
       'light', ['LightState'],
       {'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': False},
       {'rig_name': 'uno-light-analog', 'telemetry_hz': 10, 'led_pin': 6, 'button_route': 'adc', 'button_adc_channel': 0,
        'adc_press_below_mv': 1500, 'adc_release_above_mv': 3500, 'adc_pullup_ohms': 10000, 'debounce_ms': 30},
       'pulling A0 below 1500 mV (a press) flips the light on D6, bumps toggles and reports source=button; the button released above '
       '3500 mV; a switch already closed at boot is not a press.', {},
       notes='the button route is the template read-button/isotopes/analog-threshold (rendered to hal_button_adc.c)'),
    _v('uno-light-v2', 'The light test with command confirmation (LightStateV2): every command is numbered and the board answers by number',
       'fgm-6a (FIRMWARE_GENERATION_MODULE_PLAN.md 10, his ruling 7.8.3): the uno-light behaviour on a NEW wire struct, LightStateV2, that '
       'adds command_id (down: the number the sender picked), last_command_id and last_command_result (up: the board\'s answer). The '
       'board reports at once after every command, rejects a malformed one (no number, no light value) as rejected-invalid, ignores a '
       'repeat of the number it last answered, and a press of its button changes the light WITHOUT touching last_command_id - so an '
       'unrelated report can never be mistaken for a command being done. Opt-in: uno-light (LightState v1) stays the default.',
       'light_v2', ['LightStateV2'],
       {'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': False},
       {'rig_name': 'uno-light-v2', 'telemetry_hz': 10, 'led_pin': 6, 'button_pin': 2, 'debounce_ms': 30},
       'SET_LED with command_id N: the very next report says last_command_id N, last_command_result applied and the light follows; a '
       'command without a number or without led_on is answered rejected-invalid; pressing the button flips the light, bumps toggles, '
       'says source=button and leaves last_command_id as it was.', {},
       notes='the backend (board.custom.light_confirm) counts a command done only on a report with its number from the same boot_session; '
             'RX_RING=128 so a burst of whole-row commands (~100 B each) is not dropped while the board is sending its answer'),
    _v('uno-echo', 'Echo: no sensors, a command comes back whole',
       'The protocol test. No sensors and no actuators: whatever Polari sends is copied back, every field, and status '
       'says "echoed". If the values return unchanged, the wire, the header, the parser and the bridge all agree.',
       'echo', ['SimRigState'], {'led': False, 'pwm': False, 'adc': False, 'commands': True},
       {'rig_name': 'uno-echo', 'telemetry_hz': 10},
       'set any field (even temp_c, which no sensor could produce) and the next frame carries the same value back with '
       'status "echoed".', {}),
]
for _v2 in SEED_FIRMWARE_VARIANTS:
    if _v2['name'] == 'uno-light-v2':
        _v2['build_flags_json'] = json.dumps(['RX_RING=128'])
VARIANT_NAMES = [v['name'] for v in SEED_FIRMWARE_VARIANTS]


def _j(v, default):
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v or '') if v else default
    except ValueError:
        raise VariantRefused('not JSON: %r' % (v,))


def find(name, rows=None):
    """A variant as a dict: from the given rows (a server's FirmwareVariant table, dicts or objects), else the seeds."""
    for r in (rows or []):
        d = r if isinstance(r, dict) else {k: getattr(r, k, '') for k in SEED_FIRMWARE_VARIANTS[0]}
        if d.get('name') == name:
            return d
    for v in SEED_FIRMWARE_VARIANTS:
        if v['name'] == name:
            return dict(v)
    raise VariantRefused('no firmware variant %r — known: %s' % (name, ', '.join(sorted({*VARIANT_NAMES, *[getattr(r, 'name', '') if not isinstance(r, dict) else r.get('name', '') for r in (rows or [])]} - {''}))))


def resolve(variant, overrides=None, base=None):
    """Validate a variant dict → {'app', 'classes', 'features', 'knobs', 'flags'}; raises VariantRefused naming why.
    brd-bo: `base` = the pin knobs from the board's BoardPin rows (gen passes them; a variant's own knob still wins — an explicit
    per-variant choice, recorded as such in the build's repro block)."""
    app = variant.get('app') or ''
    if app not in APP_CLASSES:
        raise VariantRefused('variant %s names app %r — the UNO template has %s' % (variant.get('name'), app, ', '.join(sorted(APP_CLASSES))))
    classes = list(_j(variant.get('classes_json'), []))
    if list(classes) != list(APP_CLASSES[app]):
        raise VariantRefused('the %s app is written for %s; variant %s lists %s (a generated header alone is not firmware — a new class needs an app)'
                             % (app, ', '.join(APP_CLASSES[app]), variant.get('name'), ', '.join(classes) or 'none'))
    feats = {f: bool(_j(variant.get('features_json'), {}).get(f, False)) for f in FEATURES}
    extra = {f for f, on in feats.items() if on} - APP_FEATURES[app]
    if extra:
        raise VariantRefused('the %s app cannot use %s (it has no code for it) — turn it off or pick another app' % (app, ', '.join(sorted(extra))))
    missing = APP_NEEDS[app] - {f for f, on in feats.items() if on}
    if missing:
        raise VariantRefused('the %s app needs %s on' % (app, ', '.join(sorted(missing))))
    k = dict(DEFAULT_KNOBS, **(base or {}))
    k.update(_j(variant.get('knobs_json'), {}))
    k.update({a: b for a, b in (overrides or {}).items() if b is not None})
    why = []
    try:
        k['telemetry_hz'], k['led_pin'], k['pwm_pin'] = int(k['telemetry_hz']), int(k['led_pin']), int(k['pwm_pin'])
        k['adc_channel'], k['blink_ms'], k['device_id'], k['usart_u2x'] = int(k['adc_channel']), int(k['blink_ms']), int(k['device_id']), int(k['usart_u2x'])
        k['instance_index'], k['send_name'] = int(k['instance_index']), int(k['send_name'])
        k['button_pin'], k['sense_pin'] = int(k['button_pin']), int(k['sense_pin'])
        k['debounce_ms'], k['event_queue_len'] = int(k['debounce_ms']), int(k['event_queue_len'])
        for rk in ROUTE_INT_KNOBS:
            if rk in k:
                k[rk] = int(k[rk])
    except (TypeError, ValueError) as e:
        raise VariantRefused('a knob is not a number: %s' % e)
    if not 1 <= k['telemetry_hz'] <= 50:
        why.append('telemetry_hz %d is outside 1..50 (a frame is ~170 B; 50 Hz is ~74 %% of 115200 Bd)' % k['telemetry_hz'])
    if feats['led'] and not 2 <= k['led_pin'] <= 13:
        why.append('led_pin D%d: use D2..D13 (D0/D1 are the USB serial line)' % k['led_pin'])
    if feats['pwm'] and k['pwm_pin'] not in PWM_PINS:
        why.append('pwm_pin D%d: PWM is on D5/D6 (Timer0) or D9/D10 (Timer1); D3/D11 belong to Timer2, the 1 ms tick' % k['pwm_pin'])
    if feats['pwm'] and feats['led'] and k['pwm_pin'] == k['led_pin']:
        why.append('led_pin and pwm_pin are the same pin (D%d)' % k['led_pin'])
    if not 0 <= k['adc_channel'] <= 5:
        why.append('adc_channel %d: the UNO has A0..A5' % k['adc_channel'])
    if k['temp_formula'] not in ('tmp36', 'raw'):
        why.append('temp_formula %r: tmp36 | raw' % k['temp_formula'])
    if not 0 <= k['blink_ms'] <= 60000 or (app == 'blink' and k['blink_ms'] < 20):
        why.append('blink_ms %d: 20..60000 for the blink app (0 = off elsewhere)' % k['blink_ms'])
    if not 0 <= k['device_id'] <= 65535:
        why.append('device_id %d: a u16' % k['device_id'])
    if not 0 <= k['instance_index'] <= 255:
        why.append('instance_index %d: 0..255 (and it must fit the bridge\'s index width — checked at gen)' % k['instance_index'])
    if k['instance_index'] and not k['bridge']:
        why.append('instance_index %d without a bridge: one unbound instance is index 0' % k['instance_index'])
    if not k['send_name'] and not k['bridge']:
        why.append('send_name 0 without a bridge: an unbound board is identified by the name it sends')
    route = str(k.get('button_route', 'int0'))
    if route not in ('int0', 'pcint', 'adc'):
        why.append('button_route %r: int0 (hal.c) | pcint | adc (rendered from catoms/read-button/)' % route)
    elif route != 'int0':
        if not feats['button']:
            why.append('button_route %s without the button feature' % route)
        elif app not in ROUTE_APPS:
            why.append('button_route %s: the %s app is not written for it (only %s use hal.h\'s three button functions alone)' % (route, app, ', '.join(ROUTE_APPS)))
        else:
            from board.custom import button_routes as BR
            try:
                BR.check(route, k)
            except BR.RouteRefused as e:
                why.append('button_route %s: %s' % (route, e))
            if route == 'pcint' and feats['led'] and k['button_pin'] == k['led_pin']:
                why.append('button_pin and led_pin are the same pin (D%d)' % k['led_pin'])
            if route == 'adc' and feats['led'] and k['led_pin'] == 14 + int(k.get('button_adc_channel', 0)):
                why.append('led_pin and the button\'s ADC pin are the same pin')
    lroute = str(k.get('led_route', 'gpio'))
    if lroute not in LED_ROUTES:
        why.append('led_route %r: %s' % (lroute, ' | '.join(LED_ROUTES)))
    elif lroute == 'pwm':
        if not feats['led'] or feats['pwm']:
            why.append('led_route pwm drives the LED itself (led on, and not the separate pwm feature)')
        elif k['led_pin'] not in (5, 6):
            why.append('led_route pwm: led_pin D%d is not a Timer0 output (D5 or D6)' % k['led_pin'])
    if lroute != 'gpio' and not feats['led']:
        why.append('led_route %s without the led feature' % lroute)
    if 'loop_delay_ms' in k:
        try:
            k['loop_delay_ms'] = int(k['loop_delay_ms'])
        except (TypeError, ValueError):
            why.append('loop_delay_ms %r is not a number' % (k['loop_delay_ms'],))
        else:
            if not 0 <= k['loop_delay_ms'] <= 2000:
                why.append('loop_delay_ms %d: 0..2000' % k['loop_delay_ms'])
            elif k['loop_delay_ms'] and app != 'light':
                why.append('loop_delay_ms: only the light app has the slow-pass code (the sample failure F2)')
    if feats['button'] and route == 'int0' and k['button_pin'] != 2:
        why.append('button_pin D%d: the button is hardware-fixed to D2 (INT0) — no other pin\'s EICRA/EIMSK bits are wired for it' % k['button_pin'])
    sroute = str(k.get('sense_route', 'int1'))
    if sroute not in ('int1', 'poll', 'pcint'):
        why.append('sense_route %r: int1 (hal.c) | poll | pcint (rendered from catoms/sense-led-line/)' % sroute)
    elif sroute != 'int1':
        if not feats['sense']:
            why.append('sense_route %s without the sense feature' % sroute)
        elif app not in SENSE_ROUTE_APPS:
            why.append('sense_route %s: the %s app is not written for it (only %s use hal.h\'s two sense functions alone)' % (sroute, app, ', '.join(SENSE_ROUTE_APPS)))
        else:
            from board.custom import sense_routes as SR
            try:
                SR.check(sroute, k)
            except SR.RouteRefused as e:
                why.append('sense_route %s: %s' % (sroute, e))
            if feats['button'] and k['sense_pin'] == (k['button_pin'] if str(k.get('button_route', 'int0')) in ('int0', 'pcint') else -1):
                why.append('sense_pin and button_pin are the same pin (D%d)' % k['sense_pin'])
    if feats['sense'] and sroute == 'int1' and k['sense_pin'] != 3:
        why.append('sense_pin D%d: the sense atom is hardware-fixed to D3 (INT1) — no other pin\'s EICRA/EIMSK bits are wired for it' % k['sense_pin'])
    if feats['sense'] and feats['led'] and k['sense_pin'] == k['led_pin']:
        why.append('sense_pin and led_pin are the same pin (D%d) — the sense pin must be a wire FROM the LED pin, not the LED pin itself' % k['led_pin'])
    if feats['button'] and not 1 <= k['debounce_ms'] <= 1000:
        why.append('debounce_ms %d: 1..1000 (HAL_INT0_DEBOUNCE_MS — 0 would count contact bounce as presses)' % k['debounce_ms'])
    if feats['button'] or feats['sense']:
        if not 2 <= k['event_queue_len'] <= 64:
            why.append('event_queue_len %d: 2..64 (a ButtonClockEvent queue entry is ~11 B; the 2 KB SRAM budget is cited in the README)' % k['event_queue_len'])
    if str(k.get('rx_parser', 'resync')) not in RX_PARSERS:
        why.append('rx_parser %r: %s' % (k.get('rx_parser'), ' | '.join(RX_PARSERS)))
    if k['bridge'] and not re.match(r'^[A-Za-z0-9_.-]{1,63}$', str(k['bridge'])):
        why.append('bridge %r: letters, digits, . _ - only' % k['bridge'])
    if not re.match(r'^[A-Za-z0-9_.-]{1,63}$', str(k['rig_name'])):
        why.append('rig_name %r: letters, digits, . _ - only, up to 63 (it is the row name)' % k['rig_name'])
    flags = []
    for f in _j(variant.get('build_flags_json'), []):
        m = FLAG_RE.match(str(f))
        if not m:
            why.append('build flag %r: NAME=integer only (a define in board_config.h, never a compiler argument)' % f)
        elif m.group(1) in RESERVED:
            why.append('build flag %s redefines a knob — set the knob instead' % m.group(1))
        else:
            flags.append((m.group(1), int(m.group(2))))
    if why:
        raise VariantRefused('variant %s: %s' % (variant.get('name'), '; '.join(why)))
    return {'name': variant.get('name', ''), 'app': app, 'classes': classes, 'features': feats, 'knobs': k, 'flags': flags}


def render_config(r, indexed=False):
    """board_config.h for a resolved variant (the knobs also go into the FirmwareBuild repro block). brd-wire: INSTANCE_INDEX
    appears ONLY when the class is indexed (several boards bound on the variant's bridge) — a single-instance build has
    no instance knob at all (his ruling 2026-10-02)."""
    k, f = r['knobs'], r['features']
    lines = ['/* board_config.h — rendered by `pol board gen` (board.custom.gen) for variant %s (app %s); the knobs are' % (r['name'] or '-', r['app']),
             ' * also in the FirmwareBuild row\'s repro block. */', '#ifndef BOARD_CONFIG_H', '#define BOARD_CONFIG_H', '',
             '#define RIG_NAME     "%s"' % str(k['rig_name']).replace('"', ''),
             '#define DEVICE_ID    %du' % k['device_id'],
             '#define USART_U2X    %d' % (1 if k['usart_u2x'] else 0),
             '#define TELEMETRY_HZ %du' % k['telemetry_hz'],
             '#define FEATURE_LED  %d' % int(f['led']),
             '#define FEATURE_PWM  %d' % int(f['pwm']),
             '#define FEATURE_ADC  %d' % int(f['adc']),
             '#define FEATURE_COMMANDS %d' % int(f['commands']),
             '#define LED_PIN      %d' % k['led_pin'],
             '#define PWM_PIN      %d' % k['pwm_pin'],
             '#define ADC_CHANNEL  %d' % k['adc_channel'],
             '#define TEMP_TMP36   %d' % (1 if k['temp_formula'] == 'tmp36' else 0),
             '#define BLINK_MS     %du' % k['blink_ms'],
             '#define SEND_NAME    %d     /* 0: telemetry omits `name` (the binding is the identity) */' % (1 if k['send_name'] else 0)]
    # ucd-0e2: these lines exist ONLY for a variant whose app can use button/sense (today: button_clock) — every
    # other app's board_config.h is BYTE-IDENTICAL to before (brd-bo's own fixtures assert this; FEATURE_LED/PWM/ADC
    # are unconditional because every app could in principle use them — button/sense cannot, by APP_FEATURES).
    if f['button'] or f['sense']:
        lines += ['#define FEATURE_BUTTON %d' % int(f['button']), '#define FEATURE_SENSE  %d' % int(f['sense'])]
        if f['button']:
            route = str(k.get('button_route', 'int0'))
            if route == 'int0':
                lines += ['#define HAL_INT0     1              /* ucd-0e2: the button atom (hal.c) */',
                           '#define HAL_INT0_DEBOUNCE_MS %du' % k['debounce_ms'],
                           '#define BUTTON_PIN   %d' % k['button_pin']]
            else:   # fgm-5a: the button atom is rendered into hal_button_*.c; hal.c's INT0 block is off, the app still sees HAL_INT0
                from board.custom import button_routes as BR
                lines += ['#define HAL_INT0     1              /* the app\'s button guard; the atom itself is the rendered hal_button_*.c */',
                           '#define HAL_BUTTON_ROUTE %d          /* fgm-5a: %s (catoms/read-button) */' % (BR.ROUTES[route][0], BR.ROUTES[route][1]),
                           '#define HAL_INT0_DEBOUNCE_MS %du' % k['debounce_ms'],
                           '#define BUTTON_PIN   %d' % (k['button_pin'] if route == 'pcint' else 14 + int(k.get('button_adc_channel', 0)))]
        if f['sense']:
            sroute = str(k.get('sense_route', 'int1'))
            if sroute == 'int1':
                lines += ['#define HAL_INT1     1              /* ucd-0e2: the sense atom (hal.c) */',
                           '#define SENSE_PIN    %d' % k['sense_pin']]
            else:   # fgm-5b: the sense atom is rendered into hal_sense_*.c; hal.c's INT1 block is off, the app still sees HAL_INT1
                from board.custom import sense_routes as SR
                lines += ['#define HAL_INT1     1              /* the app\'s sense guard; the atom itself is the rendered hal_sense_*.c */',
                           '#define HAL_SENSE_ROUTE %d          /* fgm-5b: %s (catoms/sense-led-line) */' % (SR.ROUTES[sroute][0], SR.ROUTES[sroute][1]),
                           '#define SENSE_PIN    %d' % k['sense_pin']]
        lines.append('#define EVENT_QUEUE_LEN %du' % k['event_queue_len'])
    if str(k.get('led_route', 'gpio')) == 'pwm':
        lines.append('#define LED_ROUTE_PWM 1             /* smp-1: the LED pin is Timer0\'s PWM output, held at 100 % duty for on (drive-led:pwm) */')
    if int(k.get('loop_delay_ms', 0)):
        lines.append('#define LOOP_DELAY_MS %du            /* smp-1: a deliberately slow main loop (sample failure F2) */' % int(k['loop_delay_ms']))
    if indexed:
        lines.append('#define INSTANCE_INDEX %du   /* brd-wire: this board\'s index among bridge %s\'s bound instances */' % (k['instance_index'], k['bridge']))
    lines += ['#define %s %d   /* variant build flag */' % (n, v) for n, v in r['flags']]
    return '\n'.join(lines + ['', '#endif /* BOARD_CONFIG_H */', ''])


def stimulus(variant):
    """The twin's ADC drive for a variant: (adc0_mv, {channel: mv})."""
    s = _j(variant.get('twin_stimulus_json'), {}) if variant else {}
    return int(s.get('adc0_mv', 750)), {int(c): int(mv) for c, mv in (s.get('adc_mv') or {}).items()}
