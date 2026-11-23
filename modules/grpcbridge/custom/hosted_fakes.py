"""grpcbridge.custom.hosted_fakes - test support for grpcbridge_hosted_selftest: a FAKE bridge-engines worker (HTTP /capability + /bridges, the shape of
prf-bridge-engines/bridge_hosted.py) and a FAKE twin USART port that sends real LightState frames (the independent Python reference codec) and records what
the bridge sends down; td-4: a FAKE twin door's UART stream (FakeUartDoor, WebSocket). The fakes mirror the PROTOCOL only; the real worker logic is exercised by the selftest through the worker's own module, the real twin and
worker by its live half."""
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeBridgeWorker:
    """GET /capability, POST/GET/DELETE /bridges, GET /bridges/{id}/logs. bridges=False = a worker that does not host bridges; knows_door=False = a worker
    older than td-4, which ignores `twin_uart` (its answer does not repeat it) and reads the TCP port."""

    def __init__(self, bridges=True, knows_door=True, knows_tls=True):
        self.bridges_cap, self.knows_door, self.knows_tls, self.items, self.requests = bridges, knows_door, knows_tls, {}, []
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
                    cap = {'worker': 'bridge-engines', 'engines': {'java': {'available': True}, 'mvn': {'available': True}}}
                    if outer.bridges_cap:
                        cap['bridges'] = {'available': True, 'max': 6}
                    return self._json(200, cap)
                parts = self.path.split('?')[0].strip('/').split('/')
                if parts[0] == 'bridges' and len(parts) >= 2 and parts[1] in outer.items:
                    it = outer.items[parts[1]]
                    if len(parts) == 3 and parts[2] == 'logs':
                        return self._json(200, {'ok': True, 'id': parts[1], 'state': it['state'], 'lines': it['lines']})
                    return self._json(200, dict(it['view'], state=it['state'], output_tail=it['lines'][-5:], ok=True))
                self._json(404, {'ok': False, 'error': 'no bridge %s on this worker' % self.path})

            def do_POST(self):
                outer.requests.append(('POST', self.path))
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
                if self.path != '/bridges' or 'pom.xml' not in (body.get('files') or {}):
                    return self._json(400, {'ok': False, 'error': 'POST /bridges needs "files" with pom.xml'})
                bid = 'b%05d' % (len(outer.items) + 1)
                now = time.time()
                view = {'id': bid, 'session_id': body['session_id'], 'bridge_name': body['bridge_name'], 'twin_host': body['twin_host'], 'twin_port': body['twin_port'],
                        'grpc_target': body.get('grpc_target', ''), 'started': now, 'expires': now + body['ttl_s'], 'ttl_s': body['ttl_s'], 'build_fp': 'f' * 16,
                        'jar_sha256': 'a' * 64, 'build': {'cached': False, 'wall_s': 0.1}}
                line = '[bridge] source=twin-tcp %s:%s' % (body['twin_host'], body['twin_port'])
                if outer.knows_tls:   # a worker older than the bridge link ignores grpc_tls: its answer does not repeat it
                    view['grpc_tls'] = body.get('grpc_tls', '')
                if outer.knows_door:
                    view['twin_uart'] = body.get('twin_uart', '')
                    if view['twin_uart'].startswith('ws'):
                        line = '[bridge] source=twin-door %s' % view['twin_uart']
                outer.items[bid] = {'body': body, 'view': view, 'state': 'running', 'lines': [line]}
                self._json(200, dict(view, state='running', ok=True))

            def do_DELETE(self):
                outer.requests.append(('DELETE', self.path))
                bid = self.path.rsplit('/', 1)[-1]
                if outer.items.pop(bid, None) is None:
                    return self._json(404, {'ok': False, 'error': 'no bridge %s on this worker' % bid})
                self._json(200, {'ok': True, 'id': bid, 'stopped': True})

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.url = 'http://127.0.0.1:%d' % self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class FakeUsart:
    """A twin's raw USART tcp port: ONE client at a time. `script` = a list of connections; each is a list of frames (bytes) to send, after which the connection is
    closed (the last one is kept open until the client leaves). `received` = every byte the client sent down, per connection."""

    def __init__(self, script):
        self.script, self.received, self.connections, self.done, self.finished = script, [], 0, threading.Event(), threading.Event()
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(('127.0.0.1', 0))
        self.srv.listen(2)
        self.port = self.srv.getsockname()[1]
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        for i, frames in enumerate(self.script):
            try:
                conn, _ = self.srv.accept()
            except OSError:
                return
            self.connections += 1
            got = bytearray()
            conn.settimeout(0.3)
            try:
                for fr in frames:
                    conn.sendall(fr)
                    time.sleep(0.05)
                    try:
                        got += conn.recv(4096)
                    except socket.timeout:
                        pass
                if i == len(self.script) - 1:
                    self.done.set()
                    conn.settimeout(30)
                    try:
                        while True:
                            chunk = conn.recv(4096)
                            if not chunk:
                                break
                            got += chunk
                    except (socket.timeout, OSError):
                        pass
            except OSError:   # the client left before the script was sent (a bridge that refused to start)
                pass
            finally:
                self.received.append(bytes(got))
                conn.close()
                if i == len(self.script) - 1:
                    self.finished.set()

    def close(self):
        try:
            self.srv.close()
        except OSError:
            pass


