"""
@module instruments.custom.emulator

osc-2 (OSCILLOSCOPE_PLAN.md §3c): a 4-channel oscilloscope EMULATOR — a SCPI server over a raw TCP socket (the DHO's port 5555 convention; any
free port in a selftest) that answers the DHO800 command subset scopehal's driver uses (cited there), with 12-bit WORD data and a preamble the
Agilent-lineage formula reads back exactly. It stands in for the real instrument so the client, the canonical record and the chart are proven
before one is on the bench — and later (osc-5) it is an isle app other nodes reach like a real scope.

What is emulated (profile `dho804`, numbers from the datasheet table in instruments_seed):
  * 4 analog channels; sample rate and memory depth fall with the number of channels switched on (1.25 GSa/s / 625 MSa/s / 312.5 MSa/s and
    25 / 10 / 5 Mpts for 1 / 2 / 4 channels — 3 channels take the 4-channel figures, the datasheet does not list 3);
  * the acquisition: `points = memory depth`, `x_increment = 1 / sample rate`, `x_origin = -5 divisions` (the datasheet's pre-trigger delay
    range p.8) unless the timebase offset moves it; the sample rate is the channel-count maximum capped by depth / (10 div × s/div);
  * the vertical: 12 bits over ±4 divisions (datasheet p.7 "dynamic range ±4 div"), so `y_increment = 8 × V/div / 4096`, `y_reference = 2048`
    (mid-scale) and `y_origin = offset / y_increment` — OUR convention; the DHO's own reference/origin numbers are unverified and the client
    never assumes them: it reads the preamble;
  * `:WAV:DATA?` pages: `WAV:STAR` / `WAV:STOP` are 1-based inclusive and a page is at most 250,000 points (scopehal's chunk; the guide's own
    figure unread) — asking for more answers the first 250,000 of the window, as a paging client expects;
  * the signal SOURCES per channel (custom/sources.py): synth (sine / square / ramp / dc / noise), replay (a stored capture's volts), and
    osc-4's device feed; a source is set through the control API, never through SCPI (a real scope has no such command).
  * *IDN? HONESTY (D-osc-1, recommended default): `POLARI,DHO804-EMU,<session>,osc-2`; `strict_idn=True` answers the Rigol four-field form
    with EMU markers in the serial so a third-party tool keyed on the manufacturer field connects, yet nothing claims to be a real unit.
  * REFUSAL REPLAY: `refuse_wav_data=True` makes `:WAV:DATA?` answer "The instruction is not supported!" (the forum-reported DHO924S reply),
    so the client's refusal path is exercised; an unknown header queues IEEE 488.2 error -113,"Undefined header" for `:SYST:ERR?` and a
    query that is unknown answers that refusal text so a reader sees words, not a hang.

    emu = Emulator(profile='dho804', port=0); emu.start(); ... emu.port ... emu.stop()
    emu.set_source(channel, spec)   emu.state (the ScopeState, for a selftest to inspect)
Stdlib + numpy only.
"""
import socket
import socketserver
import threading
import uuid

import numpy as np

from instruments.custom import scpi
from instruments.custom import lineage as L
from instruments.custom import sources as SRC

PROFILES = {
    'dho804': {'vendor': 'RIGOL TECHNOLOGIES', 'model': 'DHO804', 'channels': 4, 'bits': 12,
               'max_srate': {1: 1.25e9, 2: 625e6, 3: 312.5e6, 4: 312.5e6}, 'max_depth': {1: 25e6, 2: 10e6, 3: 5e6, 4: 5e6},
               'page_points': 250000, 'default_depth': 10000, 'divisions_h': 10, 'divisions_v': 8, 'pretrigger_div': -5,
               'scale_min': 500e-6, 'scale_max': 10.0, 'tb_min': 5e-9, 'tb_max': 500.0, 'bw_limits': ('OFF', '20M'),
               'basis': 'DHO800 Data Sheet DSA36106-1110 pp.6-9; command set scopehal RigolOscilloscope.cpp (BSD-3)'},
}
REFUSAL_UNSUPPORTED = 'The instruction is not supported!'
EMU_VERSION = 'osc-2'


