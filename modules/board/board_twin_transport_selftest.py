"""board_twin_transport_selftest - td-1 / td-2 / td-6 (AI-Notes/plans/TWIN_DOOR_PLAN.md): reaching a twin session through the worker's twin DOOR.

Always offline: a FAKE worker, a FAKE twin control port and a FAKE door (custom.twin_session_fakes.FakeDoor, a real WebSocket server on loopback that follows
the door contract of the plan's sections 3 and 3a). It proves the BACKEND half; the real door (prf-board-engines/twin_door.py) is proven by its own selftest and by
the live half of board_twin_session_selftest against a released worker.

  - the transport is READ from /capability (`transports`), never guessed: no door -> tcp:// on the session ports; a door -> wss:// with the session id filled in
  - a malformed advertisement is refused in words; an advertised door that is DOWN refuses the session and never falls back to TCP (the user's D4)
  - the Hub speaks the same protocol over the door: token first, ack, inject, pin events fanned out; the door's close code and reason reach the refusal words
  - a wss:// door is VERIFIED under the backend's one TLS policy: an untrusted certificate is refused, POL_TLS_CA makes it trusted (never an unverified send)

    PYTHONPATH=.:modules python3 -m board.board_twin_transport_selftest      # from polari-framework/
    (board.board_selftest calls run_twin_transport(check))
"""
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import types

from board.board_twin_session_selftest import HEX, _env, _mgr


def run_twin_transport(check):
    with tempfile.TemporaryDirectory(prefix='twin-transport-test-') as td, _env(POLARI_TWIN_TOKEN_FILE=os.path.join(td, 'secret'), POLARI_TWIN_TOKEN_SECRET=None,
                                                                             POL_TLS_CA=None, POL_TLS_INSECURE=None, POLARI_INSECURE=None):
        _pick(check)
        _over_the_door(check)
        _door_down(check)
        _tls(check, td)


# ---------------------------------------------------------------------------------------------------------------- td-1
def _pick(check):
    from board.custom import twin_transport as TT
    ports = {'tcp': 9832, 'ctl': 9833}
    door = {'ctl': 'wss://twin.board-engines.isle/sessions/{id}/ctl', 'uart': 'wss://twin.board-engines.isle/sessions/{id}/uart'}
    plain = TT.pick({'sessions': {'available': True}}, 'https://board-engines.isle', 's00001', ports)
    check('td-1: a worker that advertises NO transports is reached on the session\'s TCP ports, and the reason says so: %s' % plain['why'][:90],
          plain['ctl_url'] == 'tcp://board-engines.isle:9833' and plain['uart_url'] == 'tcp://board-engines.isle:9832' and 'no twin door' in plain['why'], plain)
    via = TT.pick({'transports': door}, 'https://board-engines.isle', 's 0/1', ports)
    check('td-1: advertised transports are used with the session id filled in (and quoted): %s' % via['ctl_url'],
          via['ctl_url'] == 'wss://twin.board-engines.isle/sessions/s%200%2F1/ctl' and via['uart_url'] == 'wss://twin.board-engines.isle/sessions/s%200%2F1/uart'
          and 'read from the worker\'s /capability' in via['why'] and TT.kind(via['ctl_url']) == 'door' and TT.kind(plain['ctl_url']) == 'tcp', via)
    half = TT.pick({'transports': {'ctl': door['ctl']}}, 'https://board-engines.isle', 'a', ports)
    check('td-1: the choice is per stream: a door for ctl only leaves uart on TCP, both said in the reason',
          half['ctl_url'].startswith('wss://') and half['uart_url'] == 'tcp://board-engines.isle:9832' and 'uart on plain TCP' in half['why'], half)
    bad = {'no placeholder': {'transports': {'ctl': 'wss://twin.board-engines.isle/sessions/ctl'}},
           'no TLS off this device': {'transports': {'ctl': 'ws://twin.board-engines.isle/sessions/{id}/ctl'}},
           'a tcp url as a door': {'transports': {'ctl': 'tcp://board-engines.isle:{id}'}},
           'another scheme': {'transports': {'ctl': 'https://twin.board-engines.isle/sessions/{id}/ctl'}},
           'not an object': {'transports': 'wss://twin.board-engines.isle'},
           'an empty object': {'transports': {}},
           'an unreadable capability': None}
    said = {}
    for label, cap in bad.items():
        try:
            TT.pick(cap, 'https://board-engines.isle', 'a', ports)
            said[label] = ''
        except TT.TransportRefused as e:
            said[label] = str(e)
    check('td-1: a malformed advertisement is REFUSED in words, never repaired or skipped (%d shapes): e.g. %s' % (len(bad), said['no TLS off this device'][:100]),
          all(said.values()) and 'without TLS' in said['no TLS off this device'] and '{id}' in said['no placeholder'], said)
    check('td-1: ws:// is accepted for a loopback test door only', TT.split('ws://127.0.0.1:8765/sessions/a/ctl')[0] == 'ws')


