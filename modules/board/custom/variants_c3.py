"""
@module board.custom.variants_c3

THE ESP32-C3 FIRMWARE VARIANTS (sc-3; D-sc-4 RULED 2026-10-02: the RTOS board is the ESP32-C3). FirmwareVariant rows over
the C3 template (`board/custom/firmware/esp32c3/`: an ESP-IDF C project — FreeRTOS tasks, the SAME SimRigState frames as
the UNO over UART0, the trace on UART1). Same row class and the same validation idea as board.custom.variants (every knob
checked, a refused value says why), with the C3's own app catalogue:

  c3-sim-rig                  the rig: telemetry + commands as FreeRTOS tasks (led_on / pwm_duty held and echoed)
  c3-prio-inversion           SCENARIO ONLY — S6 BEFORE: H/M/L share R, a BINARY SEMAPHORE (no priority inheritance)
  c3-prio-inversion-mutex     SCENARIO ONLY — S6 AFTER: R is a FreeRTOS MUTEX (priority inheritance)
  c3-two-lock                 SCENARIO ONLY — S7 BEFORE: T1 takes A→B, T2 takes B→A (opposite order)
  c3-two-lock-ordered         SCENARIO ONLY — S7 AFTER: both take A before B (lock ordering)
  esp32c3-light               THE LIGHT MISSION on the C3 (smp S5): button, LED, LED sense line, UART commands and a 10 Hz report as
                              five FreeRTOS tasks; ButtonClockState + ButtonClockEvent (the sense configs' wire); proven on the C3 TWIN
  c3-two-lock-backoff         SCENARIO ONLY — S7 AFTER (alternative): the opposite order kept, the second take times out
                              after 5 ms, the first lock is given back, the task backs off and retries

The scenario variants differ from their pair in exactly ONE build flag (SC_PI_MUTEX / SC_LOCK_ORDER / SC_LOCK_TIMEOUT_MS),
so the pair's size delta is the technique's cost. They live HERE (not in firmwarefaults) because they are the template's
apps: `pol board gen c3 --variant c3-two-lock` works with board alone; firmwarefaults names them in its Scenario rows.
"""
import json
import re

BOARD = 'esp32-c3'
#: app → the classes its C is written for
APP_CLASSES = {'sim_rig': ('SimRigState',), 'prio_inversion': ('SimRigState',), 'two_lock': ('SimRigState',),
               'light': ('ButtonClockState', 'ButtonClockEvent')}
#: files an app brings besides its own .c (apps/<name> -> main/<name>) and the ESP-IDF components its main component must REQUIRE on top of the template's
APP_EXTRA_FILES = {'light': ('light_hal.h',)}
APP_REQUIRES = {'light': ('nvs_flash', 'esp_driver_gpio')}
#: the build flags each app reads (anything else is refused, not ignored)
APP_FLAGS = {'sim_rig': (), 'prio_inversion': ('SC_PI_MUTEX', 'SC_ROUNDS'), 'two_lock': ('SC_LOCK_ORDER', 'SC_LOCK_TIMEOUT_MS', 'SC_ROUNDS'), 'light': ()}
FLAG_RANGE = {'SC_PI_MUTEX': (0, 1), 'SC_LOCK_ORDER': (0, 1), 'SC_LOCK_TIMEOUT_MS': (0, 1000), 'SC_ROUNDS': (1, 64)}
DEFAULT_VARIANT = 'c3-sim-rig'
DEFAULT_KNOBS = {'rig_name': 'c3-rig', 'device_id': 7, 'telemetry_hz': 10, 'send_name': 1}
#: the light app's own knobs (smp S5). Pins: of the C3's 22 GPIOs board.custom.lifecycle_c3 (datasheet v2.4) gives a constraint row to every one except GPIO0, GPIO1 and GPIO3 - strapping
#: (GPIO2/8/9, Table 3-1 p.30), UART0 (20/21), the USB pads (18/19), the in-package flash (12-17), VDD_SPI (11), the JTAG pads (4-7; GPIO4 is also the trace UART's TX) and GPIO10's 5 ns
#: power-up glitch (Table 2-2 p.18). The light takes exactly those three: LED GPIO0, sense GPIO1, button GPIO3 (GPIO0/1 are the 32 kHz crystal pins, free when no crystal is fitted). Selftest re-derives it.
LIGHT_KNOBS = {'rig_name': 'esp32c3-light', 'led_pin': 0, 'button_pin': 3, 'sense_pin': 1, 'debounce_ms': 30, 'event_queue_len': 16, 'pin_shim': 1}
FLAG_RE = re.compile(r'^([A-Z_][A-Z0-9_]{0,31})=(-?\d{1,9})$')
SCENARIO_TAG = 'firmwarefaults (sc-3): a SCENARIO variant — never install it on a board you rely on'


