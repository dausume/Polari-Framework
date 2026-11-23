"""board.custom.twin_session_fakes_c3 - test support for c3g-3: a FAKE C3 twin control port, in the words of prf-esp-engines/polari_c3_twin.py, so the backend
half of a C3 session is proven with no worker, no QEMU and no docker. It mirrors the PROTOCOL only (pads GPIO<n>, "z", `ns` and no `cycle`, the refusals);
the real twin and worker are proven by prf-esp-engines/test_c3_twin.py and test_c3_sessions.py on the pin-model QEMU.

    FakeWorker(kind='c3', twin=FakeC3Twin)   (twin_session_fakes) is the esp-engines worker of this twin

Its "firmware" is the light: a falling edge on the button pad flips the LED pad, and a board wire carries the LED to the sense pad."""
from board.custom.twin_session_fakes import FakeTwin

PADS = tuple(range(22))
LED, SENSE, BUTTON = 0, 1, 3


def _name(pad):
    return 'GPIO%d' % pad


class FakeC3Twin(FakeTwin):
    def __init__(self, token, body=None):
        self.body = body or {}
        self.wires = [tuple(int(n) for n in w.split('-')) for w in (self.body.get('wires') or '').split(',') if w]
        self.pads, self.ns = {p: 'z' for p in PADS}, 0
        self.pads[LED] = '0'
        for a, b in self.wires:
            self.pads[b] = self.pads[a]
        super().__init__(token)

    def _pad(self, name):
        s = str(name)
        if s.startswith('GPIO') and s[4:].isdigit() and int(s[4:]) in self.pads:
            return int(s[4:])
        self._send({'t': 'refused', 'why': '%s is not a pad of this layout (pads: %s)' % (s, ' '.join(_name(p) for p in PADS))})
        return None

    def _level(self, pad, lv):
        """One pad takes a level; a change of a watched pad goes out as the real twin's pin event."""
        if self.pads[pad] == lv:
            return
        self.pads[pad] = lv
        self.ns += 1000000
        if _name(pad) in self.watch:
            self._send({'t': 'pin', 'pin': _name(pad), 'level': None if lv == 'z' else int(lv), 'z': lv == 'z', 'ns': self.ns})

    def _command(self, m):
        if 'set' in m:
            lv = {0: '0', 1: '1', 'z': 'z'}.get(m.get('level') if not isinstance(m.get('level'), bool) else int(m['level']))
            pad = self._pad(m['set'])
            if pad is not None and lv is None:
                self._send({'t': 'refused', 'why': '"set" needs "level": 0 or 1, or "z" to let the pad go'})
            elif pad is not None:
                fell = pad == BUTTON and lv == '0' and self.pads[pad] != '0'
                self._send({'t': 'ack', 'of': 'set', 'pin': _name(pad), 'level': None if lv == 'z' else int(lv), 'z': lv == 'z'})
                self._level(pad, lv)
                if fell:
                    led = '0' if self.pads[LED] == '1' else '1'
                    self._level(LED, led)
                    for a, b in self.wires:
                        if a == LED:
                            self._level(b, led)
        elif 'watch' in m:
            if not isinstance(m['watch'], list):
                self._send({'t': 'refused', 'why': '"watch" is a list of pad names'})
            elif all(self._pad(n) is not None for n in m['watch']):
                self.watch = {str(n) for n in m['watch']}
                self._send({'t': 'ack', 'of': 'watch', 'watch': sorted(self.watch)})
        elif 'run' in m:
            if m['run'] is True:
                self._send({'t': 'ack', 'of': 'run', 'run': True})
            else:
                self._send({'t': 'refused', 'why': 'the C3 twin has no pause yet: QEMU keeps its own clock (stop the session instead)'})
        elif 'reset' in m:
            self._send({'t': 'refused', 'why': 'the C3 twin has no reset yet (stop the session and start one for a fresh boot)'})
        elif 'adc' in m:
            self._send({'t': 'refused', 'why': 'the C3 pin model holds levels only: it has no ADC yet'})
        elif 'status' in m:
            self._send({'t': 'status', 'chip': 'esp32c3', 'ns': self.ns, 'running': True, 'attached': True,
                        'pads': {_name(p): self.pads[p] for p in PADS}, 'watch': sorted(self.watch), 'dropped': 0})
        else:
            self._send({'t': 'refused', 'why': 'no command in that line (set, watch, status, run)'})