# ---------------------------------------------------------------------------------------------------------------- td-2
def _over_the_door(check):
    from board.custom import twin_sessions as TS, twin_ctl_hub as HUB, twin_token
    from board.custom.twin_session_fakes import FakeDoor, FakeWorker
    worker = FakeWorker(sessions=True)
    door = FakeDoor(worker)
    worker.transports = door.transports
    mgr = _mgr()
    try:
        with _env(BOARD_ENGINES_URL=worker.url):
            v = TS.start(mgr, 'uno-light', ttl_s=120, owner='tester', hex_bytes=HEX)
            name, sid = v['name'], v['worker_session']
            row = TS._find(mgr, name)
            check('td-1: start against a worker with a door -> the row keeps HOW it is reached (%s) and why; the view says transport "door" and shows no token'
                  % row.ctl_url, row.ctl_url == '%s/sessions/%s/ctl' % (door.base, sid) and row.uart_url == '%s/sessions/%s/uart' % (door.base, sid)
                  and 'twin door' in row.transport_why and v['transport'] == 'door' and v['ports'] == 'control %s, serial report %s' % (row.ctl_url, row.uart_url)
                  and v['token'] not in json.dumps(TS.one(mgr, name)) and v['ctl_port'] == row.ctl_port, v)
            twin = worker.twins[sid]['twin']
            check('td-2: the control connection went THROUGH the door (path %s), token first; the door passed it on and the twin acked' % door.seen[:1],
                  door.seen == ['/sessions/%s/ctl' % sid] and twin.conn is not None and twin.watch == set(TS.DEFAULT_WATCH))
            sub, sub2 = TS.events(mgr, name), TS.events(mgr, name)
            r = TS.inject(mgr, name, {'set': 'PD2', 'level': 1})
            evs, evs2 = [sub.get(2), sub.get(2)], [sub2.get(2), sub2.get(2)]
            check('td-2: inject over the door -> the twin\'s ack with its cycle; pin edges fan out to every subscriber (PD2, then PD6) exactly as over TCP',
                  r['ok'] and r['reply']['t'] == 'ack' and r['reply']['cycle'] > 0
                  and [(e['pin'], e['level']) for e in evs] == [('PD2', 1), ('PD6', 1)] == [(e['pin'], e['level']) for e in evs2], (r, evs, evs2))
            r = TS.inject(mgr, name, {'set': 'PX9', 'level': 1})
            st = TS.inject(mgr, name, {'status': 1})
            check('td-2: the twin\'s own refusal words and a status reply come back over the door: %s' % r['reply'].get('why'),
                  not r['ok'] and r['reply']['why'] == 'PX9 is not a pin of atmega328p' and st['reply']['t'] == 'status')
            # the door's refusals: the code and the reason reach the words
            words = {}
            for label, url, tok in (('wrong token', row.ctl_url, 'not-the-token'), ('unknown session', '%s/sessions/nope/ctl' % door.base, twin_token.derive(name)),
                                    ('uart refused', row.uart_url, twin_token.derive(name))):
                try:
                    HUB.Hub(url, tok).connect()
                    words[label] = ''
                except HUB.HubRefused as e:
                    words[label] = str(e)
            check('td-2: the door\'s close code and reason are in the refusal words: %s' % words['wrong token'][-70:],
                  '4403' in words['wrong token'] and 'the token is wrong' in words['wrong token'] and '4404' in words['unknown session']
                  and 'no session nope' in words['unknown session'] and '4502' in words['uart refused'], words)
            # the twin goes away -> the door closes with 4410 -> every subscriber is told, the hub is dead, the next inject re-dials (and is refused in words)
            dials = door.seen.count('/sessions/%s/ctl' % sid)
            twin.close()
            closed, end = None, time.time() + 3
            while time.time() < end and closed is None:
                ev = sub.get(0.3)
                if ev and ev.get('t') == 'closed':
                    closed = ev
            check('td-2: when the twin closes its stream the door closes with 4410 and every subscriber gets a `closed` event in words: %s' % (closed and closed['why']),
                  closed is not None and '4410' in closed['why'] and TS.HUBS[name].dead, closed)
            try:
                TS.inject(mgr, name, {'status': 1})
                again = ''
            except TS.SessionRefused as e:
                again = '%s %s' % (e.status, e)
            check('td-2: the next inject re-dials the SAME door (never TCP) and its failure is a 502 in words: %s' % again[:110],
                  again.startswith('502') and 'cannot reach the twin control channel' in again and door.base in again and door.seen.count('/sessions/%s/ctl' % sid) == dials + 1, again)
            sub.close()
            sub2.close()
            # a row written before td-1 (no URLs) still says how it was reached
            old = types.SimpleNamespace(host='worker.example', tcp_port=9832, ctl_port=9833)
            check('td-1: a row written before the door existed (no URLs) is read as its TCP ports', TS.channels(old) == ('tcp://worker.example:9833', 'tcp://worker.example:9832'))
            # a malformed advertisement at start: refused, and the worker session is not left running
            worker.transports = {'ctl': 'wss://no-placeholder.example/ctl'}
            from board.custom import board_engines as be
            be._CAP_CACHE.clear()
            before = len(worker.twins)
            try:
                TS.start(mgr, 'uno-light', hex_bytes=HEX)
                bad = ''
            except TS.SessionRefused as e:
                bad = '%s %s' % (e.status, e)
            check('td-1: a malformed door advertisement refuses the start in words (502) and the worker session it had started is stopped: %s' % bad[:100],
                  bad.startswith('502') and 'cannot be read' in bad and '{id}' in bad and len(worker.twins) == before, bad)
    finally:
        _cleanup(mgr, worker, door)


