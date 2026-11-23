"""
@module board.custom.twin_kinds

c3g-3 (AI-Notes/plans/C3_SESSION_PLAN.md): what differs between the chips a twin session can run. twin_sessions asks here and names no chip itself, so one
sessions module, one control hub and one door serve every kind.

    of(config)                 the kind a config's session runs as: a C3 firmware variant -> C3, anything else -> AVR (whose generator refuses an unknown name in words)
    of_board(board)            the kind of a session row, by the board it was written with
    admit(kind, config, free)  refuses, before anything is built or asked, what this kind cannot run (a C3 config with no pads, a free-running C3)
    firmware(kind, config, data=None)   what a session of this kind posts: {'bytes', 'sha256'} and, for the C3, {'layout', 'wires', 'watch'}; `data` = bytes already built
    request(kind, fw, ...)     the worker's POST /sessions body (prf-board-engines/board_sessions.py, by SESSIONS_KIND)
    command_set(kind, body)    the checked `set` line: the C3 also takes "level": "z" (let a pad go), the UNO only 0 or 1

The C3 here is the CHIP HAL build (PIN_SHIM 0) on the pin model: the image a chip is flashed with. It is still a model of the pads, not a chip.
"""
import base64
import fcntl
import hashlib
import os

#: the UNO's twin: simavr behind polari-avr-twin, on the board-engines worker
AVR = {'name': 'avr', 'family': 'avr', 'board': 'arduino-uno-r3', 'mcu': 'atmega328p', 'watch': ['PB5', 'PD2', 'PD3', 'PD4', 'PD5', 'PD6', 'PD7'], 'release': False,
       'clock': {'unit': 'cycle', 'hz': 16000000},
       'post_timeout': 30, 'pin': 'PD2',
       'usage': 'inject takes {"set":"PD2","level":0|1}, {"adc":0,"mv":750}, {"reset":1}, {"watch":["PD6"]}, {"run":true|false} or {"status":1}'}
#: the C3's twin: the pin-model QEMU behind polari-c3-twin, on the esp-engines worker. Its worker waits up to 30 s for the twin, so the request waits longer.
C3 = {'name': 'c3', 'family': 'esp', 'board': 'esp32-c3', 'mcu': 'esp32c3', 'watch': None, 'release': True, 'clock': {'unit': 'ns', 'hz': 1000000000}, 'post_timeout': 60, 'pin': 'GPIO3',
      'usage': 'inject takes {"set":"GPIO3","level":0|1|"z"} ("z" lets the pad go), {"watch":["GPIO0"]} or {"status":1}; the C3 twin has no adc, reset or pause yet'}
KINDS = (AVR, C3)
#: one C3 build at a time shares this work folder; its build store is the cache (same source + same engine image = not built twice)
C3_WORK = 'twin-session-c3'


class KindRefused(RuntimeError):
    def __init__(self, why, status=400):
        super().__init__(why)
        self.status = status


def of(config):
    from board.custom import variants_c3 as V3
    return C3 if config in V3.VARIANT_NAMES else AVR


def of_board(board):
    return next((k for k in KINDS if k['board'] == board), AVR)


def _c3_knobs(config):
    """The pads of a C3 config as its generator resolves them for the chip HAL; refuses a C3 variant with no pads to press."""
    from board.custom import variants_c3 as V3
    try:
        r = V3.resolve(V3.find(config), {'pin_shim': 0})
    except V3.VariantRefused as e:
        raise KindRefused('config %r: %s' % (config, e))
    if r['app'] != 'light':
        raise KindRefused('config %r is the C3 %s app: it uses no pad, so a session has nothing to press or watch yet. The C3 config with pads is %s'
                          % (config, r['app'], V3.LIGHT_NAME))
    return r['knobs']


def admit(kind, config, free=False):
    if kind is C3:
        if free:
            raise KindRefused('the C3 twin runs in twin time only: it has no free-running mode (leave "free" out)')
        _c3_knobs(config)


def c3_image(config):
    """-> the merged flash image of the chip-HAL build, through the shipped pipeline (gen_c3 + build_c3 on the esp engines ladder). The first build of a
    source on an engine image takes minutes; after that the build store answers."""
    from board.custom import gen, light_c3_run as R
    work = gen.default_work(C3_WORK)
    os.makedirs(work, exist_ok=True)
    with open(os.path.join(work, '.lock'), 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            row = R.build(work, variant=config, pin_shim=0)
        except gen.GenRefused as e:
            raise KindRefused('config %r: %s' % (config, e))
        if row.get('state') != 'built' or not row.get('image_path'):
            raise KindRefused('config %r did not build: %s' % (config, row.get('notes') or row.get('state')), 422)
        with open(row['image_path'], 'rb') as f:
            return f.read()


def firmware(kind, config, data=None):
    if kind is C3:
        from board.custom import light_c3_run as R, sim_layout as SL
        k = _c3_knobs(config)
        if data is None:
            data = c3_image(config)
        try:
            layout = SL.text(SL.layout(R.SIM_CHIP))
        except SL.LayoutRefused as e:
            raise KindRefused('the pin layout of %s cannot be exported: %s' % (R.SIM_CHIP, e), 422)
        return {'bytes': data, 'sha256': hashlib.sha256(data).hexdigest(), 'layout': layout, 'wires': '%d-%d' % (k['led_pin'], k['sense_pin']),
                'watch': ['GPIO%d' % k[n] for n in ('led_pin', 'sense_pin', 'button_pin')]}
    return {'bytes': data, 'sha256': hashlib.sha256(data).hexdigest(), 'watch': list(AVR['watch'])}


def request(kind, fw, ttl_s, token, owner='', free=False):
    body = {'board': kind['board'], 'mcu': kind['mcu'], 'ttl_s': int(ttl_s), 'token': token, 'owner': owner}
    b64 = base64.b64encode(fw['bytes']).decode()
    if kind is C3:   # admit() has refused "free"; the C3 worker takes no such key
        return dict(body, image_b64=b64, layout=fw['layout'], wires=fw['wires'])
    return dict(body, hex_b64=b64, free=bool(free))


def command_set(kind, body):
    lv = body.get('level')
    if kind['release'] and lv == 'z':
        return {'set': str(body['set']), 'level': 'z'}
    if lv not in (0, 1, True, False):
        raise KindRefused('"set" needs "level": 0 or 1%s' % (', or "z" to let the pad go' if kind['release'] else ''))
    return {'set': str(body['set']), 'level': int(lv)}
