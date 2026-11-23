"""board_twin_session_c3_selftest - c3g-3 (AI-Notes/plans/C3_SESSION_PLAN.md): a C3 twin SESSION through the same backend the UNO's uses.

OFFLINE only: the kinds table, the esp family's session resolution in words, the request the esp-engines worker is sent, a press and a release
over the one control hub, the recorded interactions, the doors, and a UNO and a C3 session side by side - against a FAKE esp-engines worker and a FAKE
C3 twin (custom.twin_session_fakes_c3.py). No worker, no QEMU, no docker, no network, and no firmware is built: the image is a stand-in.
The REAL twin and worker are proven in prf-esp-engines (test_c3_twin.py, test_c3_sessions.py) on the pin-model QEMU with the real chip-HAL image.

    PYTHONPATH=.:modules python3 -m board.board_twin_session_c3_selftest      # from polari-framework/
    (board.board_selftest calls run_twin_session_c3(check))
"""
import base64
import contextlib
import hashlib
import json
import os
import tempfile
import types

from board.board_twin_session_selftest import HEX, _env, _mgr

IMG = b'\xe9' + bytes(4095)   # a stand-in for the merged flash image: the made-up worker reads no byte of it
LIGHT, NO_PADS = 'esp32c3-light', 'c3-sim-rig'


def run_twin_session_c3(check):
    with tempfile.TemporaryDirectory(prefix='twin-session-c3-test-') as td, \
            _env(POLARI_TWIN_TOKEN_FILE=os.path.join(td, 'secret'), POLARI_TWIN_TOKEN_SECRET=None, POLARI_BOARD_HOME=os.path.join(td, 'home'),
                 BOARD_ENGINES_URL=None, ESP_ENGINES_URL=None):
        from board.custom import board_engines as be, twin_kinds as K, twin_sessions as TS
        from board.custom.twin_session_fakes import FakeWorker
        from board.custom.twin_session_fakes_c3 import FakeC3Twin
        mgr = _mgr()
        old, esp, avr = FakeWorker(sessions=False, kind='c3', twin=FakeC3Twin), FakeWorker(kind='c3', twin=FakeC3Twin), FakeWorker()
        real_image = K.c3_image
        try:
            _build(check, K)
            _kinds(check, K)
            _resolve(check, be, TS, mgr, old, esp, avr)
            with _env(ESP_ENGINES_URL=esp.url):
                name = _start(check, K, TS, mgr, esp)
                _press(check, TS, mgr, name)
                _doors(check, K, TS, mgr)
                with _env(BOARD_ENGINES_URL=avr.url):
                    _side_by_side(check, TS, mgr, esp, avr)
        finally:
            K.c3_image = real_image
            for s in list(TS._rows(mgr)):
                if s.state == 'running':
                    with _env(ESP_ENGINES_URL=esp.url, BOARD_ENGINES_URL=avr.url), contextlib.suppress(TS.SessionRefused):
                        TS.stop(mgr, s.name)
            for w in (old, esp, avr):
                w.close()
            TS.HUBS.clear()


def _refused(fn, *a, **kw):
    """-> (status, words) of the refusal, or (0, '') when it did not refuse."""
    from board.custom import twin_kinds as K, twin_sessions as TS
    try:
        fn(*a, **kw)
    except (TS.SessionRefused, K.KindRefused) as e:
        return e.status, str(e)
    return 0, ''


def _build(check, K):
    """c3_image() itself, with the engine run replaced: what it asks the shipped pipeline for, and what a failed build becomes."""
    from board.custom import light_c3_run as R
    asked, real = [], R.build

    def fake_build(work, variant=None, **knobs):
        asked.append((work, variant, knobs, os.path.isfile(os.path.join(work, '.lock'))))
        if len(asked) > 1:
            return {'state': 'refused', 'notes': 'idf.py build failed (made up)', 'image_path': ''}
        with open(os.path.join(work, 'flash_image.bin'), 'wb') as f:
            f.write(IMG)
        return {'state': 'built', 'image_path': os.path.join(work, 'flash_image.bin')}
    R.build = fake_build
    try:
        got = K.c3_image(LIGHT)
        st, why = _refused(K.c3_image, LIGHT)
    finally:
        R.build = real
    work, variant, knobs, locked = asked[0]
    check('c3g-3: the C3 image of a session is the CHIP HAL build (pin_shim 0) of the config, asked of the shipped pipeline in a kept work folder of its own (its build store is the '
          'cache), one build at a time (a lock file)', got == IMG and variant == LIGHT and knobs == {'pin_shim': 0} and locked
          and work == os.path.join(os.environ['POLARI_BOARD_HOME'], K.C3_WORK), (work.replace(os.environ['POLARI_BOARD_HOME'], '<home>'), variant, knobs, locked))
    check('c3g-3: a build that fails is a refusal with the build\'s own words (HTTP 422), never a session on an old image: %s' % why, st == 422 and 'idf.py build failed' in why)