class ScopeState:
    def __init__(self, profile):
        p = PROFILES[profile]
        self.profile = profile
        self.p = p
        self.session = uuid.uuid4().hex[:8]
        self.channels = {n: {'display': n == 1, 'scale': 1.0, 'offset': 0.0, 'coupling': 'DC', 'bwl': 'OFF', 'probe': 1.0, 'vernier': 'OFF'}
                         for n in range(1, p['channels'] + 1)}
        self.tb_scale = 1e-3
        self.tb_offset = 0.0
        self.mdepth = p['default_depth']      # 'AUTO' on a real scope; the emulator keeps a number
        self.acq_type = 'NORM'
        self.trigger = {'mode': 'EDGE', 'source': 'CHAN1', 'level': 0.0, 'slope': 'POS'}
        self.run = 'RUN'
        self.wav = {'source': 'CHAN1', 'mode': 'NORM', 'format': 'WORD', 'start': 1, 'stop': p['default_depth']}
        self.sources = {n: SRC.default_source(n) for n in self.channels}
        self.errors = []
        self.acquired = {}      # channel -> raw int array of the last acquisition
        self.acq_fields = {}    # channel -> the preamble fields of that acquisition
        self.acquisitions = 0

    # ---------------------------------------------------------------- derived numbers
    def enabled(self):
        return [n for n, c in self.channels.items() if c['display']]

    def srate(self):
        n = max(1, len(self.enabled()))
        cap = self.p['max_srate'][n]
        window = self.p['divisions_h'] * self.tb_scale
        return min(cap, self.mdepth / window)

    def depth_cap(self):
        return self.p['max_depth'][max(1, len(self.enabled()))]

    def x_origin(self):
        return self.p['pretrigger_div'] * self.tb_scale + self.tb_offset

    def fields(self, channel):
        c = self.channels[channel]
        yinc = self.p['divisions_v'] * c['scale'] / (1 << self.p['bits'])
        return {'format': self.wav['format'], 'type': {'NORM': 'NORMAL', 'MAX': 'MAXIMUM', 'RAW': 'RAW'}[self.wav['mode']], 'points': int(self.mdepth), 'count': 1,
                'x_increment': 1.0 / self.srate(), 'x_origin': self.x_origin(), 'x_reference': 0.0,
                'y_increment': yinc, 'y_origin': c['offset'] / yinc, 'y_reference': float(1 << (self.p['bits'] - 1)), 'lineage': 'agilent'}

    def acquire(self):
        """One acquisition of every enabled channel at the current settings (what RUN/SINGLE/TFORce produce)."""
        self.acquisitions += 1
        self.acquired, self.acq_fields = {}, {}
        n = int(self.mdepth)
        for ch in self.enabled():
            f = self.fields(ch)
            t = L.times(n, f)
            v = SRC.evaluate(self.sources[ch], t, self.acquisitions)
            raw = np.clip(L.to_raw(v, f), 0, (1 << self.p['bits']) - 1)
            self.acquired[ch], self.acq_fields[ch] = raw, f

    def invalidate(self):
        """A setting that changes what an acquisition would be (channels on, scale, offset, timebase, depth, a source) drops the last one, so the next
        read acquires afresh at the new settings - the emulator's consistency rule; a real scope in STOP keeps stale data, and the client's
        capture() therefore always takes a fresh :SINGle before reading."""
        self.acquired, self.acq_fields = {}, {}

    def window(self):
        start, stop = max(1, int(self.wav['start'])), int(self.wav['stop'])
        stop = min(stop, int(self.mdepth), start + self.p['page_points'] - 1)
        return start, stop


def _chan(arg):
    a = arg.upper().replace('CHANNEL', 'CHAN')
    if a.startswith('CHAN') and a[4:].isdigit():
        return int(a[4:])
    return None


