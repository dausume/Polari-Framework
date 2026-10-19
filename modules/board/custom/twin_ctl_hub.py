"""
@module board.custom.twin_ctl_hub

sim-1: ONE backend connection to a twin session's control port (the twin accepts one client at a time - polari_avr_twin --ctl), fanned out to any number of
subscribers. The reader thread splits the twin's JSON lines: replies to a command (`ack` / `refused` / `status`) go to the one caller waiting, everything
else (`pin` edges) is copied into a BOUNDED queue per subscriber - a slow subscriber loses its own oldest events (and is told how many), never the others'.

    hub = Hub(host, ctl_port, token); hub.connect(watch=['PD6']); reply = hub.request({'set': 'PD2', 'level': 0})
    sub = hub.subscribe(); sub.get(timeout) -> event dict | None
"""
import collections
import json
import queue
import socket
import threading
import time

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


class Hub:
    def __init__(self, host, port, token):
        self.host, self.port, self.token = host, int(port), token
        self.sock = None
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
            with outbound.wrap('engine', 'board', 'twin-ctl'):
                return socket.create_connection((self.host, self.port), timeout=timeout)
        except ImportError:
            return socket.create_connection((self.host, self.port), timeout=timeout)

    def connect(self, watch=(), timeout=5.0):
        try:
            self.sock = self._dial(timeout)
        except OSError as e:
            raise HubRefused('the twin control port %s:%d is unreachable: %s' % (self.host, self.port, e))
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.settimeout(None)
        threading.Thread(target=self._read, daemon=True, name='twin-hub-%d' % self.port).start()
        first = self.request({'token': self.token}, timeout=timeout)
        if first.get('t') != 'ack':
            self.close('the twin refused the token: %s' % first.get('why', first))
            raise HubRefused('the twin refused the token: %s' % first.get('why', first))
        if watch:
            r = self.request({'watch': list(watch)}, timeout=timeout)
            if r.get('t') != 'ack':
                self.close('watch refused: %s' % r.get('why', r))
                raise HubRefused('the twin refused the watch list: %s' % r.get('why', r))
        return self

    def _read(self):
        buf = b''
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    try:
                        msg = json.loads(line.decode('utf-8', 'replace'))
                    except ValueError:
                        continue
                    if msg.get('t') in ('ack', 'refused', 'status'):
                        self._replies.put(msg)
                    else:
                        self._publish(msg)
        except OSError:
            pass
        self.close('the control connection ended')

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
            if self.dead or self.sock is None:
                return {'t': 'refused', 'why': 'the control connection is closed (%s)' % (self.dead_why or 'not connected')}
            while not self._replies.empty():
                self._replies.get_nowait()
            try:
                self.sock.sendall((json.dumps(cmd) + '\n').encode())
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
        for op in ('shutdown', 'close'):   # shutdown wakes the reader thread blocked in recv(); a bare close() leaves the connection open until recv returns
            try:
                if self.sock:
                    self.sock.shutdown(socket.SHUT_RDWR) if op == 'shutdown' else self.sock.close()
            except OSError:
                pass
        self._replies.put({'t': 'refused', 'why': why})
