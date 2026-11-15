"""board.custom.twin_session_fakes - test support for board_twin_session_selftest: a FAKE engines worker (HTTP /capability + /sessions) and a FAKE twin control port
(the JSON-line protocol of prf-board-engines/twin_ctl.h) so the backend half of sim-1 is proven with no worker and no docker. The fake mirrors the PROTOCOL only;
the real twin and worker are proven by the live half of the selftest."""
import contextlib
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeTwin:
    """One control port: token first, then set / adc / watch / run / status / reset; pin edges for watched pins go out as events."""

    def __init__(self, token):
        self.token, self.watch, self.adc, self.cycle, self.paused, self.closed = token, set(), {0: 750}, 0, False, False
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(('127.0.0.1', 0))
        self.srv.listen(1)
        self.port = self.srv.getsockname()[1]
        self.conn = None
        threading.Thread(target=self._serve, daemon=True).start()

    def _send(self, d):
        self.conn.sendall((json.dumps(d) + '\n').encode())

    def _serve(self):
        try:
            self.conn, _ = self.srv.accept()
        except OSError:
            return
        authed, buf = False, b''
        while not self.closed:
            try:
                chunk = self.conn.recv(4096)
            except OSError:
                return
            if not chunk:
                return
            buf += chunk
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                m = json.loads(line)
                if not authed:
                    if m.get('token') != self.token:
                        self._send({'t': 'refused', 'why': 'the token is wrong'})
                        return
                    authed = True
                    self._send({'t': 'ack', 'of': 'token'})
                    continue
                self.cycle += 800000
                if 'set' in m:
                    if m['set'] not in ('PD2', 'PD3', 'PD6', 'PB5'):
                        self._send({'t': 'refused', 'why': '%s is not a pin of atmega328p' % m['set']})
                        continue
                    self._send({'t': 'ack', 'of': 'set', 'pin': m['set'], 'level': m['level'], 'cycle': self.cycle})
                    if m['set'] in self.watch:
                        self._send({'t': 'pin', 'pin': m['set'], 'level': m['level'], 'cycle': self.cycle})
                    if m['set'] == 'PD2' and m['level'] == 1 and 'PD6' in self.watch:   # the "firmware": a release lights D6
                        self._send({'t': 'pin', 'pin': 'PD6', 'level': 1, 'cycle': self.cycle + 500000})
                elif 'adc' in m:
                    self.adc[m['adc']] = m['mv']
                    self._send({'t': 'ack', 'of': 'adc', 'adc': m['adc'], 'mv': m['mv']})
                elif 'watch' in m:
                    self.watch = set(m['watch'])
                    self._send({'t': 'ack', 'of': 'watch', 'watch': m['watch']})
                elif 'run' in m:
                    self.paused = not m['run']
                    self._send({'t': 'ack', 'of': 'run', 'run': bool(m['run'])})
                elif 'status' in m:
                    self._send({'t': 'status', 'cycle': self.cycle, 'adc0_mv': self.adc[0], 'paused': int(self.paused)})
                elif 'reset' in m:
                    self.cycle = 0
                    self._send({'t': 'ack', 'of': 'reset', 'cycle': 0})

    def close(self):
        self.closed = True
        for s in (self.conn, self.srv):
            try:
                s.close()
            except Exception:  # noqa: BLE001
                pass