def _cleanup(mgr, worker, door=None):
    from board.custom import board_engines as be, twin_sessions as TS
    for hub in list(TS.HUBS.values()):
        hub.close('selftest over')
    TS.HUBS.clear()
    be._CAP_CACHE.clear()
    if door is not None:
        door.close()
    worker.close()


# ---------------------------------------------------------------------------------------------------------------- D4
def _door_down(check):
    from board.custom import twin_sessions as TS
    from board.custom.twin_session_fakes import FakeWorker
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    dead = s.getsockname()[1]
    s.close()   # nothing listens here: an advertised door whose app is not running
    worker = FakeWorker(sessions=True, transports={'ctl': 'ws://127.0.0.1:%d/sessions/{id}/ctl' % dead, 'uart': 'ws://127.0.0.1:%d/sessions/{id}/uart' % dead})
    mgr = _mgr()
    try:
        with _env(BOARD_ENGINES_URL=worker.url):
            try:
                TS.start(mgr, 'uno-light', hex_bytes=HEX)
                why, st = '', 0
            except TS.SessionRefused as e:
                why, st = str(e), e.status
        rows = TS._rows(mgr)
        check('D4: a worker that advertises a door which is DOWN refuses the session (502) with the door\'s URL in the words: %s' % why[:150],
              st == 502 and 'ws://127.0.0.1:%d/sessions/' % dead in why and 'twin door' in why and 'plain TCP is not tried' in why, why)
        check('D4: nothing fell back to TCP (the twin\'s control port was never dialled), the worker session was stopped (DELETE) and the row is ended, not "running"',
              len(worker.made) == 1 and worker.made[0].conn is None and not worker.twins and any(m == 'DELETE' for m, _p in worker.requests)
              and [r.state for r in rows] == ['ended'] and not TS.HUBS, (worker.made, worker.requests, rows))
    finally:
        _cleanup(mgr, worker)


