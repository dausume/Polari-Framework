"""
@module board.custom.twin_ctl_hub

sim-1: ONE backend connection to a twin session's control channel (the twin accepts one client at a time - polari_avr_twin --ctl), fanned out to any number of
subscribers. The reader thread splits the twin's JSON lines: replies to a command (`ack` / `refused` / `status`) go to the one caller waiting, everything
else (`pin` edges) is copied into a BOUNDED queue per subscriber - a slow subscriber loses its own oldest events (and is told how many), never the others'.

    hub = Hub(ctl_url, token); hub.connect(watch=['PD6']); reply = hub.request({'set': 'PD2', 'level': 0})
    sub = hub.subscribe(); sub.get(timeout) -> event dict | None

td-2 (TWIN_DOOR_PLAN.md §3, §5): the channel is a URL (board.custom.twin_transport picks it from the worker's /capability).
    tcp://host:port          the twin's own control port, newline-JSON on a socket (the dev compose, which publishes the port range)
    wss://name/sessions/<id>/ctl   the worker's twin door: a WebSocket over HTTPS through the isle agent, VERIFIED under polariApiServer.tls_policy
                             (the system trust the isle mounts, or POL_TLS_CA). One JSON line per text frame both ways; the first frame is {"token"};
                             the door pings, this client answers. ws:// is accepted for a loopback test only.
Either way the Hub sees lines: `_dial` returns a small line channel (send / lines / close) and nothing above it knows which wire it is.
"""
import collections
import json
import queue
import socket
import ssl
import threading

from board.custom import twin_transport as TT

QUEUE_MAX = 1000
RECENT_MAX = 500


class HubRefused(RuntimeError):
    pass


class Subscription:
    def __init__(self, hub):
        self.hub = hub
        self.q = queue.Queue(maxsize=QUEUE_MAX)
        self.lost = 0

    def put(self, ev):
        while True:
            try:
                self.q.put_nowait(ev)
                return
            except queue.Full:   # drop this subscriber's oldest, count it
                try:
                    self.q.get_nowait()
                    self.lost += 1
                except queue.Empty:
                    pass

    def get(self, timeout=1.0):
        if self.lost:   # tell the reader what it missed before the next event
            n, self.lost = self.lost, 0
            return {'t': 'lost', 'events': n}
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        self.hub.unsubscribe(self)


class _TcpLines:
    """Newline-JSON on a plain socket."""

    def __init__(self, sock):
        self.sock, self.ended = sock, ''
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(None)

    def send(self, text):
        self.sock.sendall((text + '\n').encode())

    def lines(self):
        buf = b''
        while True:
            chunk = self.sock.recv(4096)
            if not chunk:
                return
            buf += chunk
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                yield line

    def close(self):
        for op in ('shutdown', 'close'):   # shutdown wakes the reader thread blocked in recv(); a bare close() leaves the connection open until recv returns
            try:
                self.sock.shutdown(socket.SHUT_RDWR) if op == 'shutdown' else self.sock.close()
            except OSError:
                pass


class _WsLines:
    """One JSON line per WebSocket text frame (the worker's twin door). A frame that carries several lines, or a trailing newline, is accepted too."""

    def __init__(self, ws):
        self.ws, self.ended = ws, ''

    def send(self, text):
        try:
            self.ws.send(text)
        except Exception as e:  # noqa: BLE001 - websockets raises its own ConnectionClosed; the Hub speaks OSError
            raise OSError(str(e) or type(e).__name__)

    def lines(self):
        try:
            for frame in self.ws:
                if isinstance(frame, str):
                    frame = frame.encode()
                for line in frame.split(b'\n'):
                    if line.strip():
                        yield line
        except Exception:  # noqa: BLE001 - an abnormal close ends the stream like a normal one; the reason is read below
            pass
        proto = getattr(self.ws, 'protocol', None)   # websockets 13 keeps the close frame on the sans-IO protocol object
        code, reason = getattr(proto, 'close_code', None), getattr(proto, 'close_reason', None)
        if code not in (None, 1000, 1001):   # the door's codes (TWIN_DOOR_PLAN §3a): 4403 wrong token, 4404 unknown session, 4410 ended, 4409 replaced, 4502 twin unreachable
            self.ended = 'the twin door closed the connection (code %s%s)' % (code, ': %s' % reason if reason else '')

    def close(self):
        try:
            self.ws.close()
        except Exception:  # noqa: BLE001
            pass


def _tls_context(url):
    """The VERIFYING context for a wss:// door under the backend's one TLS policy (system trust, POL_TLS_CA, or the announced POL_TLS_INSECURE bypass)."""
    try:
        from polariApiServer import tls_policy
        ctx = tls_policy.context(url)
    except ImportError:
        ctx = None
    return ctx or ssl.create_default_context()