def _kinds(check, K):
    check('c3g-3: a config\'s chip decides its session kind: uno-light -> avr (arduino-uno-r3), %s -> c3 (esp32-c3); a row is read back by its board' % LIGHT,
          K.of('uno-light') is K.AVR and K.of(LIGHT) is K.C3 and K.of_board('esp32-c3') is K.C3 and K.of_board('arduino-uno-r3') is K.AVR and K.C3['family'] == 'esp')
    fw = K.firmware(K.C3, LIGHT, IMG)
    lay = json.loads(fw['layout'])
    check('c3g-3: the C3 firmware of a session = the image, its sha256, the pin layout as the chip rows export it (JSON text, %d bytes), the LED-to-sense jumper as the board wire %s, '
          'and the three pads watched %s' % (len(fw['layout']), fw['wires'], fw['watch']),
          fw['bytes'] == IMG and fw['sha256'] == hashlib.sha256(IMG).hexdigest() and isinstance(lay, dict) and lay and fw['wires'] == '0-1' and fw['watch'] == ['GPIO0', 'GPIO1', 'GPIO3'])
    built = []
    K.c3_image = lambda config: built.append(config) or IMG
    st, why = _refused(K.admit, K.C3, NO_PADS)
    check('c3g-3: a C3 config that uses no pad is refused in words: %s' % why[:120], st == 400 and 'uses no pad' in why and LIGHT in why and _refused(K.firmware, K.C3, NO_PADS)[0] == 400 and not built)
    st, why = _refused(K.admit, K.C3, LIGHT, True)
    check('c3g-3: "free" is refused for a C3 in words (twin time only); the light itself and every UNO request are admitted',
          st == 400 and 'no free-running mode' in why and _refused(K.admit, K.C3, LIGHT) == (0, '') and _refused(K.admit, K.AVR, 'uno-light', True) == (0, ''))
    body = K.request(K.AVR, K.firmware(K.AVR, 'uno-light', HEX), 60, 't', owner='o', free=True)
    check('c3g-3: the UNO\'s request is what it was (hex_b64, board, mcu, ttl_s, token, owner, free)',
          body == {'hex_b64': base64.b64encode(HEX).decode(), 'board': 'arduino-uno-r3', 'mcu': 'atmega328p', 'ttl_s': 60, 'token': 't', 'owner': 'o', 'free': True})


def _resolve(check, be, TS, mgr, old, esp, avr):
    with _env(ESP_ENGINES_URL=old.url):
        r = be.resolve_sessions('esp')
    check('c3g-3: an esp-engines worker without /sessions is REFUSED in words naming its own knob and service: %s' % r['why'][:120],
          r['how'] == 'refused' and 'ESP_ENGINES_URL' in r['why'] and 'does not list sessions' in r['why'] and 'roll the esp-engines service' in r['why'] and 'c3g-2' in r['why'])
    r = be.resolve_sessions('esp')
    check('c3g-3: with no esp knob and no binding the refusal names the esp knob and its provider (board.esp-engines)',
          r['how'] == 'refused' and 'ESP_ENGINES_URL' in r['why'] and 'board.esp-engines' in r['why'] and 'BOARD_ENGINES_URL' not in r['why'])
    with _env(BOARD_ENGINES_URL=avr.url):
        st, why = _refused(TS.start, mgr, LIGHT, hex_bytes=IMG)
        r = be.resolve_sessions()
    check('c3g-3: a C3 session never goes to the board worker: with only BOARD_ENGINES_URL set it is refused (HTTP 424), nothing is posted, no row; the UNO still resolves there',
          st == 424 and 'ESP_ENGINES_URL' in why and not avr.twins and not TS._rows(mgr) and r['how'] == 'remote' and r['where'] == avr.url, (st, why, r))
    with _env(ESP_ENGINES_URL=esp.url):
        r = be.resolve_sessions('esp')
        st, why = _refused(TS.start, mgr, 'uno-light', hex_bytes=HEX)
    check('c3g-3: the esp knob serves the esp family only: a C3 resolves to it, a UNO session is refused (424) and nothing reaches the esp worker',
          r == {'how': 'remote', 'where': esp.url, 'why': 'knob'} and st == 424 and 'BOARD_ENGINES_URL' in why and not esp.twins)