def _num(arg):
    s = arg.upper()
    mult = {'K': 1e3, 'M': 1e6, 'G': 1e9}
    if s and s[-1] in mult:
        return float(s[:-1]) * mult[s[-1]]
    return float(s)


class Emulator:
    def __init__(self, profile='dho804', host='127.0.0.1', port=0, strict_idn=False, refuse_wav_data=False):
        if profile not in PROFILES:
            raise ValueError('no emulator profile %r (have %s)' % (profile, ', '.join(PROFILES)))
        self.state = ScopeState(profile)
        self.host, self.port = host, port
        self.strict_idn, self.refuse_wav_data = strict_idn, refuse_wav_data
        self.lock = threading.Lock()
        self._server = self._thread = None

    # ---------------------------------------------------------------- lifecycle
    def start(self):
        emu = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                while True:
                    line = self.rfile.readline()
                    if not line:
                        return
                    for unit in line.decode('utf-8', 'replace').strip().split(';'):
                        if not unit.strip():
                            continue
                        reply = emu.handle(unit)
                        if reply is not None:
                            self.wfile.write(reply if isinstance(reply, bytes) else (reply + '\n').encode())
                            self.wfile.flush()

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self._server = Server((self.host, self.port), Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True, name='scope-emulator-%s' % self.state.session)
        self._thread.start()
        return self

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    def set_source(self, channel, spec):
        with self.lock:
            self.state.sources[int(channel)] = SRC.validate(spec)
            self.state.invalidate()

    def idn(self):
        s = self.state
        if self.strict_idn:
            return scpi.idn(s.p['vendor'], s.p['model'], '%sEMU%s' % (s.p['model'][:4], s.session.upper()), 'EMU-' + EMU_VERSION)
        return scpi.idn('POLARI', s.p['model'] + '-EMU', s.session, EMU_VERSION)

    # ---------------------------------------------------------------- the command tree
    def handle(self, unit):
        """One command unit -> reply text (without newline), bytes (a block, newline included) or None (no reply)."""
        try:
            cmd = scpi.parse_message(unit)[0]
        except (ValueError, IndexError):
            self.state.errors.append('-100,"Command error"')
            return None
        with self.lock:
            try:
                return self._dispatch(cmd)
            except _Unsupported:
                self.state.errors.append('-113,"Undefined header"')
                return REFUSAL_UNSUPPORTED if cmd.query else None
            except (ValueError, KeyError, IndexError):
                self.state.errors.append('-224,"Illegal parameter value"')
                return REFUSAL_UNSUPPORTED if cmd.query else None

    def _dispatch(self, cmd):
        s, parts, q, args = self.state, cmd.parts, cmd.query, cmd.args
        M = scpi.matches
        if M(parts, ('*IDN',)) and q:
            return self.idn()
        if M(parts, ('*RST',)):
            self.state = ScopeState(s.profile)
            return None
        if M(parts, ('*OPC',)):
            return '1' if q else None
        if M(parts, ('*CLS',)):
            s.errors.clear()
            return None
        if M(parts, ('SYSTem', 'ERRor')) and q:
            return s.errors.pop(0) if s.errors else '0,"No error"'
        if M(parts, ('RUN',)):
            s.run = 'RUN'
            s.acquire()
            return None
        if M(parts, ('STOP',)):
            s.run = 'STOP'
            return None
        if M(parts, ('SINGle',)) or M(parts, ('TFORce',)):
            s.acquire()
            s.run = 'STOP'
            return None
        if M(parts, ('TRIGger', 'STATus')) and q:
            return s.run
        # channels
        if len(parts) == 2 and parts[0].upper().startswith('CHAN'):
            n = _chan(parts[0])
            if n not in s.channels:
                raise _Unsupported()
            c = s.channels[n]
            sub = parts[1]
            if scpi.long_or_short_match(sub, 'DISPlay'):
                if q:
                    return '1' if c['display'] else '0'
                c['display'] = args[0].upper() in ('1', 'ON')
                s.invalidate()
                return None
            if scpi.long_or_short_match(sub, 'SCALe'):
                if q:
                    return '%.6e' % c['scale']
                v = _num(args[0])
                c['scale'] = min(max(v, s.p['scale_min']), s.p['scale_max'])
                s.invalidate()
                return None
            if scpi.long_or_short_match(sub, 'OFFSet'):
                if q:
                    return '%.6e' % c['offset']
                c['offset'] = _num(args[0])
                s.invalidate()
                return None
            if scpi.long_or_short_match(sub, 'COUPling'):
                if q:
                    return c['coupling']
                c['coupling'] = {'AC': 'AC', 'DC': 'DC', 'GND': 'GND'}[args[0].upper()]
                return None
            if scpi.long_or_short_match(sub, 'BWLimit'):
                if q:
                    return c['bwl']
                v = args[0].upper()
                if v not in s.p['bw_limits']:
                    raise ValueError(v)
                c['bwl'] = v
                return None
            if scpi.long_or_short_match(sub, 'PROBe'):
                if q:
                    return '%g' % c['probe']
                c['probe'] = _num(args[0])
                return None
            if scpi.long_or_short_match(sub, 'VERNier'):
                if q:
                    return c['vernier']
                c['vernier'] = 'ON' if args[0].upper() in ('1', 'ON') else 'OFF'
                return None
            raise _Unsupported()
        # timebase
        if parts[0].upper() in ('TIM', 'TIMEBASE'):
            sub = parts[-1]
            if scpi.long_or_short_match(sub, 'SCALe'):
                if q:
                    return '%.6e' % s.tb_scale
                s.tb_scale = min(max(_num(args[0]), s.p['tb_min']), s.p['tb_max'])
                s.invalidate()
                return None
            if scpi.long_or_short_match(sub, 'OFFSet'):
                if q:
                    return '%.6e' % s.tb_offset
                s.tb_offset = _num(args[0])
                s.invalidate()
                return None
            if scpi.long_or_short_match(sub, 'VERNier'):
                return 'OFF' if q else None
            raise _Unsupported()
        # acquisition
        if M(parts, ('ACQuire', 'SRATe')) and q:
            return '%.6e' % s.srate()
        if M(parts, ('ACQuire', 'MDEPth')):
            if q:
                return '%d' % int(s.mdepth)
            v = args[0].upper()
            depth = s.p['default_depth'] if v == 'AUTO' else int(_num(v))
            s.mdepth = int(min(depth, s.depth_cap()))
            s.wav['start'], s.wav['stop'] = 1, s.mdepth
            s.invalidate()
            return None
        if M(parts, ('ACQuire', 'TYPE')):
            if q:
                return s.acq_type
            s.acq_type = args[0].upper()[:4]
            return None
        # trigger
        if M(parts, ('TRIGger', 'MODE')):
            if q:
                return s.trigger['mode']
            s.trigger['mode'] = args[0].upper()
            return None
        if M(parts, ('TRIGger', 'EDGE', 'SOURce')):
            if q:
                return s.trigger['source']
            if _chan(args[0]) not in s.channels:
                raise ValueError(args[0])
            s.trigger['source'] = 'CHAN%d' % _chan(args[0])
            return None
        if M(parts, ('TRIGger', 'EDGE', 'LEVel')):
            if q:
                return '%.6e' % s.trigger['level']
            s.trigger['level'] = _num(args[0])
            return None
        if M(parts, ('TRIGger', 'EDGE', 'SLOPe')):
            if q:
                return s.trigger['slope']
            s.trigger['slope'] = {'POS': 'POS', 'POSITIVE': 'POS', 'NEG': 'NEG', 'NEGATIVE': 'NEG', 'RFAL': 'RFAL'}[args[0].upper()]
            return None
        # waveform
        if parts[0].upper() in ('WAV', 'WAVEFORM') and len(parts) == 2:
            sub = parts[1]
            if scpi.long_or_short_match(sub, 'SOURce'):
                if q:
                    return s.wav['source']
                if _chan(args[0]) not in s.channels:
                    raise ValueError(args[0])
                s.wav['source'] = 'CHAN%d' % _chan(args[0])
                return None
            if scpi.long_or_short_match(sub, 'MODE'):
                if q:
                    return s.wav['mode']
                s.wav['mode'] = {'NORM': 'NORM', 'NORMAL': 'NORM', 'MAX': 'MAX', 'MAXIMUM': 'MAX', 'RAW': 'RAW'}[args[0].upper()]
                s.wav['start'], s.wav['stop'] = 1, int(s.mdepth)     # scopehal: toggling the mode resets the point window
                return None
            if scpi.long_or_short_match(sub, 'FORMat'):
                if q:
                    return s.wav['format']
                s.wav['format'] = {'WORD': 'WORD', 'BYTE': 'BYTE', 'ASC': 'ASCII', 'ASCII': 'ASCII'}[args[0].upper()]
                return None
            if scpi.long_or_short_match(sub, 'STARt'):
                if q:
                    return '%d' % s.wav['start']
                s.wav['start'] = int(_num(args[0]))
                return None
            if scpi.long_or_short_match(sub, 'STOP'):
                if q:
                    return '%d' % s.wav['stop']
                s.wav['stop'] = int(_num(args[0]))
                return None
            if scpi.long_or_short_match(sub, 'POINts'):
                if q:
                    a, b = s.window()
                    return '%d' % (b - a + 1)
                s.wav['stop'] = s.wav['start'] + int(_num(args[0])) - 1
                return None
            if scpi.long_or_short_match(sub, 'PREamble') and q:
                return self._preamble()
            if scpi.long_or_short_match(sub, 'DATA') and q:
                return self._data()
            for name, key in (('XINCrement', 'x_increment'), ('XORigin', 'x_origin'), ('XREFerence', 'x_reference'),
                              ('YINCrement', 'y_increment'), ('YORigin', 'y_origin'), ('YREFerence', 'y_reference')):
                if scpi.long_or_short_match(sub, name) and q:
                    return '%.12e' % self._current_fields()[key]
            raise _Unsupported()
        raise _Unsupported()

    def _current_fields(self):
        s = self.state
        ch = _chan(s.wav['source'])
        if ch not in s.acquired:
            s.acquire()
        f = dict(s.acq_fields.get(ch) or s.fields(ch))
        a, b = s.window()
        f['points'] = b - a + 1
        f['format'] = s.wav['format']
        f['x_origin'] = f['x_origin'] + (a - 1) * f['x_increment']     # a page's first sample is its own origin (scopehal reads it so)
        return f

    def _preamble(self):
        return L.format_agilent_preamble(self._current_fields())

    def _data(self):
        s = self.state
        if self.refuse_wav_data:
            return REFUSAL_UNSUPPORTED
        ch = _chan(s.wav['source'])
        if ch not in s.acquired:
            s.acquire()
        if ch not in s.acquired:
            return REFUSAL_UNSUPPORTED          # the channel is off: a real scope has no data for it
        a, b = s.window()
        raw = s.acquired[ch][a - 1:b]
        if s.wav['format'] == 'WORD':
            payload = raw.astype('<u2').tobytes()
        elif s.wav['format'] == 'BYTE':
            payload = (raw >> (s.p['bits'] - 8)).astype(np.uint8).tobytes()
        else:
            f = s.acq_fields[ch]
            payload = ','.join('%.6e' % v for v in L.volts(raw, f)).encode()
        return scpi.block_encode(payload) + b'\n'


class _Unsupported(Exception):
    pass


def free_port():
    with socket.socket() as sk:
        sk.bind(('127.0.0.1', 0))
        return sk.getsockname()[1]