class FakeDoor:
    """The worker's twin door (TWIN_DOOR_PLAN.md §3, §3a) in front of a FakeWorker's FakeTwins: a WebSocket server on loopback, `/sessions/<id>/ctl` joined
    to the twin's control port. First frame {"token"} (checked here, then passed on so the twin's own ack is the first frame back); one JSON line per text
    frame, sent WITHOUT the trailing newline; close codes 4400 bad first frame, 4403 wrong token, 4404 unknown session, 4410 the twin closed, 4502 the twin's
    port could not be reached. `tls` = (certfile, keyfile) serves wss://. The fake mirrors the PROTOCOL only; the real door is prf-board-engines/twin_door.py."""

    def __init__(self, worker, tls=None, host='127.0.0.1'):
        import ssl
        from websockets.sync.server import serve
        self.worker, self.seen = worker, []
        ctx = None
        if tls:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(*tls)
        self.srv = serve(self._handle, '127.0.0.1', 0, ssl=ctx)
        self.port = self.srv.socket.getsockname()[1]
        self.base = '%s://%s:%d' % ('wss' if tls else 'ws', host, self.port)
        self.transports = {'ctl': self.base + '/sessions/{id}/ctl', 'uart': self.base + '/sessions/{id}/uart'}
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def _handle(self, ws):
        parts = ws.request.path.strip('/').split('/')
        self.seen.append(ws.request.path)
        if len(parts) != 3 or parts[0] != 'sessions' or parts[2] not in ('ctl', 'uart'):
            return ws.close(4404, 'no such door path')
        t = self.worker.twins.get(parts[1])
        if t is None:
            return ws.close(4404, 'no session %s on this worker' % parts[1])
        try:
            first = json.loads(ws.recv(timeout=5))
        except Exception:  # noqa: BLE001
            return ws.close(4400, 'the first frame must be {"token": "..."}')
        if not isinstance(first, dict) or first.get('token') != t['body']['token']:
            return ws.close(4403, 'the token is wrong')
        if parts[2] == 'uart':
            return ws.close(4502, 'the fake twin has no serial port')
        try:
            sock = socket.create_connection(('127.0.0.1', t['twin'].port), timeout=3)
        except OSError:
            return ws.close(4502, 'the twin control port could not be reached')
        sock.sendall((json.dumps(first) + '\n').encode())

        def down():
            buf = b''
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    while b'\n' in buf:
                        line, buf = buf.split(b'\n', 1)
                        ws.send(line.decode())
            except Exception:  # noqa: BLE001
                pass
            with contextlib.suppress(Exception):
                ws.close(4410, 'the twin closed the stream')
        threading.Thread(target=down, daemon=True).start()
        try:
            for frame in ws:
                if not isinstance(frame, str):
                    ws.close(4400, 'the control stream takes text frames')
                    break
                sock.sendall((frame.rstrip('\n') + '\n').encode())
        except Exception:  # noqa: BLE001
            pass
        with contextlib.suppress(OSError):
            sock.close()

    def close(self):
        self.srv.shutdown()


class FakeWorker:
    """GET /capability, POST/GET/DELETE /sessions - the shape of prf-board-engines/board_sessions.py. sessions=False = an image older than sim-0.
    `transports` (a dict, e.g. a FakeDoor's) is advertised as the top-level "transports" of /capability when set."""

    def __init__(self, sessions=True, ttl_expire_after=None, transports=None):
        self.sessions_cap, self.twins, self.requests, self.ttl_expire_after, self.transports = sessions, {}, [], ttl_expire_after, transports
        self.made = []   # every FakeTwin ever started here (a stopped one leaves `twins`): `made[n].conn is None` = its control port was never dialled
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _json(self, code, d):
                b = json.dumps(d).encode()
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_GET(self):
                outer.requests.append(('GET', self.path))
                if self.path == '/capability':
                    cap = {'worker': 'board-engines', 'engines': {'avr-twin': {'available': True}}}
                    if outer.sessions_cap:
                        cap['sessions'] = {'available': True, 'max': 8}
                    if outer.transports is not None:
                        cap['transports'] = outer.transports
                    return self._json(200, cap)
                sid = self.path.rsplit('/', 1)[-1]
                if self.path.startswith('/sessions/') and sid in outer.twins:
                    t = outer.twins[sid]
                    return self._json(200, {'ok': True, 'id': sid, 'state': 'running', 'status': {'t': 'status', 'cycle': t['twin'].cycle, 'peak_rss_kb': 1234}})
                self._json(404, {'ok': False, 'error': 'no session %s on this worker' % sid})

            def do_POST(self):
                outer.requests.append(('POST', self.path))
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
                if self.path != '/sessions' or not body.get('hex_b64'):
                    return self._json(400, {'ok': False, 'error': 'POST /sessions needs hex_b64'})
                sid = 'f%05d' % (len(outer.twins) + 1)
                twin = FakeTwin(body['token'])
                outer.twins[sid] = {'twin': twin, 'body': body}
                outer.made.append(twin)
                now = time.time()
                self._json(200, {'ok': True, 'id': sid, 'ports': {'tcp': 0, 'ctl': twin.port}, 'started': now, 'expires': now + body['ttl_s'], 'status': {'t': 'status', 'cycle': 0}})

            def do_DELETE(self):
                outer.requests.append(('DELETE', self.path))
                sid = self.path.rsplit('/', 1)[-1]
                t = outer.twins.pop(sid, None)
                if not t:
                    return self._json(404, {'ok': False, 'error': 'no session %s on this worker' % sid})
                t['twin'].close()
                self._json(200, {'ok': True, 'id': sid, 'stopped': True})

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.url = 'http://127.0.0.1:%d' % self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        for t in list(self.twins.values()):
            t['twin'].close()
        self.httpd.shutdown()
        self.httpd.server_close()