def _start(check, K, TS, mgr, esp):
    st, why = _refused(TS.start, mgr, LIGHT, hex_bytes=IMG, free=True)
    st2, why2 = _refused(TS.start, mgr, NO_PADS, hex_bytes=IMG)
    check('c3g-3: start refuses "free" and a config with no pads with HTTP 400 in words; the worker is asked nothing and no row is written',
          st == 400 and st2 == 400 and 'uses no pad' in why2 and not esp.twins and not TS._rows(mgr), (st, why, st2, why2))
    v = TS.start(mgr, LIGHT, ttl_s=120, owner='tester', hex_bytes=IMG)
    sha = hashlib.sha256(IMG).hexdigest()
    check('c3g-3: start -> a running TwinSession row: participant twin:esp32-c3#0, the LOCKED firmware is the image (sha256 %s), the token shown once and in no row' % sha[:12],
          v['state'] == 'running' and v['board'] == 'esp32-c3' and v['participant'] == 'twin:esp32-c3#0' and v['firmware'] == {'sha256': sha, 'bytes': len(IMG), 'locked': True, 'config': LIGHT}
          and len(v['token']) == 32 and v['token'] not in json.dumps(TS.one(mgr, v['name'])) and v['watch'] == ['GPIO0', 'GPIO1', 'GPIO3'], v)
    sent = next(iter(esp.twins.values()))['body']
    check('c3g-3: the esp worker was sent image_b64 (the image), the layout as JSON text, wires 0-1, board esp32-c3, the derived token and the ttl - and no hex_b64, no free',
          base64.b64decode(sent['image_b64']) == IMG and isinstance(json.loads(sent['layout']), dict) and sent['wires'] == '0-1' and sent['board'] == 'esp32-c3'
          and sent['token'] == v['token'] and sent['ttl_s'] == 120 and sent['owner'] == 'tester' and 'hex_b64' not in sent and 'free' not in sent, sorted(sent))
    return v['name']


def _press(check, TS, mgr, name):
    from board.custom import bench_interactions as BI
    sub = TS.events(mgr, name)
    r = TS.inject(mgr, name, {'set': 'GPIO3', 'level': 0, 'kind': 'press', 'part': 'pushbutton'})
    evs = [sub.get(2) for _ in range(3)]
    check('c3g-3: a press (GPIO3 driven to 0) is acked with no cycle count; the button, the LED and - over the board wire - the sense pad change, each event stamped in ns',
          r['ok'] and r['reply'] == {'t': 'ack', 'of': 'set', 'pin': 'GPIO3', 'level': 0, 'z': False}
          and [(e['pin'], e['level']) for e in evs] == [('GPIO3', 0), ('GPIO0', 1), ('GPIO1', 1)] and all(e['ns'] > 0 and 'cycle' not in e for e in evs), (r, evs))
    r = TS.inject(mgr, name, {'set': 'GPIO3', 'level': 'z', 'kind': 'release', 'part': 'pushbutton'})
    ev = sub.get(2)
    check('c3g-3: the release lets the pad go ("level": "z"): acked as z, and the event says the pad floats (level null, z true), never a made-up level',
          r['ok'] and r['sent'] == {'set': 'GPIO3', 'level': 'z'} and r['reply']['z'] is True and r['reply']['level'] is None and (ev['pin'], ev['level'], ev['z']) == ('GPIO3', None, True), (r, ev))
    TS.inject(mgr, name, {'set': 'GPIO3', 'level': 0, 'kind': 'press', 'part': 'pushbutton'})
    evs = [sub.get(2) for _ in range(3)]
    check('c3g-3: a second press turns the LED off again', [(e['pin'], e['level']) for e in evs] == [('GPIO3', 0), ('GPIO0', 0), ('GPIO1', 0)], evs)
    rows = BI.listing(mgr, name)
    check('c3g-3: each action is a BenchInteraction row: the press "driven to 0", the release "let go" with no level recorded (-1), and the cycle is "not reported by the twin" (a C3 has none)',
          [x['kind'] for x in rows] == ['press', 'release', 'press'] and 'GPIO3 driven to 0' in rows[0]['what'] and 'GPIO3 let go' in rows[1]['what'] and rows[1]['value'] == -1.0
          and all(x['twin_cycle'] == -1 and x['twin_cycle_text'] == 'not reported by the twin' and x['ok'] for x in rows), rows)
    told = [TS.inject(mgr, name, b) for b in ({'adc': 0, 'mv': 750}, {'reset': 1}, {'run': False}, {'set': 'PD2', 'level': 1})]
    check('c3g-3: what the C3 twin cannot do comes back in ITS words, ok false: no ADC, no reset, no pause, and PD2 is not a pad',
          not any(x['ok'] for x in told) and 'no ADC' in told[0]['reply']['why'] and 'no reset' in told[1]['reply']['why'] and 'no pause' in told[2]['reply']['why']
          and 'PD2 is not a pad' in told[3]['reply']['why'], [x['reply'] for x in told])
    st, why = _refused(TS.inject, mgr, name, {'set': 'GPIO3', 'level': 7})
    st2, why2 = _refused(TS.inject, mgr, name, {})
    check('c3g-3: a malformed C3 inject is refused with HTTP 400 in the C3\'s words (0, 1 or "z"; pads are GPIO<n>)', st == 400 and '"z"' in why and st2 == 400 and 'GPIO3' in why2, (why, why2))
    status = TS.inject(mgr, name, {'status': 1})
    check('c3g-3: status is the twin\'s own: the chip, virtual ns and every pad\'s level', status['ok'] and status['reply']['chip'] == 'esp32c3' and status['reply']['pads']['GPIO0'] == '0'
          and json.loads(TS._find(mgr, name).last_status_json)['chip'] == 'esp32c3')
    sub.close()


