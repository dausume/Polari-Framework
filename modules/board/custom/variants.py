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
APP_CLASSES = {'sim_rig': ('SimRigState',), 'blink': ('SimRigState',), 'echo': ('SimRigState',), 'analog': ('UnoAnalogState',)}
#: app → the features it can use (a feature an app cannot use is refused, not ignored)
APP_FEATURES = {'sim_rig': {'led', 'pwm', 'adc', 'commands'}, 'blink': {'led'}, 'echo': {'commands'}, 'analog': {'adc'}}
#: app → the features it cannot work without
APP_NEEDS = {'sim_rig': {'commands'}, 'blink': {'led'}, 'echo': {'commands'}, 'analog': {'adc'}}
FEATURES = ('led', 'pwm', 'adc', 'commands')
DEFAULT_VARIANT = 'uno-sim-rig'
DEFAULT_KNOBS = {'rig_name': 'uno-rig', 'device_id': 3, 'usart_u2x': 1, 'telemetry_hz': 10, 'led_pin': 13, 'pwm_pin': 6,
                 'adc_channel': 0, 'temp_formula': 'tmp36', 'blink_ms': 0,
                 # brd-wire (grpc-j4): the bridge whose bindings set the instance-index width ('' = one instance, 0 bits),
                 # THIS build's index, and whether telemetry carries `name` (a bound interface's identity is its binding)
                 'bridge': '', 'instance_index': 0, 'send_name': 1}
PWM_PINS = (5, 6, 9, 10)
FLAG_RE = re.compile(r'^([A-Z_][A-Z0-9_]{0,31})=(-?\d{1,9})$')
#: names a build flag may not redefine (they are the knobs; set the knob instead)
RESERVED = {'RIG_NAME', 'DEVICE_ID', 'USART_U2X', 'TELEMETRY_HZ', 'FEATURE_LED', 'FEATURE_PWM', 'FEATURE_ADC', 'LED_PIN',
            'PWM_PIN', 'ADC_CHANNEL', 'TEMP_TMP36', 'BLINK_MS', 'F_CPU', 'INSTANCE_INDEX', 'SEND_NAME', 'FEATURE_COMMANDS'}


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
       {'rig_name': 'uno-rig', 'telemetry_hz': 10, 'led_pin': 13, 'pwm_pin': 6, 'adc_channel': 0, 'temp_formula': 'tmp36'},
       'temp_c follows a finger on the TMP36; setting led_on lights D13, pwm_duty dims the LED on D6; status turns '
       '"commanded".', {'adc0_mv': 750}),
    _v('uno-blink-only', 'Blink: the LED toggles by itself, nothing else',
       'The smallest firmware worth flashing: no ADC, no PWM, no command path. Tests only that frames reach the row and '
       'that a pin moves — the first thing to try on a board you are not sure about.',
       'blink', ['SimRigState'], {'led': True, 'pwm': False, 'adc': False, 'commands': False},
       {'rig_name': 'uno-blink', 'telemetry_hz': 10, 'led_pin': 13, 'blink_ms': 500},
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
       {'rig_name': 'uno-pair', 'telemetry_hz': 10, 'led_pin': 13, 'pwm_pin': 6, 'adc_channel': 0, 'temp_formula': 'tmp36',
        'bridge': 'uno-pair', 'instance_index': 0, 'send_name': 0},
       'rows uno-twin-0 and uno-twin-1 each follow their own board; setting pwm_duty on uno-twin-1 dims only board 1 '
       '(index 1 on the wire); led_on set back to false comes back false.', {'adc0_mv': 750},
       notes='build it twice: pol board gen uno --variant uno-pair --instance-index 0 | 1'),
    _v('uno-echo', 'Echo: no sensors, a command comes back whole',
       'The protocol test. No sensors and no actuators: whatever Polari sends is copied back, every field, and status '
       'says "echoed". If the values return unchanged, the wire, the header, the parser and the bridge all agree.',
       'echo', ['SimRigState'], {'led': False, 'pwm': False, 'adc': False, 'commands': True},
       {'rig_name': 'uno-echo', 'telemetry_hz': 10},
       'set any field (even temp_c, which no sensor could produce) and the next frame carries the same value back with '
       'status "echoed".', {}),
]
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


def resolve(variant, overrides=None):
    """Validate a variant dict → {'app', 'classes', 'features', 'knobs', 'flags'}; raises VariantRefused naming why."""
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
    k = dict(DEFAULT_KNOBS, **_j(variant.get('knobs_json'), {}))
    k.update({a: b for a, b in (overrides or {}).items() if b is not None})
    why = []
    try:
        k['telemetry_hz'], k['led_pin'], k['pwm_pin'] = int(k['telemetry_hz']), int(k['led_pin']), int(k['pwm_pin'])
        k['adc_channel'], k['blink_ms'], k['device_id'], k['usart_u2x'] = int(k['adc_channel']), int(k['blink_ms']), int(k['device_id']), int(k['usart_u2x'])
        k['instance_index'], k['send_name'] = int(k['instance_index']), int(k['send_name'])
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
    if indexed:
        lines.append('#define INSTANCE_INDEX %du   /* brd-wire: this board\'s index among bridge %s\'s bound instances */' % (k['instance_index'], k['bridge']))
    lines += ['#define %s %d   /* variant build flag */' % (n, v) for n, v in r['flags']]
    return '\n'.join(lines + ['', '#endif /* BOARD_CONFIG_H */', ''])


def stimulus(variant):
    """The twin's ADC drive for a variant: (adc0_mv, {channel: mv})."""
    s = _j(variant.get('twin_stimulus_json'), {}) if variant else {}
    return int(s.get('adc0_mv', 750)), {int(c): int(mv) for c, mv in (s.get('adc_mv') or {}).items()}