class VariantRefused(ValueError):
    pass


def _v(name, title, purpose, app, flags, watch, notes='', knobs=None, features=None):
    return {'name': name, 'board_definition': BOARD, 'title': title, 'purpose': purpose, 'app': app,
            'classes_json': json.dumps(list(APP_CLASSES[app])), 'features_json': json.dumps(features or {'commands': True}),
            'knobs_json': json.dumps(dict(DEFAULT_KNOBS, **(knobs or {}))), 'build_flags_json': json.dumps(flags),
            'what_to_watch': watch, 'twin_stimulus_json': '{}', 'origin': 'seeded', 'notes': notes}


_SC = {'rig_name': 'c3-scenario'}
LIGHT_NAME = 'esp32c3-light'
SEED_C3_VARIANTS = [
    _v('c3-sim-rig', 'The C3 rig: telemetry + commands as FreeRTOS tasks',
       'The ESP32-C3 speaking the same SimRigState frames as the UNO (UART0, 115200 Bd): uptime and status up at 10 Hz, led_on '
       'and pwm_duty down — held and echoed. Tests the template, the generated header on a 32-bit RISC-V target (8-byte double) '
       'and that the SAME bridge attaches to the QEMU twin\'s pty.', 'sim_rig', [],
       'status boot → ok after 1 s; setting led_on or pwm_duty comes back in the next frame with status "commanded".'),
    _v('c3-prio-inversion', 'SCENARIO ONLY — priority inversion: a binary semaphore (scenario 6 BEFORE)',
       'Three FreeRTOS tasks share R; L (2) holds it for 3 ms of its own CPU, H (4) asks 1 tick later, M (3) wakes 2 ticks after '
       'the start and runs 10 ms. R is a binary semaphore: no inheritance, so M preempts L and H waits for M\'s whole run.',
       'prio_inversion', ['SC_PI_MUTEX=0'], 'H\'s worst blocking (temp_c, ms) ≈ 12 ms ≫ the 3 ms section; @PI on UART1',
       SCENARIO_TAG, _SC),
    _v('c3-prio-inversion-mutex', 'SCENARIO ONLY — priority inversion fixed: a FreeRTOS mutex (scenario 6 AFTER)',
       'The same three tasks; R is xSemaphoreCreateMutex — priority inheritance raises L to H\'s priority while H waits, so M '
       'cannot preempt the section.', 'prio_inversion', ['SC_PI_MUTEX=1'],
       'H\'s worst blocking ≤ L\'s section; INHERIT/DISINHERIT events in the trace', SCENARIO_TAG, _SC),
    _v('c3-two-lock', 'SCENARIO ONLY — two tasks, two locks, opposite order (scenario 7 BEFORE)',
       'T1 takes A, yields 2 ticks, takes B; T2 starts 1 tick later and takes B, yields 1 tick, takes A. Both wait for ever; the '
       'telemetry task (which snapshots under A) stops too.', 'two_lock', ['SC_LOCK_ORDER=0'],
       'telemetry stops ~0.35 s in (after three frames); @DEADLOCK on UART1 with the holder/waiter table', SCENARIO_TAG, _SC),
    _v('c3-two-lock-ordered', 'SCENARIO ONLY — two locks in one global order (scenario 7 AFTER)',
       'The same tasks and gaps; T2 takes A before B as T1 does — the wait-for graph cannot close a cycle.', 'two_lock',
       ['SC_LOCK_ORDER=1'], 'every round completes; telemetry never stops', SCENARIO_TAG, _SC),
    _v('c3-two-lock-backoff', 'SCENARIO ONLY — the opposite order with a timed second take + back-off (scenario 7, alternative)',
       'The opposite order kept; each task\'s second take waits at most 5 ms, then it gives its first lock back, backs off '
       '(T1 1 tick, T2 3 ticks) and retries.', 'two_lock', ['SC_LOCK_ORDER=0', 'SC_LOCK_TIMEOUT_MS=5'],
       'every round completes, with back-offs counted in @LOCKS', SCENARIO_TAG, _SC),
    _v(LIGHT_NAME, 'The light Mission on the ESP32-C3 under FreeRTOS (twin only: no C3 board on the bench)',
       'smp S5: the uno-light-sense-poll behaviour as FreeRTOS tasks on the ESP32-C3. Tasks: rx/command (UART0), button (a GPIO edge notifies it; 30 ms lockout), sense '
       '(polls the LED line), telemetry (10 Hz, ButtonClockState + ButtonClockEvent frames), led_follow_state (the ONLY task that drives the LED pin). The mutators only alter the struct. '
       'Button GPIO3, LED GPIO0, sense GPIO1 (jumper GPIO0 to GPIO1). Proven on the QEMU twin with the two pin functions replaced by a RAM pin shim (QEMU\'s esp32c3 GPIO is a register stub); '
       'NOT proven on a chip.', 'light', [],
       'a press flips the LED and bumps button_presses with a `press` event; SET_LED from Polari flips it with status commanded; the sense line counts one edge per change; first report carries a new boot_session.',
       'twin only: the pins are a RAM shim (QEMU esp32c3 GPIO is a register stub); no C3 on the bench', LIGHT_KNOBS,
       features={'led': True, 'pwm': False, 'adc': False, 'commands': True, 'button': True, 'sense': True}),
]
VARIANT_NAMES = [v['name'] for v in SEED_C3_VARIANTS]