# ---------------------------------------------------------------------------------------------------------------- TLS
def _tls(check, td):
    from board.custom import twin_sessions as TS, twin_ctl_hub as HUB
    from board.custom.twin_session_fakes import FakeDoor, FakeWorker
    if not shutil.which('openssl'):
        check('td-2 TLS: SKIPPED - no openssl on this device to make a test certificate', True)
        return
    crt, key = os.path.join(td, 'door.crt'), os.path.join(td, 'door.key')
    made = subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1', '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                           '-keyout', key, '-out', crt], capture_output=True, text=True)
    if made.returncode != 0:
        check('td-2 TLS: SKIPPED - openssl could not make a test certificate (%s)' % made.stderr.strip()[-80:], True)
        return
    worker = FakeWorker(sessions=True)
    door = FakeDoor(worker, tls=(crt, key), host='localhost')
    worker.transports = door.transports
    mgr = _mgr()
    try:
        with _env(BOARD_ENGINES_URL=worker.url):
            try:
                TS.start(mgr, 'uno-light', hex_bytes=HEX)
                why, st = '', 0
            except TS.SessionRefused as e:
                why, st = str(e), e.status
            check('td-2 TLS: a wss:// door whose certificate this server does not trust is REFUSED (verification is never skipped): %s' % why[why.find('unreachable'):][:110],
                  st == 502 and 'certificate verify failed' in why.lower() and door.base in why and not worker.twins, why)
            with _env(POL_TLS_CA=crt):
                v = TS.start(mgr, 'uno-light', hex_bytes=HEX)
                r = TS.inject(mgr, v['name'], {'set': 'PD2', 'level': 1})
                check('td-2 TLS: with POL_TLS_CA naming the door\'s CA the same door is trusted and the session works over wss:// (%s)' % v['ctl_url'],
                      v['ctl_url'].startswith('wss://localhost:') and r['ok'] and r['reply']['t'] == 'ack', (v, r))
                try:
                    HUB.Hub(v['ctl_url'].replace('localhost', '127.0.0.1'), 'x').connect()
                    name_ok = ''
                except HUB.HubRefused as e:
                    name_ok = str(e)
                check('td-2 TLS: the NAME is checked too: the same certificate under another host name is refused: %s' % name_ok[-90:],
                      'certificate verify failed' in name_ok.lower(), name_ok)
                _one_thread(check, v['ctl_url'])
    finally:
        _cleanup(mgr, worker, door)


def _one_thread(check, url, opens=30):
    """The door channel reads and writes on ONE thread of its own. The threaded client lost about 1 TLS 1.3 handshake in 15 through the isle agent
    (2026-11-15, the installed door); the answer was one I/O thread, never a TLS 1.2 cap. Here: many opens in a row, each refused by the door's own code."""
    import threading
    from board.custom import twin_ctl_hub as HUB
    failed, versions, ended, added, io = [], set(), set(), set(), []

    async def _who():
        return threading.current_thread()

    for _ in range(opens):
        try:
            ch = HUB.open_channel(url, timeout=3)
        except (OSError, RuntimeError) as e:
            failed.append(str(e))
            continue
        added.add(ch._on_loop(_who(), 2) is ch._thread and ch._thread.name == 'twin-door-io')   # the connection's loop runs on the channel's own thread
        io.append(ch._thread)
        tls = ch.ws.transport.get_extra_info('ssl_object')
        versions.add(tls.version() if tls else 'no TLS')
        try:
            ch.send(json.dumps({'token': 'not the token'}))
        except OSError:
            pass
        for _line in ch.lines():
            pass
        ended.add(ch.ended)
        ch.close()
    for t in io:
        t.join(3)
    left = [t.name for t in io if t.is_alive()]
    check('td-2 TLS: %d opens in a row over wss:// all complete (TLS %s, never capped), each on ONE I/O thread of its own, each refused by the door\'s code '
          '(4403), and no I/O thread is left behind' % (opens, '/'.join(sorted(versions))),
          not failed and versions == {'TLSv1.3'} and added == {True} and len(ended) == 1 and '4403' in next(iter(ended)) and not left,
          (failed[:2], versions, added, ended, left))


if __name__ == '__main__':
    n = [0, 0]

    def _check(label, cond, extra=''):
        n[0] += 1
        n[1] += bool(cond)
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, '' if cond else extra))
    run_twin_transport(_check)
    print('%d/%d checks passed' % (n[1], n[0]))
    raise SystemExit(0 if n[0] == n[1] else 1)