class FakeUartDoor:
    """The UART stream of a worker's twin door (TWIN_DOOR_PLAN.md section 3a), protocol only: a WebSocket server on loopback at /sessions/<session>/uart. The
    first frame must be the text {"token": "..."} (anything else closes 4400, a wrong token 4403, another path 4404); after it every frame is binary serial
    bytes. `script` = a list of connections, each a list of frames (bytes) to send, after which the door closes THAT connection with 4410 (the twin closed the
    stream) - the last one is kept open until the client leaves. `received` = the bytes the client sent down, per accepted connection; `refused` = the close
    codes of the connections turned away. tls=(certfile, keyfile) serves wss:// (give host='localhost' to match a test certificate)."""

    def __init__(self, script, token, session='f00001', tls=None, host='127.0.0.1'):
        import ssl
        from websockets.sync.server import serve
        self.script, self.token, self.path = script, token, '/sessions/%s/uart' % session
        self.received, self.refused, self.connections, self.done, self.finished = [], [], 0, threading.Event(), threading.Event()
        self._lock = threading.Lock()
        ctx = None
        if tls:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(*tls)
        self.srv = serve(self._handle, '127.0.0.1', 0, ssl=ctx)
        self.port = self.srv.socket.getsockname()[1]
        self.url = '%s://%s:%d%s' % ('wss' if tls else 'ws', host, self.port, self.path)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def _turn_away(self, ws, code, why):
        self.refused.append(code)
        ws.close(code, why)

    def _handle(self, ws):
        if ws.request.path != self.path:
            return self._turn_away(ws, 4404, 'no such session')
        try:
            first = json.loads(ws.recv(timeout=5))
            tok = first.get('token')
        except Exception:  # noqa: BLE001 - a binary frame, not JSON, not an object, or nothing in time
            return self._turn_away(ws, 4400, 'the first frame must be {"token": "..."}')
        if tok != self.token:
            return self._turn_away(ws, 4403, 'the token is wrong')
        with self._lock:
            i = self.connections
            self.connections += 1
        frames, last, got = (self.script[i] if i < len(self.script) else []), i >= len(self.script) - 1, bytearray()
        try:
            for fr in frames:
                ws.send(fr)
                time.sleep(0.05)
                try:
                    m = ws.recv(timeout=0.3)
                    got += m if isinstance(m, bytes) else b''
                except TimeoutError:
                    pass
            if last:
                self.done.set()
                while True:
                    m = ws.recv(timeout=30)
                    got += m if isinstance(m, bytes) else b''
            else:
                ws.close(4410, 'the twin closed the stream')
        except Exception:  # noqa: BLE001 - the client left
            pass
        finally:
            self.received.append(bytes(got))
            if last:
                self.finished.set()

    def close(self):
        self.srv.shutdown()