def _j(v, default):
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v or '') if v else default
    except ValueError:
        raise VariantRefused('not JSON: %r' % (v,))


def find(name, rows=None):
    for r in (rows or []):
        d = r if isinstance(r, dict) else {k: getattr(r, k, '') for k in SEED_C3_VARIANTS[0]}
        if d.get('name') == name and d.get('board_definition', BOARD) == BOARD:
            return d
    for v in SEED_C3_VARIANTS:
        if v['name'] == name:
            return dict(v)
    raise VariantRefused('no ESP32-C3 firmware variant %r — known: %s' % (name, ', '.join(VARIANT_NAMES)))


def resolve(variant, overrides=None):
    """Validate → {'name', 'app', 'classes', 'knobs', 'flags'}; raises VariantRefused naming why."""
    app = variant.get('app') or ''
    if app not in APP_CLASSES:
        raise VariantRefused('variant %s names app %r — the C3 template has %s' % (variant.get('name'), app, ', '.join(sorted(APP_CLASSES))))
    classes = list(_j(variant.get('classes_json'), []))
    if classes != list(APP_CLASSES[app]):
        raise VariantRefused('the %s app is written for %s; variant %s lists %s' % (app, ', '.join(APP_CLASSES[app]), variant.get('name'), classes))
    k = dict(DEFAULT_KNOBS, **_j(variant.get('knobs_json'), {}))
    k.update({a: b for a, b in (overrides or {}).items() if b is not None and a in DEFAULT_KNOBS})
    why = []
    try:
        k['device_id'], k['telemetry_hz'], k['send_name'] = int(k['device_id']), int(k['telemetry_hz']), int(k['send_name'])
    except (TypeError, ValueError) as e:
        raise VariantRefused('a knob is not a number: %s' % e)
    if not 1 <= k['telemetry_hz'] <= 50:
        why.append('telemetry_hz %d is outside 1..50' % k['telemetry_hz'])
    if not 0 <= k['device_id'] <= 65535:
        why.append('device_id %d: a u16' % k['device_id'])
    if not re.match(r'^[A-Za-z0-9_.-]{1,63}$', str(k['rig_name'])):
        why.append('rig_name %r: letters, digits, . _ - only, up to 63' % k['rig_name'])
    if app == 'light':
        k = dict(LIGHT_KNOBS, **k)
        k.update({a: b for a, b in (overrides or {}).items() if b is not None and a in LIGHT_KNOBS})
        why += _light_knob_problems(k)
    flags = []
    for f in _j(variant.get('build_flags_json'), []):
        m = FLAG_RE.match(str(f))
        if not m:
            why.append('build flag %r: NAME=integer only' % f)
            continue
        n, val = m.group(1), int(m.group(2))
        if n not in APP_FLAGS[app]:
            why.append('build flag %s: the %s app reads only %s' % (n, app, ', '.join(APP_FLAGS[app]) or 'none'))
        elif not FLAG_RANGE[n][0] <= val <= FLAG_RANGE[n][1]:
            why.append('build flag %s=%d outside %d..%d' % (n, val, FLAG_RANGE[n][0], FLAG_RANGE[n][1]))
        else:
            flags.append((n, val))
    if why:
        raise VariantRefused('variant %s: %s' % (variant.get('name'), '; '.join(why)))
    return {'name': variant.get('name', ''), 'app': app, 'classes': classes, 'knobs': k, 'flags': flags}