def _doors(check, K, TS, mgr):
    import falcon
    import falcon.testing as ft
    from board.board_endpoints import construct_board_endpoints
    built = []
    K.c3_image = lambda config: built.append(config) or IMG
    server = types.SimpleNamespace(falconServer=falcon.App(), manager=mgr)
    with contextlib.redirect_stdout(open(os.devnull, 'w')):
        construct_board_endpoints(server)
    cl = ft.TestClient(server.falconServer)
    post = cl.simulate_post('/api/board/twins', json={'config': LIGHT, 'ttl_s': 90, 'owner': 'door'})
    name = (post.json or {}).get('name', '')
    check('c3g-3 DOORS: POST /api/board/twins {"config": "%s"} -> 201; the image is built once through the shipped pipeline (here a stand-in), as twin:esp32-c3#1' % LIGHT,
          post.status_code == 201 and built == [LIGHT] and post.json['participant'] == 'twin:esp32-c3#1' and len(post.json['token']) == 32, post.json)
    inj = cl.simulate_post('/api/board/twins/%s/inject' % name, json={'set': 'GPIO3', 'level': 0})
    rel = cl.simulate_post('/api/board/twins/%s/inject' % name, json={'set': 'GPIO3', 'level': 'z'})
    bad = cl.simulate_post('/api/board/twins/%s/inject' % name, json={'adc': 0, 'mv': 750})
    check('c3g-3 DOORS: POST .../inject presses and lets go (200, the twin\'s ack); an adc line -> 409 with the twin\'s words', inj.status_code == 200 and rel.status_code == 200
          and rel.json['reply']['z'] is True and bad.status_code == 409 and 'no ADC' in bad.json['reply']['why'], (inj.json, rel.json, bad.json))
    sse = cl.simulate_get('/api/board/twins/%s/events?replay=10&limit=4&seconds=5' % name)
    datas = [json.loads(ln[5:]) for ln in sse.text.splitlines() if ln.startswith('data:')]
    check('c3g-3 DOORS: GET .../events replays the pad changes (GPIO3 0, GPIO0 1, GPIO1 1, GPIO3 let go)',
          datas[0]['t'] == 'hello' and [(d['pin'], d['level']) for d in datas[1:]] == [('GPIO3', 0), ('GPIO0', 1), ('GPIO1', 1), ('GPIO3', None)], datas)
    free = cl.simulate_post('/api/board/twins', json={'config': LIGHT, 'free': True})
    none = cl.simulate_post('/api/board/twins', json={'config': NO_PADS})
    check('c3g-3 DOORS: "free" and a config with no pads -> 400 in words BEFORE any build (a build takes minutes): nothing more was built', free.status_code == 400
          and 'no free-running mode' in free.json['error'] and none.status_code == 400 and 'uses no pad' in none.json['error'] and built == [LIGHT], (free.json, none.json, built))
    gone = cl.simulate_delete('/api/board/twins/%s' % name)
    check('c3g-3 DOORS: DELETE stops it', gone.status_code == 200 and gone.json['state'] == 'ended')
    from board.custom import twin_sessions_cli as CLI
    check('c3g-3 CLI: `inject <name> set GPIO3 z` is the release; the UNO words are unchanged',
          CLI._inject_body(['set', 'GPIO3', 'z']) == {'set': 'GPIO3', 'level': 'z'} and CLI._inject_body(['set', 'PD2', '1']) == {'set': 'PD2', 'level': 1})
    lines = [CLI.event_line(e) for e in datas[1:3] + datas[4:5]] + [CLI.event_line({'t': 'pin', 'pin': 'PD6', 'level': 1, 'cycle': 1300000})]
    st_line = CLI.status_line({'t': 'status', 'chip': 'esp32c3', 'ns': 5000000, 'pads': {'GPIO0': '1', 'GPIO1': '1', 'GPIO3': 'z'}})
    check('c3g-3 CLI: `events` prints a C3 edge with its virtual ns and a pad let go in words (%s | %s); a UNO edge keeps its cycle line; `show` prints the C3 status as pads'
          % (lines[0].strip(), lines[2].strip()), lines[0].startswith('ns ') and lines[0].endswith('GPIO3 -> 0') and lines[1].endswith('GPIO0 -> 1') and lines[2].endswith('GPIO3 -> let go')
          and lines[3] == 'cycle 1300000      PD6 -> 1' and 'GPIO0=1 GPIO1=1' in st_line and 'GPIO3' not in st_line, (lines, st_line))