def open_channel(url, timeout=5.0):
    """-> a line channel for `url` (see the module docstring). Raises OSError / TransportRefused / RuntimeError with words."""
    scheme, host, port, _ = TT.split(url)
    if scheme == 'tcp':
        return _TcpLines(socket.create_connection((host, port), timeout=timeout))
    try:
        from websockets.sync.client import connect
    except ImportError:
        raise RuntimeError('this server has no `websockets` package, which a twin door (%s) needs' % url)
    try:
        return _WsLines(connect(url, ssl=_tls_context(url) if scheme == 'wss' else None, open_timeout=timeout, close_timeout=2))
    except (OSError, RuntimeError):
        raise
    except Exception as e:  # noqa: BLE001 - a refused upgrade (the agent answers 404/502 when the door is down) is a websockets exception
        raise OSError(str(e) or type(e).__name__)


class Hub:
    def __init__(self, url, token):
        self.url, self.token = url, token
        self.chan = None
        self.dead = False
        self.dead_why = ''
        self._subs = []
        self._lock = threading.Lock()
        self._rlock = threading.Lock()
        self._replies = queue.Queue()
        self.recent = collections.deque(maxlen=RECENT_MAX)
        self.seq = 0

    # ---- connection
    def _dial(self, timeout):
        try:
            from polariApiServer import outbound
        except ImportError:
            return open_channel(self.url, timeout)
        with outbound.wrap('engine', 'board', 'twin-ctl'):
            return open_channel(self.url, timeout)

    def connect(self, watch=(), timeout=5.0):
        try:
            self.chan = self._dial(timeout)
        except (OSError, RuntimeError) as e:   # TransportRefused is a RuntimeError: a malformed URL is said in its own words
            raise HubRefused('the twin control channel %s is unreachable: %s' % (self.url, e))
        threading.Thread(target=self._read, daemon=True, name='twin-hub').start()
        first = self.request({'token': self.token}, timeout=timeout)
        if first.get('t') != 'ack':
            why = first.get('why', first)
            words = 'the twin control channel %s closed before the token was accepted: %s' % (self.url, why) if self.dead else 'the twin refused the token: %s' % why
            self.close(words)
            raise HubRefused(words)
        if watch:
            r = self.request({'watch': list(watch)}, timeout=timeout)
            if r.get('t') != 'ack':
                self.close('watch refused: %s' % r.get('why', r))
                raise HubRefused('the twin refused the watch list: %s' % r.get('why', r))
        return self

    def _read(self):
        chan = self.chan
        try:
            for line in chan.lines():
                try:
                    msg = json.loads(line.decode('utf-8', 'replace'))
                except ValueError:
                    continue
                if not isinstance(msg, dict):
                    continue
                if msg.get('t') in ('ack', 'refused', 'status'):
                    self._replies.put(msg)
                else:
                    self._publish(msg)
        except OSError:
            pass
        self.close(chan.ended or 'the control connection ended')

    def _publish(self, msg):
        with self._lock:
            self.seq += 1
            msg = dict(msg, seq=self.seq)
            self.recent.append(msg)
            subs = list(self._subs)
        for s in subs:
            s.put(msg)

    # ---- commands
    def request(self, cmd, timeout=3.0):
        """Send one command line and return the twin's reply ({'t': 'ack'|'refused'|'status', ...}); a timeout is a refusal in words."""
        with self._rlock:
            if self.dead or self.chan is None:
                return {'t': 'refused', 'why': 'the control connection is closed (%s)' % (self.dead_why or 'not connected')}
            while not self._replies.empty():
                self._replies.get_nowait()
            try:
                self.chan.send(json.dumps(cmd))
                return self._replies.get(timeout=timeout)
            except queue.Empty:
                return {'t': 'refused', 'why': 'the twin did not answer within %gs' % timeout}
            except OSError as e:
                return {'t': 'refused', 'why': 'the control connection failed: %s' % e}

    # ---- fan-out
    def subscribe(self, replay=0):
        s = Subscription(self)
        with self._lock:
            if replay:
                for ev in list(self.recent)[-int(replay):]:
                    s.put(ev)
            self._subs.append(s)
            if self.dead:
                s.put({'t': 'closed', 'why': self.dead_why})
        return s

    def unsubscribe(self, sub):
        with self._lock:
            if sub in self._subs:
                self._subs.remove(sub)

    def close(self, why='closed'):
        with self._lock:
            if self.dead:
                return
            self.dead, self.dead_why = True, why
            subs = list(self._subs)
        for s in subs:
            s.put({'t': 'closed', 'why': why})
        if self.chan is not None:
            self.chan.close()
        self._replies.put({'t': 'refused', 'why': why})