#: GPIOs the light may not use (see LIGHT_KNOBS); the selftest derives the same list from board.custom.lifecycle_c3 and compares
LIGHT_FORBIDDEN = {2: 'strapping', 8: 'strapping', 9: 'strapping', 18: 'USB pad', 19: 'USB pad', 20: 'UART0 RX', 21: 'UART0 TX', 4: 'trace UART TX / JTAG', 5: 'JTAG', 6: 'JTAG', 7: 'JTAG',
                   10: 'power-up glitch', 11: 'VDD_SPI', 12: 'in-package flash', 13: 'in-package flash', 14: 'in-package flash', 15: 'in-package flash', 16: 'in-package flash', 17: 'in-package flash'}


def _light_knob_problems(k):
    why = []
    try:
        for n in ('led_pin', 'button_pin', 'sense_pin', 'debounce_ms', 'event_queue_len', 'pin_shim'):
            k[n] = int(k[n])
    except (TypeError, ValueError) as e:
        return ['a light knob is not a number: %s' % e]
    pins = [k['led_pin'], k['button_pin'], k['sense_pin']]
    for role, n in zip(('led_pin', 'button_pin', 'sense_pin'), pins):
        if not 0 <= n <= 21:
            why.append('%s %d: the QFN32 C3 bonds GPIO0..21' % (role, n))
        elif n in LIGHT_FORBIDDEN:
            why.append('%s %d is %s' % (role, n, LIGHT_FORBIDDEN[n]))
    if len(set(pins)) != 3:
        why.append('led, button and sense pins must differ: %s' % pins)
    if not 5 <= k['debounce_ms'] <= 200:
        why.append('debounce_ms %d outside 5..200' % k['debounce_ms'])
    if not 2 <= k['event_queue_len'] <= 64:
        why.append('event_queue_len %d outside 2..64' % k['event_queue_len'])
    if k['pin_shim'] not in (0, 1):
        why.append('pin_shim is 0 (the chip HAL) or 1 (the RAM pin shim the twin needs)')
    return why


def render_config(r):
    """main/board_config.h for a resolved C3 variant."""
    k = r['knobs']
    lines = ['/* board_config.h — rendered by `pol board gen c3` (board.custom.gen_c3) for variant %s (app %s); the knobs are' % (r['name'] or '-', r['app']),
             ' * also in the FirmwareBuild row\'s repro block. */', '#ifndef BOARD_CONFIG_H', '#define BOARD_CONFIG_H', '',
             '#define POLARI_APP   "%s"' % r['app'],
             '#define RIG_NAME     "%s"' % str(k['rig_name']).replace('"', ''),
             '#define DEVICE_ID    %du' % k['device_id'],
             '#define TELEMETRY_HZ %du' % k['telemetry_hz'],
             '#define SEND_NAME    %d' % (1 if k['send_name'] else 0),
             '#define FEATURE_VALUE %d   /* temp_c carries the scenario\'s decisive value (0: c3-sim-rig has no sensor) */' % (0 if r['app'] == 'sim_rig' else 1)]
    if r['app'] == 'light':
        lines += ['#define LED_GPIO %d        /* light knobs: led_pin / button_pin / sense_pin are GPIO numbers (variants_c3.LIGHT_KNOBS says why these are free pins) */' % k['led_pin'],
                  '#define BUTTON_GPIO %d' % k['button_pin'], '#define SENSE_GPIO %d' % k['sense_pin'], '#define DEBOUNCE_MS %d' % k['debounce_ms'],
                  '#define EVENT_QUEUE_LEN %d' % k['event_queue_len'],
                  '#define PIN_SHIM %d   /* 1: the two pin functions are a RAM shim (the QEMU twin has no pin model); 0: the chip HAL (gpio driver) */' % k['pin_shim']]
    lines += ['#define %s %d   /* variant build flag */' % (n, v) for n, v in r['flags']]
    return '\n'.join(lines + ['', '#endif /* BOARD_CONFIG_H */', ''])