def _side_by_side(check, TS, mgr, esp, avr):
    u = TS.start(mgr, 'uno-light', ttl_s=60, hex_bytes=HEX)
    c = TS.start(mgr, LIGHT, ttl_s=60, hex_bytes=IMG)
    sent = next(iter(avr.twins.values()))['body']
    check('c3g-3: a UNO and a C3 session run side by side, each on its own worker, each counted per board (twin:arduino-uno-r3#0 beside twin:esp32-c3#1); the UNO request has its old keys',
          u['participant'] == 'twin:arduino-uno-r3#0' and c['participant'] == 'twin:esp32-c3#1' and u['worker'] == avr.url and c['worker'] == esp.url
          and set(sent) == {'hex_b64', 'board', 'mcu', 'ttl_s', 'token', 'owner', 'free'} and u['watch'] == TS.DEFAULT_WATCH, (u['participant'], c['participant'], sorted(sent)))
    r = TS.inject(mgr, u['name'], {'set': 'PD2', 'level': 1})
    st, why = _refused(TS.inject, mgr, u['name'], {'set': 'PD2', 'level': 'z'})
    check('c3g-3: the UNO session is as it was: its ack carries the cycle, and "z" is refused for it (HTTP 400: 0 or 1)',
          r['ok'] and r['reply']['cycle'] > 0 and st == 400 and why == '"set" needs "level": 0 or 1', (r, st, why))
    parts = [p['variant'] for p in TS.participants(mgr)]
    check('c3g-3: both are Hardware Solution participants', 'twin:arduino-uno-r3#0' in parts and 'twin:esp32-c3#1' in parts, parts)
    for v in (u, c):
        TS.stop(mgr, v['name'])
    first = [s for s in TS._rows(mgr) if s.state == 'running']
    check('c3g-3: stopping each asks its own worker: the board worker holds no twin, the esp worker only the first C3 session, which is still running',
          not avr.twins and len(esp.twins) == 1 and [s.participant for s in first] == ['twin:esp32-c3#0'], (list(esp.twins), list(avr.twins)))
    TS.stop(mgr, first[0].name)
    check('c3g-3: the last stop leaves the esp worker with no twin and no running row', not esp.twins and not [s for s in TS._rows(mgr) if s.state == 'running'])


if __name__ == '__main__':
    n = [0, 0]

    def _check(label, cond, extra=''):
        n[0] += 1
        n[1] += bool(cond)
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, '' if cond else extra))
    run_twin_session_c3(_check)
    print('%d/%d checks passed' % (n[1], n[0]))
    raise SystemExit(0 if n[0] == n[1] else 1)
